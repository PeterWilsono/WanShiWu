"""生活管家接口 Schema；字段与 PROJECT_SPEC.md 7.2 / 8.1 对应。"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.life.models import Recurrence, TodoStatus


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


class TodoListResponse(BaseModel):
    items: list[TodoResponse]
    total: int = Field(description="符合筛选条件的总条数")
    page: int
    page_size: int
