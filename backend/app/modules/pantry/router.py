"""食材批次、FEFO 消耗与临期查询路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.pantry.models import Ingredient
from app.modules.pantry.schemas import (
    ConsumeRequest,
    ExpiringQuery,
    IngredientCreate,
    IngredientListQuery,
    IngredientListResponse,
    IngredientResponse,
    IngredientUpdate,
)
from app.modules.pantry.service import (
    consume_ingredient,
    create_ingredient,
    delete_ingredient,
    get_ingredient,
    list_expiring_ingredients,
    list_ingredients,
    resolve_expiring_days,
    update_ingredient,
)

router = APIRouter(tags=["食材管家"])
DbSession = Annotated[Session, Depends(get_db)]


def serialize_ingredient(ingredient: Ingredient) -> dict:
    return IngredientResponse.model_validate(ingredient).model_dump(mode="json")


@router.post("/ingredients")
def create_ingredient_endpoint(
    data: IngredientCreate, db: DbSession, current_user: CurrentUser
) -> dict:
    return ok(serialize_ingredient(create_ingredient(db, current_user.id, data)), "入库成功")


@router.get("/ingredients")
def list_ingredients_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[IngredientListQuery, Depends()],
) -> dict:
    items, total = list_ingredients(db, current_user.id, query)
    result = IngredientListResponse(
        items=[IngredientResponse.model_validate(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.get("/ingredients/expiring")
def list_expiring_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[ExpiringQuery, Depends()],
) -> dict:
    days = resolve_expiring_days(current_user.settings_json, query.days)
    result = list_expiring_ingredients(db, current_user.id, days, current_user.timezone)
    return ok(result.model_dump(mode="json"))


@router.post("/ingredients/consume")
def consume_ingredient_endpoint(
    data: ConsumeRequest, db: DbSession, current_user: CurrentUser
) -> dict:
    result = consume_ingredient(db, current_user.id, data)
    return ok(result.model_dump(mode="json"), "扣减成功")


@router.get("/ingredients/{ingredient_id}")
def get_ingredient_endpoint(ingredient_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return ok(serialize_ingredient(get_ingredient(db, current_user.id, ingredient_id)))


@router.patch("/ingredients/{ingredient_id}")
def update_ingredient_endpoint(
    ingredient_id: int,
    data: IngredientUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    ingredient = update_ingredient(db, current_user.id, ingredient_id, data)
    return ok(serialize_ingredient(ingredient), "更新成功")


@router.delete("/ingredients/{ingredient_id}")
def delete_ingredient_endpoint(
    ingredient_id: int, db: DbSession, current_user: CurrentUser
) -> dict:
    delete_ingredient(db, current_user.id, ingredient_id)
    return ok(message="删除成功")
