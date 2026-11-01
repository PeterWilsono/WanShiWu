"""菜谱做菜原子扣减与缺料批量加入购物清单测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.pantry.models import ShoppingItem
from app.modules.pantry.schemas import RecipeShoppingRequest
from app.modules.pantry.service import add_recipe_missing_to_shopping

PASSWORD = "correct-recipe-transaction-317"


def auth_headers(client: TestClient, username: str = "recipe-cook") -> tuple[dict[str, str], dict]:
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
    quantity: str = "4",
    unit: str = "个",
    **overrides: object,
) -> dict:
    response = client.post(
        "/api/v1/ingredients",
        headers=headers,
        json={"name": name, "quantity": quantity, "unit": unit, "storage": "fridge", **overrides},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def ingredient_detail(client: TestClient, headers: dict[str, str], item: dict) -> dict:
    response = client.get(f"/api/v1/ingredients/{item['id']}", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]


def test_cook_deducts_multiple_ingredients_with_fefo(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    no_expiry = create_ingredient(client, headers, quantity="4", expire_on=None)
    earlier = create_ingredient(client, headers, quantity="2", expire_on="2026-11-01")
    tomato = create_ingredient(client, headers, name="番茄", quantity="500", unit="克")

    response = client.post(
        "/api/v1/pantry/cook",
        headers=headers,
        json={
            "recipe_name": "番茄炒蛋",
            "uses": [
                {"name": "鸡蛋", "quantity": "3", "unit": "个"},
                {"name": "番茄", "quantity": "200", "unit": "克"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["recipe_name"] == "番茄炒蛋"
    assert [item["remaining_stock"] for item in data["consumed"]] == ["3.00", "300.00"]
    assert [batch["ingredient_id"] for batch in data["consumed"][0]["batches"]] == [
        earlier["id"], no_expiry["id"],
    ]
    assert ingredient_detail(client, headers, earlier)["status"] == "used_up"
    assert ingredient_detail(client, headers, no_expiry)["quantity"] == "3.00"
    assert ingredient_detail(client, headers, tomato)["quantity"] == "300.00"


def test_cook_shortage_rolls_back_every_ingredient(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    eggs = create_ingredient(client, headers, quantity="2")
    create_ingredient(client, headers, name="番茄", quantity="100", unit="克")

    response = client.post(
        "/api/v1/pantry/cook",
        headers=headers,
        json={
            "recipe_name": "番茄炒蛋",
            "uses": [
                {"name": "鸡蛋", "quantity": "2", "unit": "个"},
                {"name": "番茄", "quantity": "200", "unit": "克"},
            ],
        },
    )

    assert response.status_code == 422 and response.json()["code"] == 42201
    assert response.json()["data"]["shortage"] == "100.00"
    restored = ingredient_detail(client, headers, eggs)
    assert restored["quantity"] == "2.00" and restored["status"] == "active"


def test_cook_combines_duplicate_demand_and_never_uses_other_users_stock(
    client: TestClient,
) -> None:
    headers, _ = auth_headers(client)
    other_headers, _ = auth_headers(client, "other-stock-owner")
    eggs = create_ingredient(client, headers, quantity="3")
    create_ingredient(client, other_headers, quantity="20")

    response = client.post(
        "/api/v1/pantry/cook",
        headers=headers,
        json={
            "recipe_name": "双倍炒蛋",
            "uses": [
                {"name": "鸡蛋", "quantity": "2", "unit": "个"},
                {"name": "鸡蛋", "quantity": "2", "unit": "个"},
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["data"]["available"] == "1.00"
    assert response.json()["data"]["shortage"] == "1.00"
    assert ingredient_detail(client, headers, eggs)["quantity"] == "3.00"


def test_cook_validation_and_authentication(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    empty = client.post(
        "/api/v1/pantry/cook",
        headers=headers,
        json={"recipe_name": "空菜谱", "uses": []},
    )
    invalid_unit = client.post(
        "/api/v1/pantry/cook",
        headers=headers,
        json={
            "recipe_name": "错误单位",
            "uses": [{"name": "鸡蛋", "quantity": "1", "unit": "箱"}],
        },
    )
    assert empty.status_code == 422 and empty.json()["code"] == 40001
    assert invalid_unit.status_code == 422 and invalid_unit.json()["code"] == 40001
    assert client.post("/api/v1/pantry/cook", json={}).status_code == 401


def test_recipe_missing_is_added_as_one_batch(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    response = client.post(
        "/api/v1/pantry/recipes/shopping-items",
        headers=headers,
        json={
            "recipe_name": "番茄炖牛腩",
            "missing": [
                {"name": "牛腩", "quantity": "500", "unit": "克"},
                {"name": "番茄", "quantity": "2", "unit": "个"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert len(items) == 2
    assert all(item["source"] == "recipe" for item in items)
    assert all(item["recipe_name"] == "番茄炖牛腩" for item in items)
    assert all(item["done"] is False for item in items)
    listed = client.get("/api/v1/shopping-items", headers=headers).json()["data"]
    assert listed["total"] == 2
    assert client.post("/api/v1/pantry/recipes/shopping-items", json={}).status_code == 401


def test_recipe_missing_validation(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    response = client.post(
        "/api/v1/pantry/recipes/shopping-items",
        headers=headers,
        json={"recipe_name": "空菜谱", "missing": []},
    )
    assert response.status_code == 422 and response.json()["code"] == 40001


def test_recipe_missing_service_rolls_back_on_database_failure(
    db_session: Session, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, user = auth_headers(client)
    data = RecipeShoppingRequest.model_validate(
        {
            "recipe_name": "测试菜谱",
            "missing": [
                {"name": "第一项", "quantity": "1", "unit": "个"},
                {"name": "第二项", "quantity": "1", "unit": "个"},
            ],
        }
    )

    import app.modules.pantry.service as pantry_service

    original = pantry_service.create_shopping_item

    def fail_second(*args: object, **kwargs: object) -> ShoppingItem:
        item = original(*args, **kwargs)
        if item.name == "第二项":
            raise RuntimeError("模拟数据库失败")
        return item

    monkeypatch.setattr(pantry_service, "create_shopping_item", fail_second)
    with pytest.raises(RuntimeError, match="模拟数据库失败"):
        add_recipe_missing_to_shopping(db_session, user["id"], data)

    assert db_session.query(ShoppingItem).filter_by(user_id=user["id"]).count() == 0
