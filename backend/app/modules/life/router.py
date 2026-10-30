"""生活管家路由；当前包含待办新建与列表。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.life.models import Todo
from app.modules.life.schemas import TodoCreate, TodoListQuery, TodoListResponse, TodoResponse
from app.modules.life.service import create_todo, list_todos

router = APIRouter(tags=["生活管家"])
DbSession = Annotated[Session, Depends(get_db)]


def serialize_todo(todo: Todo) -> dict[str, Any]:
    return TodoResponse.model_validate(todo).model_dump(mode="json")


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
