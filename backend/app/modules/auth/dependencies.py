"""认证依赖：供所有需要登录的接口复用。"""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.auth.models import User

_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="先通过 /api/v1/auth/login 获取 access_token",
)


def _unauthorized() -> AppError:
    return AppError(ErrorCode.UNAUTHORIZED, "未登录或令牌无效", 401)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """验证 Bearer JWT 并读取当前用户；任何认证失败均返回 40101。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise _unauthorized() from exc

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
