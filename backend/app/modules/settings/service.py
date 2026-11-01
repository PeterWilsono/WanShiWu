"""个人设置、模型配置保存与真实连接测试。"""

import time
from collections.abc import Callable
from datetime import datetime

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.modules.auth.models import User
from app.modules.settings.crypto import decrypt_api_key, encrypt_api_key
from app.modules.settings.models import LLMProvider, UserLLMConfig
from app.modules.settings.schemas import (
    PROVIDER_DEFAULTS,
    GeneralSettingsResponse,
    GeneralSettingsUpdate,
    LLMConfigFields,
    LLMConfigUpdate,
    LLMProviderResponse,
    LLMTestResponse,
    SettingsResponse,
    validate_provider_fields,
)


def _get_config(db: Session, user_id: int, provider: LLMProvider) -> UserLLMConfig | None:
    return db.scalar(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == user_id,
            UserLLMConfig.provider == provider,
        )
    )


def _general(user: User) -> GeneralSettingsResponse:
    raw_days = user.settings_json.get("expiring_days", 3)
    raw_limit = user.settings_json.get("daily_llm_call_limit", settings.daily_llm_call_limit)
    return GeneralSettingsResponse(
        timezone=user.timezone,
        expiring_days=raw_days if isinstance(raw_days, int) else 3,
        daily_llm_call_limit=(
            raw_limit if isinstance(raw_limit, int) else settings.daily_llm_call_limit
        ),
    )


def _active_provider(user: User) -> LLMProvider | None:
    value = user.settings_json.get("active_llm_provider")
    return LLMProvider(value) if value in {item.value for item in LLMProvider} else None


def get_settings(db: Session, user: User) -> SettingsResponse:
    active = _active_provider(user)
    environment_configured = bool(settings.llm_api_key.strip()) and settings.llm_api_key not in {
        "your-api-key-here",
        "change-me",
    }
    providers = []
    for provider in LLMProvider:
        saved = _get_config(db, user.id, provider)
        defaults = PROVIDER_DEFAULTS[provider]
        use_environment = (
            saved is None and provider == LLMProvider.DEEPSEEK and environment_configured
        )
        providers.append(
            LLMProviderResponse(
                provider=provider,
                label=defaults["label"],
                base_url=(
                    saved.base_url
                    if saved
                    else settings.llm_base_url if use_environment else defaults["base_url"]
                ),
                model=(
                    saved.model
                    if saved
                    else settings.llm_model if use_environment else defaults["model"]
                ),
                configured=saved is not None or use_environment,
                source="user" if saved else "environment" if use_environment else "none",
                is_active=active == provider or (active is None and use_environment),
                key_hint=saved.key_hint if saved else None,
                last_tested_at=saved.last_tested_at if saved else None,
                last_test_success=saved.last_test_success if saved else None,
                last_test_error=saved.last_test_error if saved else None,
                console_url=defaults["console_url"],
            )
        )
    return SettingsResponse(general=_general(user), active_provider=active, providers=providers)


def update_general_settings(user: User, data: GeneralSettingsUpdate) -> GeneralSettingsResponse:
    user.timezone = data.timezone
    user.settings_json = {
        **user.settings_json,
        "expiring_days": data.expiring_days,
        "daily_llm_call_limit": data.daily_llm_call_limit,
    }
    return _general(user)


def save_llm_config(
    db: Session, user: User, provider: LLMProvider, data: LLMConfigUpdate
) -> SettingsResponse:
    try:
        base_url, model = validate_provider_fields(provider, data.base_url, data.model)
    except ValueError as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, str(exc), 422) from exc
    saved = _get_config(db, user.id, provider)
    if saved is None and not data.api_key:
        raise AppError(ErrorCode.VALIDATION_ERROR, "首次配置需要填写 API Key", 422)
    if saved is None:
        saved = UserLLMConfig(
            user_id=user.id,
            provider=provider,
            base_url=base_url,
            model=model,
            api_key_ciphertext="",
            key_hint="",
        )
        db.add(saved)
    saved.base_url = base_url
    saved.model = model
    if data.api_key:
        saved.api_key_ciphertext = encrypt_api_key(data.api_key)
        saved.key_hint = f"••••{data.api_key[-4:]}"
        saved.last_tested_at = None
        saved.last_test_success = None
        saved.last_test_error = None
    if data.is_active:
        user.settings_json = {**user.settings_json, "active_llm_provider": provider.value}
    db.commit()
    return get_settings(db, user)


