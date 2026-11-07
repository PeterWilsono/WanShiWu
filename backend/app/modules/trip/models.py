"""旅行规划数据模型：行程主表与每日条目。"""

from datetime import date, time
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, String, Text, Time
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UserOwnedMixin


class GeneratedBy(StrEnum):
    MANUAL = "manual"
    AI = "ai"


class TripStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


class TripItemCategory(StrEnum):
    TRANSPORT = "transport"
    LODGING = "lodging"
    FOOD = "food"
    ACTIVITY = "activity"
    OTHER = "other"


def constrained_enum(enum_class: type[StrEnum], length: int) -> SqlEnum:
    return SqlEnum(
        enum_class,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        length=length,
        validate_strings=True,
        create_constraint=True,
    )


class Trip(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("days BETWEEN 1 AND 30", name="ck_trips_days_range"),
        CheckConstraint("travelers BETWEEN 1 AND 20", name="ck_trips_travelers_range"),
        CheckConstraint(
            "budget_cents IS NULL OR budget_cents >= 0", name="ck_trips_budget_non_negative"
        ),
        Index("ix_trips_user_start_date", "user_id", "start_date"),
    )

    title: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    days: Mapped[int] = mapped_column(default=1)
    travelers: Mapped[int] = mapped_column(default=1)
    budget_cents: Mapped[int | None] = mapped_column(BigInteger)
    preferences: Mapped[str | None] = mapped_column(Text)
    generated_by: Mapped[GeneratedBy] = mapped_column(
        constrained_enum(GeneratedBy, 10), default=GeneratedBy.MANUAL
    )
    status: Mapped[TripStatus] = mapped_column(
        constrained_enum(TripStatus, 10), default=TripStatus.DRAFT
    )


class TripItem(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "trip_items"
    __table_args__ = (
        CheckConstraint("day_index BETWEEN 1 AND 30", name="ck_trip_items_day_range"),
        CheckConstraint("sort_order >= 0", name="ck_trip_items_sort_non_negative"),
        CheckConstraint("cost_cents >= 0", name="ck_trip_items_cost_non_negative"),
        CheckConstraint(
            "actual_cost_cents IS NULL OR actual_cost_cents > 0",
            name="ck_trip_items_actual_cost_positive",
        ),
        Index("ix_trip_items_trip_day_sort", "trip_id", "day_index", "sort_order"),
    )

    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    day_index: Mapped[int]
    sort_order: Mapped[int] = mapped_column(default=0)
    start_time: Mapped[time | None] = mapped_column(Time)
    place: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    category: Mapped[TripItemCategory] = mapped_column(
        constrained_enum(TripItemCategory, 10), default=TripItemCategory.ACTIVITY
    )
    cost_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    actual_cost_cents: Mapped[int | None] = mapped_column(BigInteger)
    ledger_transaction_id: Mapped[int | None] = mapped_column(BigInteger)
