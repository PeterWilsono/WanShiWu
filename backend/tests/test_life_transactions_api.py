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


def test_get_transaction_detail_success(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    created = create_transaction(client, headers, category["id"], "详情账目")

    response = client.get(f"/api/v1/transactions/{created['id']}", headers=headers)

    assert response.status_code == 200
    transaction = response.json()["data"]
    assert transaction["id"] == created["id"]
    assert transaction["note"] == "详情账目"
    assert transaction["category"]["id"] == category["id"]
    assert transaction["category"]["name"] == category["name"]


def test_update_transaction_all_fields_and_normalize(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    expense = default_category(client, headers)
    income = default_category(client, headers, "income")
    created = create_transaction(client, headers, expense["id"])

    response = client.patch(
        f"/api/v1/transactions/{created['id']}",
        headers=headers,
        json={
            "amount_cents": 50000,
            "type": "income",
            "category_id": income["id"],
            "note": "  项目奖金  ",
            "occurred_at": "2026-11-11T12:00:00+08:00",
            "source": "trip",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "更新成功"
    transaction = response.json()["data"]
    assert transaction["amount_cents"] == 50000
    assert transaction["type"] == "income"
    assert transaction["category_id"] == income["id"]
    assert transaction["category"]["name"] == income["name"]
    assert transaction["note"] == "项目奖金"
    assert transaction["occurred_at"] == "2026-11-11T04:00:00Z"
    assert transaction["source"] == "trip"


def test_update_transaction_empty_object_keeps_values(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    created = create_transaction(client, headers, category["id"])

    response = client.patch(f"/api/v1/transactions/{created['id']}", headers=headers, json={})

    assert response.status_code == 200
    transaction = response.json()["data"]
    assert transaction["amount_cents"] == created["amount_cents"]
    assert transaction["type"] == created["type"]
    assert transaction["category_id"] == created["category_id"]
    assert transaction["note"] == created["note"]
    assert transaction["occurred_at"] == created["occurred_at"]


def test_update_transaction_can_clear_note_only(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    created = create_transaction(client, headers, category["id"], "待清空备注")

    response = client.patch(
        f"/api/v1/transactions/{created['id']}", headers=headers, json={"note": None}
    )

    assert response.status_code == 200
    transaction = response.json()["data"]
    assert transaction["note"] is None
    assert transaction["amount_cents"] == created["amount_cents"]
    assert transaction["category_id"] == created["category_id"]


@pytest.mark.parametrize(
    "payload",
    [
        {"amount_cents": 0},
        {"amount_cents": -1},
        {"amount_cents": 12.5},
        {"amount_cents": 12.0},
        {"amount_cents": True},
        {"amount_cents": None},
        {"type": None},
        {"category_id": 0},
        {"category_id": None},
        {"note": "x" * 201},
        {"occurred_at": "2026-11-10T09:00:00"},
        {"occurred_at": None},
        {"source": "unknown"},
        {"source": None},
    ],
)
def test_update_transaction_validation_errors_without_changes(
    client: TestClient, payload: dict
) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    created = create_transaction(client, headers, category["id"], "原始账目")

    response = client.patch(f"/api/v1/transactions/{created['id']}", headers=headers, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == 40001
    current = client.get(f"/api/v1/transactions/{created['id']}", headers=headers).json()["data"]
    assert current["amount_cents"] == created["amount_cents"]
    assert current["type"] == created["type"]
    assert current["category_id"] == created["category_id"]
    assert current["note"] == created["note"]
    assert current["occurred_at"] == created["occurred_at"]


def test_update_transaction_merges_type_and_category_validation(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    expense = default_category(client, headers)
    income = default_category(client, headers, "income")
    created = create_transaction(client, headers, expense["id"], "组合校验")

    only_type = client.patch(
        f"/api/v1/transactions/{created['id']}", headers=headers, json={"type": "income"}
    )
    only_category = client.patch(
        f"/api/v1/transactions/{created['id']}",
        headers=headers,
        json={"category_id": income["id"]},
    )
    both = client.patch(
        f"/api/v1/transactions/{created['id']}",
        headers=headers,
        json={"type": "income", "category_id": income["id"]},
    )

    assert only_type.status_code == 422
    assert only_type.json()["code"] == 42201
    assert only_category.status_code == 422
    assert only_category.json()["code"] == 42201
    assert both.status_code == 200
    assert both.json()["data"]["type"] == "income"
    assert both.json()["data"]["category_id"] == income["id"]


def test_update_transaction_rejects_other_user_category(client: TestClient) -> None:
    headers, _ = auth_headers(client, "first")
    category = default_category(client, headers)
    created = create_transaction(client, headers, category["id"], "保持原分类")
    other_headers, _ = auth_headers(client, "second")
    other_category = default_category(client, other_headers)

    response = client.patch(
        f"/api/v1/transactions/{created['id']}",
        headers=headers,
        json={"category_id": other_category["id"]},
    )

    assert response.status_code == 404
    assert response.json()["code"] == 40401
    current = client.get(f"/api/v1/transactions/{created['id']}", headers=headers).json()["data"]
    assert current["category_id"] == category["id"]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_transaction_detail_operations_require_login(client: TestClient, method: str) -> None:
    kwargs = {"json": {}} if method == "patch" else {}
    response = getattr(client, method)("/api/v1/transactions/1", **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_transaction_missing_and_other_user_return_same_404(
    client: TestClient, db_session: Session, method: str
) -> None:
    owner_headers, _ = auth_headers(client, "owner")
    category = default_category(client, owner_headers)
    created = create_transaction(client, owner_headers, category["id"], "本人账目")
    other_headers, _ = auth_headers(client, "other")
    kwargs = {"json": {"note": "越权"}} if method == "patch" else {}

    other_response = getattr(client, method)(
        f"/api/v1/transactions/{created['id']}", headers=other_headers, **kwargs
    )
    missing_response = getattr(client, method)(
        "/api/v1/transactions/999999", headers=other_headers, **kwargs
    )

    assert other_response.status_code == 404
    assert other_response.json()["code"] == 40401
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == 40401
    db_session.expire_all()
    stored = db_session.get(Transaction, created["id"])
    assert stored.note == "本人账目"
    assert stored.deleted_at is None


def test_delete_transaction_is_soft_and_hidden(client: TestClient, db_session: Session) -> None:
    headers, _ = auth_headers(client)
    category = default_category(client, headers)
    created = create_transaction(client, headers, category["id"], "软删除账目")

    deleted = client.delete(f"/api/v1/transactions/{created['id']}", headers=headers)

    assert deleted.status_code == 200
    assert deleted.json() == {"code": 0, "message": "删除成功", "data": None}
    db_session.expire_all()
    stored = db_session.get(Transaction, created["id"])
    assert stored is not None
    assert stored.deleted_at is not None
    detail = client.get(f"/api/v1/transactions/{created['id']}", headers=headers)
    listed = client.get("/api/v1/transactions", headers=headers).json()["data"]
    repeated = client.delete(f"/api/v1/transactions/{created['id']}", headers=headers)
    assert detail.status_code == 404
    assert listed["total"] == 0
    assert listed["items"] == []
    assert repeated.status_code == 404


def test_deleted_transaction_still_protects_category_from_deletion(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    custom = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "临时分类", "type": "expense"},
    ).json()["data"]
    created = create_transaction(client, headers, custom["id"], "历史记录")
    deleted = client.delete(f"/api/v1/transactions/{created['id']}", headers=headers)
    assert deleted.status_code == 200

    response = client.delete(f"/api/v1/categories/{custom['id']}", headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    assert response.json()["message"] == "已有账目引用该分类，只能改名"
