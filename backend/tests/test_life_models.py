"""生活管家模型、约束和索引测试（PROJECT_SPEC.md 7.1~7.3）。"""

from datetime import timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.modules.auth.models import User
from app.modules.life.models import (
    Category,
    Event,
    Recurrence,
    Todo,
    TodoStatus,
    Transaction,
    TransactionSource,
    TransactionType,
)


def create_user(db: Session, username: str = "peter") -> User:
    user = User(username=username, password_hash="hash")
    db.add(user)
    db.commit()
    return user


def create_category(db: Session, user_id: int) -> Category:
    category = Category(user_id=user_id, name="餐饮", type=TransactionType.EXPENSE)
    db.add(category)
    db.commit()
    return category


def test_life_models_create_and_defaults(db_session: Session) -> None:
    user = create_user(db_session)
    occurred_at = now_utc()

    todo = Todo(user_id=user.id, title="写周报", tags_json=["工作", "本周"])
    event = Event(user_id=user.id, title="复诊", start_at=occurred_at)
    category = Category(user_id=user.id, name="工资", type=TransactionType.INCOME)
    db_session.add_all([todo, event, category])
    db_session.commit()

    transaction = Transaction(
        user_id=user.id,
        amount_cents=12345,
        type=TransactionType.INCOME,
        category_id=category.id,
        occurred_at=occurred_at,
    )
    db_session.add(transaction)
    db_session.commit()

    assert todo.status is TodoStatus.PENDING
    assert todo.priority == 2
    assert todo.recurrence is Recurrence.NONE
    assert todo.tags_json == ["工作", "本周"]
    assert todo.completed_at is None and todo.deleted_at is None
    assert todo.created_at.tzinfo is not None
    assert event.all_day is False
    assert transaction.source is TransactionSource.MANUAL
    assert transaction.amount_cents == 12345
    assert transaction.category.name == "工资"


def test_life_composite_indexes_and_category_unique_constraint(db_session: Session) -> None:
    inspector = inspect(db_session.get_bind())

    indexes = {item["name"]: item for item in inspector.get_indexes("todos")}
    assert indexes["ix_todos_user_status_due_at"]["column_names"] == [
        "user_id",
        "status",
        "due_at",
    ]
    indexes = {item["name"]: item for item in inspector.get_indexes("events")}
    assert indexes["ix_events_user_start_at"]["column_names"] == ["user_id", "start_at"]
    indexes = {item["name"]: item for item in inspector.get_indexes("transactions")}
    assert indexes["ix_transactions_user_occurred_at"]["column_names"] == [
        "user_id",
        "occurred_at",
    ]
    assert indexes["ix_transactions_user_category_id"]["column_names"] == [
        "user_id",
        "category_id",
    ]

    unique_constraints = inspector.get_unique_constraints("categories")
    assert any(item["column_names"] == ["user_id", "type", "name"] for item in unique_constraints)


def test_category_unique_only_within_same_user_and_type(db_session: Session) -> None:
    user = create_user(db_session)
    other_user = create_user(db_session, "other")
    db_session.add(Category(user_id=user.id, name="其他", type=TransactionType.EXPENSE))
    db_session.commit()

    db_session.add(Category(user_id=user.id, name="其他", type=TransactionType.EXPENSE))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 同名但类型不同，或属于另一个用户，都允许存在。
    db_session.add_all(
        [
            Category(user_id=user.id, name="其他", type=TransactionType.INCOME),
            Category(user_id=other_user.id, name="其他", type=TransactionType.EXPENSE),
        ]
    )
    db_session.commit()


def test_transaction_rejects_missing_category(db_session: Session) -> None:
    user = create_user(db_session)
    db_session.add(
        Transaction(
            user_id=user.id,
            amount_cents=100,
            type=TransactionType.EXPENSE,
            category_id=999999,
            occurred_at=now_utc(),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_transaction_rejects_non_positive_amount(db_session: Session) -> None:
    user = create_user(db_session)
    category = create_category(db_session, user.id)
    db_session.add(
        Transaction(
            user_id=user.id,
            amount_cents=0,
            type=TransactionType.EXPENSE,
            category_id=category.id,
            occurred_at=now_utc(),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_event_rejects_end_before_start(db_session: Session) -> None:
    user = create_user(db_session)
    start_at = now_utc()
    db_session.add(
        Event(
            user_id=user.id,
            title="错误日程",
            start_at=start_at,
            end_at=start_at - timedelta(seconds=1),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_event_rejects_negative_reminder(db_session: Session) -> None:
    user = create_user(db_session)
    db_session.add(
        Event(user_id=user.id, title="错误提醒", start_at=now_utc(), remind_before_min=-1)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_todo_rejects_priority_outside_range(db_session: Session) -> None:
    user = create_user(db_session)
    db_session.add(Todo(user_id=user.id, title="错误优先级", priority=4))
    with pytest.raises(IntegrityError):
        db_session.commit()
