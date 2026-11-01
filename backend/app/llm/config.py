"""解析当前用户的模型配置；用户配置优先，环境变量仅作本地开发兜底。"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.modules.auth.models import User
from app.modules.settings.crypto import decrypt_api_key
from app.modules.settings.models import LLMProvider, UserLLMConfig


@dataclass(frozen=True)
class LLMRuntimeConfig:
    provider: LLMProvider
    base_url: str
    model: str
    api_key: str
    timeout_seconds: int
    daily_call_limit: int


def _valid_api_key(value: str) -> bool:
    return bool(value.strip()) and value not in {"your-api-key-here", "change-me"}


def _daily_limit(user: User) -> int:
    configured = user.settings_json.get("daily_llm_call_limit", settings.daily_llm_call_limit)
    if isinstance(configured, int) and configured > 0:
        return configured
    return settings.daily_llm_call_limit


def resolve_llm_config(
    db: Session, user_id: int, *, allow_placeholder: bool = False
) -> LLMRuntimeConfig:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(ErrorCode.UNAUTHORIZED, "用户不存在或登录已失效", 401)

    active = user.settings_json.get("active_llm_provider")
    if active in {item.value for item in LLMProvider}:
        saved = db.scalar(
            select(UserLLMConfig).where(
                UserLLMConfig.user_id == user_id,
                UserLLMConfig.provider == active,
            )
        )
        if saved is not None:
            return LLMRuntimeConfig(
                provider=saved.provider,
                base_url=saved.base_url,
                model=saved.model,
                api_key=decrypt_api_key(saved.api_key_ciphertext),
                timeout_seconds=settings.llm_timeout_seconds,
                daily_call_limit=_daily_limit(user),
            )

    if allow_placeholder or _valid_api_key(settings.llm_api_key):
        return LLMRuntimeConfig(
            provider=LLMProvider.DEEPSEEK,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            daily_call_limit=_daily_limit(user),
        )
    raise AppError(
        ErrorCode.LLM_CALL_FAILED,
        "尚未配置 AI 模型，请到「我的 → 设置 → AI 模型」完成配置",
        503,
    )
