"""密码哈希与 JWT 签发/校验（PROJECT_SPEC.md 5.1 / 8.1）。

密码使用 argon2 单向哈希，数据库绝不保存原始密码；JWT 只存放用户 ID、
签发时间和过期时间，不存放密码、设置等敏感或易变化的数据。
"""

from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.time import now_utc

JWT_ALGORITHM = "HS256"
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """生成带随机盐的 argon2 哈希；相同密码每次得到的哈希也不同。"""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码；哈希无效时也返回 False，不把内部解析异常暴露给接口层。"""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    """签发访问令牌；sub 按 JWT 规范使用字符串。"""
    issued_at = now_utc()
    lifetime = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=lifetime),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """解码并验证签名、过期时间和必需字段；异常交由认证依赖统一转换。"""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )
