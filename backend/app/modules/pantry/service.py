"""食材管家业务逻辑；所有库存查询均限定当前用户。"""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, nulls_last, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.modules.pantry.models import Ingredient, IngredientStatus, ShoppingItem, ShoppingSource
from app.modules.pantry.schemas import (
    ConsumeBatchResult,
    ConsumeRequest,
    ConsumeResponse,
    CookRequest,
    CookResponse,
    ExpiringIngredientResponse,
    ExpiringResponse,
    IngredientCreate,
    IngredientListQuery,
    IngredientResponse,
    IngredientUpdate,
    RecipeShoppingRequest,
    ShoppingItemCreate,
    ShoppingItemListQuery,
    ShoppingItemUpdate,
)


def create_ingredient(
    db: Session, user_id: int, data: IngredientCreate, *, commit: bool = True
) -> Ingredient:
    """每次入库都创建新批次，不与同名旧批次合并。"""
    ingredient = Ingredient(user_id=user_id, **data.model_dump())
    db.add(ingredient)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(ingredient)
    return ingredient


def list_ingredients(
    db: Session, user_id: int, query: IngredientListQuery
) -> tuple[list[Ingredient], int]:
    filters = [Ingredient.user_id == user_id, Ingredient.deleted_at.is_(None)]
    if query.status is not None:
        filters.append(Ingredient.status == query.status)
    if query.storage is not None:
        filters.append(Ingredient.storage == query.storage)
    if query.name and query.name.strip():
        filters.append(Ingredient.name == query.name.strip())
    total = db.scalar(select(func.count()).select_from(Ingredient).where(*filters)) or 0
    statement = (
        select(Ingredient)
        .where(*filters)
        .order_by(
            Ingredient.storage,
            nulls_last(Ingredient.expire_on.asc()),
            Ingredient.created_at,
            Ingredient.id,
        )
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    return list(db.scalars(statement).all()), total


def get_ingredient(db: Session, user_id: int, ingredient_id: int) -> Ingredient:
    ingredient = db.scalar(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.user_id == user_id,
            Ingredient.deleted_at.is_(None),
        )
    )
    if ingredient is None:
        raise AppError(ErrorCode.NOT_FOUND, "食材批次不存在", 404)
    return ingredient


def update_ingredient(
    db: Session, user_id: int, ingredient_id: int, data: IngredientUpdate
) -> Ingredient:
    ingredient = get_ingredient(db, user_id, ingredient_id)
    updates = data.model_dump(exclude_unset=True)
    quantity = updates.get("quantity", ingredient.quantity)
    status = updates.get("status", ingredient.status)
    if status == IngredientStatus.USED_UP or quantity == 0:
        quantity = Decimal("0")
        status = IngredientStatus.USED_UP
    if status == IngredientStatus.ACTIVE and quantity <= 0:
        raise AppError(ErrorCode.BUSINESS_RULE_VIOLATION, "active 批次的数量必须大于 0", 422)
    updates["quantity"] = quantity
    updates["status"] = status
    for field, value in updates.items():
        setattr(ingredient, field, value)
    db.commit()
    db.refresh(ingredient)
    return ingredient


def delete_ingredient(db: Session, user_id: int, ingredient_id: int) -> None:
    ingredient = get_ingredient(db, user_id, ingredient_id)
    ingredient.deleted_at = now_utc()
    db.commit()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def consume_ingredient(
    db: Session, user_id: int, data: ConsumeRequest, *, commit: bool = True
) -> ConsumeResponse:
    """按 FEFO 扣减；库存不足时在任何写入之前返回精确缺口。

    commit=False 供 cook 等多食材事务复用，由最外层统一提交或回滚。
    """
    filters = [
        Ingredient.user_id == user_id,
        Ingredient.name == data.name,
        Ingredient.unit == data.unit,
        Ingredient.status == IngredientStatus.ACTIVE,
        Ingredient.quantity > 0,
        Ingredient.deleted_at.is_(None),
    ]
    batches = list(
        db.scalars(
            select(Ingredient)
            .where(*filters)
            .order_by(nulls_last(Ingredient.expire_on.asc()), Ingredient.created_at, Ingredient.id)
        ).all()
    )
    available = sum((batch.quantity for batch in batches), Decimal("0"))
    if available < data.quantity:
        same_name_units = list(
            db.scalars(
                select(Ingredient.unit)
                .where(
                    Ingredient.user_id == user_id,
                    Ingredient.name == data.name,
                    Ingredient.status == IngredientStatus.ACTIVE,
                    Ingredient.quantity > 0,
                    Ingredient.deleted_at.is_(None),
                )
                .distinct()
            ).all()
        )
        shortage = data.quantity - available
        unit_hint = ""
        if data.unit not in same_name_units and same_name_units:
            unit_hint = f"；同名食材现有单位：{'、'.join(same_name_units)}"
        if commit:
            db.rollback()
        raise AppError(
            ErrorCode.BUSINESS_RULE_VIOLATION,
            f"{data.name}库存不足，还缺 {_decimal_text(shortage)}{data.unit}{unit_hint}",
            422,
            {
                "name": data.name,
                "unit": data.unit.value,
                "requested": _decimal_text(data.quantity),
                "available": _decimal_text(available),
                "shortage": _decimal_text(shortage),
            },
        )

    remaining = data.quantity
    results: list[ConsumeBatchResult] = []
    for batch in batches:
        if remaining == 0:
            break
        consumed = min(batch.quantity, remaining)
        batch.quantity -= consumed
        remaining -= consumed
        if batch.quantity == 0:
            batch.status = IngredientStatus.USED_UP
        results.append(
            ConsumeBatchResult(
                ingredient_id=batch.id,
                consumed_quantity=consumed,
                remaining_quantity=batch.quantity,
                status=batch.status,
            )
        )
    try:
        if commit:
            db.commit()
        else:
            db.flush()
    except Exception:
        db.rollback()
        raise
    return ConsumeResponse(
        name=data.name,
        unit=data.unit,
        consumed_quantity=data.quantity,
        remaining_stock=available - data.quantity,
        batches=results,
    )


