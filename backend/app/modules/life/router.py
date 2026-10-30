"""生活管家路由；包含待办完整操作以及日程新建与范围列表。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.life.models import Event, Todo
from app.modules.life.schemas import (
    EventCreate,
    EventListQuery,
    EventListResponse,
    EventResponse,
    TodoCompleteResponse,
    TodoCreate,
    TodoListQuery,
    TodoListResponse,
    TodoResponse,
    TodoUpdate,
)
from app.modules.life.service import (
    complete_todo,
    create_event,
    create_todo,
    delete_todo,
    get_todo,
    list_events,
    list_todos,
    update_todo,
)

router = APIRouter(tags=["生活管家"])
DbSession = Annotated[Session, Depends(get_db)]


def serialize_todo(todo: Todo) -> dict[str, Any]:
    return TodoResponse.model_validate(todo).model_dump(mode="json")


def serialize_event(event: Event) -> dict[str, Any]:
    return EventResponse.model_validate(event).model_dump(mode="json")


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
