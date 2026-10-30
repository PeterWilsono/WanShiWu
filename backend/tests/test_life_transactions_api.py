"""账目新建与列表：整数分、分类匹配、用户时区月份、筛选分页和隔离。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.life.models import Transaction

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient, username: str = "peter") -> tuple[dict, dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def default_category(client: TestClient, headers: dict, category_type: str = "expense") -> dict:
    categories = client.get(
        "/api/v1/categories", headers=headers, params={"type": category_type}
    ).json()["data"]
    return categories[0]


def create_transaction(
    client: TestClient, headers: dict, category_id: int, note: str = "午餐", **overrides
) -> dict:
    payload = {
        "amount_cents": 12345,
        "type": "expense",
        "category_id": category_id,
        "note": note,
        "occurred_at": "2026-11-10T09:00:00+08:00",
        **overrides,
    }
    response = client.post("/api/v1/transactions", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_create_transaction_success_and_normalize(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)

    response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "amount_cents": 12345,
            "type": "expense",
            "category_id": category["id"],
            "note": "  团队午餐  ",
            "occurred_at": "2026-11-10T09:00:00+08:00",
        },
    )

    assert response.status_code == 200
    transaction = response.json()["data"]
    assert transaction["amount_cents"] == 12345
    assert transaction["type"] == "expense"
    assert transaction["category_id"] == category["id"]
    assert transaction["category"]["name"] == category["name"]
    assert transaction["category"]["type"] == "expense"
    assert transaction["note"] == "团队午餐"
    assert transaction["occurred_at"] == "2026-11-10T01:00:00Z"
    assert transaction["source"] == "manual"
    assert "deleted_at" not in transaction


def test_create_income_with_explicit_source_and_blank_note(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers, "income")

    transaction = create_transaction(
        client,
        headers,
        category["id"],
        type="income",
        note="   ",
        source="assistant",
    )

    assert transaction["type"] == "income"
    assert transaction["category"]["type"] == "income"
    assert transaction["source"] == "assistant"
    assert transaction["note"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_cents": 0},
        {"amount_cents": -1},
        {"amount_cents": 12.5},
        {"amount_cents": 12.0},
        {"amount_cents": True},
        {"amount_cents": None},
        {"type": "other"},
        {"category_id": 0},
        {"note": "x" * 201},
        {"occurred_at": "2026-11-10T09:00:00"},
        {"occurred_at": None},
        {"source": "unknown"},
    ],
)
def test_create_transaction_validation_errors(client: TestClient, overrides: dict) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    payload = {
        "amount_cents": 100,
        "type": "expense",
        "category_id": category["id"],
        "occurred_at": "2026-11-10T09:00:00+08:00",
        **overrides,
    }

    response = client.post("/api/v1/transactions", headers=headers, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_create_transaction_rejects_category_type_mismatch(
    client: TestClient, db_session: Session
) -> None:
    headers, _ = auth_headers(client)
    income = default_category(client, headers, "income")

    response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "amount_cents": 100,
            "type": "expense",
            "category_id": income["id"],
            "occurred_at": "2026-11-10T09:00:00Z",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    assert response.json()["message"] == "分类类型与账目类型不一致"
    assert db_session.query(Transaction).count() == 0


def test_create_transaction_rejects_missing_or_other_user_category(client: TestClient) -> None:
    owner_headers, _ = auth_headers(client, "owner")
    category = default_category(client, owner_headers)
    other_headers, _ = auth_headers(client, "other")

    for category_id in [category["id"], 999999]:
        response = client.post(
            "/api/v1/transactions",
            headers=other_headers,
            json={
                "amount_cents": 100,
                "type": "expense",
                "category_id": category_id,
                "occurred_at": "2026-11-10T09:00:00Z",
            },
        )
        assert response.status_code == 404
        assert response.json()["code"] == 40401
        assert response.json()["message"] == "分类不存在"


@pytest.mark.parametrize("method", ["get", "post"])
def test_transactions_require_login(client: TestClient, method: str) -> None:
    kwargs = {"json": {}} if method == "post" else {}
    response = getattr(client, method)("/api/v1/transactions", **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_list_transactions_excludes_other_users_and_soft_deleted(
    client: TestClient, db_session: Session
) -> None:
    headers, _ = auth_headers(client, "first")
    category = default_category(client, headers)
    create_transaction(client, headers, category["id"], "保留账目")
    deleted = create_transaction(client, headers, category["id"], "删除账目")
    other_headers, _ = auth_headers(client, "second")
    other_category = default_category(client, other_headers)
    create_transaction(client, other_headers, other_category["id"], "他人账目")
    db_session.get(Transaction, deleted["id"]).deleted_at = now_utc()
    db_session.commit()

    response = client.get("/api/v1/transactions", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["note"] for item in data["items"]] == ["保留账目"]


def test_list_transactions_month_uses_user_timezone(client: TestClient) -> None:
    headers, user = auth_headers(client)
    assert user["timezone"] == "Asia/Shanghai"
    category = default_category(client, headers)
    create_transaction(client, headers, category["id"], "上月", occurred_at="2026-10-31T15:59:59Z")
    create_transaction(
        client, headers, category["id"], "本月初", occurred_at="2026-10-31T16:00:00Z"
    )
    create_transaction(
        client, headers, category["id"], "本月末", occurred_at="2026-11-30T15:59:59Z"
    )
    create_transaction(client, headers, category["id"], "下月", occurred_at="2026-11-30T16:00:00Z")

    response = client.get(
        "/api/v1/transactions",
        headers=headers,
        params={"month": "2026-11", "sort": "occurred_at", "order": "asc"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert [item["note"] for item in data["items"]] == ["本月初", "本月末"]


def test_list_transactions_filters_type_and_category(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    expense = default_category(client, headers)
    income = default_category(client, headers, "income")
    custom_response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "宠物", "type": "expense"},
    )
    custom = custom_response.json()["data"]
    create_transaction(client, headers, expense["id"], "餐饮支出")
    create_transaction(client, headers, custom["id"], "宠物支出")
    create_transaction(client, headers, income["id"], "工资收入", type="income")

    response = client.get(
        "/api/v1/transactions",
        headers=headers,
        params={"type": "expense", "category_id": custom["id"]},
    )

    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["note"] for item in data["items"]] == ["宠物支出"]


def test_list_transactions_pagination_and_amount_sort(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    create_transaction(client, headers, category["id"], "最高", amount_cents=300)
    create_transaction(client, headers, category["id"], "最低", amount_cents=100)
    create_transaction(client, headers, category["id"], "中间", amount_cents=200)

    first = client.get(
        "/api/v1/transactions",
        headers=headers,
        params={"sort": "amount_cents", "order": "asc", "page": 1, "page_size": 2},
    ).json()["data"]
    second = client.get(
        "/api/v1/transactions",
        headers=headers,
        params={"sort": "amount_cents", "order": "asc", "page": 2, "page_size": 2},
    ).json()["data"]

    assert first["total"] == 3
    assert [item["note"] for item in first["items"]] == ["最低", "中间"]
    assert [item["note"] for item in second["items"]] == ["最高"]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"month": "2026-13"},
        {"month": "2026-1"},
        {"category_id": 0},
        {"type": "other"},
        {"sort": "note"},
        {"order": "up"},
    ],
)
def test_list_transactions_rejects_invalid_query(client: TestClient, params: dict) -> None:
    headers, _ = auth_headers(client)
    response = client.get("/api/v1/transactions", headers=headers, params=params)
    assert response.status_code == 422
    assert response.json()["code"] == 40001
