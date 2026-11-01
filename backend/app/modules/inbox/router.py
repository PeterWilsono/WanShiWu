"""收藏箱 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.inbox.models import BookmarkStatus
from app.modules.inbox.schemas import BookmarkCreate, BookmarkUpdate
from app.modules.inbox.service import (
    bookmark_response,
    create_bookmark,
    delete_bookmark,
    get_bookmark,
    list_bookmarks,
    list_tags,
    search_bookmarks,
    update_bookmark,
)

router = APIRouter(tags=["收藏箱"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/bookmarks")
def list_bookmarks_endpoint(
    db: Db,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: BookmarkStatus | None = None,
    tag: str | None = Query(default=None, max_length=30),
) -> dict:
    result = list_bookmarks(
        db,
        current_user.id,
        page=page,
        page_size=page_size,
        status=status,
        tag=tag,
    )
    return ok(result.model_dump(mode="json"))


@router.post("/bookmarks")
def create_bookmark_endpoint(db: Db, current_user: CurrentUser, data: BookmarkCreate) -> dict:
    bookmark = create_bookmark(db, current_user.id, data)
    result = bookmark_response(db, current_user.id, bookmark)
    return ok(result.model_dump(mode="json"), "收藏已保存，等待处理")


@router.get("/bookmarks/search")
def search_bookmarks_endpoint(
    db: Db,
    current_user: CurrentUser,
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    result = search_bookmarks(db, current_user.id, q, page=page, page_size=page_size)
    return ok(result.model_dump(mode="json"))


@router.get("/bookmarks/{bookmark_id}")
def get_bookmark_endpoint(db: Db, current_user: CurrentUser, bookmark_id: int) -> dict:
    bookmark = get_bookmark(db, current_user.id, bookmark_id)
    result = bookmark_response(db, current_user.id, bookmark)
    return ok(result.model_dump(mode="json"))


@router.patch("/bookmarks/{bookmark_id}")
def update_bookmark_endpoint(
    db: Db, current_user: CurrentUser, bookmark_id: int, data: BookmarkUpdate
) -> dict:
    bookmark = update_bookmark(db, current_user.id, bookmark_id, data)
    result = bookmark_response(db, current_user.id, bookmark)
    return ok(result.model_dump(mode="json"), "收藏已更新")


@router.delete("/bookmarks/{bookmark_id}")
def delete_bookmark_endpoint(db: Db, current_user: CurrentUser, bookmark_id: int) -> dict:
    delete_bookmark(db, current_user.id, bookmark_id)
    return ok(None, "收藏已删除")


@router.get("/tags")
def list_tags_endpoint(db: Db, current_user: CurrentUser) -> dict:
    return ok({"items": [item.model_dump(mode="json") for item in list_tags(db, current_user.id)]})
