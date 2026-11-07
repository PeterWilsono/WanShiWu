"""生活资源软删除恢复：待办、日程提醒、账目统计与幂等性。"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.life.models import Reminder, ReminderTargetType

PASSWORD = "correct-horse-123"


def auth(client: TestClient, username: str = "restore-user") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_restore_todo_returns_same_record_and_is_idempotent(client: TestClient) -> None:
    headers = auth(client)
    todo = client.post(
        "/api/v1/todos", json={"title": "保留原编号", "tags": ["重要"]}, headers=headers
    ).json()["data"]
    assert client.delete(f"/api/v1/todos/{todo['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/todos/{todo['id']}", headers=headers).status_code == 404

    first = client.post(f"/api/v1/todos/{todo['id']}/restore", headers=headers)
    second = client.post(f"/api/v1/todos/{todo['id']}/restore", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["id"] == todo["id"]
    assert first.json()["data"]["tags"] == ["重要"]
    assert second.json()["data"] == first.json()["data"]


def test_restore_event_also_restores_reminder_without_resetting_delivery(
    client: TestClient, db_session: Session
) -> None:
    headers = auth(client, "restore-event")
    event = client.post(
        "/api/v1/events",
        json={
            "title": "带提醒的日程",
            "start_at": "2026-11-10T09:00:00+08:00",
            "remind_before_min": 15,
        },
        headers=headers,
    ).json()["data"]
    reminder = db_session.scalar(
        select(Reminder).where(
            Reminder.target_type == ReminderTargetType.EVENT,
            Reminder.target_id == event["id"],
        )
    )
    fired_at = now_utc()
    reminder.fired_at = fired_at
    reminder.read_at = fired_at
    db_session.commit()

    client.delete(f"/api/v1/events/{event['id']}", headers=headers)
    assert reminder.deleted_at is not None
    response = client.post(f"/api/v1/events/{event['id']}/restore", headers=headers)
    assert response.status_code == 200
    db_session.refresh(reminder)
    assert reminder.deleted_at is None
    assert reminder.fired_at == fired_at
    assert reminder.read_at == fired_at


def test_restore_transaction_reenters_monthly_stats(client: TestClient) -> None:
    headers = auth(client, "restore-transaction")
    category = client.get("/api/v1/categories?type=expense", headers=headers).json()["data"][0]
    transaction = client.post(
        "/api/v1/transactions",
        json={
            "amount_cents": 1250,
            "type": "expense",
            "category_id": category["id"],
            "occurred_at": "2026-11-04T12:00:00+08:00",
        },
        headers=headers,
    ).json()["data"]
    client.delete(f"/api/v1/transactions/{transaction['id']}", headers=headers)
    empty = client.get("/api/v1/stats/monthly?month=2026-11", headers=headers).json()["data"]
    assert empty["expense_cents"] == 0

    restored = client.post(
        f"/api/v1/transactions/{transaction['id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    stats = client.get("/api/v1/stats/monthly?month=2026-11", headers=headers).json()["data"]
    assert stats["expense_cents"] == 1250


def test_restore_endpoints_do_not_expose_other_users_records(client: TestClient) -> None:
    owner = auth(client, "restore-owner")
    todo = client.post("/api/v1/todos", json={"title": "仅本人恢复"}, headers=owner).json()["data"]
    client.delete(f"/api/v1/todos/{todo['id']}", headers=owner)
    other = auth(client, "restore-other")
    response = client.post(f"/api/v1/todos/{todo['id']}/restore", headers=other)
    assert response.status_code == 404
    assert response.json()["code"] == 40401