def delete_llm_config(db: Session, user: User, provider: LLMProvider) -> SettingsResponse:
    saved = _get_config(db, user.id, provider)
    if saved is not None:
        db.delete(saved)
    if _active_provider(user) == provider:
        user.settings_json = {
            key: value
            for key, value in user.settings_json.items()
            if key != "active_llm_provider"
        }
    db.commit()
    return get_settings(db, user)


def _connection_error(exc: Exception) -> str:
    if isinstance(exc, APIStatusError):
        if exc.status_code in {401, 403}:
            return "API Key 无效或没有访问权限"
        if exc.status_code == 404:
            return "模型或接口地址不存在，请检查模型名称和 Base URL"
        if exc.status_code == 429:
            return "请求过于频繁或账户额度不足"
        if exc.status_code >= 500:
            return "模型服务暂时不可用，请稍后重试"
        return "模型拒绝了请求，请检查模型名称与账户状态"
    if isinstance(exc, APITimeoutError):
        return "连接超时，请检查网络后重试"
    if isinstance(exc, APIConnectionError):
        return "无法连接模型服务，请检查网络与 Base URL"
    return "连接测试失败，请检查配置后重试"


def _resolve_test_key(
    user: User, provider: LLMProvider, saved: UserLLMConfig | None, supplied: str | None
) -> str:
    if supplied:
        return supplied
    if saved is not None:
        return decrypt_api_key(saved.api_key_ciphertext)
    if (
        provider == LLMProvider.DEEPSEEK
        and settings.llm_api_key.strip()
        and settings.llm_api_key not in {"your-api-key-here", "change-me"}
    ):
        return settings.llm_api_key
    raise AppError(ErrorCode.VALIDATION_ERROR, "请先填写并保存 API Key，再测试连接", 422)


def test_llm_connection(
    db: Session,
    user: User,
    provider: LLMProvider,
    data: LLMConfigFields,
    *,
    sdk_factory: Callable[..., OpenAI] | None = None,
    monotonic: Callable[[], float] = time.perf_counter,
    current_time: Callable[[], datetime] = now_utc,
) -> LLMTestResponse:
    try:
        base_url, model = validate_provider_fields(provider, data.base_url, data.model)
    except ValueError as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, str(exc), 422) from exc
    saved = _get_config(db, user.id, provider)
    api_key = _resolve_test_key(user, provider, saved, data.api_key)
    started = monotonic()
    try:
        factory = sdk_factory or OpenAI
        sdk = factory(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        token_limit = (
            {"max_completion_tokens": 8}
            if provider == LLMProvider.MIMO
            else {"max_tokens": 8}
        )
        response = sdk.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "只回复：连接成功"}],
            **token_limit,
            stream=False,
        )
        if not response.choices:
            raise ValueError("empty choices")
        latency_ms = max(0, round((monotonic() - started) * 1000))
        result = LLMTestResponse(
            provider=provider,
            model=model,
            success=True,
            latency_ms=latency_ms,
            message="连接成功，模型已响应",
        )
        if saved is not None:
            saved.last_tested_at = current_time()
            saved.last_test_success = True
            saved.last_test_error = None
            db.commit()
        return result
    except AppError:
        raise
    except Exception as exc:
        message = _connection_error(exc)
        if saved is not None:
            saved.last_tested_at = current_time()
            saved.last_test_success = False
            saved.last_test_error = message
            db.commit()
        raise AppError(ErrorCode.LLM_CALL_FAILED, message, 502) from exc
