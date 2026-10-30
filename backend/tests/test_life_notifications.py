"""提醒扫描、通知查询、已读和调度器配置。"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.life.models import Reminder, ReminderTargetType
from app.modules.life.service import fire_due_reminders
from app.scheduler.reminders import create_scheduler

PASSWORD = "correct-horse-123"
NOW = datetime(2026, 11, 10, 1, 0, tzinfo=UTC)


def auth_headers(client: TestClient, username: str = "peter") -> tuple[dict, dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def add_reminder(db: Session, user_id: int, message: str, **overrides) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        target_type=ReminderTargetType.EVENT,
        target_id=overrides.pop("target_id", 1),
        remind_at=overrides.pop("remind_at", NOW - timedelta(minutes=1)),
        message=message,
        **overrides,
    )
    db.add(reminder)
    db.flush()
    return reminder


def test_scan_fires_only_due_active_reminders_once(db_session: Session) -> None:
    user = User(username="peter", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    due = add_reminder(db_session, user.id, "到点")
    future = add_reminder(
        db_session, user.id, "未来", target_id=2, remind_at=NOW + timedelta(minutes=1)
    )
    fired = add_reminder(db_session, user.id, "已触发", target_id=3, fired_at=NOW)
    deleted = add_reminder(db_session, user.id, "已删除", target_id=4, deleted_at=NOW)
    db_session.commit()

    assert fire_due_reminders(db_session, NOW) == 1
    for reminder in [due, future, fired, deleted]:
        db_session.refresh(reminder)
    assert due.fired_at == NOW
    assert future.fired_at is None
    assert fired.fired_at == NOW
    assert deleted.fired_at is None
    assert fire_due_reminders(db_session, NOW + timedelta(minutes=1)) == 1  # 未来提醒随后到点
    assert fire_due_reminders(db_session, NOW + timedelta(minutes=2)) == 0


def test_scan_rejects_naive_time(db_session: Session) -> None:
    with pytest.raises(ValueError, match="必须带时区"):
        fire_due_reminders(db_session, datetime(2026, 11, 10, 1, 0))


def test_notifications_only_return_fired_and_support_unread(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    unread = add_reminder(db_session, user["id"], "未读", fired_at=NOW)
    add_reminder(db_session, user["id"], "已读", target_id=2, fired_at=NOW, read_at=NOW)
    add_reminder(db_session, user["id"], "未来", target_id=3)
    add_reminder(db_session, user["id"], "删除", target_id=4, fired_at=NOW, deleted_at=NOW)
    db_session.commit()

    response = client.get("/api/v1/notifications", headers=headers, params={"unread": "true"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["unread_count"] == 1
    assert [item["id"] for item in data["items"]] == [unread.id]
    assert data["items"][0]["message"] == "未读"

    response = client.get("/api/v1/notifications", headers=headers)
    data = response.json()["data"]
    assert data["total"] == 2
    assert data["unread_count"] == 1
    assert {item["message"] for item in data["items"]} == {"未读", "已读"}


def test_mark_notification_read_is_idempotent(client: TestClient, db_session: Session) -> None:
    headers, user = auth_headers(client)
    reminder = add_reminder(db_session, user["id"], "待阅读", fired_at=NOW)
    db_session.commit()

    first = client.post(f"/api/v1/notifications/{reminder.id}/read", headers=headers)
    assert first.status_code == 200
    first_read_at = first.json()["data"]["read_at"]
    assert first_read_at is not None
    second = client.post(f"/api/v1/notifications/{reminder.id}/read", headers=headers)
    assert second.status_code == 200
    assert second.json()["data"]["read_at"] == first_read_at

    response = client.get("/api/v1/notifications", headers=headers, params={"unread": "true"})
    assert response.json()["data"]["unread_count"] == 0


def test_notifications_are_user_isolated_and_future_cannot_be_read(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    other_headers, other = auth_headers(client, "other")
    own = add_reminder(db_session, user["id"], "自己的", fired_at=NOW)
    other_reminder = add_reminder(db_session, other["id"], "他人的", fired_at=NOW)
    future = add_reminder(db_session, user["id"], "未来", target_id=2)
    db_session.commit()

    response = client.get("/api/v1/notifications", headers=headers)
    assert [item["id"] for item in response.json()["data"]["items"]] == [own.id]
    assert (
        client.post(f"/api/v1/notifications/{other_reminder.id}/read", headers=headers).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/notifications/{future.id}/read", headers=headers).status_code == 404
    )
    assert (
        client.post(f"/api/v1/notifications/{own.id}/read", headers=other_headers).status_code
        == 404
    )


def test_notifications_require_login_and_validate_query(client: TestClient) -> None:
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.post("/api/v1/notifications/1/read").status_code == 401
    headers, _ = auth_headers(client)
    response = client.get("/api/v1/notifications", headers=headers, params={"page_size": 101})
    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_scheduler_runs_scan_every_minute_without_overlap() -> None:
    scheduler = create_scheduler()
    job = scheduler.get_job("fire_due_reminders")
    assert job is not None
    assert job.trigger.interval == timedelta(minutes=1)
    assert job.max_instances == 1
    assert job.coalesce is True
