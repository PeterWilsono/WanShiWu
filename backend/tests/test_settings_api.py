"""个人设置与模型配置测试；连接测试全部 mock，不访问真实服务。"""

from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import APIStatusError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.llm.client import LLMClient
from app.modules.auth.models import User
from app.modules.settings.models import LLMProvider, UserLLMConfig

PASSWORD = "correct-horse-123"
MIMO_KEY = "sk-mimo-secret-1234"
DEEPSEEK_KEY = "sk-deepseek-secret-5678"


def auth_headers(client: TestClient, username: str = "settings-user") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def save_provider(
    client: TestClient,
    headers: dict[str, str],
    provider: str,
    api_key: str | None,
    *,
    active: bool = True,
):
    return client.put(
        f"/api/v1/settings/llm/{provider}",
        headers=headers,
        json={"api_key": api_key, "is_active": active},
    )


def provider_data(response, provider: str) -> dict:
    return next(
        item for item in response.json()["data"]["providers"] if item["provider"] == provider
    )


def test_initial_settings_and_general_update(client: TestClient) -> None:
    headers = auth_headers(client)
    initial = client.get("/api/v1/settings", headers=headers)

    assert initial.status_code == 200
    assert initial.json()["data"]["general"] == {
        "timezone": "Asia/Shanghai",
        "expiring_days": 3,
        "daily_llm_call_limit": 200,
    }
    assert provider_data(initial, "mimo")["configured"] is False
    assert provider_data(initial, "mimo")["model"] == "mimo-v2.6-pro"
    assert provider_data(initial, "deepseek")["model"] == "deepseek-flash"

    updated = client.put(
        "/api/v1/settings/general",
        headers=headers,
        json={"timezone": "UTC", "expiring_days": 7, "daily_llm_call_limit": 20},
    )
    invalid = client.put(
        "/api/v1/settings/general",
        headers=headers,
        json={"timezone": "Mars/Base", "expiring_days": 7, "daily_llm_call_limit": 20},
    )

    assert updated.status_code == 200
    assert updated.json()["data"]["expiring_days"] == 7
    assert updated.json()["data"]["daily_llm_call_limit"] == 20
    assert invalid.status_code == 422


