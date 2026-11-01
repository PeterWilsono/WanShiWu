"""工具到业务服务的可插拔 dispatch；新增模块时在这里注册处理器。"""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.llm.schemas import (
    AddExpenseArgs,
    AddIncomeArgs,
    AddIngredientArgs,
    CreateEventArgs,
    CreateTodoArgs,
    CreateTripArgs,
    MoneyArgs,
    SaveBookmarkArgs,
    ToolArgs,
)
from app.modules.inbox.schemas import BookmarkCreate
from app.modules.inbox.service import create_bookmark
from app.modules.life.models import Category, TransactionType
from app.modules.life.schemas import EventCreate, TodoCreate, TransactionCreate
from app.modules.life.service import create_event, create_todo, create_transaction
from app.modules.pantry.schemas import IngredientCreate
from app.modules.pantry.service import create_ingredient
from app.modules.trip.models import GeneratedBy
from app.modules.trip.schemas import TripCreate
from app.modules.trip.service import create_trip

ActionResult = tuple[str, int]
ActionHandler = Callable[[Session, int, ToolArgs], ActionResult]


def _create_todo(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, CreateTodoArgs)
    todo = create_todo(db, user_id, TodoCreate.model_validate(args.model_dump()), commit=False)
    return "todo", todo.id


def _create_event(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, CreateEventArgs)
    event = create_event(db, user_id, EventCreate.model_validate(args.model_dump()), commit=False)
    return "event", event.id


def _create_money(db: Session, user_id: int, args: MoneyArgs, kind: str) -> ActionResult:
    transaction_type = TransactionType(kind)
    category = db.scalar(
        select(Category).where(
            Category.user_id == user_id,
            Category.name == args.category,
            Category.type == transaction_type,
            Category.deleted_at.is_(None),
        )
    )
    if category is None:
        raise AppError(
            ErrorCode.BUSINESS_RULE_VIOLATION,
            f"{args.category}分类不存在或收支类型不匹配，请先创建分类",
            422,
        )
    data = TransactionCreate(
        amount_cents=int(args.amount * 100),
        type=transaction_type,
        category_id=category.id,
        note=args.note,
        occurred_at=args.occurred_at or now_utc(),
        source="assistant",
    )
    transaction = create_transaction(db, user_id, data, commit=False)
    return "transaction", transaction.id


def _add_ingredient(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, AddIngredientArgs)
    ingredient = create_ingredient(
        db,
        user_id,
        IngredientCreate.model_validate(args.model_dump()),
        commit=False,
    )
    return "ingredient", ingredient.id


def _save_bookmark(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, SaveBookmarkArgs)
    bookmark = create_bookmark(
        db,
        user_id,
        BookmarkCreate(url=str(args.url), note=args.note),
        commit=False,
    )
    return "bookmark", bookmark.id


def _create_trip(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, CreateTripArgs)
    budget_cents = (
        int((args.budget * 100).to_integral_exact()) if args.budget is not None else None
    )
    trip = create_trip(
        db,
        user_id,
        TripCreate(
            title=f"{args.destination}{args.days}日旅行",
            destination=args.destination,
            days=args.days,
            budget_cents=budget_cents,
            preferences=args.preferences,
            generated_by=GeneratedBy.AI,
        ),
        commit=False,
    )
    return "trip", trip.id


def _add_expense(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, AddExpenseArgs)
    return _create_money(db, user_id, args, "expense")


def _add_income(db: Session, user_id: int, args: ToolArgs) -> ActionResult:
    assert isinstance(args, AddIncomeArgs)
    return _create_money(db, user_id, args, "income")


DISPATCH: dict[str, ActionHandler] = {
    "create_todo": _create_todo,
    "create_event": _create_event,
    "add_expense": _add_expense,
    "add_income": _add_income,
    "add_ingredient": _add_ingredient,
    "save_bookmark": _save_bookmark,
    "create_trip": _create_trip,
}
