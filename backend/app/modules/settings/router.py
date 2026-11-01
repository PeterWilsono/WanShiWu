"""我的设置接口；所有配置按当前登录用户隔离。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.settings.models import LLMProvider
from app.modules.settings.schemas import (
    GeneralSettingsUpdate,
    LLMConfigUpdate,
    LLMConnectionTest,
)
from app.modules.settings.service import (
    delete_llm_config,
    get_settings,
    save_llm_config,
    test_llm_connection,
    update_general_settings,
)

router = APIRouter(prefix="/settings", tags=["个人设置"])
Db = Annotated[Session, Depends(get_db)]


@router.get("")
def read_settings(db: Db, current_user: CurrentUser) -> dict:
    return ok(get_settings(db, current_user).model_dump(mode="json"))


@router.put("/general")
def update_general(data: GeneralSettingsUpdate, db: Db, current_user: CurrentUser) -> dict:
    result = update_general_settings(current_user, data)
    db.commit()
    return ok(result.model_dump(mode="json"), "通用设置已保存")


@router.put("/llm/{provider}")
def update_llm_config(
    provider: LLMProvider, data: LLMConfigUpdate, db: Db, current_user: CurrentUser
) -> dict:
    result = save_llm_config(db, current_user, provider, data)
    return ok(result.model_dump(mode="json"), "模型配置已保存")


@router.post("/llm/{provider}/test")
def test_llm(
    provider: LLMProvider, data: LLMConnectionTest, db: Db, current_user: CurrentUser
) -> dict:
    result = test_llm_connection(db, current_user, provider, data)
    return ok(result.model_dump(mode="json"), result.message)


@router.delete("/llm/{provider}")
def remove_llm_config(provider: LLMProvider, db: Db, current_user: CurrentUser) -> dict:
    result = delete_llm_config(db, current_user, provider)
    return ok(result.model_dump(mode="json"), "模型配置已删除")
