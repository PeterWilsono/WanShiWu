"""收藏 CRUD、标签与全文搜索业务规则。"""

from collections.abc import Sequence
from urllib.parse import urlsplit

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.modules.inbox.fts import delete_bookmark_fts, upsert_bookmark_fts
from app.modules.inbox.models import Bookmark, BookmarkStatus, BookmarkTag, Tag, TagSource
from app.modules.inbox.schemas import (
    BookmarkCreate,
    BookmarkListResponse,
    BookmarkResponse,
    BookmarkTagResponse,
    BookmarkUpdate,
    TagResponse,
)


def get_bookmark(db: Session, user_id: int, bookmark_id: int) -> Bookmark:
    bookmark = db.scalar(
        select(Bookmark).where(
            Bookmark.id == bookmark_id,
            Bookmark.user_id == user_id,
            Bookmark.deleted_at.is_(None),
        )
    )
    if bookmark is None:
        raise AppError(ErrorCode.NOT_FOUND, "收藏不存在", 404)
    return bookmark


def _tag_map(
    db: Session, user_id: int, bookmark_ids: Sequence[int]
) -> dict[int, list[BookmarkTagResponse]]:
    if not bookmark_ids:
        return {}
    rows = db.execute(
        select(BookmarkTag, Tag)
        .join(Tag, Tag.id == BookmarkTag.tag_id)
        .where(
            BookmarkTag.bookmark_id.in_(bookmark_ids),
            Tag.user_id == user_id,
            Tag.deleted_at.is_(None),
        )
        .order_by(Tag.name, Tag.id)
    ).all()
    result: dict[int, list[BookmarkTagResponse]] = {item_id: [] for item_id in bookmark_ids}
    for association, tag in rows:
        result[association.bookmark_id].append(
            BookmarkTagResponse(id=tag.id, name=tag.name, source=association.source)
        )
    return result


def bookmark_response(db: Session, user_id: int, bookmark: Bookmark) -> BookmarkResponse:
    tags = _tag_map(db, user_id, [bookmark.id]).get(bookmark.id, [])
    return BookmarkResponse(
        id=bookmark.id,
        url=bookmark.url,
        title=bookmark.title,
        summary=bookmark.summary,
        content=bookmark.content,
        status=bookmark.status,
        fail_reason=bookmark.fail_reason,
        note=bookmark.note,
        source_domain=bookmark.source_domain,
        fetched_at=bookmark.fetched_at,
        tags=tags,
        created_at=bookmark.created_at,
        updated_at=bookmark.updated_at,
    )


def _bookmark_list_response(
    db: Session,
    user_id: int,
    bookmarks: Sequence[Bookmark],
    total: int,
    page: int,
    page_size: int,
) -> BookmarkListResponse:
    tags = _tag_map(db, user_id, [item.id for item in bookmarks])
    items = []
    for bookmark in bookmarks:
        item = bookmark_response(db, user_id, bookmark)
        item.tags = tags.get(bookmark.id, [])
        items.append(item)
    return BookmarkListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


def _set_manual_tags(db: Session, user_id: int, bookmark: Bookmark, names: list[str]) -> None:
    db.execute(
        delete(BookmarkTag).where(
            BookmarkTag.bookmark_id == bookmark.id,
            BookmarkTag.source == TagSource.MANUAL,
        )
    )
    for name in names:
        tag = db.scalar(select(Tag).where(Tag.user_id == user_id, Tag.name == name))
        if tag is None:
            tag = Tag(user_id=user_id, name=name)
            db.add(tag)
            db.flush()
        elif tag.deleted_at is not None:
            tag.deleted_at = None
        association = db.get(BookmarkTag, (bookmark.id, tag.id))
        if association is None:
            db.add(
                BookmarkTag(bookmark_id=bookmark.id, tag_id=tag.id, source=TagSource.MANUAL)
            )
        else:
            association.source = TagSource.MANUAL
    db.flush()


def create_bookmark(
    db: Session, user_id: int, data: BookmarkCreate, *, commit: bool = True
) -> Bookmark:
    bookmark = db.scalar(
        select(Bookmark).where(Bookmark.user_id == user_id, Bookmark.url == data.url)
    )
    if bookmark is not None and bookmark.deleted_at is None:
        raise AppError(ErrorCode.CONFLICT, "这个链接已经收藏过了", 409)
    if bookmark is None:
        bookmark = Bookmark(user_id=user_id, url=data.url)
        db.add(bookmark)
    else:
        db.execute(delete(BookmarkTag).where(BookmarkTag.bookmark_id == bookmark.id))
        bookmark.deleted_at = None
        bookmark.created_at = now_utc()
        bookmark.summary = None
        bookmark.content = None
        bookmark.fetched_at = None
    bookmark.title = data.title.strip() if data.title else None
    bookmark.note = data.note.strip() if data.note else None
    bookmark.status = BookmarkStatus.PENDING
    bookmark.fail_reason = None
    bookmark.source_domain = urlsplit(data.url).hostname
    db.flush()
    _set_manual_tags(db, user_id, bookmark, data.tags)
    upsert_bookmark_fts(db, bookmark)
    if commit:
        db.commit()
        db.refresh(bookmark)
    return bookmark


