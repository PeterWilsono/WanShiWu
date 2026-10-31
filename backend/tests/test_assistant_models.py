"""AI 助手解析记录模型、约束与索引测试。"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.assistant.models import AssistantRecord, AssistantStatus
from app.core.time import now_utc
from app.modules.auth.models import User


def create_user(db: Session) -> User:
    user = User(username="assistant-owner", password_hash="hash")
    db.add(user)
    db.commit()
    return user


def test_assistant_record_defaults_and_execution_fields(db_session: Session) -> None:
    user = create_user(db_session)
    record = AssistantRecord(
        user_id=user.id,
        raw_text="明天下午三点看牙医",
        intent="create_event",
        parsed_json=[{"tool": "create_event", "args": {"title": "看牙医"}}],
    )
    db_session.add(record)
    db_session.commit()

    assert record.status is AssistantStatus.PENDING
    assert record.result_ref is None and record.error is None
    assert record.executed_at is None and record.deleted_at is None
    assert record.created_at.tzinfo is not None
    assert record.parsed_json[0]["tool"] == "create_event"

    record.status = AssistantStatus.EXECUTED
    record.result_ref = "event:12"
    record.executed_at = now_utc()
    db_session.commit()
    db_session.refresh(record)
    assert record.status is AssistantStatus.EXECUTED
    assert record.result_ref == "event:12"
    assert record.executed_at is not None and record.executed_at.tzinfo is not None


def test_assistant_record_composite_index(db_session: Session) -> None:
    indexes = {
        item["name"]: item
        for item in inspect(db_session.get_bind()).get_indexes("assistant_records")
    }
    assert indexes["ix_assistant_records_user_status_created_at"]["column_names"] == [
        "user_id",
        "status",
        "created_at",
    ]


@pytest.mark.parametrize(("field", "value"), [("raw_text", ""), ("status", "running")])
def test_assistant_record_rejects_invalid_values(
    db_session: Session, field: str, value: str
) -> None:
    user = create_user(db_session)
    record = AssistantRecord(user_id=user.id, raw_text="有效输入", intent="unknown")
    setattr(record, field, value)
    db_session.add(record)

    with pytest.raises((IntegrityError, StatementError)):
        db_session.commit()
