"""AI 菜谱生成与库存重核算；模型无权决定真实库存。"""

import json
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import nulls_last, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.llm.client import LLMClient
from app.llm.structured import parse_json_object
from app.modules.auth.models import User
from app.modules.pantry.models import Ingredient, IngredientStatus, IngredientUnit
from app.modules.pantry.schemas import (
    LLMRecipeOutput,
    Recipe,
    RecipeIngredient,
    RecipeRecommendRequest,
    RecipeRecommendResponse,
)

StockKey = tuple[str, IngredientUnit]


@lru_cache(maxsize=1)
def _recipe_prompt() -> str:
    prompt_path = Path(__file__).parents[2].joinpath("llm", "prompts", "recipe.txt")
    return prompt_path.read_text(encoding="utf-8")


def _inventory(db: Session, user_id: int) -> list[Ingredient]:
    """菜谱之间是备选关系，因此每道菜都基于同一份库存快照核算。"""
    return list(
        db.scalars(
            select(Ingredient)
            .where(
                Ingredient.user_id == user_id,
                Ingredient.status == IngredientStatus.ACTIVE,
                Ingredient.quantity > 0,
                Ingredient.deleted_at.is_(None),
            )
            .order_by(nulls_last(Ingredient.expire_on.asc()), Ingredient.created_at, Ingredient.id)
            .limit(200)
        ).all()
    )


def _messages(
    inventory: list[Ingredient], data: RecipeRecommendRequest, today: str
) -> list[dict[str, str]]:
    payload = {
        "today": today,
        "servings": data.servings,
        "preferences": data.preferences,
        "recommendation_mode": "inventory_first" if inventory else "free_with_shopping_list",
        "inventory": [
            {
                "name": item.name,
                "quantity": format(item.quantity, "f"),
                "unit": item.unit.value,
                "expire_on": item.expire_on.isoformat() if item.expire_on else None,
                "storage": item.storage.value,
            }
            for item in inventory
        ],
    }
    return [
        {"role": "system", "content": _recipe_prompt()},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _validate_output(text: str, *, inventory_empty: bool) -> LLMRecipeOutput:
    output = LLMRecipeOutput.model_validate(parse_json_object(text))
    if not inventory_empty and any(not recipe.uses for recipe in output.recipes):
        raise ValueError("有库存时每道菜至少需要一项现有食材")
    return output


def _reconcile(output: LLMRecipeOutput, inventory: list[Ingredient]) -> RecipeRecommendResponse:
    available: dict[StockKey, Decimal] = {}
    for item in inventory:
        key = (item.name, item.unit)
        available[key] = available.get(key, Decimal("0")) + item.quantity

    recipes: list[Recipe] = []
    for candidate in output.recipes:
        required: dict[StockKey, Decimal] = {}
        for item in [*candidate.uses, *candidate.missing]:
            key = (item.name, item.unit)
            required[key] = required.get(key, Decimal("0")) + item.quantity

        uses: list[RecipeIngredient] = []
        missing: list[RecipeIngredient] = []
        for (name, unit), quantity in required.items():
            in_stock = available.get((name, unit), Decimal("0"))
            used = min(in_stock, quantity).quantize(Decimal("0.01"))
            shortage = (quantity - used).quantize(Decimal("0.01"))
            if used > 0:
                uses.append(RecipeIngredient(name=name, quantity=used, unit=unit))
            if shortage > 0:
                missing.append(RecipeIngredient(name=name, quantity=shortage, unit=unit))
        recipes.append(
            Recipe(
                name=candidate.name,
                minutes=candidate.minutes,
                uses=uses,
                missing=missing,
                steps=candidate.steps,
            )
        )
    return RecipeRecommendResponse(recipes=recipes, inventory_empty=not inventory)


def recommend_recipes(
    db: Session,
    user: User,
    llm: LLMClient,
    data: RecipeRecommendRequest,
    *,
    current_time: datetime | None = None,
) -> RecipeRecommendResponse:
    current = current_time or now_utc()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("菜谱推荐时间必须带时区")
    today = current.astimezone(ZoneInfo(user.timezone)).date().isoformat()
    inventory = _inventory(db, user.id)
    messages = _messages(inventory, data, today)
    validated: LLMRecipeOutput | None = None
    last_error: ValueError | ValidationError | None = None

    for attempt in range(2):
        result = llm.chat(
            messages,
            response_format={"type": "json_object"},
            module="pantry",
            purpose="recipe",
        )
        try:
            validated = _validate_output(result.text, inventory_empty=not inventory)
            break
        except (ValueError, ValidationError) as exc:
            last_error = exc
            if attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上一次输出未通过菜谱 JSON 校验，"
                            "请严格按原始结构重新返回恰好 3 道菜。"
                        ),
                    }
                )

    if validated is None:
        raise AppError(
            ErrorCode.LLM_INVALID_OUTPUT,
            "AI 菜谱格式异常，请稍后重试",
            502,
        ) from last_error
    return _reconcile(validated, inventory)
