"""生活管家路由；包含待办、日程、收支分类与账目管理。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.life.models import Category, Event, Reminder, Todo, Transaction, TransactionType
from app.modules.life.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    EventCreate,
    EventListQuery,
    EventListResponse,
    EventResponse,
    EventUpdate,
    NotificationListQuery,
    NotificationListResponse,
    NotificationResponse,
    StatsMonthQuery,
    TodoCompleteResponse,
    TodoCreate,
    TodoListQuery,
    TodoListResponse,
    TodoResponse,
    TodoUpdate,
    TransactionCreate,
    TransactionListQuery,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.modules.life.service import (
    complete_todo,
    create_category,
    create_event,
    create_todo,
    create_transaction,
    delete_category,
    delete_event,
    delete_todo,
    delete_transaction,
    get_daily_stats,
    get_event,
    get_monthly_stats,
    get_todo,
    get_transaction,
    list_categories,
    list_events,
    list_notifications,
    list_todos,
    list_transactions,
    mark_notification_read,
    update_category,
    update_event,
    update_todo,
    update_transaction,
)

router = APIRouter(tags=["生活管家"])
DbSession = Annotated[Session, Depends(get_db)]


def serialize_todo(todo: Todo) -> dict[str, Any]:
    return TodoResponse.model_validate(todo).model_dump(mode="json")


def serialize_event(event: Event) -> dict[str, Any]:
    return EventResponse.model_validate(event).model_dump(mode="json")


def serialize_category(category: Category) -> dict[str, Any]:
    return CategoryResponse.model_validate(category).model_dump(mode="json")


def serialize_transaction(transaction: Transaction) -> dict[str, Any]:
    return TransactionResponse.model_validate(transaction).model_dump(mode="json")


def serialize_notification(reminder: Reminder) -> dict[str, Any]:
    return NotificationResponse.model_validate(reminder).model_dump(mode="json")


@router.post("/todos")
def create_todo_endpoint(data: TodoCreate, db: DbSession, current_user: CurrentUser) -> dict:
    todo = create_todo(db, current_user.id, data)
    return ok(serialize_todo(todo), "创建成功")


@router.get("/todos")
def list_todos_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[TodoListQuery, Depends()],
) -> dict:
    items, total = list_todos(db, current_user.id, query)
    result = TodoListResponse(
        items=[TodoResponse.model_validate(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.get("/todos/{todo_id}")
def get_todo_endpoint(todo_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return ok(serialize_todo(get_todo(db, current_user.id, todo_id)))


@router.patch("/todos/{todo_id}")
def update_todo_endpoint(
    todo_id: int,
    data: TodoUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    todo = update_todo(db, current_user.id, todo_id, data)
    return ok(serialize_todo(todo), "更新成功")


@router.delete("/todos/{todo_id}")
def delete_todo_endpoint(todo_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    delete_todo(db, current_user.id, todo_id)
    return ok(message="删除成功")


@router.post("/todos/{todo_id}/complete")
def complete_todo_endpoint(todo_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    todo, next_todo = complete_todo(db, current_user.id, todo_id)
    result = TodoCompleteResponse(
        todo=TodoResponse.model_validate(todo),
        next_todo=TodoResponse.model_validate(next_todo) if next_todo else None,
    )
    return ok(result.model_dump(mode="json"), "完成成功")


@router.post("/events")
def create_event_endpoint(data: EventCreate, db: DbSession, current_user: CurrentUser) -> dict:
    event = create_event(db, current_user.id, data)
    return ok(serialize_event(event), "创建成功")


@router.get("/events")
def list_events_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[EventListQuery, Depends()],
) -> dict:
    items, total = list_events(db, current_user.id, query)
    result = EventListResponse(
        items=[EventResponse.model_validate(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.get("/events/{event_id}")
def get_event_endpoint(event_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return ok(serialize_event(get_event(db, current_user.id, event_id)))


@router.patch("/events/{event_id}")
def update_event_endpoint(
    event_id: int,
    data: EventUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    event = update_event(db, current_user.id, event_id, data)
    return ok(serialize_event(event), "更新成功")


@router.delete("/events/{event_id}")
def delete_event_endpoint(event_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    delete_event(db, current_user.id, event_id)
    return ok(message="删除成功")


@router.get("/notifications")
def list_notifications_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[NotificationListQuery, Depends()],
) -> dict:
    items, total, unread_count = list_notifications(db, current_user.id, query)
    result = NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        unread_count=unread_count,
        page=query.page,
        page_size=query.page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.post("/notifications/{notification_id}/read")
def read_notification_endpoint(
    notification_id: int, db: DbSession, current_user: CurrentUser
) -> dict:
    reminder = mark_notification_read(db, current_user.id, notification_id)
    return ok(serialize_notification(reminder), "已标记为已读")


@router.get("/categories")
def list_categories_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    category_type: Annotated[TransactionType | None, Query(alias="type")] = None,
) -> dict:
    items = list_categories(db, current_user.id, category_type)
    return ok([serialize_category(item) for item in items])


@router.post("/categories")
def create_category_endpoint(
    data: CategoryCreate, db: DbSession, current_user: CurrentUser
) -> dict:
    category = create_category(db, current_user.id, data)
    return ok(serialize_category(category), "创建成功")


@router.patch("/categories/{category_id}")
def update_category_endpoint(
    category_id: int,
    data: CategoryUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    category = update_category(db, current_user.id, category_id, data)
    return ok(serialize_category(category), "更新成功")


@router.delete("/categories/{category_id}")
def delete_category_endpoint(category_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    delete_category(db, current_user.id, category_id)
    return ok(message="删除成功")


@router.post("/transactions")
def create_transaction_endpoint(
    data: TransactionCreate, db: DbSession, current_user: CurrentUser
) -> dict:
    transaction = create_transaction(db, current_user.id, data)
    return ok(serialize_transaction(transaction), "创建成功")


@router.get("/transactions")
def list_transactions_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[TransactionListQuery, Depends()],
) -> dict:
    items, total = list_transactions(db, current_user.id, query, current_user.timezone)
    result = TransactionListResponse(
        items=[TransactionResponse.model_validate(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.get("/transactions/{transaction_id}")
def get_transaction_endpoint(transaction_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return ok(serialize_transaction(get_transaction(db, current_user.id, transaction_id)))


@router.patch("/transactions/{transaction_id}")
def update_transaction_endpoint(
    transaction_id: int,
    data: TransactionUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    transaction = update_transaction(db, current_user.id, transaction_id, data)
    return ok(serialize_transaction(transaction), "更新成功")


@router.delete("/transactions/{transaction_id}")
def delete_transaction_endpoint(
    transaction_id: int, db: DbSession, current_user: CurrentUser
) -> dict:
    delete_transaction(db, current_user.id, transaction_id)
    return ok(message="删除成功")


@router.get("/stats/monthly")
def monthly_stats_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[StatsMonthQuery, Depends()],
) -> dict:
    result = get_monthly_stats(db, current_user.id, query.month, current_user.timezone)
    return ok(result.model_dump(mode="json"))


@router.get("/stats/daily")
def daily_stats_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    query: Annotated[StatsMonthQuery, Depends()],
) -> dict:
    result = get_daily_stats(db, current_user.id, query.month, current_user.timezone)
    return ok(result.model_dump(mode="json", by_alias=True))
