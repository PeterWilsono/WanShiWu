"""AI 记录历史、状态筛选、取消、幂等与用户隔离测试。"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assistant.models import AssistantRecord, AssistantStatus

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient, username: str = "record-user") -> tuple[dict[str, str], dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def make_record(
    db: Session, user_id: int, status: AssistantStatus = AssistantStatus.PENDING, text: str = "测试"
) -> AssistantRecord:
    record = AssistantRecord(
        user_id=user_id,
        raw_text=text,
        intent="create_todo",
        parsed_json=[{"tool": "create_todo", "args": {"title": text}, "summary": text}],
        status=status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_record_list_supports_pagination_status_and_user_isolation(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    first = make_record(db_session, user["id"], text="第一条")
    make_record(db_session, user["id"], AssistantStatus.EXECUTED, "已执行")
    third = make_record(db_session, user["id"], text="第三条")
    _, other = auth_headers(client, "record-other")
    make_record(db_session, other["id"], text="他人记录")

    response = client.get(
        "/api/v1/assistant/records",
        headers=headers,
        params={"status": "pending", "page": 1, "page_size": 1},
    )
    second_page = client.get(
        "/api/v1/assistant/records",
        headers=headers,
        params={"status": "pending", "page": 2, "page_size": 1},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total"] == 2 and data["page_size"] == 1
    assert [item["id"] for item in data["items"]] == [third.id]
    assert data["items"][0]["parsed_json"][0]["args"]["title"] == "第三条"
    assert second_page.json()["data"]["items"][0]["id"] == first.id


def test_cancel_pending_record_marks_cancelled_without_business_execution(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    record = make_record(db_session, user["id"])

    response = client.post(f"/api/v1/assistant/records/{record.id}/cancel", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "cancelled"
    assert data["result_ref"] is None and data["executed_at"] is None
    db_session.refresh(record)
    assert record.status == AssistantStatus.CANCELLED


def test_cancel_repeated_or_executed_record_returns_conflict(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    cancelled = make_record(db_session, user["id"])
    executed = make_record(db_session, user["id"], AssistantStatus.EXECUTED)
    client.post(f"/api/v1/assistant/records/{cancelled.id}/cancel", headers=headers)

    repeated = client.post(f"/api/v1/assistant/records/{cancelled.id}/cancel", headers=headers)
    completed = client.post(f"/api/v1/assistant/records/{executed.id}/cancel", headers=headers)

    assert repeated.status_code == 409 and repeated.json()["code"] == 40901
    assert completed.status_code == 409 and completed.json()["code"] == 40901


def test_record_endpoints_require_auth_and_hide_other_users_records(
    client: TestClient, db_session: Session
) -> None:
    _, owner = auth_headers(client, "record-owner")
    record = make_record(db_session, owner["id"])
    headers, _ = auth_headers(client, "record-intruder")

    other_cancel = client.post(f"/api/v1/assistant/records/{record.id}/cancel", headers=headers)
    unauthenticated_list = client.get("/api/v1/assistant/records")
    unauthenticated_cancel = client.post(f"/api/v1/assistant/records/{record.id}/cancel")
    invalid_status = client.get(
        "/api/v1/assistant/records", headers=headers, params={"status": "unknown"}
    )

    assert other_cancel.status_code == 404 and other_cancel.json()["code"] == 40401
    assert unauthenticated_list.status_code == 401
    assert unauthenticated_cancel.status_code == 401
    assert invalid_status.status_code == 422 and invalid_status.json()["code"] == 40001
    db_session.refresh(record)
    assert record.status == AssistantStatus.PENDING
