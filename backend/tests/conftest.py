"""测试公共设施。

依据 PROJECT_SPEC.md 12.2：测试使用独立的内存 SQLite，
每个测试函数之间数据隔离；禁止真实调用大模型与外部网络。
"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 导入 session 模块以注册 SQLite PRAGMA 监听器（WAL / 外键），模拟应用运行环境
from app.db import session as db_session_module  # noqa: F401
from app.db.base import Base

# 注册所有模型，确保 create_all 覆盖全部表；后续模块在此追加导入
from app.modules.auth import models as auth_models  # noqa: F401


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """每个测试函数独立的内存库：建表 → 测试 → 销毁，互不影响。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        # 内存库必须共享同一连接，否则每个新连接都是全新的空库
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
