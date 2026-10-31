"""食材批次与购物清单的数据库约束测试。"""

from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.pantry.models import (
    Ingredient,
    IngredientStatus,
    IngredientUnit,
    ShoppingItem,
    ShoppingSource,
    Storage,
)


def create_user(db: Session) -> User:
    user = User(username="pantry-user", password_hash="hash")
    db.add(user)
    db.commit()
    return user


def test_pantry_models_create_defaults_and_decimal_quantity(db_session: Session) -> None:
    user = create_user(db_session)
    ingredient = Ingredient(
        user_id=user.id,
        name="鸡蛋",
        quantity=Decimal("10.50"),
        unit=IngredientUnit.PIECE,
        storage=Storage.FRIDGE,
    )
    item = ShoppingItem(user_id=user.id, name="牛奶")
    db_session.add_all([ingredient, item])
    db_session.commit()

    assert ingredient.status is IngredientStatus.ACTIVE
    assert ingredient.quantity == Decimal("10.50")
    assert ingredient.expire_on is None and ingredient.deleted_at is None
    assert item.done is False and item.source is ShoppingSource.MANUAL
    assert item.quantity is None and item.unit is None


def test_pantry_indexes_exist(db_session: Session) -> None:
    inspector = inspect(db_session.get_bind())
    ingredient_indexes = {item["name"]: item for item in inspector.get_indexes("ingredients")}
    assert ingredient_indexes["ix_ingredients_user_name_expire"]["column_names"] == [
        "user_id",
        "name",
        "expire_on",
    ]
    assert ingredient_indexes["ix_ingredients_user_status_expire"]["column_names"] == [
        "user_id",
        "status",
        "expire_on",
    ]
    shopping_indexes = {item["name"]: item for item in inspector.get_indexes("shopping_items")}
    assert shopping_indexes["ix_shopping_items_user_done_created"]["column_names"] == [
        "user_id",
        "done",
        "created_at",
    ]


def test_ingredient_rejects_negative_quantity(db_session: Session) -> None:
    user = create_user(db_session)
    db_session.add(
        Ingredient(
            user_id=user.id,
            name="错误库存",
            quantity=Decimal("-0.01"),
            unit=IngredientUnit.GRAM,
            storage=Storage.ROOM,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_shopping_item_rejects_non_positive_quantity(db_session: Session) -> None:
    user = create_user(db_session)
    db_session.add(
        ShoppingItem(
            user_id=user.id,
            name="错误购物项",
            quantity=Decimal("0"),
            unit=IngredientUnit.PACK,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_pantry_rejects_unregistered_unit(db_session: Session) -> None:
    user = create_user(db_session)
    db_session.add(
        Ingredient(
            user_id=user.id,
            name="错误单位",
            quantity=Decimal("1"),
            unit="箱",
            storage=Storage.FRIDGE,
        )
    )
    with pytest.raises((IntegrityError, StatementError)):
        db_session.commit()
