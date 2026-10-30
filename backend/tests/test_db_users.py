"""users 表与 SQLite PRAGMA 测试（PROJECT_SPEC.md 7.1 / 7.2）。"""

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.models import User


def test_create_and_query_user(db_session: Session) -> None:
    """可正常创建并查询用户，默认值符合 7.2 定义。"""
    user = User(username="peter", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.created_at is not None
    assert user.created_at.tzinfo is not None, "created_at 必须带时区（UTC）"

    found = db_session.scalar(select(User).where(User.username == "peter"))
    assert found is not None
    assert found.timezone == "Asia/Shanghai"
    assert found.settings_json == {}


def test_username_unique_constraint(db_session: Session) -> None:
    """username 唯一：重复用户名必须报 IntegrityError。"""
    db_session.add(User(username="peter", password_hash="h1"))
    db_session.commit()
    db_session.add(User(username="peter", password_hash="h2"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_sqlite_foreign_keys_enabled(db_session: Session) -> None:
    """连接级 PRAGMA foreign_keys 必须为 ON（7.1）。"""
    assert db_session.scalar(text("PRAGMA foreign_keys")) == 1


def test_sqlite_wal_mode_for_file_db(tmp_path) -> None:
    """WAL 只对文件库生效；内存库 journal_mode 恒为 memory，故用临时文件库验证。"""
    engine = create_engine(f"sqlite:///{tmp_path.as_posix()}/test.db")
    with engine.connect() as conn:
        assert conn.scalar(text("PRAGMA journal_mode")) == "wal"
    engine.dispose()
