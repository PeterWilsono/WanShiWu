"""手动行程、每日预算、条目与单事务重排序测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.trip.models import Trip, TripItem
from app.modules.trip.schemas import ReorderRequest
from app.modules.trip.service import reorder_trip_items

PASSWORD = "correct-trip-569"


def auth_headers(client: TestClient, username: str = "traveler") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_trip(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "title": "杭州两日慢行",
        "destination": "杭州",
        "start_date": "2026-12-10",
        "days": 2,
        "budget_cents": 100000,
        "preferences": "少走路，多留空白",
        "items": [
            {"day_index": 1, "start_time": "09:00", "place": "西湖", "cost_cents": 35000},
            {"day_index": 2, "start_time": "10:30", "place": "茶馆", "cost_cents": 12000},
        ],
    }
    payload.update(overrides)
    response = client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_create_trip_calculates_budget_and_daily_subtotals(client: TestClient) -> None:
    headers = auth_headers(client)
    data = create_trip(client, headers)
    assert data["planned_cents"] == 47000
    assert data["budget_remaining_cents"] == 53000
    assert data["over_budget"] is False
    assert [day["subtotal_cents"] for day in data["daily_summaries"]] == [35000, 12000]
    assert data["daily_summaries"][0]["date"] == "2026-12-10"
    assert data["daily_summaries"][1]["date"] == "2026-12-11"
    assert data["items"][0]["start_time"] == "09:00:00"

    listed = client.get("/api/v1/trips?page_size=1", headers=headers).json()["data"]
    assert listed["total"] == 1 and len(listed["items"]) == 1


def test_update_trip_and_reject_shrinking_below_existing_items(client: TestClient) -> None:
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    response = client.patch(
        f"/api/v1/trips/{trip['id']}", json={"days": 1}, headers=headers
    )
    assert response.status_code == 422
    assert "不能缩短" in response.json()["message"]

    response = client.patch(
        f"/api/v1/trips/{trip['id']}",
        json={"title": "杭州三日", "days": 3, "budget_cents": 40000, "status": "confirmed"},
        headers=headers,
    )
    data = response.json()["data"]
    assert data["days"] == 3 and data["title"] == "杭州三日"
    assert data["status"] == "confirmed"
    assert data["over_budget"] is True and data["budget_remaining_cents"] == -7000


def test_add_update_delete_item_recalculates_budget(client: TestClient) -> None:
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    added = client.post(
        f"/api/v1/trips/{trip['id']}/items",
        json={"day_index": 1, "place": "博物馆", "cost_cents": 5000},
        headers=headers,
    )
    assert added.status_code == 200
    item = added.json()["data"]
    assert item["sort_order"] == 1

    updated = client.patch(
        f"/api/v1/trips/{trip['id']}/items/{item['id']}",
        json={"day_index": 2, "cost_cents": 6000, "note": "需预约"},
        headers=headers,
    )
    assert updated.json()["data"]["day_index"] == 2
    detail = client.get(f"/api/v1/trips/{trip['id']}", headers=headers).json()["data"]
    assert detail["planned_cents"] == 53000
    assert detail["daily_summaries"][1]["subtotal_cents"] == 18000

    assert client.patch(
        f"/api/v1/trips/{trip['id']}/items/{item['id']}",
        json={"day_index": 3}, headers=headers,
    ).status_code == 422
    assert client.delete(
        f"/api/v1/trips/{trip['id']}/items/{item['id']}", headers=headers
    ).status_code == 200
    detail = client.get(f"/api/v1/trips/{trip['id']}", headers=headers).json()["data"]
    assert detail["planned_cents"] == 47000


def test_reorder_across_days_returns_new_subtotals(client: TestClient) -> None:
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    first, second = trip["items"]
    response = client.put(
        f"/api/v1/trips/{trip['id']}/items/reorder",
        json={"items": [
            {"id": first["id"], "day_index": 2, "sort_order": 0},
            {"id": second["id"], "day_index": 1, "sort_order": 0},
        ]},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert [day["subtotal_cents"] for day in data["daily_summaries"]] == [12000, 35000]
    assert data["planned_cents"] == 47000


def test_reorder_rejects_missing_duplicate_and_foreign_items(client: TestClient) -> None:
    headers = auth_headers(client)
    other_headers = auth_headers(client, "other-traveler")
    trip = create_trip(client, headers)
    first, second = trip["items"]
    path = f"/api/v1/trips/{trip['id']}/items/reorder"
    missing = client.put(
        path, json={"items": [{"id": first["id"], "day_index": 1, "sort_order": 0}]},
        headers=headers,
    )
    assert missing.status_code == 422
    duplicate = client.put(
        path,
        json={"items": [
            {"id": first["id"], "day_index": 1, "sort_order": 0},
            {"id": first["id"], "day_index": 2, "sort_order": 0},
        ]},
        headers=headers,
    )
    assert duplicate.status_code == 422
    foreign = client.put(
        path,
        json={"items": [
            {"id": first["id"], "day_index": 1, "sort_order": 0},
            {"id": second["id"], "day_index": 2, "sort_order": 0},
        ]},
        headers=other_headers,
    )
    assert foreign.status_code == 404


def test_reorder_commit_failure_rolls_back_all_changes(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    first, second = trip["items"]
    original_commit = db_session.commit

    def fail_commit() -> None:
        raise RuntimeError("simulated reorder failure")

    db_session.commit = fail_commit
    with pytest.raises(RuntimeError, match="simulated reorder failure"):
        reorder_trip_items(
            db_session,
            1,
            trip["id"],
            ReorderRequest(items=[
                {"id": first["id"], "day_index": 2, "sort_order": 0},
                {"id": second["id"], "day_index": 1, "sort_order": 0},
            ]),
        )
    db_session.commit = original_commit
    db_session.rollback()
    items = db_session.scalars(select(TripItem).order_by(TripItem.id)).all()
    assert [(item.day_index, item.sort_order) for item in items] == [(1, 0), (2, 0)]


def test_delete_trip_soft_deletes_items_and_export_markdown(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    other_headers = auth_headers(client, "export-other")
    trip = create_trip(client, headers, budget_cents=40000)
    exported = client.get(f"/api/v1/trips/{trip['id']}/export?format=md", headers=headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "# 杭州两日慢行" in exported.text
    assert "预算余额：-70.00 元" in exported.text
    assert "当日小计：350.00 元" in exported.text
    assert client.get(f"/api/v1/trips/{trip['id']}", headers=other_headers).status_code == 404

    assert client.delete(f"/api/v1/trips/{trip['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/trips/{trip['id']}", headers=headers).status_code == 404
    assert db_session.get(Trip, trip["id"]).deleted_at is not None
    assert all(item.deleted_at is not None for item in db_session.scalars(select(TripItem)).all())


def test_trip_validation_and_authentication(client: TestClient) -> None:
    headers = auth_headers(client)
    assert client.post(
        "/api/v1/trips",
        json={"title": "错误", "destination": "杭州", "days": 1, "items": [
            {"day_index": 2, "place": "西湖", "cost_cents": 0}
        ]},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/trips/1/items", json={"day_index": 1, "place": "西湖", "cost_cents": -1},
        headers=headers,
    ).status_code in {404, 422}
    assert client.get("/api/v1/trips").status_code == 401
