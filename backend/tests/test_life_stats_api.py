"""月度与每日收支统计接口测试。"""

from fastapi.testclient import TestClient

API = "/api/v1"


def register_user(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        f"{API}/auth/register", json={"username": username, "password": "test-password"}
    )
    assert response.status_code == 200
    login = client.post(
        f"{API}/auth/login", json={"username": username, "password": "test-password"}
    )
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def category_id(client: TestClient, headers: dict[str, str], name: str, kind: str) -> int:
    response = client.get(f"{API}/categories", headers=headers)
    return next(
        item["id"]
        for item in response.json()["data"]
        if item["name"] == name and item["type"] == kind
    )


def add_transaction(
    client: TestClient,
    headers: dict[str, str],
    *,
    amount_cents: int,
    kind: str,
    category: str,
    occurred_at: str,
) -> int:
    response = client.post(
        f"{API}/transactions",
        headers=headers,
        json={
            "amount_cents": amount_cents,
            "type": kind,
            "category_id": category_id(client, headers, category, kind),
            "occurred_at": occurred_at,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def test_monthly_stats_aggregate_totals_and_categories_in_user_timezone(
    client: TestClient,
) -> None:
    headers = register_user(client, "stats-monthly")
    add_transaction(
        client,
        headers,
        amount_cents=1000,
        kind="expense",
        category="餐饮",
        occurred_at="2026-03-01T00:00:00+08:00",
    )
    add_transaction(
        client,
        headers,
        amount_cents=2500,
        kind="expense",
        category="交通",
        occurred_at="2026-03-31T23:59:59+08:00",
    )
    add_transaction(
        client,
        headers,
        amount_cents=100000,
        kind="income",
        category="工资",
        occurred_at="2026-03-15T12:00:00+08:00",
    )
    # 下月月初、其他用户、软删除账目都不能进入本月统计。
    add_transaction(
        client,
        headers,
        amount_cents=9999,
        kind="expense",
        category="餐饮",
        occurred_at="2026-04-01T00:00:00+08:00",
    )
    deleted_id = add_transaction(
        client,
        headers,
        amount_cents=500,
        kind="expense",
        category="购物",
        occurred_at="2026-03-10T12:00:00+08:00",
    )
    assert client.delete(f"{API}/transactions/{deleted_id}", headers=headers).status_code == 200
    other_headers = register_user(client, "stats-other")
    add_transaction(
        client,
        other_headers,
        amount_cents=7777,
        kind="expense",
        category="餐饮",
        occurred_at="2026-03-10T12:00:00+08:00",
    )

    response = client.get(f"{API}/stats/monthly?month=2026-03", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["month"] == "2026-03"
    assert data["income_cents"] == 100000
    assert data["expense_cents"] == 3500
    assert data["balance_cents"] == 96500
    assert {(item["category_name"], item["amount_cents"]) for item in data["categories"]} == {
        ("工资", 100000),
        ("交通", 2500),
        ("餐饮", 1000),
    }


def test_daily_stats_return_complete_local_month_and_zero_fill(client: TestClient) -> None:
    headers = register_user(client, "stats-daily")
    for amount, category, occurred_at in [
        (1000, "餐饮", "2026-03-01T00:00:00+08:00"),
        (300, "餐饮", "2026-03-01T23:30:00+08:00"),
        (2500, "交通", "2026-03-31T23:59:59+08:00"),
        (100000, "工资", "2026-03-01T12:00:00+08:00"),
    ]:
        add_transaction(
            client,
            headers,
            amount_cents=amount,
            kind="income" if category == "工资" else "expense",
            category=category,
            occurred_at=occurred_at,
        )

    response = client.get(f"{API}/stats/daily?month=2026-03", headers=headers)

    assert response.status_code == 200
    days = response.json()["data"]["days"]
    assert len(days) == 31
    assert days[0] == {"date": "2026-03-01", "expense_cents": 1300}
    assert days[-1] == {"date": "2026-03-31", "expense_cents": 2500}
    assert all(item["expense_cents"] == 0 for item in days[1:-1])


def test_empty_month_return_zero_stats(client: TestClient) -> None:
    headers = register_user(client, "stats-empty")

    monthly = client.get(f"{API}/stats/monthly?month=2026-02", headers=headers)
    daily = client.get(f"{API}/stats/daily?month=2026-02", headers=headers)

    assert monthly.json()["data"] == {
        "month": "2026-02",
        "income_cents": 0,
        "expense_cents": 0,
        "balance_cents": 0,
        "categories": [],
    }
    assert len(daily.json()["data"]["days"]) == 28
    assert all(item["expense_cents"] == 0 for item in daily.json()["data"]["days"])


def test_stats_require_valid_month_and_authentication(client: TestClient) -> None:
    headers = register_user(client, "stats-validation")

    for path in ["/stats/monthly", "/stats/daily"]:
        assert client.get(f"{API}{path}?month=2026-03").status_code == 401
        assert client.get(f"{API}{path}", headers=headers).json()["code"] == 40001
        assert client.get(f"{API}{path}?month=2026-13", headers=headers).json()["code"] == 40001
