"""收藏周报的用户时区、幂等与列表测试。"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.llm.client import LLMResult
from app.llm.fake import FakeLLMClient
from app.modules.auth.models import User
from app.modules.inbox.digest_service import (
    generate_due_weekly_digests,
    generate_weekly_digest,
)
from app.scheduler.reminders import create_scheduler

PASSWORD = "correct-weekly-569"
SUNDAY = datetime(2026, 11, 1, 12, 30, tzinfo=UTC)  # 上海周日 20:30


def auth_headers(client: TestClient, username: str = "weekly") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_weekly_digest_uses_fake_llm_and_user_isolation(client: TestClient, db_session) -> None:
    headers = auth_headers(client)
    other_headers = auth_headers(client, "other-weekly")
    client.post(
        "/api/v1/bookmarks",
        json={"url": "https://example.com/weekly", "title": "周读"},
        headers=headers,
    )
    user = db_session.get(User, 1)
    llm = FakeLLMClient([LLMResult("## 本周收藏回顾\n\n- 本周关注阅读。", [], 1, 1, 1)])
    digest = generate_weekly_digest(db_session, user, llm, current_time=SUNDAY)
    assert digest.week_start.isoformat() == "2026-10-26"
    assert digest.bookmark_count == 1
    assert "本周关注阅读" in digest.content_md

    repeated = generate_weekly_digest(db_session, user, llm, current_time=SUNDAY)
    assert repeated.id == digest.id
    assert len(llm.calls) == 1

    response = client.get("/api/v1/inbox/weekly-digests", headers=headers)
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["id"] == digest.id
    assert client.get("/api/v1/inbox/weekly-digests", headers=other_headers).json()[
        "data"
    ]["total"] == 0


def test_empty_week_does_not_call_llm(client: TestClient, db_session) -> None:
    auth_headers(client)
    llm = FakeLLMClient()
    digest = generate_weekly_digest(
        db_session, db_session.get(User, 1), llm, current_time=SUNDAY
    )
    assert digest.bookmark_count == 0
    assert "还没有新增收藏" in digest.content_md
    assert not llm.calls


def test_due_scan_respects_user_timezone_and_unique_week(client: TestClient, db_session) -> None:
    auth_headers(client)
    auth_headers(client, "utc-user")
    utc_user = db_session.get(User, 2)
    utc_user.timezone = "UTC"
    db_session.commit()
    def factory(db, user_id):
        return FakeLLMClient()

    assert generate_due_weekly_digests(db_session, factory, current_time=SUNDAY) == 1
    assert generate_due_weekly_digests(db_session, factory, current_time=SUNDAY) == 0
    monday = datetime(2026, 11, 2, 12, 30, tzinfo=UTC)
    assert generate_due_weekly_digests(db_session, factory, current_time=monday) == 0


def test_scheduler_registers_weekly_job() -> None:
    scheduler = create_scheduler()
    assert scheduler.get_job("generate_weekly_digests") is not None
