"""分类初始化与管理：默认值、唯一性、用户隔离、引用保护和软删除。"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.life.models import Category, Transaction, TransactionType

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient, username: str = "peter") -> tuple[dict, dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def create_category(
    client: TestClient, headers: dict, name: str, category_type: str = "expense", **overrides
) -> dict:
    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": name, "type": category_type, **overrides},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_register_initializes_default_categories(client: TestClient) -> None:
    headers, _ = auth_headers(client)

    response = client.get("/api/v1/categories", headers=headers)

    assert response.status_code == 200
    categories = response.json()["data"]
    assert len(categories) == 10
    assert all(item["is_default"] for item in categories)
    expense = {item["name"] for item in categories if item["type"] == "expense"}
    income = {item["name"] for item in categories if item["type"] == "income"}
    assert expense == {"餐饮", "交通", "购物", "居家", "娱乐", "医疗", "学习", "其他"}
    assert income == {"工资", "其他"}
    assert all(item["icon"] for item in categories)


def test_category_list_filters_type_and_rejects_invalid_type(client: TestClient) -> None:
    headers, _ = auth_headers(client)

    expense = client.get("/api/v1/categories", headers=headers, params={"type": "expense"})
    income = client.get("/api/v1/categories", headers=headers, params={"type": "income"})
    invalid = client.get("/api/v1/categories", headers=headers, params={"type": "other"})

    assert len(expense.json()["data"]) == 8
    assert {item["type"] for item in expense.json()["data"]} == {"expense"}
    assert len(income.json()["data"]) == 2
    assert {item["type"] for item in income.json()["data"]} == {"income"}
    assert invalid.status_code == 422
    assert invalid.json()["code"] == 40001


def test_create_custom_category_and_normalize(client: TestClient) -> None:
    headers, _ = auth_headers(client)

    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "  宠物  ", "type": "expense", "icon": "  pet  "},
    )

    assert response.status_code == 200
    category = response.json()["data"]
    assert category["name"] == "宠物"
    assert category["type"] == "expense"
    assert category["icon"] == "pet"
    assert category["is_default"] is False
    assert "deleted_at" not in category


def test_category_name_unique_only_within_user_and_type(client: TestClient) -> None:
    headers, _ = auth_headers(client, "first")
    create_category(client, headers, "自定义")

    duplicate = client.post(
        "/api/v1/categories", headers=headers, json={"name": "自定义", "type": "expense"}
    )
    other_type = client.post(
        "/api/v1/categories", headers=headers, json={"name": "自定义", "type": "income"}
    )
    other_headers, _ = auth_headers(client, "second")
    other_user = client.post(
        "/api/v1/categories", headers=other_headers, json={"name": "自定义", "type": "expense"}
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40901
    assert other_type.status_code == 200
    assert other_user.status_code == 200


def test_update_category_allows_rename_default_and_clear_icon(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    default = client.get("/api/v1/categories", headers=headers).json()["data"][0]

    response = client.patch(
        f"/api/v1/categories/{default['id']}",
        headers=headers,
        json={"name": "  日常餐饮  ", "icon": None},
    )

    assert response.status_code == 200
    category = response.json()["data"]
    assert category["name"] == "日常餐饮"
    assert category["icon"] is None
    assert category["is_default"] is True
    assert category["type"] == default["type"]


def test_update_category_rejects_duplicate_without_changes(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    first = create_category(client, headers, "分类甲")
    create_category(client, headers, "分类乙")

    response = client.patch(
        f"/api/v1/categories/{first['id']}", headers=headers, json={"name": "分类乙"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == 40901
    current = client.get("/api/v1/categories", headers=headers).json()["data"]
    assert next(item for item in current if item["id"] == first["id"])["name"] == "分类甲"


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "expense"},
        {"name": "缺少类型"},
        {"name": "   ", "type": "expense"},
        {"name": "非法类型", "type": "other"},
        {"name": "超长图标", "type": "expense", "icon": "x" * 31},
        {"name": "x" * 31, "type": "expense"},
    ],
)
def test_create_category_validation_errors(client: TestClient, payload: dict) -> None:
    headers, _ = auth_headers(client)
    response = client.post("/api/v1/categories", headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_update_category_rejects_blank_or_null_name(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = create_category(client, headers, "有效名称")
    for payload in [{"name": "   "}, {"name": None}]:
        response = client.patch(
            f"/api/v1/categories/{category['id']}", headers=headers, json=payload
        )
        assert response.status_code == 422
        assert response.json()["code"] == 40001


@pytest.mark.parametrize("method", ["get", "post", "patch", "delete"])
def test_category_operations_require_login(client: TestClient, method: str) -> None:
    url = "/api/v1/categories/1" if method in {"patch", "delete"} else "/api/v1/categories"
    kwargs = {"json": {}} if method in {"post", "patch"} else {}
    response = getattr(client, method)(url, **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_category_missing_and_other_user_return_same_404(
    client: TestClient, db_session: Session, method: str
) -> None:
    owner_headers, _ = auth_headers(client, "owner")
    category = create_category(client, owner_headers, "本人分类")
    other_headers, _ = auth_headers(client, "other")
    kwargs = {"json": {"name": "越权"}} if method == "patch" else {}

    other_response = getattr(client, method)(
        f"/api/v1/categories/{category['id']}", headers=other_headers, **kwargs
    )
    missing_response = getattr(client, method)(
        "/api/v1/categories/999999", headers=other_headers, **kwargs
    )

    assert other_response.status_code == 404
    assert other_response.json()["code"] == 40401
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == 40401
    db_session.expire_all()
    stored = db_session.get(Category, category["id"])
    assert stored.name == "本人分类"
    assert stored.deleted_at is None


def test_default_category_cannot_be_deleted(client: TestClient, db_session: Session) -> None:
    headers, _ = auth_headers(client)
    category = client.get("/api/v1/categories", headers=headers).json()["data"][0]

    response = client.delete(f"/api/v1/categories/{category['id']}", headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    assert response.json()["message"] == "内置分类不可删除"
    db_session.expire_all()
    assert db_session.get(Category, category["id"]).deleted_at is None


def test_category_referenced_even_by_deleted_transaction_cannot_be_deleted(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    category = create_category(client, headers, "历史分类")
    db_session.add(
        Transaction(
            user_id=user["id"],
            amount_cents=100,
            type=TransactionType.EXPENSE,
            category_id=category["id"],
            occurred_at=datetime(2026, 11, 1, tzinfo=UTC),
            deleted_at=now_utc(),
        )
    )
    db_session.commit()

    response = client.delete(f"/api/v1/categories/{category['id']}", headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    assert response.json()["message"] == "已有账目引用该分类，只能改名"
    db_session.expire_all()
    assert db_session.get(Category, category["id"]).deleted_at is None


def test_unused_custom_category_is_soft_deleted(client: TestClient, db_session: Session) -> None:
    headers, _ = auth_headers(client)
    category = create_category(client, headers, "不再使用")

    response = client.delete(f"/api/v1/categories/{category['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "删除成功"
    db_session.expire_all()
    stored = db_session.get(Category, category["id"])
    assert stored is not None
    assert stored.deleted_at is not None
    categories = client.get("/api/v1/categories", headers=headers).json()["data"]
    assert all(item["id"] != category["id"] for item in categories)
    repeated = client.delete(f"/api/v1/categories/{category['id']}", headers=headers)
    assert repeated.status_code == 404
    assert repeated.json()["code"] == 40401
