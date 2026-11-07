"""食材批次、FEFO 消耗与临期查询路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.assistant.dependencies import LLMClientDependency
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.pantry.models import Ingredient, ShoppingItem
from app.modules.pantry.recipe_service import recommend_recipes
from app.modules.pantry.schemas import (
    ConsumeRequest,
    CookRequest,
    ExpiringQuery,
    IngredientCreate,
    IngredientListQuery,
    IngredientListResponse,
    IngredientResponse,
    IngredientUpdate,
    RecipeRecommendRequest,
    RecipeShoppingRequest,
    RecipeShoppingResponse,
    ShoppingItemCreate,
    ShoppingItemListQuery,
    ShoppingItemListResponse,
    ShoppingItemResponse,
    ShoppingItemUpdate,
)
from app.modules.pantry.service import (
    add_recipe_missing_to_shopping,
    consume_ingredient,
    cook_recipe,
    create_ingredient,
    create_shopping_item,
    delete_ingredient,
    delete_shopping_item,
    get_ingredient,
    list_expiring_ingredients,
    list_ingredients,
    list_shopping_items,
    resolve_expiring_days,
    restore_ingredient,
    restore_shopping_item,
    update_ingredient,
    update_shopping_item,
)

router = APIRouter(tags=["食材管家"])
DbSession = Annotated[Session, Depends(get_db)]


def serialize_ingredient(ingredient: Ingredient) -> dict:
    return IngredientResponse.model_validate(ingredient).model_dump(mode="json")


def serialize_shopping_item(item: ShoppingItem) -> dict:
    return ShoppingItemResponse.model_validate(item).model_dump(mode="json")


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


@router.post("/pantry/recipes")
def recommend_recipes_endpoint(
    data: RecipeRecommendRequest,
    db: DbSession,
    current_user: CurrentUser,
    llm: LLMClientDependency,
) -> dict:
    result = recommend_recipes(db, current_user, llm, data)
    return ok(result.model_dump(mode="json"), "菜谱推荐成功")


@router.post("/pantry/cook")
def cook_recipe_endpoint(data: CookRequest, db: DbSession, current_user: CurrentUser) -> dict:
    result = cook_recipe(db, current_user.id, data)
    return ok(result.model_dump(mode="json"), "已按菜谱扣减库存")


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


@router.post("/ingredients/{ingredient_id}/restore")
def restore_ingredient_endpoint(
    ingredient_id: int, db: DbSession, current_user: CurrentUser
) -> dict:
    ingredient = restore_ingredient(db, current_user.id, ingredient_id)
    return ok(serialize_ingredient(ingredient), "恢复成功")


@router.delete("/ingredients/{ingredient_id}")
def delete_ingredient_endpoint(
    ingredient_id: int, db: DbSession, current_user: CurrentUser
) -> dict:
    delete_ingredient(db, current_user.id, ingredient_id)
    return ok(message="删除成功")


@router.post("/pantry/recipes/shopping-items")
def add_recipe_missing_endpoint(
    data: RecipeShoppingRequest, db: DbSession, current_user: CurrentUser
) -> dict:
    items = add_recipe_missing_to_shopping(db, current_user.id, data)
    result = RecipeShoppingResponse(
        items=[ShoppingItemResponse.model_validate(item) for item in items]
    )
    return ok(result.model_dump(mode="json"), "缺料已加入购物清单")


@router.post("/shopping-items")
def create_shopping_item_endpoint(
    data: ShoppingItemCreate, db: DbSession, current_user: CurrentUser
) -> dict:
    item = create_shopping_item(db, current_user.id, data)
    return ok(serialize_shopping_item(item), "添加成功")


@router.get("/shopping-items")
def list_shopping_items_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[ShoppingItemListQuery, Depends()],
) -> dict:
    items, total = list_shopping_items(db, current_user.id, query)
    result = ShoppingItemListResponse(
        items=[ShoppingItemResponse.model_validate(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.patch("/shopping-items/{item_id}")
def update_shopping_item_endpoint(
    item_id: int,
    data: ShoppingItemUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    item = update_shopping_item(db, current_user.id, item_id, data)
    return ok(serialize_shopping_item(item), "更新成功")


@router.post("/shopping-items/{item_id}/restore")
def restore_shopping_item_endpoint(item_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    item = restore_shopping_item(db, current_user.id, item_id)
    return ok(serialize_shopping_item(item), "恢复成功")


@router.delete("/shopping-items/{item_id}")
def delete_shopping_item_endpoint(item_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    delete_shopping_item(db, current_user.id, item_id)
    return ok(message="删除成功")
