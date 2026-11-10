"""AI 工具参数的唯一校验入口；模型输出和用户确认都必须经过这些模型。"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class ToolArgs(BaseModel):
    """禁止模型附加未登记字段，避免拼写错误被静默忽略。"""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CreateTodoArgs(ToolArgs):
    title: str = Field(min_length=1, max_length=200)
    due_at: AwareDatetime | None = None
    priority: int = Field(default=2, ge=1, le=3)
    note: str | None = Field(default=None, max_length=2000)


class CreateEventArgs(ToolArgs):
    title: str = Field(min_length=1, max_length=200)
    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    location: str | None = Field(default=None, max_length=200)
    remind_before_min: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_time_order(self) -> "CreateEventArgs":
        if self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("结束时间不能早于开始时间")
        return self


class MoneyArgs(ToolArgs):
    amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    category: str = Field(min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=200)
    occurred_at: AwareDatetime | None = None

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> int | float:
        """JSON 中金额仍为数字；确认写库时再由字符串精确换算为分。"""
        return int(value) if value == value.to_integral_value() else float(value)


class AddExpenseArgs(MoneyArgs):
    pass


class AddIncomeArgs(MoneyArgs):
    pass


class AddIngredientArgs(ToolArgs):
    name: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    unit: Literal["个", "克", "千克", "毫升", "升", "包", "瓶"]
    expire_on: date | None = None
    storage: Literal["fridge", "freezer", "room"] = "room"


class SaveBookmarkArgs(ToolArgs):
    url: AnyHttpUrl
    note: str | None = Field(default=None, max_length=500)


class CreateTripArgs(ToolArgs):
    destination: str = Field(min_length=1, max_length=100)
    days: int = Field(ge=1, le=30)
    budget: Decimal | None = Field(default=None, ge=0, le=Decimal("99999999.99"), decimal_places=2)
    preferences: str | None = Field(default=None, max_length=1000)


class AskClarificationArgs(ToolArgs):
    question: str = Field(min_length=1, max_length=500)


TOOL_ARG_MODELS: dict[str, type[ToolArgs]] = {
    "create_todo": CreateTodoArgs,
    "create_event": CreateEventArgs,
    "add_expense": AddExpenseArgs,
    "add_income": AddIncomeArgs,
    "add_ingredient": AddIngredientArgs,
    "save_bookmark": SaveBookmarkArgs,
    "create_trip": CreateTripArgs,
    "ask_clarification": AskClarificationArgs,
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "create_todo": (
        "新建待办：用户自己要完成的一件事，可带截止时间 due_at。"
        "带具体时间的个人安排（去踢球、跑步、交材料、买东西、打扫等）也用这个工具，"
        "它会同时出现在待办清单和日历里；地点等补充信息写入 note。"
    ),
    "create_event": (
        "新建日程：与他人约定、需要按时到场参加的会议、约见、就诊、面试、课程、"
        "婚礼、演出、航班或车次。日程只占时间段，不会出现在待办清单，因此不要用它记录"
        "用户自己要去完成的事。"
    ),
    "add_expense": "记录一笔支出，需要金额、分类和发生时间。",
    "add_income": "记录一笔收入，需要金额、分类和发生时间。",
    "add_ingredient": "把买到的食材加进库存，需要名称、数量、单位和存放方式。",
    "save_bookmark": "收藏一个网页链接，可附带备注。",
    "create_trip": "创建一个旅行计划草稿，需要目的地和天数。",
    "ask_clarification": "信息不足时只追问，不执行任何写入。",
}

TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": (
                f"万事屋动作：{TOOL_DESCRIPTIONS[name]} "
                "严格按参数 Schema 填写，不得附加字段。"
            ),
            "parameters": model.model_json_schema(),
            "strict": True,
        },
    }
    for name, model in TOOL_ARG_MODELS.items()
]
