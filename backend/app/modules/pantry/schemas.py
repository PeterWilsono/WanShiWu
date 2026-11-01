"""食材库存、FEFO 消耗与临期接口 Schema。"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class RecipeIngredient(BaseModel):
    """菜谱用量；单位与库存完全一致时才可扣减，本期不自动换算。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(strict=True, min_length=1, max_length=50)
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


class CookRequest(BaseModel):
    recipe_name: str = Field(min_length=1, max_length=100)
    uses: list[RecipeIngredient] = Field(min_length=1, max_length=50)

    @field_validator("recipe_name", mode="before")
    @classmethod
    def strip_recipe_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CookResponse(BaseModel):
    recipe_name: str
    consumed: list[ConsumeResponse]


class RecipeShoppingRequest(BaseModel):
    recipe_name: str = Field(min_length=1, max_length=100)
    missing: list[RecipeIngredient] = Field(min_length=1, max_length=50)

    @field_validator("recipe_name", mode="before")
    @classmethod
    def strip_recipe_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


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


class RecipeShoppingResponse(BaseModel):
    items: list[ShoppingItemResponse]


class RecipeRecommendRequest(BaseModel):
    preferences: str | None = Field(default=None, max_length=200)
    servings: int = Field(default=2, ge=1, le=12)

    @field_validator("preferences", mode="before")
    @classmethod
    def strip_preferences(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(strict=True, min_length=1, max_length=100)
    minutes: int = Field(strict=True, ge=1, le=480)
    uses: list[RecipeIngredient] = Field(max_length=50)
    missing: list[RecipeIngredient] = Field(max_length=50)
    steps: list[str] = Field(min_length=2, max_length=12)

    @field_validator("name")
    @classmethod
    def validate_recipe_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("菜谱名不能为空")
        return stripped

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, value: list[str]) -> list[str]:
        if any(not isinstance(step, str) or not 1 <= len(step.strip()) <= 200 for step in value):
            raise ValueError("每个步骤必须是 1 至 200 字的非空字符串")
        return [step.strip() for step in value]


class RecipeRecommendResponse(BaseModel):
    recipes: list[Recipe] = Field(min_length=3, max_length=3)
    inventory_empty: bool = False


class LLMRecipeIngredient(RecipeIngredient):
    """模型附带的说明字段不参与库存计算，可以安全忽略。"""

    model_config = ConfigDict(extra="ignore")


class LLMRecipe(Recipe):
    """兼容数字字符串；空库存时允许 uses 为空，由服务端统一列入缺料。"""

    model_config = ConfigDict(extra="ignore")

    minutes: int = Field(strict=False, ge=1, le=480)
    uses: list[LLMRecipeIngredient] = Field(max_length=50)
    missing: list[LLMRecipeIngredient] = Field(max_length=50)

    @model_validator(mode="after")
    def require_ingredients(self) -> "LLMRecipe":
        if not self.uses and not self.missing:
            raise ValueError("每道菜至少需要一项食材")
        return self


class LLMRecipeOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recipes: list[LLMRecipe] = Field(min_length=3, max_length=3)
