"""待办新建/列表接口：成功、参数错误、未登录、越权隔离与筛选分页。"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
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
