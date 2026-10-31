"""统一 AI 入口路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.assistant.dependencies import LLMClientDependency
from app.assistant.schemas import ConfirmRequest, ConfirmResponse, ParseRequest, ParseResponse
from app.assistant.service import confirm_actions, parse_text
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser

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
    payload: ConfirmRequest, db: DbSession, current_user: CurrentUser
) -> dict[str, object]:
    result: ConfirmResponse = confirm_actions(db, current_user, payload)
    return ok(result.model_dump(mode="json"), message="已确认并写入")
