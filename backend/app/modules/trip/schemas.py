"""旅行规划请求、响应与预算结构。"""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.trip.models import GeneratedBy, TripStatus

MAX_MONEY_CENTS = 9_999_999_999


class TripItemCreate(BaseModel):
    day_index: int = Field(ge=1, le=30)
    sort_order: int | None = Field(default=None, ge=0)
    start_time: time | None = None
    place: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    cost_cents: int = Field(default=0, ge=0, le=MAX_MONEY_CENTS)


class TripItemUpdate(BaseModel):
    day_index: int | None = Field(default=None, ge=1, le=30)
    sort_order: int | None = Field(default=None, ge=0)
    start_time: time | None = None
    place: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    cost_cents: int | None = Field(default=None, ge=0, le=MAX_MONEY_CENTS)


class TripCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)
    start_date: date | None = None
    days: int = Field(ge=1, le=30)
    budget_cents: int | None = Field(default=None, ge=0, le=MAX_MONEY_CENTS)
    preferences: str | None = Field(default=None, max_length=1000)
    generated_by: GeneratedBy = GeneratedBy.MANUAL
    status: TripStatus = TripStatus.DRAFT
    items: list[TripItemCreate] = Field(default_factory=list, max_length=240)

    @model_validator(mode="after")
    def validate_item_days(self):
        if any(item.day_index > self.days for item in self.items):
            raise ValueError("行程条目的日期不能超过总天数")
        return self


class TripUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    destination: str | None = Field(default=None, min_length=1, max_length=100)
    start_date: date | None = None
    days: int | None = Field(default=None, ge=1, le=30)
    budget_cents: int | None = Field(default=None, ge=0, le=MAX_MONEY_CENTS)
    preferences: str | None = Field(default=None, max_length=1000)
    status: TripStatus | None = None


class ReorderItem(BaseModel):
    id: int = Field(ge=1)
    day_index: int = Field(ge=1, le=30)
    sort_order: int = Field(ge=0)


class ReorderRequest(BaseModel):
    items: list[ReorderItem] = Field(max_length=240)

    @model_validator(mode="after")
    def validate_unique_positions(self):
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("重排序条目 ID 不能重复")
        positions = [(item.day_index, item.sort_order) for item in self.items]
        if len(positions) != len(set(positions)):
            raise ValueError("同一天内不能有重复排序位置")
        return self


class TripItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    day_index: int
    sort_order: int
    start_time: time | None
    place: str
    note: str | None
    cost_cents: int
    created_at: datetime
    updated_at: datetime


class DaySummary(BaseModel):
    day_index: int
    date: date | None
    items: list[TripItemResponse]
    subtotal_cents: int


class TripResponse(BaseModel):
    id: int
    title: str
    destination: str
    start_date: date | None
    days: int
    budget_cents: int | None
    preferences: str | None
    generated_by: GeneratedBy
    status: TripStatus
    items: list[TripItemResponse]
    daily_summaries: list[DaySummary]
    planned_cents: int
    budget_remaining_cents: int | None
    over_budget: bool
    created_at: datetime
    updated_at: datetime


class TripListResponse(BaseModel):
    items: list[TripResponse]
    total: int
    page: int
    page_size: int


class TripGenerateRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=100)
    start_date: date | None = None
    days: int = Field(ge=1, le=30)
    budget_cents: int | None = Field(default=None, ge=0, le=MAX_MONEY_CENTS)
    preferences: str | None = Field(default=None, max_length=1000)
