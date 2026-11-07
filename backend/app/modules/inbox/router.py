"""收藏箱 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.assistant.dependencies import LLMClientDependency
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.inbox.ai_service import mark_for_retry, regenerate_from_manual_content
from app.modules.inbox.dependencies import BookmarkProcessor
from app.modules.inbox.digest_service import list_weekly_digests
from app.modules.inbox.models import BookmarkStatus
from app.modules.inbox.schemas import BookmarkCreate, BookmarkUpdate, ManualContentRequest
from app.modules.inbox.service import (
    bookmark_response,
    create_bookmark,
    delete_bookmark,
    get_bookmark,
    list_bookmarks,
    list_tags,
    restore_bookmark,
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
def create_bookmark_endpoint(
    db: Db,
    current_user: CurrentUser,
    data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    processor: BookmarkProcessor,
) -> dict:
    bookmark = create_bookmark(db, current_user.id, data)
    background_tasks.add_task(processor, bookmark.id, current_user.id)
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


@router.post("/bookmarks/{bookmark_id}/retry")
def retry_bookmark_endpoint(
    db: Db,
    current_user: CurrentUser,
    bookmark_id: int,
    background_tasks: BackgroundTasks,
    processor: BookmarkProcessor,
) -> dict:
    bookmark = mark_for_retry(db, current_user.id, bookmark_id)
    background_tasks.add_task(processor, bookmark.id, current_user.id)
    result = bookmark_response(db, current_user.id, bookmark)
    return ok(result.model_dump(mode="json"), "已重新加入处理队列")


@router.put("/bookmarks/{bookmark_id}/content")
def update_content_endpoint(
    db: Db,
    current_user: CurrentUser,
    bookmark_id: int,
    data: ManualContentRequest,
    llm: LLMClientDependency,
) -> dict:
    bookmark = regenerate_from_manual_content(db, current_user.id, bookmark_id, data, llm)
    result = bookmark_response(db, current_user.id, bookmark)
    return ok(result.model_dump(mode="json"), "正文与 AI 摘要已更新")


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


@router.post("/bookmarks/{bookmark_id}/restore")
def restore_bookmark_endpoint(db: Db, current_user: CurrentUser, bookmark_id: int) -> dict:
    bookmark = restore_bookmark(db, current_user.id, bookmark_id)
    result = bookmark_response(db, current_user.id, bookmark)
    return ok(result.model_dump(mode="json"), "收藏已恢复")


@router.delete("/bookmarks/{bookmark_id}")
def delete_bookmark_endpoint(db: Db, current_user: CurrentUser, bookmark_id: int) -> dict:
    delete_bookmark(db, current_user.id, bookmark_id)
    return ok(None, "收藏已删除")


@router.get("/inbox/weekly-digests")
def weekly_digests_endpoint(
    db: Db,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    result = list_weekly_digests(db, current_user.id, page=page, page_size=page_size)
    return ok(result.model_dump(mode="json"))


@router.get("/tags")
def list_tags_endpoint(db: Db, current_user: CurrentUser) -> dict:
    return ok({"items": [item.model_dump(mode="json") for item in list_tags(db, current_user.id)]})
