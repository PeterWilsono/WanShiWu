"""数据库引擎与会话管理（PROJECT_SPEC.md 4.1 / 7.1）。"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    """SQLite 文件库的父目录不存在时自动创建。

    SQLite 自身不会创建目录，若不处理，首次启动会因目录不存在而报错。
    """
    prefix = "sqlite:///"
    if url.startswith(prefix) and ":memory:" not in url:
        db_path = Path(url.removeprefix(prefix))
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    # SQLite 默认禁止跨线程使用连接，FastAPI 多线程场景需关闭该检查
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """每次新建连接都执行必需 PRAGMA（7.1）。

    - foreign_keys=ON：SQLite 默认不强制外键，必须显式开启；
    - journal_mode=WAL：读写不互斥，减少 database is locked。
    监听挂在 Engine 类上，测试用内存库同样生效（内存库 journal_mode
    会返回 memory 而非 wal，属 SQLite 正常行为）。
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每请求一个会话；测试通过 dependency_overrides 替换为内存库。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
