"""食材库存、FEFO 消耗与临期接口 Schema。"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.pantry.models import IngredientStatus, IngredientUnit, ShoppingSource, Storage


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit: IngredientUnit
    expire_on: date | None = None
    purchased_on: date | None = None
    storage: Storage
    note: str | None = Field(default=None, max_length=200)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    unit: IngredientUnit | None = None
    expire_on: date | None = None
    purchased_on: date | None = None
    storage: Storage | None = None
    status: IngredientStatus | None = None
    note: str | None = Field(default=None, max_length=200)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class IngredientListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    status: IngredientStatus | None = IngredientStatus.ACTIVE
    storage: Storage | None = None
    name: str | None = Field(default=None, max_length=50)


class IngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: Decimal
    unit: IngredientUnit
    expire_on: date | None
    purchased_on: date | None
    storage: Storage
    status: IngredientStatus
    note: str | None
    created_at: datetime
    updated_at: datetime


class IngredientListResponse(BaseModel):
    items: list[IngredientResponse]
    total: int
    page: int
    page_size: int


class ConsumeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit: IngredientUnit

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ConsumeBatchResult(BaseModel):
    ingredient_id: int
    consumed_quantity: Decimal
    remaining_quantity: Decimal
    status: IngredientStatus


class ConsumeResponse(BaseModel):
    name: str
    unit: IngredientUnit
    consumed_quantity: Decimal
    remaining_stock: Decimal
    batches: list[ConsumeBatchResult]


class ExpiringQuery(BaseModel):
    days: int | None = Field(default=None, ge=0, le=365)


class ExpiringIngredientResponse(IngredientResponse):
    days_to_expire: int


class ExpiringResponse(BaseModel):
    today: date
    days: int
    expired: list[ExpiringIngredientResponse]
    expiring: list[ExpiringIngredientResponse]


class ShoppingItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    unit: IngredientUnit | None = None
    source: ShoppingSource = ShoppingSource.MANUAL
    recipe_name: str | None = Field(default=None, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ShoppingItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    unit: IngredientUnit | None = None
    done: bool | None = None
    source: ShoppingSource | None = None
    recipe_name: str | None = Field(default=None, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ShoppingItemListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    done: bool | None = None
    source: ShoppingSource | None = None


class ShoppingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: Decimal | None
    unit: IngredientUnit | None
    done: bool
    source: ShoppingSource
    recipe_name: str | None
    created_at: datetime
    updated_at: datetime


class ShoppingItemListResponse(BaseModel):
    items: list[ShoppingItemResponse]
    total: int
    page: int
    page_size: int
