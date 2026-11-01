"""统一 AI 入口路由。"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.assistant.dependencies import LLMClientDependency
from app.assistant.schemas import (
    AssistantRecordListResponse,
    AssistantRecordResponse,
    ConfirmRequest,
    ConfirmResponse,
    ParseRequest,
    ParseResponse,
    RecordListQuery,
)
from app.assistant.service import cancel_record, confirm_actions, list_records, parse_text
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.inbox.dependencies import BookmarkProcessor

router = APIRouter(prefix="/assistant", tags=["AI 助手"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/parse")
def parse_endpoint(
    payload: ParseRequest,
    db: DbSession,
    current_user: CurrentUser,
    llm: LLMClientDependency,
) -> dict[str, object]:
    result: ParseResponse = parse_text(db, current_user, llm, payload.text)
    return ok(result.model_dump(mode="json"))


@router.post("/confirm")
def confirm_endpoint(
    payload: ConfirmRequest,
    db: DbSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    processor: BookmarkProcessor,
) -> dict[str, object]:
    result: ConfirmResponse = confirm_actions(db, current_user, payload)
    for item in result.results:
        if item.tool == "save_bookmark":
            background_tasks.add_task(processor, item.id, current_user.id)
    return ok(result.model_dump(mode="json"), message="已确认并写入")


@router.get("/records")
def records_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[RecordListQuery, Query()],
) -> dict[str, object]:
    result: AssistantRecordListResponse = list_records(db, current_user.id, query)
    return ok(result.model_dump(mode="json"))


@router.post("/records/{record_id}/cancel")
def cancel_record_endpoint(
    record_id: int, db: DbSession, current_user: CurrentUser
) -> dict[str, object]:
    record = cancel_record(db, current_user.id, record_id)
    result = AssistantRecordResponse.model_validate(record)
    return ok(result.model_dump(mode="json"), message="已取消待确认记录")
