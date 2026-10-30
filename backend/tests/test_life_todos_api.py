"""待办新建/列表接口：成功、参数错误、未登录、越权隔离与筛选分页。"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.auth.models import User
from app.modules.life.models import Todo, TodoStatus

PASSWORD = "correct-horse-123"


def register_and_login(client: TestClient, username: str = "peter") -> tuple[dict, dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def create_todo(client: TestClient, headers: dict, title: str, **overrides):
    payload = {"title": title, **overrides}
    return client.post("/api/v1/todos", json=payload, headers=headers)


def test_create_todo_success_and_normalize(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    response = create_todo(
        client,
        headers,
        "  写项目周报  ",
        due_at="2026-10-31T15:00:00+08:00",
        tags=["工作", "工作", " 本周 "],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0 and body["message"] == "创建成功"
    todo = body["data"]
    assert todo["title"] == "写项目周报"
    assert todo["status"] == "pending"
    assert todo["priority"] == 2
    assert todo["recurrence"] == "none"
    assert todo["tags"] == ["工作", "本周"]
    assert datetime.fromisoformat(todo["due_at"].replace("Z", "+00:00")) == datetime(
        2026, 10, 31, 7, 0, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "非法优先级", "priority": 4},
        {"title": "无时区", "due_at": "2026-10-31T15:00:00"},
        {"title": "空标签", "tags": ["工作", "  "]},
    ],
)
def test_create_todo_validation_errors(client: TestClient, payload: dict) -> None:
    headers, _ = register_and_login(client)
    response = create_todo(client, headers, **payload)
    assert response.status_code == 422
    assert response.json()["code"] == 40001


@pytest.mark.parametrize("method", ["get", "post"])
def test_todos_require_login(client: TestClient, method: str) -> None:
    request = getattr(client, method)
    kwargs = {"json": {"title": "未登录"}} if method == "post" else {}
    response = request("/api/v1/todos", **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_list_todos_excludes_other_users_and_soft_deleted(
    client: TestClient, db_session: Session
) -> None:
    headers, current_user = register_and_login(client)
    create_todo(client, headers, "当前用户待办")

    other_user = User(username="other", password_hash="hash")
    db_session.add(other_user)
    db_session.commit()
    db_session.add_all(
        [
            Todo(user_id=other_user.id, title="其他用户待办"),
            Todo(user_id=current_user["id"], title="已删除待办", deleted_at=now_utc()),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/todos", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["title"] for item in data["items"]] == ["当前用户待办"]


def test_list_todos_filters_by_status_due_range_and_exact_tag(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    base = now_utc()
    create_todo(
        client,
        headers,
        "符合条件",
        due_at=(base + timedelta(days=1)).isoformat(),
        tags=["工作"],
    )
    create_todo(
        client,
        headers,
        "标签只应精确匹配",
        due_at=(base + timedelta(days=1)).isoformat(),
        tags=["远程工作"],
    )
    create_todo(
        client,
        headers,
        "超出时间范围",
        due_at=(base + timedelta(days=5)).isoformat(),
        tags=["工作"],
    )

    response = client.get(
        "/api/v1/todos",
        headers=headers,
        params={
            "status": "pending",
            "tag": "工作",
            "due_after": (base - timedelta(seconds=1)).isoformat(),
            "due_before": (base + timedelta(days=2)).isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["title"] for item in data["items"]] == ["符合条件"]


def test_list_todos_pagination_and_sorting(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    for title in ["第一条", "第二条", "第三条"]:
        create_todo(client, headers, title)

    first_page = client.get(
        "/api/v1/todos",
        headers=headers,
        params={"page": 1, "page_size": 2, "sort": "created_at", "order": "asc"},
    ).json()["data"]
    second_page = client.get(
        "/api/v1/todos",
        headers=headers,
        params={"page": 2, "page_size": 2, "sort": "created_at", "order": "asc"},
    ).json()["data"]

    assert first_page["total"] == 3
    assert [item["title"] for item in first_page["items"]] == ["第一条", "第二条"]
    assert second_page["page"] == 2
    assert [item["title"] for item in second_page["items"]] == ["第三条"]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"due_after": "2026-11-01T00:00:00"},
        {
            "due_after": "2026-11-02T00:00:00+08:00",
            "due_before": "2026-11-01T00:00:00+08:00",
        },
    ],
)
def test_list_todos_rejects_invalid_query(client: TestClient, params: dict) -> None:
    headers, _ = register_and_login(client)
    response = client.get("/api/v1/todos", headers=headers, params=params)
    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_list_todos_done_status_filter(client: TestClient, db_session: Session) -> None:
    headers, user = register_and_login(client)
    create_todo(client, headers, "待完成")
    db_session.add(Todo(user_id=user["id"], title="已完成", status=TodoStatus.DONE))
    db_session.commit()

    response = client.get("/api/v1/todos", headers=headers, params={"status": "done"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["title"] == "已完成"


def test_get_todo_detail_success(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    todo_id = create_todo(client, headers, "查看详情", note="保留备注").json()["data"]["id"]

    response = client.get(f"/api/v1/todos/{todo_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["title"] == "查看详情"
    assert response.json()["data"]["note"] == "保留备注"


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_todo_detail_missing_and_other_user_return_same_404(
    client: TestClient, method: str
) -> None:
    headers, _ = register_and_login(client, "owner")
    other_headers, _ = register_and_login(client, "other")
    todo_id = create_todo(client, headers, "仅本人可见").json()["data"]["id"]
    kwargs = {"json": {"title": "越权修改"}} if method == "patch" else {}

    missing = getattr(client, method)("/api/v1/todos/999999", headers=headers, **kwargs)
    other_user = getattr(client, method)(
        f"/api/v1/todos/{todo_id}", headers=other_headers, **kwargs
    )

    for response in [missing, other_user]:
        assert response.status_code == 404
        assert response.json() == {"code": 40401, "message": "待办不存在", "data": None}


def test_update_todo_partial_and_explicit_null(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    created = create_todo(
        client,
        headers,
        "原标题",
        note="原备注",
        due_at="2026-11-01T09:00:00+08:00",
        priority=1,
        tags=["工作"],
    ).json()["data"]

    partial = client.patch(
        f"/api/v1/todos/{created['id']}",
        headers=headers,
        json={"title": "  新标题  ", "priority": 3},
    )
    assert partial.status_code == 200
    assert partial.json()["message"] == "更新成功"
    updated = partial.json()["data"]
    assert updated["title"] == "新标题"
    assert updated["priority"] == 3
    assert updated["note"] == "原备注"
    assert updated["due_at"] == created["due_at"]
    assert updated["tags"] == ["工作"]

    cleared = client.patch(
        f"/api/v1/todos/{created['id']}",
        headers=headers,
        json={"note": None, "due_at": None, "tags": []},
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["note"] is None
    assert cleared.json()["data"]["due_at"] is None
    assert cleared.json()["data"]["tags"] == []


def test_update_todo_status_maintains_completed_at(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    todo_id = create_todo(client, headers, "完成状态").json()["data"]["id"]

    done = client.patch(f"/api/v1/todos/{todo_id}", headers=headers, json={"status": "done"})
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "done"
    completed_at = done.json()["data"]["completed_at"]
    assert completed_at is not None
    assert datetime.fromisoformat(completed_at.replace("Z", "+00:00")).tzinfo is not None

    pending = client.patch(f"/api/v1/todos/{todo_id}", headers=headers, json={"status": "pending"})
    assert pending.status_code == 200
    assert pending.json()["data"]["status"] == "pending"
    assert pending.json()["data"]["completed_at"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": None},
        {"priority": None},
        {"priority": 4},
        {"status": None},
        {"status": "invalid"},
        {"due_at": "2026-11-01T09:00:00"},
        {"tags": None},
        {"tags": ["  "]},
    ],
)
def test_update_todo_validation_errors(client: TestClient, payload: dict) -> None:
    headers, _ = register_and_login(client)
    todo_id = create_todo(client, headers, "参数校验").json()["data"]["id"]

    response = client.patch(f"/api/v1/todos/{todo_id}", headers=headers, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_update_todo_empty_patch_is_noop(client: TestClient) -> None:
    headers, _ = register_and_login(client)
    created = create_todo(client, headers, "空更新", note="不变").json()["data"]

    response = client.patch(f"/api/v1/todos/{created['id']}", headers=headers, json={})

    assert response.status_code == 200
    assert response.json()["data"] == created


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_todo_detail_requires_login(client: TestClient, method: str) -> None:
    kwargs = {"json": {"title": "未登录"}} if method == "patch" else {}
    response = getattr(client, method)("/api/v1/todos/1", **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_delete_todo_is_soft_delete_and_excluded_from_queries(
    client: TestClient, db_session: Session
) -> None:
    headers, user = register_and_login(client)
    todo_id = create_todo(client, headers, "软删除我").json()["data"]["id"]

    deleted = client.delete(f"/api/v1/todos/{todo_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"code": 0, "message": "删除成功", "data": None}

    row = db_session.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user["id"]))
    assert row is not None
    assert row.deleted_at is not None
    assert client.get(f"/api/v1/todos/{todo_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/todos", headers=headers).json()["data"]["total"] == 0
    assert client.delete(f"/api/v1/todos/{todo_id}", headers=headers).status_code == 404
