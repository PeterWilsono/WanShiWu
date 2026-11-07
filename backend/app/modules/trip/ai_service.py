"""AI 行程草稿：严格校验、一次纠错重试、代码换算与预算汇总。"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.core.errors import AppError, ErrorCode
from app.llm.client import LLMClient
from app.llm.structured import parse_json_object
from app.modules.trip.models import GeneratedBy, TripStatus
from app.modules.trip.schemas import (
    LLMTripOutput,
    TripCreate,
    TripGenerateRequest,
    TripGenerateResponse,
    TripItemCreate,
)


@lru_cache(maxsize=1)
def _trip_prompt() -> str:
    path = Path(__file__).parents[2].joinpath("llm", "prompts", "trip_generate.txt")
    return path.read_text(encoding="utf-8")


def _messages(data: TripGenerateRequest) -> list[dict[str, str]]:
    payload = data.model_dump(mode="json")
    payload["budget_yuan"] = (
        str(data.budget_cents / 100) if data.budget_cents is not None else None
    )
    payload.pop("budget_cents", None)
    return [
        {"role": "system", "content": _trip_prompt()},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _convert_output(output: LLMTripOutput, data: TripGenerateRequest) -> TripGenerateResponse:
    if len(output.days) != data.days:
        raise ValueError("AI 返回天数与请求不一致")
    if [day.day_index for day in output.days] != list(range(1, data.days + 1)):
        raise ValueError("AI 返回的日期编号必须从 1 连续递增")
    items: list[TripItemCreate] = []
    for day in output.days:
        times = [item.start_time for item in day.items if item.start_time is not None]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValueError("同一天的时间必须严格升序且不能重复")
        for sort_order, item in enumerate(day.items):
            cost_cents = int((item.cost_yuan * 100).to_integral_exact())
            items.append(
                TripItemCreate(
                    day_index=day.day_index,
                    sort_order=sort_order,
                    start_time=item.start_time,
                    place=item.place,
                    note=item.note,
                    cost_cents=cost_cents,
                )
            )
    draft = TripCreate(
        title=output.title,
        destination=data.destination,
        start_date=data.start_date,
        days=data.days,
        travelers=data.travelers,
        budget_cents=data.budget_cents,
        preferences=data.preferences,
        generated_by=GeneratedBy.AI,
        status=TripStatus.DRAFT,
        items=items,
    )
    planned = sum(item.cost_cents for item in items)
    remaining = data.budget_cents - planned if data.budget_cents is not None else None
    return TripGenerateResponse(
        draft=draft,
        planned_cents=planned,
        budget_remaining_cents=remaining,
        over_budget=remaining is not None and remaining < 0,
    )


def generate_trip_draft(llm: LLMClient, data: TripGenerateRequest) -> TripGenerateResponse:
    messages = _messages(data)
    validated: TripGenerateResponse | None = None
    last_error: json.JSONDecodeError | ValidationError | ValueError | None = None
    for attempt in range(2):
        result = llm.chat(
            messages,
            response_format={"type": "json_object"},
            module="trip",
            purpose="trip_generate",
        )
        try:
            output = LLMTripOutput.model_validate(parse_json_object(result.text))
            validated = _convert_output(output, data)
            break
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上一次草稿未通过校验。请按原始 JSON 结构重新生成，"
                            "确保天数、连续日期、每天 1～8 项和时间顺序全部正确。"
                        ),
                    }
                )
    if validated is None:
        raise AppError(
            ErrorCode.LLM_INVALID_OUTPUT,
            "AI 行程格式异常，请手动创建或稍后重试",
            502,
        ) from last_error
    return validated
