"""完成待办：普通完成、周期顺延、冲突、用户隔离与事务回滚。"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.auth.models import User
from app.modules.life.models import Recurrence, Todo, TodoStatus
from app.modules.life.service import complete_todo

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient, username: str = "peter") -> dict:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_todo(client: TestClient, headers: dict, **payload) -> dict:
    response = client.post("/api/v1/todos", headers=headers, json=payload)
    assert response.status_code == 200
    return response.json()["data"]


def test_complete_normal_todo_without_due_date(client: TestClient, db_session: Session) -> None:
    headers = auth_headers(client)
    todo = create_todo(client, headers, title="普通待办")

    response = client.post(f"/api/v1/todos/{todo['id']}/complete", headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "完成成功"
    data = response.json()["data"]
    assert data["todo"]["status"] == "done"
    assert data["todo"]["completed_at"] is not None
    assert data["next_todo"] is None
    assert db_session.scalar(select(func.count()).select_from(Todo)) == 1


@pytest.mark.parametrize(
    ("recurrence", "due_at", "expected_next"),
    [
        ("daily", "2026-10-31T23:30:00+08:00", "2026-11-01T15:30:00+00:00"),
        ("weekly", "2026-10-31T08:00:00+00:00", "2026-11-07T08:00:00+00:00"),
        ("monthly", "2026-01-31T08:00:00+00:00", "2026-02-28T08:00:00+00:00"),
        ("monthly", "2024-01-31T08:00:00+00:00", "2024-02-29T08:00:00+00:00"),
        ("monthly", "2026-12-31T08:00:00+00:00", "2027-01-31T08:00:00+00:00"),
    ],
)
def test_complete_recurring_todo_creates_next_instance(
    client: TestClient, recurrence: str, due_at: str, expected_next: str
) -> None:
    headers = auth_headers(client)
    todo = create_todo(
        client,
        headers,
        title="周期任务",
        note="复制备注",
        due_at=due_at,
        priority=3,
        recurrence=recurrence,
        tags=["习惯"],
    )

    response = client.post(f"/api/v1/todos/{todo['id']}/complete", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["todo"]["status"] == "done"
    next_todo = data["next_todo"]
    assert next_todo["id"] != todo["id"]
    assert next_todo["status"] == "pending"
    assert next_todo["completed_at"] is None
    assert next_todo["title"] == "周期任务"
    assert next_todo["note"] == "复制备注"
    assert next_todo["priority"] == 3
    assert next_todo["recurrence"] == recurrence
    assert next_todo["tags"] == ["习惯"]
    actual = datetime.fromisoformat(next_todo["due_at"].replace("Z", "+00:00"))
    assert actual == datetime.fromisoformat(expected_next).astimezone(UTC)


def test_repeat_complete_returns_conflict_without_creating_more(client: TestClient) -> None:
    headers = auth_headers(client)
    todo = create_todo(
        client,
        headers,
        title="不要重复生成",
        due_at="2026-10-31T08:00:00+00:00",
        recurrence="daily",
    )
    client.post(f"/api/v1/todos/{todo['id']}/complete", headers=headers)

    response = client.post(f"/api/v1/todos/{todo['id']}/complete", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == 40901
    todos = client.get("/api/v1/todos", headers=headers).json()["data"]
    assert todos["total"] == 2


def test_cancelled_todo_cannot_be_completed(client: TestClient) -> None:
    headers = auth_headers(client)
    todo = create_todo(client, headers, title="已取消")
    client.patch(f"/api/v1/todos/{todo['id']}", headers=headers, json={"status": "cancelled"})

    response = client.post(f"/api/v1/todos/{todo['id']}/complete", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == 40901


def test_recurring_todo_requires_due_date_to_complete(client: TestClient) -> None:
    headers = auth_headers(client)
    todo = create_todo(client, headers, title="缺少基准时间", recurrence="weekly")

    response = client.post(f"/api/v1/todos/{todo['id']}/complete", headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    unchanged = client.get(f"/api/v1/todos/{todo['id']}", headers=headers).json()["data"]
    assert unchanged["status"] == "pending"
    assert unchanged["completed_at"] is None
    assert client.get("/api/v1/todos", headers=headers).json()["data"]["total"] == 1


def test_complete_requires_login(client: TestClient) -> None:
    response = client.post("/api/v1/todos/1/complete")
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_complete_missing_or_other_user_returns_404(client: TestClient) -> None:
    headers = auth_headers(client, "owner")
    other_headers = auth_headers(client, "other")
    todo = create_todo(client, headers, title="本人任务")

    missing = client.post("/api/v1/todos/999999/complete", headers=headers)
    other = client.post(f"/api/v1/todos/{todo['id']}/complete", headers=other_headers)

    for response in [missing, other]:
        assert response.status_code == 404
        assert response.json()["code"] == 40401


def test_complete_rolls_back_status_and_next_todo_on_commit_failure(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = User(username="rollback", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    todo = Todo(
        user_id=user.id,
        title="事务回滚",
        due_at=now_utc(),
        recurrence=Recurrence.DAILY,
    )
    db_session.add(todo)
    db_session.commit()

    def fail_commit() -> None:
        raise RuntimeError("模拟提交失败")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="模拟提交失败"):
        complete_todo(db_session, user.id, todo.id)

    assert db_session.scalar(select(func.count()).select_from(Todo)) == 1
    persisted = db_session.scalar(select(Todo).where(Todo.id == todo.id))
    assert persisted is not None
    assert persisted.status == TodoStatus.PENDING
    assert persisted.completed_at is None