def update_bookmark(
    db: Session, user_id: int, bookmark_id: int, data: BookmarkUpdate
) -> Bookmark:
    bookmark = get_bookmark(db, user_id, bookmark_id)
    updates = data.model_dump(exclude_unset=True)
    tags = updates.pop("tags", None)
    for field, value in updates.items():
        setattr(bookmark, field, value.strip() if isinstance(value, str) else value)
    if tags is not None:
        _set_manual_tags(db, user_id, bookmark, tags)
    upsert_bookmark_fts(db, bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


def delete_bookmark(db: Session, user_id: int, bookmark_id: int) -> None:
    bookmark = get_bookmark(db, user_id, bookmark_id)
    bookmark.deleted_at = now_utc()
    delete_bookmark_fts(db, bookmark.id)
    db.commit()


def list_bookmarks(
    db: Session,
    user_id: int,
    *,
    page: int,
    page_size: int,
    status: BookmarkStatus | None = None,
    tag: str | None = None,
) -> BookmarkListResponse:
    filters = [Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None)]
    if status is not None:
        filters.append(Bookmark.status == status)
    statement = select(Bookmark).where(*filters)
    count_statement = select(func.count(Bookmark.id)).where(*filters)
    if tag:
        statement = statement.join(BookmarkTag).join(Tag).where(
            Tag.user_id == user_id,
            Tag.name == tag,
            Tag.deleted_at.is_(None),
        )
        count_statement = count_statement.join(BookmarkTag).join(Tag).where(
            Tag.user_id == user_id,
            Tag.name == tag,
            Tag.deleted_at.is_(None),
        )
    total = db.scalar(count_statement) or 0
    bookmarks = db.scalars(
        statement.order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return _bookmark_list_response(db, user_id, bookmarks, total, page, page_size)


def _like_query(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_bookmarks(
    db: Session, user_id: int, query: str, *, page: int, page_size: int
) -> BookmarkListResponse:
    query = query.strip()
    if len(query) < 3:
        pattern = _like_query(query)
        filters = [
            Bookmark.user_id == user_id,
            Bookmark.deleted_at.is_(None),
            or_(
                Bookmark.title.like(pattern, escape="\\"),
                Bookmark.summary.like(pattern, escape="\\"),
                Bookmark.content.like(pattern, escape="\\"),
            ),
        ]
        total = db.scalar(select(func.count(Bookmark.id)).where(*filters)) or 0
        bookmarks = db.scalars(
            select(Bookmark)
            .where(*filters)
            .order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return _bookmark_list_response(db, user_id, bookmarks, total, page, page_size)

    fts_query = '"' + query.replace('"', '""') + '"'
    params = {
        "user_id": user_id,
        "query": fts_query,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    total = db.execute(
        text(
            "SELECT count(*) FROM bookmarks b "
            "WHERE b.user_id = :user_id AND b.deleted_at IS NULL "
            "AND b.id IN (SELECT rowid FROM bookmarks_fts WHERE bookmarks_fts MATCH :query)"
        ),
        params,
    ).scalar_one()
    ids = db.execute(
        text(
            "SELECT b.id FROM bookmarks b "
            "WHERE b.user_id = :user_id AND b.deleted_at IS NULL "
            "AND b.id IN (SELECT rowid FROM bookmarks_fts WHERE bookmarks_fts MATCH :query) "
            "ORDER BY b.created_at DESC, b.id DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).scalars().all()
    bookmarks = db.scalars(select(Bookmark).where(Bookmark.id.in_(ids))).all() if ids else []
    by_id = {item.id: item for item in bookmarks}
    ordered = [by_id[item_id] for item_id in ids]
    return _bookmark_list_response(db, user_id, ordered, total, page, page_size)


def list_tags(db: Session, user_id: int) -> list[TagResponse]:
    tags = db.scalars(
        select(Tag)
        .where(Tag.user_id == user_id, Tag.deleted_at.is_(None))
        .order_by(Tag.name, Tag.id)
    ).all()
    return [TagResponse.model_validate(tag) for tag in tags]
