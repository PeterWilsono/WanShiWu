"""统一 LLM 客户端测试；SDK 全部 mock，禁止真实网络调用。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, call

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.llm.client import LLMClient
from app.llm.models import LLMCallLog
from app.modules.auth.models import User

NOW = datetime(2026, 3, 15, 4, 0, tzinfo=UTC)


def create_user(db: Session) -> User:
    user = User(username="llm-user", password_hash="hash", timezone="Asia/Shanghai")
    db.add(user)
    db.commit()
    return user


def completion(arguments: str = '{"title":"看牙医"}') -> SimpleNamespace:
    function = SimpleNamespace(name="create_event", arguments=arguments)
    tool_call = SimpleNamespace(function=function)
    message = SimpleNamespace(content="已理解", tool_calls=[tool_call])
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=8),
    )


def make_client(db: Session, user_id: int, sdk: Mock, ticks: list[float]) -> tuple[LLMClient, Mock]:
    sleep = Mock()
    clock = iter(ticks)
    client = LLMClient(
        db,
        user_id,
        sdk_client=sdk,
        sleep=sleep,
        monotonic=lambda: next(clock),
        current_time=lambda: NOW,
    )
    return client, sleep


def api_error(status_code: int) -> APIStatusError:
    request = httpx2.Request("POST", "https://example.test/chat")
    return APIStatusError(
        "request failed", response=httpx2.Response(status_code, request=request), body=None
    )


def only_log(db: Session) -> LLMCallLog:
    return db.execute(select(LLMCallLog)).scalar_one()


def test_chat_returns_tools_usage_and_success_log(db_session: Session) -> None:
    user = create_user(db_session)
    sdk = Mock()
    sdk.chat.completions.create.return_value = completion()
    client, sleep = make_client(db_session, user.id, sdk, [100.0, 100.125])
    tools = [{"type": "function", "function": {"name": "create_event"}}]

    result = client.chat(
        [{"role": "user", "content": "明天看牙医"}],
        tools=tools,
        response_format={"type": "json_object"},
        module="assistant",
        purpose="intent_parse",
    )

    assert result.text == "已理解"
    assert result.tool_calls[0].name == "create_event"
    assert result.tool_calls[0].arguments == {"title": "看牙医"}
    assert (result.prompt_tokens, result.completion_tokens, result.latency_ms) == (12, 8, 125)
    sdk.chat.completions.create.assert_called_once()
    kwargs = sdk.chat.completions.create.call_args.kwargs
    assert kwargs["tools"] == tools and kwargs["tool_choice"] == "auto"
    assert kwargs["response_format"] == {"type": "json_object"}
    log = only_log(db_session)
    assert log.success is True and log.error_type is None
    assert (log.prompt_tokens, log.completion_tokens, log.latency_ms) == (12, 8, 125)
    assert not hasattr(log, "prompt") and not hasattr(log, "response")
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        APIConnectionError(
            message="offline", request=httpx2.Request("POST", "https://example.test/chat")
        ),
        api_error(500),
    ],
)
def test_network_and_5xx_retry_twice_then_succeed(db_session: Session, error: Exception) -> None:
    user = create_user(db_session)
    sdk = Mock()
    sdk.chat.completions.create.side_effect = [error, error, completion()]
    client, sleep = make_client(db_session, user.id, sdk, [100.0, 100.3])

    result = client.chat([{"role": "user", "content": "测试"}], module="assistant", purpose="test")

    assert result.text == "已理解"
    assert sdk.chat.completions.create.call_count == 3
    assert sleep.call_args_list == [call(0.5), call(1.0)]
    assert only_log(db_session).success is True


def test_4xx_does_not_retry_and_records_failure(db_session: Session) -> None:
    user = create_user(db_session)
    sdk = Mock()
    sdk.chat.completions.create.side_effect = api_error(400)
    client, sleep = make_client(db_session, user.id, sdk, [100.0, 100.2])

    with pytest.raises(AppError) as caught:
        client.chat([{"role": "user", "content": "测试"}], module="assistant", purpose="test")

    assert caught.value.code == ErrorCode.LLM_CALL_FAILED
    assert sdk.chat.completions.create.call_count == 1
    sleep.assert_not_called()
    log = only_log(db_session)
    assert log.success is False and log.error_type == "http_error"


def test_invalid_tool_json_returns_50202_and_logs(db_session: Session) -> None:
    user = create_user(db_session)
    sdk = Mock()
    sdk.chat.completions.create.return_value = completion("not-json")
    client, sleep = make_client(db_session, user.id, sdk, [100.0, 100.05, 100.1])

    with pytest.raises(AppError) as caught:
        client.chat([{"role": "user", "content": "测试"}], module="assistant", purpose="test")

    assert caught.value.code == ErrorCode.LLM_INVALID_OUTPUT
    assert sdk.chat.completions.create.call_count == 1
    sleep.assert_not_called()
    assert only_log(db_session).error_type == "invalid_output"


def test_daily_limit_uses_current_user_local_day(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = create_user(db_session)
    other = User(username="llm-other", password_hash="hash", timezone="Asia/Shanghai")
    db_session.add(other)
    db_session.commit()
    # NOW 是上海 12:00；其他用户当天和当前用户昨天的记录不占当前额度。
    db_session.add_all(
        [
            LLMCallLog(
                user_id=other.id,
                module="assistant",
                purpose="test",
                model="model",
                success=True,
                created_at=NOW,
            ),
            LLMCallLog(
                user_id=user.id,
                module="assistant",
                purpose="test",
                model="model",
                success=True,
                created_at=datetime(2026, 3, 14, 4, 0, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()
    monkeypatch.setattr(settings, "daily_llm_call_limit", 1)
    sdk = Mock()
    sdk.chat.completions.create.return_value = completion()
    client, _ = make_client(db_session, user.id, sdk, [100.0, 100.1])
    client.chat([{"role": "user", "content": "第一次"}], module="assistant", purpose="test")

    with pytest.raises(AppError) as caught:
        client.chat([{"role": "user", "content": "第二次"}], module="assistant", purpose="test")

    assert caught.value.code == ErrorCode.LLM_DAILY_LIMIT
    assert caught.value.http_status == 429
    assert sdk.chat.completions.create.call_count == 1
