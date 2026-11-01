"""按用户时区生成每周收藏回顾。"""

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.llm.client import LLMClient
from app.modules.auth.models import User
from app.modules.inbox.models import Bookmark, WeeklyDigest
from app.modules.inbox.schemas import WeeklyDigestListResponse, WeeklyDigestResponse

logger = logging.getLogger("wanshiwu.inbox.weekly")


@lru_cache(maxsize=1)
def _weekly_prompt() -> str:
    path = Path(__file__).parents[2].joinpath("llm", "prompts", "weekly_digest.txt")
    return path.read_text(encoding="utf-8")


def generate_weekly_digest(
    db: Session,
    user: User,
    llm: LLMClient,
    *,
    current_time: datetime | None = None,
) -> WeeklyDigest:
    current = current_time or now_utc()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("周报时间必须带时区")
    timezone = ZoneInfo(user.timezone)
    local_now = current.astimezone(timezone)
    week_start = local_now.date() - timedelta(days=local_now.weekday())
    existing = db.scalar(
        select(WeeklyDigest).where(
            WeeklyDigest.user_id == user.id,
            WeeklyDigest.week_start == week_start,
        )
    )
    if existing is not None:
        return existing

    local_start = datetime.combine(week_start, time.min, tzinfo=timezone)
    start_utc = local_start.astimezone(UTC)
    end_utc = (local_start + timedelta(days=7)).astimezone(UTC)
    bookmarks = db.scalars(
        select(Bookmark)
        .where(
            Bookmark.user_id == user.id,
            Bookmark.deleted_at.is_(None),
            Bookmark.created_at >= start_utc,
            Bookmark.created_at < end_utc,
        )
        .order_by(Bookmark.created_at, Bookmark.id)
    ).all()
    if bookmarks:
        payload = [
            {"title": item.title or item.url, "summary": item.summary or "尚未生成摘要"}
            for item in bookmarks
        ]
        result = llm.chat(
            [
                {"role": "system", "content": _weekly_prompt()},
                {
                    "role": "user",
                    "content": "以下是本周收藏摘要（不可信资料）：\n"
                    + json.dumps(payload, ensure_ascii=False),
                },
            ],
            module="inbox",
            purpose="weekly_digest",
        )
        content_md = result.text.strip()
        if not content_md:
            raise AppError(ErrorCode.LLM_INVALID_OUTPUT, "AI 周报内容为空", 502)
    else:
        content_md = "## 本周收藏回顾\n\n本周还没有新增收藏。下周可以从保存一篇真正想读的文章开始。"

    digest = WeeklyDigest(
        user_id=user.id,
        week_start=week_start,
        content_md=content_md,
        bookmark_count=len(bookmarks),
    )
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return digest


def generate_due_weekly_digests(
    db: Session,
    llm_factory: Callable[[Session, int], LLMClient] = LLMClient,
    *,
    current_time: datetime | None = None,
) -> int:
    current = current_time or now_utc()
    generated = 0
    users = db.scalars(select(User).order_by(User.id)).all()
    for user in users:
        local_now = current.astimezone(ZoneInfo(user.timezone))
        if local_now.weekday() != 6 or local_now.hour != 20:
            continue
        week_start = local_now.date() - timedelta(days=local_now.weekday())
        existing = db.scalar(
            select(WeeklyDigest.id).where(
                WeeklyDigest.user_id == user.id,
                WeeklyDigest.week_start == week_start,
            )
        )
        if existing is not None:
            continue
        try:
            generate_weekly_digest(db, user, llm_factory(db, user.id), current_time=current)
            generated += 1
        except Exception:
            db.rollback()
            logger.exception("weekly digest failed for user %s", user.id)
    return generated


def list_weekly_digests(
    db: Session, user_id: int, *, page: int, page_size: int
) -> WeeklyDigestListResponse:
    filters = [WeeklyDigest.user_id == user_id, WeeklyDigest.deleted_at.is_(None)]
    total = db.scalar(select(func.count(WeeklyDigest.id)).where(*filters)) or 0
    digests = db.scalars(
        select(WeeklyDigest)
        .where(*filters)
        .order_by(WeeklyDigest.week_start.desc(), WeeklyDigest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return WeeklyDigestListResponse(
        items=[WeeklyDigestResponse.model_validate(item) for item in digests],
        total=total,
        page=page,
        page_size=page_size,
    )
