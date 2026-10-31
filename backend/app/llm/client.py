"""统一 LLM 客户端：配置、超时、重试、限额和审计日志。"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from openai.types.chat import ChatCompletion
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.llm.models import LLMCallLog
from app.modules.auth.models import User


@dataclass(frozen=True)
class LLMToolCall:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class LLMResult:
    text: str
    tool_calls: list[LLMToolCall]
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class LLMClient:
    """业务模块只依赖本类；SDK 自带重试关闭，重试策略在这里统一实现。"""

    def __init__(
        self,
        db: Session,
        user_id: int,
        sdk_client: OpenAI | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.perf_counter,
        current_time: Callable[[], datetime] = now_utc,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.sdk = sdk_client or OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        self.sleep = sleep
        self.monotonic = monotonic
        self.current_time = current_time

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
        response_format: dict[str, object] | None = None,
        *,
        module: str,
        purpose: str,
    ) -> LLMResult:
        self._check_daily_limit()
        started = self.monotonic()
        for attempt in range(3):
            try:
                response = self.sdk.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    **self._optional_params(tools, response_format),
                )
                result = self._to_result(response, self._latency(started))
                self._write_log(module, purpose, result=result)
                return result
            except (ValueError, AttributeError) as exc:
                self._write_log(module, purpose, error_type="invalid_output", started=started)
                raise AppError(
                    ErrorCode.LLM_INVALID_OUTPUT, "AI 输出无法解析，请手动填写", 502
                ) from exc
            except Exception as exc:
                if attempt < 2 and self._is_retryable(exc):
                    self.sleep(0.5 * (2**attempt))
                    continue
                self._write_log(module, purpose, error_type=self._error_type(exc), started=started)
                raise AppError(
                    ErrorCode.LLM_CALL_FAILED, "AI 服务暂时不可用，请稍后重试或手动填写", 502
                ) from exc
        raise AssertionError("unreachable")

    @staticmethod
    def _optional_params(
        tools: list[dict[str, object]] | None, response_format: dict[str, object] | None
    ) -> dict[str, object]:
        params: dict[str, object] = {}
        if tools is not None:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        if response_format is not None:
            params["response_format"] = response_format
        return params

    def _check_daily_limit(self) -> None:
        user = self.db.get(User, self.user_id)
        if user is None:
            raise AppError(ErrorCode.UNAUTHORIZED, "用户不存在或登录已失效", 401)
        current = self.current_time()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("限额检查时间必须带时区")
        timezone = ZoneInfo(user.timezone)
        local_start = current.astimezone(timezone).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start = local_start.astimezone(UTC)
        end = (local_start + timedelta(days=1)).astimezone(UTC)
        count = (
            self.db.scalar(
                select(func.count())
                .select_from(LLMCallLog)
                .where(
                    LLMCallLog.user_id == self.user_id,
                    LLMCallLog.created_at >= start,
                    LLMCallLog.created_at < end,
                )
            )
            or 0
        )
        if count >= settings.daily_llm_call_limit:
            raise AppError(ErrorCode.LLM_DAILY_LIMIT, "今日 AI 调用次数已达上限，请明日再试", 429)

    def _to_result(self, response: ChatCompletion, latency_ms: int) -> LLMResult:
        choices = response.choices
        if not choices:
            raise ValueError("模型响应缺少 choices")
        message = choices[0].message
        tool_calls = []
        for call in message.tool_calls or []:
            arguments = json.loads(call.function.arguments)
            if not isinstance(arguments, dict):
                raise ValueError("工具参数必须是 JSON 对象")
            tool_calls.append(LLMToolCall(name=call.function.name, arguments=arguments))
        usage = getattr(response, "usage", None)
        return LLMResult(
            text=message.content or "",
            tool_calls=tool_calls,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )

    def _latency(self, started: float) -> int:
        return max(0, round((self.monotonic() - started) * 1000))

    def _write_log(
        self,
        module: str,
        purpose: str,
        *,
        result: LLMResult | None = None,
        error_type: str | None = None,
        started: float | None = None,
    ) -> None:
        self.db.add(
            LLMCallLog(
                user_id=self.user_id,
                module=module,
                purpose=purpose,
                model=settings.llm_model,
                prompt_tokens=result.prompt_tokens if result else 0,
                completion_tokens=result.completion_tokens if result else 0,
                latency_ms=(
                    result.latency_ms
                    if result
                    else self._latency(started if started is not None else self.monotonic())
                ),
                success=result is not None,
                error_type=error_type,
                created_at=self.current_time(),
            )
        )
        self.db.commit()

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        return isinstance(error, APIConnectionError) or (
            isinstance(error, APIStatusError) and error.status_code >= 500
        )

    @staticmethod
    def _error_type(error: Exception) -> str:
        if isinstance(error, APITimeoutError):
            return "timeout"
        if isinstance(error, APIConnectionError):
            return "network_error"
        if isinstance(error, APIStatusError):
            return "http_error"
        return "client_error"
