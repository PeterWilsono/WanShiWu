"""食材管家数据模型（PROJECT_SPEC.md 7.2、10.2）。"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, Index, Numeric, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UserOwnedMixin


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """数据库保存枚举值，而不是 Python 枚举成员名。"""
    return [member.value for member in enum_class]


class IngredientUnit(StrEnum):
    PIECE = "个"
    GRAM = "克"
    KILOGRAM = "千克"
    MILLILITER = "毫升"
    LITER = "升"
    PACK = "包"
    BOTTLE = "瓶"


class Storage(StrEnum):
    FRIDGE = "fridge"
    FREEZER = "freezer"
    ROOM = "room"


class IngredientStatus(StrEnum):
    ACTIVE = "active"
    USED_UP = "used_up"
    DISCARDED = "discarded"


class ShoppingSource(StrEnum):
    MANUAL = "manual"
    RECIPE = "recipe"


def constrained_enum(enum_class: type[StrEnum], length: int) -> SqlEnum:
    return SqlEnum(
        enum_class,
        values_callable=enum_values,
        native_enum=False,
        length=length,
        validate_strings=True,
        create_constraint=True,
    )


class Ingredient(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    """一次入库对应一个独立批次；不同批次不合并保质期。"""

    __tablename__ = "ingredients"
    __table_args__ = (
        Index("ix_ingredients_user_name_expire", "user_id", "name", "expire_on"),
        Index("ix_ingredients_user_status_expire", "user_id", "status", "expire_on"),
        Index("ix_ingredients_user_storage", "user_id", "storage"),
        CheckConstraint("quantity >= 0", name="ck_ingredients_quantity_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(50), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit: Mapped[IngredientUnit] = mapped_column(constrained_enum(IngredientUnit, 10))
    expire_on: Mapped[date | None] = mapped_column(Date)
    purchased_on: Mapped[date | None] = mapped_column(Date)
    storage: Mapped[Storage] = mapped_column(constrained_enum(Storage, 10))
    status: Mapped[IngredientStatus] = mapped_column(
        constrained_enum(IngredientStatus, 10), default=IngredientStatus.ACTIVE
    )
    note: Mapped[str | None] = mapped_column(String(200))


class ShoppingItem(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "shopping_items"
    __table_args__ = (
        Index("ix_shopping_items_user_done_created", "user_id", "done", "created_at"),
        CheckConstraint(
            "quantity IS NULL OR quantity > 0", name="ck_shopping_items_quantity_positive"
        ),
    )

    name: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[IngredientUnit | None] = mapped_column(constrained_enum(IngredientUnit, 10))
    done: Mapped[bool] = mapped_column(default=False)
    source: Mapped[ShoppingSource] = mapped_column(
        constrained_enum(ShoppingSource, 20), default=ShoppingSource.MANUAL
    )
    recipe_name: Mapped[str | None] = mapped_column(String(100))
