"""生活管家接口 Schema；字段与 PROJECT_SPEC.md 7.2 / 8.1 对应。"""

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.life.models import (
    Recurrence,
    ReminderTargetType,
    TodoStatus,
    TransactionSource,
    TransactionType,
)


def to_aware_utc(value: datetime | None) -> datetime | None:
    """接口时间必须带时区，进入业务层前统一转换为 UTC。"""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含时区偏移")
    return value.astimezone(UTC)


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="待办标题")
    note: str | None = Field(default=None, description="备注")
    due_at: datetime | None = Field(default=None, description="截止时间，ISO 8601 且带时区")
    priority: int = Field(default=2, ge=1, le=3, description="优先级：1 低 / 2 中 / 3 高")
    recurrence: Recurrence = Field(default=Recurrence.NONE, description="重复周期")
    tags: list[str] = Field(default_factory=list, description="标签字符串数组")

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime | None:
        return to_aware_utc(value)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in value:
            tag = tag.strip()
            if not tag:
                raise ValueError("标签不能为空白")
            if tag not in normalized:
                normalized.append(tag)
        return normalized


class TodoUpdate(BaseModel):
    """PATCH 入参：所有字段可选，未传与显式 null 由 exclude_unset 区分。"""

    title: str = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None)
    due_at: datetime | None = Field(default=None)
    priority: int = Field(default=None, ge=1, le=3)
    status: TodoStatus = Field(default=None)
    recurrence: Recurrence = Field(default=None)
    tags: list[str] = Field(default=None)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime | None:
        return to_aware_utc(value)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for tag in value:
            tag = tag.strip()
            if not tag:
                raise ValueError("标签不能为空白")
            if tag not in normalized:
                normalized.append(tag)
        return normalized


class TodoListQuery(BaseModel):
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数，最大 100")
    status: TodoStatus | None = Field(default=None, description="按状态筛选")
    due_after: datetime | None = Field(default=None, description="截止时间在此时之后（含）")
    due_before: datetime | None = Field(default=None, description="截止时间在此时之前（含）")
    tag: str | None = Field(default=None, description="按单个标签筛选")
    sort: Literal["due_at", "created_at", "priority"] = Field(
        default="created_at", description="排序字段"
    )
    order: Literal["asc", "desc"] = Field(default="desc", description="排序方向")


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    note: str | None
    due_at: datetime | None
    priority: int
    status: TodoStatus
    completed_at: datetime | None
    recurrence: Recurrence
    tags: list[str] = Field(validation_alias="tags_json")
    created_at: datetime
    updated_at: datetime


class TodoCompleteResponse(BaseModel):
    todo: TodoResponse = Field(description="已完成的当前待办")
    next_todo: TodoResponse | None = Field(description="周期待办生成的新实例；普通待办为 null")


class TodoListResponse(BaseModel):
    items: list[TodoResponse]
    total: int = Field(description="符合筛选条件的总条数")
    page: int
    page_size: int


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime = Field(description="开始时间，ISO 8601 且带时区")
    end_at: datetime | None = Field(default=None, description="结束时间，不得早于开始时间")
    all_day: bool = False
    location: str | None = Field(default=None, max_length=200)
    remind_before_min: int | None = Field(default=None, ge=0, description="提前提醒分钟数")
    note: str | None = None

    @field_validator("title", "location", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_event_time(cls, value: datetime | None) -> datetime | None:
        return to_aware_utc(value)

    @model_validator(mode="after")
    def validate_time_order(self) -> "EventCreate":
        if self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("结束时间不能早于开始时间")
        return self


class EventUpdate(BaseModel):
    """PATCH 入参；未传字段保持不变，可空字段允许显式传 null 清空。"""

    title: str = Field(default=None, min_length=1, max_length=200)
    start_at: datetime = Field(default=None, description="开始时间，不允许清空")
    end_at: datetime | None = Field(default=None)
    all_day: bool = Field(default=None)
    location: str | None = Field(default=None, max_length=200)
    remind_before_min: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None)

    @field_validator("title", "location", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_event_time(cls, value: datetime | None) -> datetime | None:
        return to_aware_utc(value)


class EventListQuery(BaseModel):
    """按日程与 [range_start, range_end] 窗口是否重叠筛选。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    range_start: datetime | None = Field(default=None, description="查询窗口开始（含）")
    range_end: datetime | None = Field(default=None, description="查询窗口结束（含）")


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    start_at: datetime
    end_at: datetime | None
    all_day: bool
    location: str | None
    remind_before_min: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    page_size: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    type: TransactionType
    icon: str | None = Field(default=None, max_length=30)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("icon")
    @classmethod
    def normalize_icon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class CategoryUpdate(BaseModel):
    """分类只允许改名称和图标；类型与内置标记不可通过 PATCH 修改。"""

    name: str = Field(default=None, min_length=1, max_length=30)
    icon: str | None = Field(default=None, max_length=30)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("icon")
    @classmethod
    def normalize_icon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: TransactionType
    icon: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class TransactionCreate(BaseModel):
    amount_cents: int = Field(gt=0, strict=True, description="金额，严格整数分")
    type: TransactionType
    category_id: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=200)
    occurred_at: datetime = Field(description="实际发生时间，ISO 8601 且带时区")
    source: TransactionSource = Field(default=TransactionSource.MANUAL)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        converted = to_aware_utc(value)
        assert converted is not None
        return converted


class TransactionUpdate(BaseModel):
    """PATCH 入参；非空字段不接受 null，备注可显式清空。"""

    amount_cents: int = Field(default=None, gt=0, strict=True)
    type: TransactionType = Field(default=None)
    category_id: int = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=200)
    occurred_at: datetime = Field(default=None)
    source: TransactionSource = Field(default=None)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime | None) -> datetime | None:
        return to_aware_utc(value)


class TransactionListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    month: str | None = Field(
        default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="月份 YYYY-MM，按用户时区"
    )
    category_id: int | None = Field(default=None, ge=1)
    type: TransactionType | None = None
    sort: Literal["occurred_at", "amount_cents", "created_at"] = "occurred_at"
    order: Literal["asc", "desc"] = "desc"


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount_cents: int
    type: TransactionType
    category_id: int
    category: CategoryResponse
    note: str | None
    occurred_at: datetime
    source: TransactionSource
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class NotificationListQuery(BaseModel):
    unread: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: ReminderTargetType
    target_id: int | None
    remind_at: datetime
    message: str
    fired_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class StatsMonthQuery(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="统计月份 YYYY-MM")


class CategoryStats(BaseModel):
    category_id: int
    category_name: str
    type: TransactionType
    amount_cents: int = Field(description="该分类当月金额，整数分")


class MonthlyStatsResponse(BaseModel):
    month: str
    income_cents: int = Field(description="当月总收入，整数分")
    expense_cents: int = Field(description="当月总支出，整数分")
    balance_cents: int = Field(description="收入减支出，可能为负数")
    categories: list[CategoryStats] = Field(description="按类型、金额排序的分类汇总")


class DailyExpenseStats(BaseModel):
    day: date = Field(serialization_alias="date", description="用户时区中的自然日")
    expense_cents: int = Field(description="当日支出，无账目时为 0")


class DailyStatsResponse(BaseModel):
    month: str
    days: list[DailyExpenseStats] = Field(description="从月初到月末的完整每日支出序列")
