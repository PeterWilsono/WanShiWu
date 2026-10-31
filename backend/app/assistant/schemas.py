"""AI 助手接口入参与出参。"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


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
