"""生活管家业务逻辑；所有查询都限定当前用户并过滤软删除。"""

import calendar
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.modules.life.models import (
    Category,
    Event,
    Recurrence,
    Todo,
    TodoStatus,
    Transaction,
    TransactionType,
)
from app.modules.life.schemas import (
    CategoryCreate,
    CategoryUpdate,
    EventCreate,
    EventListQuery,
    EventUpdate,
    TodoCreate,
    TodoListQuery,
    TodoUpdate,
    TransactionCreate,
    TransactionListQuery,
    to_aware_utc,
)


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


def create_event(db: Session, user_id: int, data: EventCreate) -> Event:
    event = Event(user_id=user_id, **data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, user_id: int, query: EventListQuery) -> tuple[list[Event], int]:
    try:
        range_start = to_aware_utc(query.range_start)
        range_end = to_aware_utc(query.range_end)
    except ValueError as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, str(exc), 422) from exc
    if range_start and range_end and range_start > range_end:
        raise AppError(ErrorCode.VALIDATION_ERROR, "range_start 不能晚于 range_end", 422)

    filters = [Event.user_id == user_id, Event.deleted_at.is_(None)]
    if range_start is not None:
        # 无结束时间的日程视为一个时间点；有结束时间的按实际区间判断重叠。
        filters.append(func.coalesce(Event.end_at, Event.start_at) >= range_start)
    if range_end is not None:
        filters.append(Event.start_at <= range_end)

    total = db.scalar(select(func.count()).select_from(Event).where(*filters)) or 0
    statement = (
        select(Event)
        .where(*filters)
        .order_by(Event.start_at.asc(), Event.id.asc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    return list(db.scalars(statement).all()), total


def get_event(db: Session, user_id: int, event_id: int) -> Event:
    """只返回当前用户未删除的日程，避免通过越权响应泄露数据是否存在。"""
    event = db.scalar(
        select(Event).where(
            Event.id == event_id,
            Event.user_id == user_id,
            Event.deleted_at.is_(None),
        )
    )
    if event is None:
        raise AppError(ErrorCode.NOT_FOUND, "日程不存在", 404)
    return event


def update_event(db: Session, user_id: int, event_id: int, data: EventUpdate) -> Event:
    """局部更新日程，并用更新后的完整时间组合校验先后关系。"""
    event = get_event(db, user_id, event_id)
    updates = data.model_dump(exclude_unset=True)
    start_at = updates.get("start_at", event.start_at)
    end_at = updates.get("end_at", event.end_at)
    if end_at is not None and end_at < start_at:
        raise AppError(ErrorCode.VALIDATION_ERROR, "结束时间不能早于开始时间", 422)

    for field, value in updates.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, user_id: int, event_id: int) -> None:
    """软删除日程；查询与后续详情访问都会过滤该记录。"""
    event = get_event(db, user_id, event_id)
    event.deleted_at = now_utc()
    db.commit()


# 图标使用字符串标识而不存 emoji，前端后续可映射为自己的图标组件。
DEFAULT_CATEGORIES: tuple[tuple[TransactionType, str, str], ...] = (
    (TransactionType.EXPENSE, "餐饮", "food"),
    (TransactionType.EXPENSE, "交通", "transport"),
    (TransactionType.EXPENSE, "购物", "shopping"),
    (TransactionType.EXPENSE, "居家", "home"),
    (TransactionType.EXPENSE, "娱乐", "entertainment"),
    (TransactionType.EXPENSE, "医疗", "medical"),
    (TransactionType.EXPENSE, "学习", "study"),
    (TransactionType.EXPENSE, "其他", "other"),
    (TransactionType.INCOME, "工资", "salary"),
    (TransactionType.INCOME, "其他", "other"),
)


def initialize_default_categories(db: Session, user_id: int) -> None:
    """补齐用户缺失的内置分类；只加入当前事务，由调用方统一提交。"""
    existing = set(
        db.execute(select(Category.type, Category.name).where(Category.user_id == user_id)).all()
    )
    categories = [
        Category(user_id=user_id, type=category_type, name=name, icon=icon, is_default=True)
        for category_type, name, icon in DEFAULT_CATEGORIES
        if (category_type, name) not in existing
    ]
    db.add_all(categories)


def list_categories(
    db: Session, user_id: int, category_type: TransactionType | None
) -> list[Category]:
    filters = [Category.user_id == user_id, Category.deleted_at.is_(None)]
    if category_type is not None:
        filters.append(Category.type == category_type)
    statement = (
        select(Category)
        .where(*filters)
        .order_by(Category.type.asc(), Category.is_default.desc(), Category.id.asc())
    )
    return list(db.scalars(statement).all())


def ensure_category_name_available(
    db: Session,
    user_id: int,
    category_type: TransactionType,
    name: str,
    exclude_id: int | None = None,
) -> None:
    filters = [
        Category.user_id == user_id,
        Category.type == category_type,
        Category.name == name,
        Category.deleted_at.is_(None),
    ]
    if exclude_id is not None:
        filters.append(Category.id != exclude_id)
    if db.scalar(select(Category.id).where(*filters).limit(1)) is not None:
        raise AppError(ErrorCode.CONFLICT, "同一收支类型下分类名称已存在", 409)


def create_category(db: Session, user_id: int, data: CategoryCreate) -> Category:
    ensure_category_name_available(db, user_id, data.type, data.name)
    category = Category(
        user_id=user_id,
        name=data.name,
        type=data.type,
        icon=data.icon,
        is_default=False,
    )
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(ErrorCode.CONFLICT, "同一收支类型下分类名称已存在", 409) from exc
    db.refresh(category)
    return category


def get_category(db: Session, user_id: int, category_id: int) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.deleted_at.is_(None),
        )
    )
    if category is None:
        raise AppError(ErrorCode.NOT_FOUND, "分类不存在", 404)
    return category