def test_save_two_providers_switch_and_preserve_keys(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    mimo = save_provider(client, headers, "mimo", MIMO_KEY)
    deepseek = save_provider(client, headers, "deepseek", DEEPSEEK_KEY)

    assert mimo.status_code == deepseek.status_code == 200
    assert MIMO_KEY not in mimo.text and DEEPSEEK_KEY not in deepseek.text
    assert provider_data(deepseek, "mimo")["key_hint"] == "••••1234"
    assert provider_data(deepseek, "mimo")["is_active"] is False
    assert provider_data(deepseek, "deepseek")["is_active"] is True
    saved_rows = db_session.scalars(select(UserLLMConfig)).all()
    assert len(saved_rows) == 2
    assert all(MIMO_KEY not in row.api_key_ciphertext for row in saved_rows)
    assert all(DEEPSEEK_KEY not in row.api_key_ciphertext for row in saved_rows)

    switched = save_provider(client, headers, "mimo", None)
    assert switched.status_code == 200
    assert provider_data(switched, "mimo")["is_active"] is True
    assert provider_data(switched, "deepseek")["is_active"] is False


def test_provider_requires_key_and_official_https_url(client: TestClient) -> None:
    headers = auth_headers(client)
    missing = save_provider(client, headers, "mimo", None)
    unofficial = client.put(
        "/api/v1/settings/llm/mimo",
        headers=headers,
        json={"api_key": MIMO_KEY, "base_url": "https://example.com/v1"},
    )
    insecure = client.put(
        "/api/v1/settings/llm/deepseek",
        headers=headers,
        json={"api_key": DEEPSEEK_KEY, "base_url": "http://api.deepseek.com"},
    )

    assert missing.status_code == 422
    assert unofficial.status_code == 422
    assert insecure.status_code == 422


def test_connection_test_success_uses_masked_saved_config(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = auth_headers(client)
    save_provider(client, headers, "mimo", MIMO_KEY)
    sdk = Mock()
    sdk.chat.completions.create.return_value = SimpleNamespace(choices=[object()])
    factory = Mock(return_value=sdk)
    monkeypatch.setattr("app.modules.settings.service.OpenAI", factory)

    response = client.post(
        "/api/v1/settings/llm/mimo/test", headers=headers, json={"api_key": None}
    )

    assert response.status_code == 200
    assert response.json()["data"]["success"] is True
    assert factory.call_args.kwargs["api_key"] == MIMO_KEY
    assert factory.call_args.kwargs["base_url"] == "https://api.xiaomimimo.com/v1"
    assert sdk.chat.completions.create.call_args.kwargs["model"] == "mimo-v2.6-pro"
    saved = db_session.scalar(select(UserLLMConfig))
    assert saved is not None and saved.last_test_success is True
    assert MIMO_KEY not in response.text


def test_connection_failure_is_sanitized_and_saved(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = auth_headers(client)
    save_provider(client, headers, "deepseek", DEEPSEEK_KEY)
    sdk = Mock()
    request = httpx2.Request("POST", "https://api.deepseek.com/chat/completions")
    sdk.chat.completions.create.side_effect = APIStatusError(
        f"invalid key {DEEPSEEK_KEY}",
        response=httpx2.Response(401, request=request),
        body=None,
    )
    monkeypatch.setattr("app.modules.settings.service.OpenAI", Mock(return_value=sdk))

    response = client.post("/api/v1/settings/llm/deepseek/test", headers=headers, json={})

    assert response.status_code == 502
    assert response.json()["message"] == "API Key 无效或没有访问权限"
    assert DEEPSEEK_KEY not in response.text
    saved = db_session.scalar(select(UserLLMConfig))
    assert saved is not None and saved.last_test_success is False


def test_configs_are_user_isolated_and_delete_clears_active(client: TestClient) -> None:
    first = auth_headers(client, "settings-first")
    save_provider(client, first, "mimo", MIMO_KEY)
    second = auth_headers(client, "settings-second")

    second_view = client.get("/api/v1/settings", headers=second)
    assert provider_data(second_view, "mimo")["configured"] is False
    removed = client.delete("/api/v1/settings/llm/mimo", headers=first)
    assert removed.status_code == 200
    assert provider_data(removed, "mimo")["configured"] is False
    assert removed.json()["data"]["active_provider"] is None


def test_settings_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/settings").status_code == 401
    assert client.post("/api/v1/settings/llm/mimo/test", json={}).status_code == 401


def test_llm_client_uses_selected_provider_and_per_user_limit(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(client)
    save_provider(client, headers, "mimo", MIMO_KEY)
    user = db_session.scalar(select(User).where(User.username == "settings-user"))
    assert user is not None
    sdk = Mock()
    sdk.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="好", tool_calls=[]))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
    )

    llm = LLMClient(db_session, user.id, sdk_client=sdk)
    result = llm.chat(
        [{"role": "user", "content": "你好"}], module="settings", purpose="test"
    )

    assert result.text == "好"
    assert llm.config.provider == LLMProvider.MIMO
    assert sdk.chat.completions.create.call_args.kwargs["model"] == "mimo-v2.6-pro"


def test_llm_client_explains_missing_configuration(db_session: Session) -> None:
    user = User(username="no-model", password_hash="hash", settings_json={})
    db_session.add(user)
    db_session.commit()

    llm = LLMClient(db_session, user.id)
    with pytest.raises(AppError) as caught:
        llm.chat([{"role": "user", "content": "你好"}], module="settings", purpose="test")

    assert caught.value.http_status == 503
    assert "我的 → 设置" in caught.value.message
