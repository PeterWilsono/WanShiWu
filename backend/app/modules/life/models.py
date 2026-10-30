"""生活管家数据模型（PROJECT_SPEC.md 7.2 / 7.3）。"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UserOwnedMixin
from app.db.types import UTCDateTime


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """让 SQLAlchemy 存枚举值（pending），而不是成员名（PENDING）。"""
    return [member.value for member in enum_class]


class TodoStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


class Recurrence(StrEnum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionSource(StrEnum):
    MANUAL = "manual"
    ASSISTANT = "assistant"
    PANTRY = "pantry"
    TRIP = "trip"


class Todo(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "todos"
    __table_args__ = (
        Index("ix_todos_user_status_due_at", "user_id", "status", "due_at"),
        CheckConstraint("priority BETWEEN 1 AND 3", name="ck_todos_priority_range"),
    )

    title: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    priority: Mapped[int] = mapped_column(SmallInteger, default=2)
    status: Mapped[TodoStatus] = mapped_column(
        SqlEnum(
            TodoStatus,
            values_callable=enum_values,
            native_enum=False,
            length=20,
            validate_strings=True,
            create_constraint=True,
        ),
        default=TodoStatus.PENDING,
    )
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    recurrence: Mapped[Recurrence] = mapped_column(
        SqlEnum(
            Recurrence,
            values_callable=enum_values,
            native_enum=False,
            length=20,
            validate_strings=True,
            create_constraint=True,
        ),
        default=Recurrence.NONE,
    )
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)


class Event(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_user_start_at", "user_id", "start_at"),
        CheckConstraint("end_at IS NULL OR end_at >= start_at", name="ck_events_end_after_start"),
        CheckConstraint(
            "remind_before_min IS NULL OR remind_before_min >= 0",
            name="ck_events_remind_before_non_negative",
        ),
    )

    title: Mapped[str] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(UTCDateTime)
    end_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    all_day: Mapped[bool] = mapped_column(default=False)
    location: Mapped[str | None] = mapped_column(String(200))
    remind_before_min: Mapped[int | None] = mapped_column()
    note: Mapped[str | None] = mapped_column(Text)


class Category(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "type", "name", name="uq_categories_user_type_name"),
    )

    name: Mapped[str] = mapped_column(String(30))
    type: Mapped[TransactionType] = mapped_column(
        SqlEnum(
            TransactionType,
            values_callable=enum_values,
            native_enum=False,
            length=10,
            validate_strings=True,
            create_constraint=True,
        )
    )
    icon: Mapped[str | None] = mapped_column(String(30))
    is_default: Mapped[bool] = mapped_column(default=False)


class Transaction(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_occurred_at", "user_id", "occurred_at"),
        Index("ix_transactions_user_category_id", "user_id", "category_id"),
        CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
    )

    amount_cents: Mapped[int] = mapped_column(BigInteger)
    type: Mapped[TransactionType] = mapped_column(
        SqlEnum(
            TransactionType,
            values_callable=enum_values,
            native_enum=False,
            length=10,
            validate_strings=True,
            create_constraint=True,
        )
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    note: Mapped[str | None] = mapped_column(String(200))
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime)
    source: Mapped[TransactionSource] = mapped_column(
        SqlEnum(
            TransactionSource,
            values_callable=enum_values,
            native_enum=False,
            length=20,
            validate_strings=True,
            create_constraint=True,
        ),
        default=TransactionSource.MANUAL,
    )

    category: Mapped[Category] = relationship()
