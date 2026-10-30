"""认证路由（PROJECT_SPEC.md 8.4）。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.response import ok
from app.core.security import create_access_token
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.modules.auth.service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
def register(data: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    if not settings.allow_register:
        # 注册关闭时不暴露额外信息，按不可用资源处理。
        raise AppError(ErrorCode.NOT_FOUND, "资源不存在", 404)
    user = register_user(db, data)
    return ok(UserResponse.model_validate(user).model_dump(mode="json"), "注册成功")


@router.post("/login")
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    user = authenticate_user(db, data.username, data.password)
    token = TokenResponse(access_token=create_access_token(user.id))
    return ok(token.model_dump(), "登录成功")


@router.get("/me")
def me(current_user: CurrentUser) -> dict:
    return ok(UserResponse.model_validate(current_user).model_dump(mode="json"))
