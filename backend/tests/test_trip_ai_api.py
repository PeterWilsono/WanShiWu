"""AI 行程草稿的结构校验、金额换算、重试与零写库测试。"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.dependencies import get_llm_client
from app.llm.client import LLMResult
from app.llm.fake import FakeLLMClient
from app.main import app
from app.modules.trip.models import Trip, TripItem

PASSWORD = "correct-trip-ai-829"


def auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": "ai-traveler", "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": "ai-traveler", "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def result(payload: dict | str) -> LLMResult:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return LLMResult(text, [], 20, 10, 30)


def item(place: str = "西湖", start_time: str = "09:00", cost: float = 120.50) -> dict:
    return {"start_time": start_time, "place": place, "note": "慢行", "cost_yuan": cost}


def output(days: list[dict] | None = None) -> dict:
    return {"title": "杭州两日慢行", "days": days or [{"day_index": 1, "items": [item()]}]}


def generate(client: TestClient, headers: dict[str, str], **overrides):
    payload = {
        "destination": "杭州",
        "start_date": "2026-12-10",
        "days": 1,
        "budget_cents": 20000,
        "preferences": "少走路，多留空白",
    }
    payload.update(overrides)
    return client.post("/api/v1/trips/generate", json=payload, headers=headers)


def test_generate_valid_draft_converts_money_without_writing_database(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    days = [
        {"day_index": 1, "items": [item()]},
        {"day_index": 2, "items": [item("茶馆", "10:30", 0.25)]},
    ]
    llm = FakeLLMClient([result(output(days))])
    app.dependency_overrides[get_llm_client] = lambda: llm

    response = generate(client, headers, days=2)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["draft"]["generated_by"] == "ai"
    assert data["draft"]["status"] == "draft"
    assert data["draft"]["destination"] == "杭州"
    assert [entry["cost_cents"] for entry in data["draft"]["items"]] == [12050, 25]
    assert [entry["sort_order"] for entry in data["draft"]["items"]] == [0, 0]
    assert data["planned_cents"] == 12075
    assert data["budget_remaining_cents"] == 7925
    assert data["over_budget"] is False
    assert db_session.scalars(select(Trip)).all() == []
    assert db_session.scalars(select(TripItem)).all() == []
    assert llm.calls[0]["module"] == "trip"
    assert llm.calls[0]["response_format"] == {"type": "json_object"}
    assert "不可信" in llm.calls[0]["messages"][0]["content"]


def test_invalid_json_is_retried_once_with_correction(client: TestClient) -> None:
    headers = auth_headers(client)
    llm = FakeLLMClient([result("not-json"), result(output())])
    app.dependency_overrides[get_llm_client] = lambda: llm
    response = generate(client, headers)
    assert response.status_code == 200
    assert len(llm.calls) == 2
    assert "未通过校验" in llm.calls[1]["messages"][-1]["content"]


@pytest.mark.parametrize(
    ("days", "bad_output"),
    [
        (2, output()),
        (2, output([
            {"day_index": 1, "items": [item()]},
            {"day_index": 1, "items": [item("重复日期")]},
        ])),
        (1, output([{"day_index": 1, "items": []}])),
        (1, output([{"day_index": 1, "items": [item(start_time="10:00"), item("较晚", "09:00")]}])),
        (1, output([{"day_index": 1, "items": [item(cost=1.234)]}])),
        (1, {**output(), "planned_cents": 999}),
    ],
    ids=[
        "wrong-days", "nonconsecutive-days", "empty-day", "time-order", "money-scale", "extra-total"
    ],
)
def test_structurally_invalid_output_is_rejected_after_one_retry(
    client: TestClient, db_session: Session, days: int, bad_output: dict
) -> None:
    headers = auth_headers(client)
    llm = FakeLLMClient([result(bad_output), result(bad_output)])
    app.dependency_overrides[get_llm_client] = lambda: llm
    response = generate(client, headers, days=days)
    assert response.status_code == 502
    assert response.json()["code"] == 50202
    assert len(llm.calls) == 2
    assert db_session.scalars(select(Trip)).all() == []


def test_generate_requires_authentication_and_valid_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/trips/generate", json={"destination": "杭州", "days": 1}
    )
    assert response.status_code == 401
    headers = auth_headers(client)
    llm = FakeLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: llm
    assert generate(client, headers, days=0).status_code == 422
    assert generate(client, headers, budget_cents=-1).status_code == 422
    assert llm.calls == []
