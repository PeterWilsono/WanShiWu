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


def test_get_event_detail_success(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    created = create_event(
        client,
        headers,
        "牙医复诊",
        end_at="2026-11-10T10:00:00+08:00",
        location="口腔医院",
        remind_before_min=30,
    )

    response = client.get(f"/api/v1/events/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["code"] == 0
    event = response.json()["data"]
    assert event["id"] == created["id"]
    assert event["title"] == "牙医复诊"
    assert event["location"] == "口腔医院"
    assert event["remind_before_min"] == 30
    assert "deleted_at" not in event


def test_update_event_partial_fields_and_normalize_time(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    created = create_event(
        client,
        headers,
        "原标题",
        end_at="2026-11-10T10:00:00+08:00",
        location="原地点",
        note="保留备注",
    )

    response = client.patch(
        f"/api/v1/events/{created['id']}",
        headers=headers,
        json={
            "title": "  新标题  ",
            "start_at": "2026-11-11T12:00:00+08:00",
            "end_at": "2026-11-11T13:30:00+08:00",
            "all_day": True,
            "location": "  新地点  ",
            "remind_before_min": 0,
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "更新成功"
    event = response.json()["data"]
    assert event["title"] == "新标题"
    assert event["location"] == "新地点"
    assert event["all_day"] is True
    assert event["remind_before_min"] == 0
    assert event["note"] == "保留备注"
    assert datetime.fromisoformat(event["start_at"].replace("Z", "+00:00")) == datetime(
        2026, 11, 11, 4, 0, tzinfo=UTC
    )
    assert datetime.fromisoformat(event["end_at"].replace("Z", "+00:00")) == datetime(
        2026, 11, 11, 5, 30, tzinfo=UTC
    )


def test_update_event_empty_object_keeps_values(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    created = create_event(client, headers, "保持不变", location="会议室")

    response = client.patch(f"/api/v1/events/{created['id']}", headers=headers, json={})

    assert response.status_code == 200
    event = response.json()["data"]
    assert event["title"] == created["title"]
    assert event["start_at"] == created["start_at"]
    assert event["location"] == created["location"]


def test_update_event_can_clear_only_nullable_fields(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    created = create_event(
        client,
        headers,
        "清空可选字段",
        end_at="2026-11-10T10:00:00+08:00",
        location="地点",
        remind_before_min=10,
        note="备注",
    )

    response = client.patch(
        f"/api/v1/events/{created['id']}",
        headers=headers,
        json={"end_at": None, "location": None, "remind_before_min": None, "note": None},
    )

    assert response.status_code == 200
    event = response.json()["data"]
    assert event["end_at"] is None
    assert event["location"] is None
    assert event["remind_before_min"] is None
    assert event["note"] is None
    assert event["title"] == created["title"]
    assert event["start_at"] == created["start_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"start_at": None},
        {"start_at": "2026-11-10T09:00:00"},
        {"end_at": "2026-11-10T10:00:00"},
        {"end_at": "2026-11-10T08:59:00+08:00"},
        {"start_at": "2026-11-10T11:00:00+08:00"},
        {"remind_before_min": -1},
    ],
)
def test_update_event_rejects_invalid_data_without_changes(
    client: TestClient, payload: dict
) -> None:
    headers, _ = auth_headers(client)
    created = create_event(
        client, headers, "原始日程", end_at="2026-11-10T10:00:00+08:00", remind_before_min=15
    )

    response = client.patch(f"/api/v1/events/{created['id']}", headers=headers, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == 40001
    current = client.get(f"/api/v1/events/{created['id']}", headers=headers).json()["data"]
    assert current["title"] == created["title"]
    assert current["start_at"] == created["start_at"]
    assert current["end_at"] == created["end_at"]
    assert current["remind_before_min"] == created["remind_before_min"]


def test_update_event_can_clear_end_then_move_start_later(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    created = create_event(client, headers, "先清空结束时间", end_at="2026-11-10T10:00:00+08:00")

    cleared = client.patch(
        f"/api/v1/events/{created['id']}", headers=headers, json={"end_at": None}
    )
    moved = client.patch(
        f"/api/v1/events/{created['id']}",
        headers=headers,
        json={"start_at": "2026-11-12T09:00:00+08:00"},
    )

    assert cleared.status_code == 200
    assert moved.status_code == 200
    assert moved.json()["data"]["end_at"] is None
    assert moved.json()["data"]["start_at"] == "2026-11-12T01:00:00Z"


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_event_detail_operations_require_login(client: TestClient, method: str) -> None:
    kwargs = {"json": {}} if method == "patch" else {}
    response = getattr(client, method)("/api/v1/events/1", **kwargs)
    assert response.status_code == 401
    assert response.json()["code"] == 40101


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_event_detail_operations_return_same_404_for_missing(
    client: TestClient, method: str
) -> None:
    headers, _ = auth_headers(client)
    kwargs = {"json": {}} if method == "patch" else {}
    response = getattr(client, method)("/api/v1/events/999999", headers=headers, **kwargs)
    assert response.status_code == 404
    assert response.json()["code"] == 40401
    assert response.json()["message"] == "日程不存在"


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_event_detail_operations_isolate_users(
    client: TestClient, db_session: Session, method: str
) -> None:
    owner_headers, owner = auth_headers(client, "owner")
    created = create_event(client, owner_headers, "仅本人可见")
    other_headers, _ = auth_headers(client, "other")
    kwargs = {"json": {"title": "越权修改"}} if method == "patch" else {}

    response = getattr(client, method)(
        f"/api/v1/events/{created['id']}", headers=other_headers, **kwargs
    )

    assert response.status_code == 404
    assert response.json()["code"] == 40401
    db_session.expire_all()
    event = db_session.get(Event, created["id"])
    assert event.user_id == owner["id"]
    assert event.title == "仅本人可见"
    assert event.deleted_at is None


def test_delete_event_is_soft_and_hidden_from_queries(
    client: TestClient, db_session: Session
) -> None:
    headers, _ = auth_headers(client)
    created = create_event(client, headers, "软删除日程")

    deleted = client.delete(f"/api/v1/events/{created['id']}", headers=headers)

    assert deleted.status_code == 200
    assert deleted.json() == {"code": 0, "message": "删除成功", "data": None}
    db_session.expire_all()
    stored = db_session.get(Event, created["id"])
    assert stored is not None
    assert stored.deleted_at is not None
    assert stored.deleted_at.tzinfo is not None

    detail = client.get(f"/api/v1/events/{created['id']}", headers=headers)
    listed = client.get("/api/v1/events", headers=headers).json()["data"]
    repeated = client.delete(f"/api/v1/events/{created['id']}", headers=headers)
    assert detail.status_code == 404
    assert detail.json()["code"] == 40401
    assert listed["total"] == 0
    assert listed["items"] == []
    assert repeated.status_code == 404
    assert repeated.json()["code"] == 40401
