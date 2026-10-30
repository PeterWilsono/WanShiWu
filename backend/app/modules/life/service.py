"""生活管家业务逻辑；所有查询都限定当前用户并过滤软删除。"""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.modules.life.models import Todo
from app.modules.life.schemas import TodoCreate, TodoListQuery, to_aware_utc


def create_todo(db: Session, user_id: int, data: TodoCreate) -> Todo:
    todo = Todo(
        user_id=user_id,
        title=data.title,
        note=data.note,
        due_at=data.due_at,
        priority=data.priority,
        recurrence=data.recurrence,
        tags_json=data.tags,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def list_todos(db: Session, user_id: int, query: TodoListQuery) -> tuple[list[Todo], int]:
    # FastAPI 对 BaseModel 查询依赖中的自定义 validator 不会稳定转成 422，
    # 因此在 service 边界统一完成跨字段/时区校验并转换 AppError。
    try:
        due_after = to_aware_utc(query.due_after)
        due_before = to_aware_utc(query.due_before)
    except ValueError as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, str(exc), 422) from exc
    if due_after and due_before and due_after > due_before:
        raise AppError(ErrorCode.VALIDATION_ERROR, "due_after 不能晚于 due_before", 422)
    tag = query.tag.strip() if query.tag else None

    filters = [Todo.user_id == user_id, Todo.deleted_at.is_(None)]
    if query.status is not None:
        filters.append(Todo.status == query.status)
    if due_after is not None:
        filters.append(Todo.due_at >= due_after)
    if due_before is not None:
        filters.append(Todo.due_at <= due_before)
    if tag:
        # SQLite json_each：精确匹配 JSON 数组中的某个字符串，值使用绑定参数防注入。
        filters.append(
            text(
                "EXISTS (SELECT 1 FROM json_each(todos.tags_json) AS tags_each "
                "WHERE tags_each.value = :tag)"
            ).bindparams(tag=tag)
        )

    total = db.scalar(select(func.count()).select_from(Todo).where(*filters)) or 0
    sort_column = {
        "due_at": Todo.due_at,
        "created_at": Todo.created_at,
        "priority": Todo.priority,
    }[query.sort]
    order_by = sort_column.asc() if query.order == "asc" else sort_column.desc()
    id_order = Todo.id.asc() if query.order == "asc" else Todo.id.desc()

    statement = (
        select(Todo)
        .where(*filters)
        .order_by(order_by, id_order)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    return list(db.scalars(statement).all()), total