def cook_recipe(db: Session, user_id: int, data: CookRequest) -> CookResponse:
    """整道菜只提交一次；任何食材不足都恢复此前的所有扣减。"""
    try:
        consumed = [
            consume_ingredient(
                db,
                user_id,
                ConsumeRequest(name=item.name, quantity=item.quantity, unit=item.unit),
                commit=False,
            )
            for item in data.uses
        ]
        db.commit()
    except Exception:
        db.rollback()
        raise
    return CookResponse(recipe_name=data.recipe_name, consumed=consumed)


def resolve_expiring_days(settings: dict, requested_days: int | None) -> int:
    if requested_days is not None:
        return requested_days
    configured = settings.get("expiring_days", 3)
    if isinstance(configured, int) and not isinstance(configured, bool) and 0 <= configured <= 365:
        return configured
    return 3


def list_expiring_ingredients(
    db: Session,
    user_id: int,
    days: int,
    timezone: str,
    *,
    current_time: datetime | None = None,
) -> ExpiringResponse:
    """按用户当地自然日区分已过期与临期，不使用服务器本地日期。"""
    today = (current_time or now_utc()).astimezone(ZoneInfo(timezone)).date()
    rows = list(
        db.scalars(
            select(Ingredient).where(
                Ingredient.user_id == user_id,
                Ingredient.status == IngredientStatus.ACTIVE,
                Ingredient.quantity > 0,
                Ingredient.expire_on.is_not(None),
                Ingredient.expire_on <= today + timedelta(days=days),
                Ingredient.deleted_at.is_(None),
            )
        ).all()
    )
    expired: list[ExpiringIngredientResponse] = []
    expiring: list[ExpiringIngredientResponse] = []
    for ingredient in sorted(rows, key=lambda item: (item.expire_on, item.id)):
        days_to_expire = (ingredient.expire_on - today).days
        response = ExpiringIngredientResponse(
            **IngredientResponse.model_validate(ingredient).model_dump(),
            days_to_expire=days_to_expire,
        )
        (expired if days_to_expire < 0 else expiring).append(response)
    return ExpiringResponse(today=today, days=days, expired=expired, expiring=expiring)


def create_shopping_item(
    db: Session, user_id: int, data: ShoppingItemCreate, *, commit: bool = True
) -> ShoppingItem:
    """创建购物项；菜谱联动也经此 service 入口，并复用外层事务。"""
    item = ShoppingItem(user_id=user_id, **data.model_dump())
    db.add(item)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(item)
    return item


def add_recipe_missing_to_shopping(
    db: Session, user_id: int, data: RecipeShoppingRequest
) -> list[ShoppingItem]:
    """缺料整批写入，避免多次独立请求造成只添加了一部分。"""
    try:
        items = [
            create_shopping_item(
                db,
                user_id,
                ShoppingItemCreate(
                    name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    source=ShoppingSource.RECIPE,
                    recipe_name=data.recipe_name,
                ),
                commit=False,
            )
            for item in data.missing
        ]
        db.commit()
    except Exception:
        db.rollback()
        raise
    return items


def list_shopping_items(
    db: Session, user_id: int, query: ShoppingItemListQuery
) -> tuple[list[ShoppingItem], int]:
    filters = [ShoppingItem.user_id == user_id, ShoppingItem.deleted_at.is_(None)]
    if query.done is not None:
        filters.append(ShoppingItem.done == query.done)
    if query.source is not None:
        filters.append(ShoppingItem.source == query.source)
    total = db.scalar(select(func.count()).select_from(ShoppingItem).where(*filters)) or 0
    statement = (
        select(ShoppingItem)
        .where(*filters)
        .order_by(ShoppingItem.done, ShoppingItem.created_at.desc(), ShoppingItem.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    return list(db.scalars(statement).all()), total


def get_shopping_item(db: Session, user_id: int, item_id: int) -> ShoppingItem:
    item = db.scalar(
        select(ShoppingItem).where(
            ShoppingItem.id == item_id,
            ShoppingItem.user_id == user_id,
            ShoppingItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "购物项不存在", 404)
    return item


def update_shopping_item(
    db: Session, user_id: int, item_id: int, data: ShoppingItemUpdate
) -> ShoppingItem:
    item = get_shopping_item(db, user_id, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_shopping_item(db: Session, user_id: int, item_id: int) -> None:
    item = get_shopping_item(db, user_id, item_id)
    item.deleted_at = now_utc()
    db.commit()