def update_category(db: Session, user_id: int, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category(db, user_id, category_id)
    updates = data.model_dump(exclude_unset=True)
    name = updates.get("name", category.name)
    ensure_category_name_available(db, user_id, category.type, name, exclude_id=category.id)
    for field, value in updates.items():
        setattr(category, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(ErrorCode.CONFLICT, "同一收支类型下分类名称已存在", 409) from exc
    db.refresh(category)
    return category


def delete_category(db: Session, user_id: int, category_id: int) -> None:
    category = get_category(db, user_id, category_id)
    if category.is_default:
        raise AppError(ErrorCode.BUSINESS_RULE_VIOLATION, "内置分类不可删除", 422)
    # 已删除的历史账目仍引用分类，因此检查时不过滤 transactions.deleted_at。
    referenced = db.scalar(
        select(Transaction.id)
        .where(Transaction.user_id == user_id, Transaction.category_id == category.id)
        .limit(1)
    )
    if referenced is not None:
        raise AppError(ErrorCode.BUSINESS_RULE_VIOLATION, "已有账目引用该分类，只能改名", 422)
    category.deleted_at = now_utc()
    db.commit()


def validate_transaction_category(
    db: Session, user_id: int, category_id: int, transaction_type: TransactionType
) -> Category:
    category = get_category(db, user_id, category_id)
    if category.type != transaction_type:
        raise AppError(ErrorCode.BUSINESS_RULE_VIOLATION, "分类类型与账目类型不一致", 422)
    return category


def create_transaction(db: Session, user_id: int, data: TransactionCreate) -> Transaction:
    category = validate_transaction_category(db, user_id, data.category_id, data.type)
    transaction = Transaction(
        user_id=user_id,
        amount_cents=data.amount_cents,
        type=data.type,
        category=category,
        note=data.note,
        occurred_at=data.occurred_at,
        source=data.source,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def month_bounds_utc(month: str, timezone_name: str) -> tuple[datetime, datetime]:
    """把用户时区中的自然月换算成左闭右开的 UTC 区间。"""
    year, month_number = (int(part) for part in month.split("-"))
    timezone = ZoneInfo(timezone_name)
    start = datetime(year, month_number, 1, tzinfo=timezone)
    if month_number == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone)
    else:
        end = datetime(year, month_number + 1, 1, tzinfo=timezone)
    return start.astimezone(UTC), end.astimezone(UTC)


def list_transactions(
    db: Session,
    user_id: int,
    query: TransactionListQuery,
    timezone_name: str,
) -> tuple[list[Transaction], int]:
    filters = [Transaction.user_id == user_id, Transaction.deleted_at.is_(None)]
    if query.month is not None:
        month_start, month_end = month_bounds_utc(query.month, timezone_name)
        filters.extend(
            [Transaction.occurred_at >= month_start, Transaction.occurred_at < month_end]
        )
    if query.category_id is not None:
        filters.append(Transaction.category_id == query.category_id)
    if query.type is not None:
        filters.append(Transaction.type == query.type)

    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    sort_column = {
        "occurred_at": Transaction.occurred_at,
        "amount_cents": Transaction.amount_cents,
        "created_at": Transaction.created_at,
    }[query.sort]
    order_by = sort_column.asc() if query.order == "asc" else sort_column.desc()
    id_order = Transaction.id.asc() if query.order == "asc" else Transaction.id.desc()
    statement = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(*filters)
        .order_by(order_by, id_order)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    return list(db.scalars(statement).all()), total
