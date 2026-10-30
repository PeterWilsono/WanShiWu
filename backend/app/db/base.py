"""SQLAlchemy Base 与公共字段 mixin。

依据 PROJECT_SPEC.md 7.1：所有业务表默认包含
id / user_id / created_at / updated_at / deleted_at（软删除）。
users 等特殊表在 7.2 中单独列出字段，不使用这些 mixin。
"""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.time import now_utc
from app.db.types import UTCDateTime


class Base(DeclarativeBase):
    """所有模型的声明式基类（SQLAlchemy 2.0 风格，5.1）。"""


class UserOwnedMixin:
    """用户业务表通用主键与归属字段；所有查询都必须带 user_id（7.1）。"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class TimestampMixin:
    """created_at / updated_at 通用时间字段，UTC 存储（7.1）。"""

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, onupdate=now_utc)


class SoftDeleteMixin:
    """deleted_at 软删除字段：数据不物理删除，查询时过滤 IS NULL（7.1）。"""

    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
