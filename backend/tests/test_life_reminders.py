"""日程与提醒的同事务联动：创建、重排、清空、恢复和删除。"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.life.models import Event, Reminder, ReminderTargetType
from app.modules.life.schemas import EventCreate
from app.modules.life.service import create_event as create_event_service

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient) -> dict:
    client.post("/api/v1/auth/register", json={"username": "peter", "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": "peter", "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_event(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {"title": "项目评审", "start_at": "2026-11-10T09:00:00+08:00", **overrides}
    response = client.post("/api/v1/events", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def event_reminder(db: Session, event_id: int) -> Reminder:
    reminder = db.scalar(
        select(Reminder).where(
            Reminder.target_type == ReminderTargetType.EVENT,
            Reminder.target_id == event_id,
        )
    )
    assert reminder is not None
    return reminder


def test_create_event_with_reminder_uses_utc(client: TestClient, db_session: Session) -> None:
    headers = auth_headers(client)
    event = create_event(client, headers, remind_before_min=15)

    reminder = event_reminder(db_session, event["id"])
    assert reminder.user_id == 1
    assert reminder.remind_at == datetime(2026, 11, 10, 0, 45, tzinfo=UTC)
    assert reminder.message == "日程：项目评审"
    assert reminder.fired_at is None
    assert reminder.read_at is None
    assert reminder.deleted_at is None


def test_create_event_without_reminder_creates_no_row(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    create_event(client, headers)
    assert db_session.scalar(select(func.count()).select_from(Reminder)) == 0


def test_update_event_reschedules_and_resets_old_state(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    event = create_event(client, headers, remind_before_min=15)
    reminder = event_reminder(db_session, event["id"])
    fired_at = datetime(2026, 11, 10, 0, 45, tzinfo=UTC)
    reminder.fired_at = fired_at
    reminder.read_at = fired_at
    db_session.commit()

    # 仅改标题不改变提醒计划，已触发/已读状态保留，展示文案同步更新。
    response = client.patch(
        f"/api/v1/events/{event['id']}", headers=headers, json={"title": "季度评审"}
    )
    assert response.status_code == 200
    db_session.refresh(reminder)
    assert reminder.message == "日程：季度评审"
    assert reminder.fired_at == fired_at
    assert reminder.read_at == fired_at

    response = client.patch(
        f"/api/v1/events/{event['id']}",
        headers=headers,
        json={"start_at": "2026-11-10T10:00:00+08:00", "remind_before_min": 30},
    )
    assert response.status_code == 200
    db_session.refresh(reminder)
    assert reminder.remind_at == datetime(2026, 11, 10, 1, 30, tzinfo=UTC)
    assert reminder.fired_at is None
    assert reminder.read_at is None


def test_clear_and_restore_reminder_reuses_target_row(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    event = create_event(client, headers, remind_before_min=15)
    reminder = event_reminder(db_session, event["id"])
    reminder_id = reminder.id

    response = client.patch(
        f"/api/v1/events/{event['id']}", headers=headers, json={"remind_before_min": None}
    )
    assert response.status_code == 200
    db_session.refresh(reminder)
    assert reminder.deleted_at is not None

    response = client.patch(
        f"/api/v1/events/{event['id']}", headers=headers, json={"remind_before_min": 5}
    )
    assert response.status_code == 200, response.text
    db_session.refresh(reminder)
    assert reminder.id == reminder_id
    assert reminder.deleted_at is None
    assert reminder.remind_at == datetime(2026, 11, 10, 0, 55, tzinfo=UTC)
    assert db_session.scalar(select(func.count()).select_from(Reminder)) == 1


def test_delete_event_soft_deletes_reminder(client: TestClient, db_session: Session) -> None:
    headers = auth_headers(client)
    event = create_event(client, headers, remind_before_min=0)
    reminder = event_reminder(db_session, event["id"])

    response = client.delete(f"/api/v1/events/{event['id']}", headers=headers)
    assert response.status_code == 200
    db_session.refresh(reminder)
    assert reminder.deleted_at is not None
    assert db_session.get(Event, event["id"]).deleted_at is not None


def test_create_event_and_reminder_roll_back_together(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth_headers(client)
    original_commit = db_session.commit

    def fail_commit() -> None:
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        create_event_service(
            db_session,
            1,
            EventCreate(
                title="事务测试",
                start_at=datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
                remind_before_min=10,
            ),
        )
    monkeypatch.setattr(db_session, "commit", original_commit)
    assert db_session.scalar(select(func.count()).select_from(Event)) == 0
    assert db_session.scalar(select(func.count()).select_from(Reminder)) == 0
