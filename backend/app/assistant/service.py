"""AI 意图解析：调用模型、严格校验、保存待确认记录，不写业务表。"""

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.executors import DISPATCH
from app.assistant.models import AssistantRecord, AssistantStatus
from app.assistant.schemas import (
    ActionResult,
    AssistantAction,
    ConfirmRequest,
    ConfirmResponse,
    ParseResponse,
)
from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.llm.client import LLMClient, LLMResult
from app.llm.schemas import TOOL_ARG_MODELS, TOOL_DEFINITIONS, AskClarificationArgs
from app.modules.auth.models import User

_WEEKDAYS = "一二三四五六日"


@lru_cache(maxsize=1)
def _intent_prompt() -> str:
    return (
        Path(__file__)
        .parents[1]
        .joinpath("llm", "prompts", "intent.txt")
        .read_text(encoding="utf-8")
    )


def _messages(text: str, current_time: datetime, timezone: str) -> list[dict[str, str]]:
    local_time = current_time.astimezone(ZoneInfo(timezone))
    prompt = _intent_prompt().format(
        current_time=local_time.isoformat(),
        weekday=f"星期{_WEEKDAYS[local_time.weekday()]}",
        timezone=timezone,
    )
    return [{"role": "system", "content": prompt}, {"role": "user", "content": text}]


def _summary(tool: str, args: dict[str, object]) -> str:
    if tool == "create_todo":
        return f"新建待办：{args['title']}"
    if tool == "create_event":
        return f"新建日程：{args['title']}，{args['start_at']}"
    if tool in {"add_expense", "add_income"}:
        kind = "支出" if tool == "add_expense" else "收入"
        return f"记录{kind}：{args['amount']} 元（{args['category']}）"
    if tool == "add_ingredient":
        return f"添加食材：{args['name']} {args['quantity']} {args['unit']}"
    if tool == "save_bookmark":
        return f"收藏链接：{args['url']}"
    if tool == "create_trip":
        return f"创建旅行计划：{args['destination']}，{args['days']} 天"
    return str(args["question"])


def _validate_result(result: LLMResult) -> tuple[list[AssistantAction], str | None]:
    if not 1 <= len(result.tool_calls) <= 5:
        raise ValueError("工具调用数量必须为 1 至 5 个")
    actions: list[AssistantAction] = []
    clarification: str | None = None
    for call in result.tool_calls:
        model = TOOL_ARG_MODELS.get(call.name)
        if model is None:
            raise ValueError("模型返回了未登记工具")
        validated = model.model_validate(call.arguments)
        args = validated.model_dump(mode="json")
        if isinstance(validated, AskClarificationArgs):
            if len(result.tool_calls) != 1:
                raise ValueError("追问不能与其他动作混用")
            clarification = validated.question
        actions.append(
            AssistantAction(tool=call.name, args=args, summary=_summary(call.name, args))
        )
    return actions, clarification


def parse_text(
    db: Session,
    user: User,
    llm: LLMClient,
    text: str,
    *,
    current_time: datetime | None = None,
) -> ParseResponse:
    current = current_time or now_utc()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("解析时间必须带时区")
    messages = _messages(text, current, user.timezone)
    actions: list[AssistantAction] | None = None
    clarification: str | None = None
    last_error: ValidationError | ValueError | None = None
    for attempt in range(2):
        result = llm.chat(
            messages,
            tools=TOOL_DEFINITIONS,
            module="assistant",
            purpose="intent_parse",
        )
        try:
            actions, clarification = _validate_result(result)
            break
        except (ValidationError, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上一次工具输出未通过校验，请重新解析最初输入并严格按工具 Schema 返回。"
                        ),
                    }
                )

    if actions is None:
        record = AssistantRecord(
            user_id=user.id,
            raw_text=text,
            intent="parse_failed",
            parsed_json=[],
            status=AssistantStatus.FAILED,
            error="AI 输出未通过工具参数校验",
        )
        db.add(record)
        db.commit()
        raise AppError(ErrorCode.LLM_INVALID_OUTPUT, "AI 没有理解，请手动填写", 502) from last_error

    intent = actions[0].tool if len(actions) == 1 else "multi_action"
    record = AssistantRecord(
        user_id=user.id,
        raw_text=text,
        intent=intent,
        parsed_json=[action.model_dump(mode="json") for action in actions],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ParseResponse(
        record_id=record.id,
        actions=[action for action in actions if action.tool != "ask_clarification"],
        clarification=clarification,
    )


def _mark_failed(db: Session, record: AssistantRecord, message: str) -> None:
    record.status = AssistantStatus.FAILED
    record.error = message[:2000]
    record.result_ref = None
    record.executed_at = None
    db.commit()


def confirm_actions(
    db: Session, user: User, payload: ConfirmRequest, *, current_time: datetime | None = None
) -> ConfirmResponse:
    record = db.scalar(
        select(AssistantRecord).where(
            AssistantRecord.id == payload.record_id,
            AssistantRecord.user_id == user.id,
            AssistantRecord.deleted_at.is_(None),
        )
    )
    if record is None:
        raise AppError(ErrorCode.NOT_FOUND, "AI 解析记录不存在", 404)
    if record.status != AssistantStatus.PENDING:
        raise AppError(ErrorCode.CONFLICT, "该记录已处理，不能重复确认", 409)

    try:
        validated = [
            (action.tool, TOOL_ARG_MODELS[action.tool].model_validate(action.args))
            for action in payload.actions
        ]
        if any(tool == "ask_clarification" for tool, _ in validated):
            raise ValueError("追问动作需要补充信息，不能直接确认")
        unsupported = [tool for tool, _ in validated if tool not in DISPATCH]
        if unsupported:
            raise ValueError(f"动作所属模块尚未开放：{', '.join(unsupported)}")
    except (KeyError, ValidationError, ValueError) as exc:
        db.rollback()
        _mark_failed(db, record, f"确认参数校验失败：{exc}")
        raise AppError(ErrorCode.VALIDATION_ERROR, f"确认参数不合法：{exc}", 422) from exc

    results: list[ActionResult] = []
    try:
        for tool, args in validated:
            resource, resource_id = DISPATCH[tool](db, user.id, args)
            ref = f"{resource}:{resource_id}"
            results.append(ActionResult(tool=tool, ref=ref, id=resource_id))
        record.status = AssistantStatus.EXECUTED
        record.result_ref = ",".join(item.ref for item in results)
        record.error = None
        record.executed_at = current_time or now_utc()
        record.parsed_json = [
            AssistantAction(tool=tool, args=args.model_dump(mode="json"), summary="")
            .model_copy(update={"summary": _summary(tool, args.model_dump(mode="json"))})
            .model_dump(mode="json")
            for tool, args in validated
        ]
        db.commit()
    except AppError:
        db.rollback()
        _mark_failed(db, record, "业务规则校验失败，未写入任何动作")
        raise
    except Exception as exc:
        db.rollback()
        _mark_failed(db, record, f"执行失败：{exc}")
        raise

    return ConfirmResponse(record_id=record.id, status=record.status.value, results=results)
