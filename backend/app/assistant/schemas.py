"""AI 助手接口入参与出参。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class AssistantAction(BaseModel):
    tool: str
    args: dict[str, Any]
    summary: str


class ParseResponse(BaseModel):
    record_id: int
    actions: list[AssistantAction]
    clarification: str | None


class ConfirmRequest(BaseModel):
    record_id: int = Field(gt=0)
    actions: list[AssistantAction] = Field(min_length=1, max_length=5)


class ActionResult(BaseModel):
    tool: str
    ref: str
    id: int


class ConfirmResponse(BaseModel):
    record_id: int
    status: str
    results: list[ActionResult]


class AssistantRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_text: str
    intent: str
    parsed_json: list[dict[str, Any]]
    status: Literal["pending", "executed", "cancelled", "failed"]
    result_ref: str | None
    error: str | None
    executed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RecordListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Literal["pending", "executed", "cancelled", "failed"] | None = None


class AssistantRecordListResponse(BaseModel):
    items: list[AssistantRecordResponse]
    total: int
    page: int
    page_size: int
