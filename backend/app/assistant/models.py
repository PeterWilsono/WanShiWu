"""AI 助手解析记录模型（PROJECT_SPEC.md 7.2）。"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, Index, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UserOwnedMixin
from app.db.types import UTCDateTime


class AssistantStatus(StrEnum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AssistantRecord(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "assistant_records"
    __table_args__ = (
        Index("ix_assistant_records_user_status_created_at", "user_id", "status", "created_at"),
        CheckConstraint("raw_text <> ''", name="ck_assistant_records_raw_text_not_empty"),
    )

    raw_text: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(50))
    parsed_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[AssistantStatus] = mapped_column(
        SqlEnum(
            AssistantStatus,
            values_callable=lambda enum_class: [member.value for member in enum_class],
            native_enum=False,
            length=20,
            validate_strings=True,
            create_constraint=True,
        ),
        default=AssistantStatus.PENDING,
    )
    result_ref: Mapped[str | None] = mapped_column(String(100))
    error: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
