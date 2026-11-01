"""收藏箱数据模型：收藏、标签、关联与每周回顾。"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UserOwnedMixin
from app.db.types import UTCDateTime


class BookmarkStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class TagSource(StrEnum):
    MANUAL = "manual"
    AI = "ai"


def constrained_enum(enum_class: type[StrEnum], length: int) -> SqlEnum:
    return SqlEnum(
        enum_class,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        length=length,
        validate_strings=True,
        create_constraint=True,
    )


class Bookmark(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_bookmarks_user_url"),
        Index("ix_bookmarks_user_status_created", "user_id", "status", "created_at"),
    )

    url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BookmarkStatus] = mapped_column(
        constrained_enum(BookmarkStatus, 20), default=BookmarkStatus.PENDING
    )
    fail_reason: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(500))
    source_domain: Mapped[str | None] = mapped_column(String(100))
    fetched_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Tag(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    name: Mapped[str] = mapped_column(String(30))


class BookmarkTag(Base):
    __tablename__ = "bookmark_tags"
    __table_args__ = (
        CheckConstraint("source IN ('manual', 'ai')", name="ck_bookmark_tags_source"),
    )

    bookmark_id: Mapped[int] = mapped_column(
        ForeignKey("bookmarks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[TagSource] = mapped_column(constrained_enum(TagSource, 10))


class WeeklyDigest(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "weekly_digests"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_digests_user_week"),
        CheckConstraint("bookmark_count >= 0", name="ck_weekly_digests_count_non_negative"),
    )

    week_start: Mapped[date] = mapped_column(Date)
    content_md: Mapped[str] = mapped_column(Text)
    bookmark_count: Mapped[int] = mapped_column(default=0)
