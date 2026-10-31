"""AI parse 流程测试：FakeLLMClient 预设结果，不访问真实模型。"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assistant.dependencies import get_llm_client
from app.assistant.models import AssistantRecord, AssistantStatus
from app.llm.client import LLMResult, LLMToolCall
from app.llm.fake import FakeLLMClient
from app.llm.schemas import TOOL_ARG_MODELS, CreateEventArgs
from app.main import app
from app.modules.life.models import Event, Todo, Transaction

PASSWORD = "correct-horse-123"
NOW = datetime(2026, 10, 30, 1, 0, tzinfo=UTC)


def auth_headers(client: TestClient, username: str = "assistant-user") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def llm_result(*calls: tuple[str, dict]) -> LLMResult:
    return LLMResult(
        text="",
        tool_calls=[LLMToolCall(name=name, arguments=args) for name, args in calls],
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=20,
    )


def use_fake(client: TestClient, fake: FakeLLMClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: fake


def parse(client: TestClient, headers: dict[str, str], text: str = "明天下午三点约了牙医"):
    return client.post("/api/v1/assistant/parse", headers=headers, json={"text": text})


def test_parse_event_injects_time_and_never_writes_business_data(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.assistant.service.now_utc", lambda: NOW)
    headers = auth_headers(client)
    fake = FakeLLMClient(
        [
            llm_result(
                (
                    "create_event",
                    {
                        "title": " 牙医 ",
                        "start_at": "2026-10-31T15:00:00+08:00",
                        "end_at": None,
                        "location": None,
                    },
                )
            )
        ]
    )
    use_fake(client, fake)

    response = parse(client, headers)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["record_id"] > 0 and data["clarification"] is None
    assert data["actions"] == [
        {
            "tool": "create_event",
            "args": {
                "title": "牙医",
                "start_at": "2026-10-31T15:00:00+08:00",
                "end_at": None,
                "location": None,
                "remind_before_min": None,
            },
            "summary": "新建日程：牙医，2026-10-31T15:00:00+08:00",
        }
    ]
    prompt = fake.calls[0]["messages"][0]["content"]
    assert "2026-10-30T09:00:00+08:00" in prompt
    assert "星期五" in prompt and "Asia/Shanghai" in prompt
    assert len(fake.calls[0]["tools"]) == 8
    assert db_session.scalar(select(func.count()).select_from(Event)) == 0
    assert db_session.scalar(select(func.count()).select_from(Todo)) == 0
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0
    record = db_session.get(AssistantRecord, data["record_id"])
    assert record.status == AssistantStatus.PENDING
    assert record.raw_text == "明天下午三点约了牙医"


def test_parse_supports_multiple_actions_and_json_number_amount(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient(
        [
            llm_result(
                ("add_expense", {"amount": 35.5, "category": "餐饮", "note": "午饭"}),
                ("create_todo", {"title": "交电费", "due_at": "2026-11-06T23:59:00+08:00"}),
            )
        ]
    )
    use_fake(client, fake)

    response = parse(client, headers, "午饭花了35.5，下周五前交电费")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [item["tool"] for item in data["actions"]] == ["add_expense", "create_todo"]
    assert data["actions"][0]["args"]["amount"] == 35.5
    assert isinstance(data["actions"][0]["args"]["amount"], float)
    record = db_session.get(AssistantRecord, data["record_id"])
    assert record.intent == "multi_action"
    assert len(record.parsed_json) == 2


def test_parse_clarification_has_no_executable_action(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient(
        [llm_result(("ask_clarification", {"question": "买了什么？花了多少钱？"}))]
    )
    use_fake(client, fake)

    response = parse(client, headers, "买了点东西")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["actions"] == []
    assert data["clarification"] == "买了什么？花了多少钱？"
    record = db_session.get(AssistantRecord, data["record_id"])
    assert record.intent == "ask_clarification"
    assert record.parsed_json[0]["tool"] == "ask_clarification"


def test_parse_invalid_tool_output_retries_once_then_succeeds(
    client: TestClient,
) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient(
        [
            llm_result(("unknown_tool", {})),
            llm_result(("create_todo", {"title": "交电费"})),
        ]
    )
    use_fake(client, fake)

    response = parse(client, headers, "周五前交电费")

    assert response.status_code == 200, response.text
    assert response.json()["data"]["actions"][0]["tool"] == "create_todo"
    assert len(fake.calls) == 2
    assert "未通过校验" in fake.calls[1]["messages"][-1]["content"]


def test_parse_twice_invalid_output_returns_50202_and_failed_record(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient(
        [
            llm_result(("add_expense", {"amount": -1, "category": "餐饮"})),
            llm_result(("create_event", {"title": "缺少开始时间"})),
        ]
    )
    use_fake(client, fake)

    response = parse(client, headers)

    assert response.status_code == 502
    assert response.json()["code"] == 50202
    assert len(fake.calls) == 2
    record = db_session.execute(select(AssistantRecord)).scalar_one()
    assert record.status == AssistantStatus.FAILED
    assert record.parsed_json == []


def test_parse_requires_auth_and_valid_text(client: TestClient) -> None:
    fake = FakeLLMClient([llm_result(("create_todo", {"title": "不应执行"}))])
    use_fake(client, fake)

    unauthenticated = client.post("/api/v1/assistant/parse", json={"text": "测试"})
    blank = client.post(
        "/api/v1/assistant/parse", headers=auth_headers(client), json={"text": "   "}
    )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["code"] == 40101
    assert blank.status_code == 422
    assert blank.json()["code"] == 40001
    assert fake.calls == []


def test_tool_schema_rejects_extra_fields_naive_time_and_bad_event_order() -> None:
    assert set(TOOL_ARG_MODELS) == {
        "create_todo",
        "create_event",
        "add_expense",
        "add_income",
        "add_ingredient",
        "save_bookmark",
        "create_trip",
        "ask_clarification",
    }
    with pytest.raises(ValidationError):
        CreateEventArgs.model_validate(
            {"title": "牙医", "start_at": "2026-10-31T15:00:00", "unexpected": True}
        )
    with pytest.raises(ValidationError):
        CreateEventArgs.model_validate(
            {
                "title": "牙医",
                "start_at": "2026-10-31T15:00:00+08:00",
                "end_at": "2026-10-31T14:00:00+08:00",
            }
        )
