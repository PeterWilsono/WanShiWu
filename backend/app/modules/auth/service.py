"""认证业务逻辑：路由只负责接收参数和返回结果，规则集中在 service。"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.security import hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import RegisterRequest
from app.modules.life.service import initialize_default_categories


def register_user(db: Session, data: RegisterRequest) -> User:
    """创建用户；用户名重复时由数据库唯一约束最终兜底。"""
    existing = db.scalar(select(User).where(User.username == data.username))
    if existing is not None:
        raise AppError(ErrorCode.CONFLICT, "用户名已存在", 409)

    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    try:
        # 先取得用户 id，再让默认分类与用户在同一个事务中落库。
        db.flush()
        initialize_default_categories(db, user.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(ErrorCode.CONFLICT, "用户名已存在", 409) from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    """校验登录凭据；用户不存在和密码错误使用同一提示，避免泄露账号是否存在。"""
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(ErrorCode.BAD_CREDENTIALS, "用户名或密码错误", 401)
    return user
