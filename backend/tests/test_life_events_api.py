"""日程新建与列表：时间校验、重叠范围、分页和用户数据隔离。"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.auth.models import User
from app.modules.life.models import Event

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient, username: str = "peter") -> tuple[dict, dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def create_event(client: TestClient, headers: dict, title: str, **overrides) -> dict:
    payload = {"title": title, "start_at": "2026-11-10T09:00:00+08:00", **overrides}
    response = client.post("/api/v1/events", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_create_event_success_and_normalize(client: TestClient) -> None:
    headers, _ = auth_headers(client)

    response = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "  项目评审会  ",
            "start_at": "2026-11-10T09:00:00+08:00",
            "end_at": "2026-11-10T10:30:00+08:00",
            "all_day": False,
            "location": "  3 号会议室  ",
            "remind_before_min": 15,
            "note": "准备季度数据",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "创建成功"
    event = response.json()["data"]
    assert event["title"] == "项目评审会"
    assert event["location"] == "3 号会议室"
    assert event["all_day"] is False
    assert event["remind_before_min"] == 15
    assert event["note"] == "准备季度数据"
    assert datetime.fromisoformat(event["start_at"].replace("Z", "+00:00")) == datetime(
        2026, 11, 10, 1, 0, tzinfo=UTC
    )
    assert datetime.fromisoformat(event["end_at"].replace("Z", "+00:00")) == datetime(
        2026, 11, 10, 2, 30, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "缺少开始时间"},
        {"title": "   ", "start_at": "2026-11-10T09:00:00+08:00"},
        {"title": "无时区开始", "start_at": "2026-11-10T09:00:00"},
        {
            "title": "无时区结束",
            "start_at": "2026-11-10T09:00:00+08:00",
            "end_at": "2026-11-10T10:00:00",
        },
        {
            "title": "结束早于开始",
            "start_at": "2026-11-10T09:00:00+08:00",
            "end_at": "2026-11-10T08:59:59+08:00",
        },
        {
            "title": "负数提醒",
            "start_at": "2026-11-10T09:00:00+08:00",
            "remind_before_min": -1,
        },
    ],
)
def test_create_event_validation_errors(client: TestClient, payload: dict) -> None:
    headers, _ = auth_headers(client)
    response = client.post("/api/v1/events", headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == 40001


@pytest.mark.parametrize("method", ["get", "post"])
def test_events_require_login(client: TestClient, method: str) -> None:
    kwargs = (
        {"json": {"title": "未登录", "start_at": "2026-11-10T09:00:00Z"}}
        if method == "post"
        else {}
    )
    response = getattr(client, method)("/api/v1/events", **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_list_events_excludes_other_users_and_soft_deleted(
    client: TestClient, db_session: Session
) -> None:
    headers, current_user = auth_headers(client)
    create_event(client, headers, "当前用户日程")
    other_user = User(username="other", password_hash="hash")
    db_session.add(other_user)
    db_session.commit()
    start_at = datetime(2026, 11, 10, 1, 0, tzinfo=UTC)
    db_session.add_all(
        [
            Event(user_id=other_user.id, title="其他用户日程", start_at=start_at),
            Event(
                user_id=current_user["id"],
                title="已删除日程",
                start_at=start_at,
                deleted_at=now_utc(),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/events", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["title"] for item in data["items"]] == ["当前用户日程"]


def test_list_events_uses_overlap_semantics(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    create_event(
        client, headers, "之前结束", start_at="2026-11-08T00:00:00Z", end_at="2026-11-09T00:00:00Z"
    )
    create_event(
        client,
        headers,
        "开始前结束在窗口内",
        start_at="2026-11-09T12:00:00Z",
        end_at="2026-11-10T12:00:00Z",
    )
    create_event(
        client,
        headers,
        "窗口内开始之后结束",
        start_at="2026-11-10T12:00:00Z",
        end_at="2026-11-12T00:00:00Z",
    )
    create_event(
        client,
        headers,
        "覆盖整个窗口",
        start_at="2026-11-01T00:00:00Z",
        end_at="2026-12-01T00:00:00Z",
    )
    create_event(client, headers, "之后开始", start_at="2026-11-12T00:00:00Z")
    create_event(client, headers, "窗口内单点", start_at="2026-11-10T08:00:00Z")
    create_event(client, headers, "窗口前单点", start_at="2026-11-09T23:00:00Z")

    response = client.get(
        "/api/v1/events",
        headers=headers,
        params={
            "range_start": "2026-11-10T00:00:00Z",
            "range_end": "2026-11-11T00:00:00Z",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 4
    assert [item["title"] for item in data["items"]] == [
        "覆盖整个窗口",
        "开始前结束在窗口内",
        "窗口内单点",
        "窗口内开始之后结束",
    ]


def test_list_events_pagination_and_start_time_order(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    for title, start_at in [
        ("第三天", "2026-11-12T08:00:00Z"),
        ("第一天", "2026-11-10T08:00:00Z"),
        ("第二天", "2026-11-11T08:00:00Z"),
    ]:
        create_event(client, headers, title, start_at=start_at)

    first = client.get(
        "/api/v1/events", headers=headers, params={"page": 1, "page_size": 2}
    ).json()["data"]
    second = client.get(
        "/api/v1/events", headers=headers, params={"page": 2, "page_size": 2}
    ).json()["data"]

    assert first["total"] == 3
    assert [item["title"] for item in first["items"]] == ["第一天", "第二天"]
    assert [item["title"] for item in second["items"]] == ["第三天"]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"range_start": "2026-11-10T00:00:00"},
        {
            "range_start": "2026-11-11T00:00:00Z",
            "range_end": "2026-11-10T00:00:00Z",
        },
    ],
)
def test_list_events_rejects_invalid_query(client: TestClient, params: dict) -> None:
    headers, _ = auth_headers(client)
    response = client.get("/api/v1/events", headers=headers, params=params)
    assert response.status_code == 422
    assert response.json()["code"] == 40001
