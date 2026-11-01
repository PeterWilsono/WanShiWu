"""个人设置与模型配置接口模型；响应中永远没有完整 API Key。"""

from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

from app.modules.settings.models import LLMProvider

PROVIDER_DEFAULTS: dict[LLMProvider, dict[str, str]] = {
    LLMProvider.MIMO: {
        "label": "小米 MiMo",
        "base_url": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.6-pro",
        "console_url": "https://platform.xiaomimimo.com/#/console/api-keys",
    },
    LLMProvider.DEEPSEEK: {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-flash",
        "console_url": "https://platform.deepseek.com/api_keys",
    },
}

ALLOWED_BASE_URLS: dict[LLMProvider, set[str]] = {
    LLMProvider.MIMO: {
        "https://api.xiaomimimo.com/v1",
        "https://token-plan-cn.xiaomimimo.com/v1",
    },
    LLMProvider.DEEPSEEK: {
        "https://api.deepseek.com",
        "https://api.deepseek.com/v1",
    },
}


class GeneralSettingsUpdate(BaseModel):
    timezone: str = Field(min_length=1, max_length=50)
    expiring_days: int = Field(ge=1, le=30)
    daily_llm_call_limit: int = Field(ge=1, le=10000)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (KeyError, ValueError) as exc:
            raise ValueError("无效的 IANA 时区") from exc
        return value


class GeneralSettingsResponse(BaseModel):
    timezone: str
    expiring_days: int
    daily_llm_call_limit: int


class LLMConfigFields(BaseModel):
    api_key: str | None = Field(default=None, max_length=256)
    base_url: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("api_key", "model", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().rstrip("/") or None


class LLMConfigUpdate(LLMConfigFields):
    is_active: bool = False


class LLMConnectionTest(LLMConfigFields):
    pass


class LLMProviderResponse(BaseModel):
    provider: LLMProvider
    label: str
    base_url: str
    model: str
    configured: bool
    source: str
    is_active: bool
    key_hint: str | None
    last_tested_at: datetime | None
    last_test_success: bool | None
    last_test_error: str | None
    console_url: str


class SettingsResponse(BaseModel):
    general: GeneralSettingsResponse
    active_provider: LLMProvider | None
    providers: list[LLMProviderResponse]


class LLMTestResponse(BaseModel):
    provider: LLMProvider
    model: str
    success: bool
    latency_ms: int
    message: str


def validate_provider_fields(
    provider: LLMProvider, base_url: str | None, model: str | None
) -> tuple[str, str]:
    defaults = PROVIDER_DEFAULTS[provider]
    normalized_url = base_url or defaults["base_url"]
    parsed = urlsplit(normalized_url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or normalized_url not in ALLOWED_BASE_URLS[provider]
    ):
        raise ValueError("Base URL 必须使用所选服务商的官方 HTTPS 地址")
    normalized_model = model or defaults["model"]
    if any(char.isspace() for char in normalized_model):
        raise ValueError("模型名称不能包含空白字符")
    return normalized_url, normalized_model
