"""SQLite FTS5 索引维护；业务表与索引在同一事务中更新。"""

from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.modules.inbox.models import Bookmark

BOOKMARKS_FTS_DDL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts "
    "USING fts5(title, summary, content, tokenize='trigram')"
)


def ensure_bookmarks_fts(db: Session | Connection) -> None:
    """create_all 不识别虚拟表，因此测试与迁移需要显式执行同一 DDL。"""
    db.execute(text(BOOKMARKS_FTS_DDL))


def upsert_bookmark_fts(db: Session, bookmark: Bookmark) -> None:
    db.execute(text("DELETE FROM bookmarks_fts WHERE rowid = :id"), {"id": bookmark.id})
    db.execute(
        text(
            "INSERT INTO bookmarks_fts(rowid, title, summary, content) "
            "VALUES (:id, :title, :summary, :content)"
        ),
        {
            "id": bookmark.id,
            "title": bookmark.title or "",
            "summary": bookmark.summary or "",
            "content": bookmark.content or "",
        },
    )


def delete_bookmark_fts(db: Session, bookmark_id: int) -> None:
    db.execute(text("DELETE FROM bookmarks_fts WHERE rowid = :id"), {"id": bookmark_id})
