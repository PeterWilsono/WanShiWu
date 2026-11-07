"""S5 旅行恢复、分类预算与真实花销联动。"""

from fastapi.testclient import TestClient

PASSWORD = "correct-trip-s5-482"


def auth_headers(client: TestClient, username: str = "trip-s5") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_trip(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "title": "成都三日",
            "destination": "成都",
            "start_date": "2026-12-20",
            "days": 3,
            "travelers": 2,
            "budget_cents": 300000,
            "items": [
                {
                    "day_index": 1,
                    "start_time": "08:30",
                    "place": "高铁前往成都",
                    "category": "transport",
                    "cost_cents": 50000,
                },
                {
                    "day_index": 2,
                    "start_time": "12:00",
                    "place": "社区川菜馆",
                    "category": "food",
                    "cost_cents": 12000,
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_restore_trip_and_item_preserves_earlier_individual_delete(client: TestClient) -> None:
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    first, second = trip["items"]
    assert trip["travelers"] == 2
    assert trip["actual_cents"] == 0
    assert [entry["category"] for entry in trip["category_summaries"]] == [
        "transport",
        "food",
    ]

    assert client.delete(
        f"/api/v1/trips/{trip['id']}/items/{second['id']}", headers=headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/trips/{trip['id']}/items/{second['id']}/restore", headers=headers
    ).status_code == 200
    assert client.delete(
        f"/api/v1/trips/{trip['id']}/items/{second['id']}", headers=headers
    ).status_code == 200

    assert client.delete(f"/api/v1/trips/{trip['id']}", headers=headers).status_code == 200
    assert client.get("/api/v1/trips", headers=headers).json()["data"]["items"] == []
    restored = client.post(f"/api/v1/trips/{trip['id']}/restore", headers=headers)
    assert restored.status_code == 200, restored.text
    data = restored.json()["data"]
    assert [item["id"] for item in data["items"]] == [first["id"]]
    assert data["planned_cents"] == 50000

    other = auth_headers(client, "trip-s5-other")
    assert client.post(f"/api/v1/trips/{trip['id']}/restore", headers=other).status_code == 404


def test_mark_spent_creates_one_real_trip_transaction(client: TestClient) -> None:
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    item = trip["items"][1]
    response = client.post(
        f"/api/v1/trips/{trip['id']}/items/{item['id']}/spend",
        headers=headers,
        json={"amount_cents": 13500, "occurred_at": "2026-12-21T12:20:00+08:00"},
    )
    assert response.status_code == 200, response.text
    spent = response.json()["data"]
    assert spent["actual_cost_cents"] == 13500
    transaction_id = spent["ledger_transaction_id"]
    assert transaction_id is not None

    transactions = client.get(
        "/api/v1/transactions?month=2026-12&page_size=100", headers=headers
    ).json()["data"]["items"]
    linked = [entry for entry in transactions if entry["id"] == transaction_id]
    assert len(linked) == 1
    assert linked[0]["source"] == "trip"
    assert linked[0]["amount_cents"] == 13500
    assert linked[0]["category"]["name"] == "餐饮"

    detail = client.get(f"/api/v1/trips/{trip['id']}", headers=headers).json()["data"]
    assert detail["actual_cents"] == 13500
    food = next(entry for entry in detail["category_summaries"] if entry["category"] == "food")
    assert food == {"category": "food", "planned_cents": 12000, "actual_cents": 13500}

    duplicate = client.post(
        f"/api/v1/trips/{trip['id']}/items/{item['id']}/spend",
        headers=headers,
        json={"amount_cents": 13500, "occurred_at": "2026-12-21T12:20:00+08:00"},
    )
    assert duplicate.status_code == 409
    assert len(client.get(
        "/api/v1/transactions?month=2026-12&page_size=100", headers=headers
    ).json()["data"]["items"]) == 1

    exported = client.get(f"/api/v1/trips/{trip['id']}/export?format=md", headers=headers)
    assert "同行人数：2 人" in exported.text
    assert "餐饮：预计 120.00 元，实际 135.00 元" in exported.text
