"""users 表模型（PROJECT_SPEC.md 7.2）。

users 是特殊表：自身即用户主体，不含 user_id / deleted_at 等通用业务字段，
字段以 7.2 的 users 表定义为准（id / username / password_hash /
timezone / settings_json / created_at）。
"""

from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.base import Base
from app.db.types import UTCDateTime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # argon2 哈希，不可逆
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")
    # 个人设置：临期提醒天数、每日 LLM 上限等（7.2）
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc)
