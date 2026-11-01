"""测试公共设施。

依据 PROJECT_SPEC.md 12.2：测试使用独立的内存 SQLite，
每个测试函数之间数据隔离；禁止真实调用大模型与外部网络。
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 必须在导入应用配置前设置：测试不启动真实后台调度，避免写入开发数据库。
os.environ["SCHEDULER_ENABLED"] = "false"

# 导入 session 模块以注册 SQLite PRAGMA 监听器（WAL / 外键），模拟应用运行环境。
# 同时注册所有模型，确保 create_all 覆盖全部表；后续模块在此追加导入。
from app.assistant import models as assistant_models  # noqa: E402,F401
from app.db import session as db_session_module  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.llm import models as llm_models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.modules.auth import models as auth_models  # noqa: E402,F401
from app.modules.inbox import models as inbox_models  # noqa: E402,F401
from app.modules.inbox.dependencies import get_bookmark_processor  # noqa: E402
from app.modules.inbox.fts import ensure_bookmarks_fts  # noqa: E402
from app.modules.life import models as life_models  # noqa: E402,F401
from app.modules.pantry import models as pantry_models  # noqa: E402,F401


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
    ensure_bookmarks_fts(session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """接口测试客户端：把应用数据库依赖替换为当前测试的独立内存库。"""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_bookmark_processor():
        def process(_bookmark_id: int, _user_id: int) -> None:
            return None

        return process

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_bookmark_processor] = override_bookmark_processor
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
