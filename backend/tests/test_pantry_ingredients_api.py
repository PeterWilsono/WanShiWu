"""食材批次 CRUD、FEFO、临期、异常与用户隔离测试。"""

from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.pantry.models import Ingredient
from app.modules.pantry.schemas import ConsumeRequest
from app.modules.pantry.service import consume_ingredient

PASSWORD = "correct-pantry-825"


def auth_headers(client: TestClient, username: str = "pantry-api") -> tuple[dict[str, str], dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def create_ingredient(
    client: TestClient,
    headers: dict[str, str],
    name: str = "鸡蛋",
    quantity: str = "2",
    unit: str = "个",
    **overrides: object,
) -> dict:
    payload = {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "storage": "fridge",
        **overrides,
    }
    response = client.post("/api/v1/ingredients", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_ingredient_create_list_filter_and_validation(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    created = create_ingredient(client, headers, name="牛奶", quantity="1.25", unit="升")
    create_ingredient(client, headers, name="鸡蛋", storage="room")

    assert created["quantity"] == "1.25" and created["status"] == "active"
    response = client.get(
        "/api/v1/ingredients", headers=headers, params={"storage": "fridge", "name": "牛奶"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["id"] == created["id"]

    invalid = client.post(
        "/api/v1/ingredients",
        headers=headers,
        json={"name": "错误", "quantity": "-1", "unit": "个", "storage": "room"},
    )
    assert invalid.status_code == 422 and invalid.json()["code"] == 40001
    assert client.get("/api/v1/ingredients").status_code == 401


def test_ingredient_patch_delete_and_user_isolation(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    other_headers, _ = auth_headers(client, "pantry-other")
    created = create_ingredient(client, headers)

    other_detail = client.get(f"/api/v1/ingredients/{created['id']}", headers=other_headers)
    assert other_detail.status_code == 404
    updated = client.patch(
        f"/api/v1/ingredients/{created['id']}", headers=headers, json={"quantity": 0}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "used_up"
    assert updated.json()["data"]["quantity"] == "0.00"
    assert client.delete(f"/api/v1/ingredients/{created['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/ingredients/{created['id']}", headers=headers).status_code == 404


def test_fefo_consumes_early_expiry_first_and_marks_used_up(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    no_expiry = create_ingredient(client, headers, quantity="4", expire_on=None)
    later = create_ingredient(client, headers, quantity="2", expire_on="2026-11-10")
    earlier = create_ingredient(client, headers, quantity="3", expire_on="2026-11-01")

    response = client.post(
        "/api/v1/ingredients/consume",
        headers=headers,
        json={"name": "鸡蛋", "quantity": "6", "unit": "个"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert Decimal(data["consumed_quantity"]) == Decimal("6")
    assert Decimal(data["remaining_stock"]) == Decimal("3")
    assert [batch["ingredient_id"] for batch in data["batches"]] == [
        earlier["id"],
        later["id"],
        no_expiry["id"],
    ]
    assert [batch["consumed_quantity"] for batch in data["batches"]] == ["3.00", "2.00", "1.00"]
    assert data["batches"][0]["status"] == "used_up"
    assert data["batches"][2]["remaining_quantity"] == "3.00"


def test_consume_shortage_does_not_partially_deduct_and_reports_unit(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    pieces = create_ingredient(client, headers, quantity="2", unit="个")
    create_ingredient(client, headers, quantity="500", unit="克")

    response = client.post(
        "/api/v1/ingredients/consume",
        headers=headers,
        json={"name": "鸡蛋", "quantity": "3", "unit": "个"},
    )
    assert response.status_code == 422 and response.json()["code"] == 42201
    assert response.json()["data"]["shortage"] == "1.00"
    detail = client.get(f"/api/v1/ingredients/{pieces['id']}", headers=headers).json()["data"]
    assert detail["quantity"] == "2.00" and detail["status"] == "active"

    mismatch = client.post(
        "/api/v1/ingredients/consume",
        headers=headers,
        json={"name": "鸡蛋", "quantity": "1", "unit": "包"},
    )
    assert mismatch.status_code == 422
    assert "个、克" in mismatch.json()["message"] or "克、个" in mismatch.json()["message"]


def test_consume_does_not_use_other_users_stock(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    other_headers, _ = auth_headers(client, "stock-owner")
    create_ingredient(client, other_headers, quantity="10")

    response = client.post(
        "/api/v1/ingredients/consume",
        headers=headers,
        json={"name": "鸡蛋", "quantity": "1", "unit": "个"},
    )
    assert response.status_code == 422
    assert Decimal(response.json()["data"]["available"]) == Decimal("0")


def test_expiring_separates_expired_and_uses_days_setting(client: TestClient) -> None:
    headers, user = auth_headers(client)
    today = now_utc().astimezone(ZoneInfo(user["timezone"])).date()
    create_ingredient(client, headers, name="昨天过期", expire_on=str(today - timedelta(days=1)))
    create_ingredient(client, headers, name="今天到期", expire_on=str(today))
    create_ingredient(client, headers, name="三天内", expire_on=str(today + timedelta(days=3)))
    create_ingredient(client, headers, name="四天以后", expire_on=str(today + timedelta(days=4)))
    create_ingredient(client, headers, name="长期保存", expire_on=None)

    response = client.get("/api/v1/ingredients/expiring", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["days"] == 3 and data["today"] == str(today)
    assert [item["name"] for item in data["expired"]] == ["昨天过期"]
    assert [item["name"] for item in data["expiring"]] == ["今天到期", "三天内"]
    assert data["expired"][0]["days_to_expire"] == -1

    today_only = client.get("/api/v1/ingredients/expiring", headers=headers, params={"days": 0})
    assert [item["name"] for item in today_only.json()["data"]["expiring"]] == ["今天到期"]
    assert (
        client.get(
            "/api/v1/ingredients/expiring", headers=headers, params={"days": 366}
        ).status_code
        == 422
    )


def test_consume_service_commit_false_leaves_outer_transaction_control(
    db_session: Session, client: TestClient
) -> None:
    headers, user = auth_headers(client)
    create_ingredient(client, headers, quantity="2")

    result = consume_ingredient(
        db_session,
        user["id"],
        ConsumeRequest(name="鸡蛋", quantity=Decimal("1"), unit="个"),
        commit=False,
    )
    assert result.remaining_stock == Decimal("1.00")
    db_session.rollback()
    ingredient = db_session.query(Ingredient).filter_by(user_id=user["id"]).one()
    assert ingredient.quantity == Decimal("2.00")
