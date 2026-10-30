"""生活管家业务逻辑；所有查询都限定当前用户并过滤软删除。"""

import calendar
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.modules.life.models import Recurrence, Todo, TodoStatus
from app.modules.life.schemas import TodoCreate, TodoListQuery, TodoUpdate, to_aware_utc


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


def get_todo(db: Session, user_id: int, todo_id: int) -> Todo:
    """读取当前用户的有效待办；不存在、越权、已删除统一按 404 处理。"""
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == user_id,
            Todo.deleted_at.is_(None),
        )
    )
    if todo is None:
        raise AppError(ErrorCode.NOT_FOUND, "待办不存在", 404)
    return todo


def update_todo(db: Session, user_id: int, todo_id: int, data: TodoUpdate) -> Todo:
    """部分更新待办；只修改请求中明确出现的字段。"""
    todo = get_todo(db, user_id, todo_id)
    updates = data.model_dump(exclude_unset=True)
    if "tags" in updates:
        updates["tags_json"] = updates.pop("tags")
    if "status" in updates:
        updates["completed_at"] = now_utc() if updates["status"] == TodoStatus.DONE else None
    for field, value in updates.items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, user_id: int, todo_id: int) -> None:
    """软删除待办，保留数据库行以便审计与后续恢复能力。"""
    todo = get_todo(db, user_id, todo_id)
    todo.deleted_at = now_utc()
    db.commit()


def advance_due_at(due_at: datetime, recurrence: Recurrence) -> datetime:
    """以原截止时间为基准顺延一个周期，保留原时刻与时区。"""
    if recurrence == Recurrence.DAILY:
        return due_at + timedelta(days=1)
    if recurrence == Recurrence.WEEKLY:
        return due_at + timedelta(weeks=1)
    if recurrence == Recurrence.MONTHLY:
        # 不固定加 30 天；月末日期在短月中收敛到该月最后一天。
        year = due_at.year + (due_at.month // 12)
        month = due_at.month % 12 + 1
        day = min(due_at.day, calendar.monthrange(year, month)[1])
        return due_at.replace(year=year, month=month, day=day)
    raise AppError(ErrorCode.BUSINESS_RULE_VIOLATION, "普通待办没有下一次周期", 422)


def complete_todo(db: Session, user_id: int, todo_id: int) -> tuple[Todo, Todo | None]:
    """完成待办；周期待办的下一次实例与状态更新在同一事务中提交。"""
    todo = get_todo(db, user_id, todo_id)
    if todo.status != TodoStatus.PENDING:
        raise AppError(ErrorCode.CONFLICT, "只有进行中的待办可以完成", 409)
    if todo.recurrence != Recurrence.NONE and todo.due_at is None:
        raise AppError(
            ErrorCode.BUSINESS_RULE_VIOLATION,
            "周期性待办必须设置截止时间才能生成下一次",
            422,
        )

    next_todo = None
    if todo.recurrence != Recurrence.NONE:
        next_todo = Todo(
            user_id=user_id,
            title=todo.title,
            note=todo.note,
            due_at=advance_due_at(todo.due_at, todo.recurrence),
            priority=todo.priority,
            recurrence=todo.recurrence,
            # 复制列表，避免两个 ORM 对象意外共享同一个 Python 列表。
            tags_json=list(todo.tags_json),
        )
    try:
        todo.status = TodoStatus.DONE
        todo.completed_at = now_utc()
        if next_todo is not None:
            db.add(next_todo)
        db.commit()
        db.refresh(todo)
        if next_todo is not None:
            db.refresh(next_todo)
    except Exception:
        # 任一步失败都撤销整组修改，避免“已完成但没生成下一次”。
        db.rollback()
        raise
    return todo, next_todo
