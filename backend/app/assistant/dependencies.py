"""AI 相关依赖；测试可覆盖此工厂注入 FakeLLMClient。"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.client import LLMClient
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User


def get_llm_client(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LLMClient:
    return LLMClient(db, current_user.id)


LLMClientDependency = Annotated[LLMClient, Depends(get_llm_client)]
