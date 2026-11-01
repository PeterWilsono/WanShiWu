"""收藏箱请求与响应模型。"""

from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.inbox.models import BookmarkStatus, TagSource


def normalize_url(value: str) -> str:
    value = value.strip()
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL 格式不正确") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise ValueError("仅支持有效的 http / https 链接")
    if parsed.username or parsed.password:
        raise ValueError("链接不能包含用户名或密码")
    try:
        hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("URL 域名不正确") from exc
    if len(hostname) > 100:
        raise ValueError("URL 域名过长")
    host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = f"{host}:{port}" if port is not None else host
    normalized = urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    if len(normalized) > 2000:
        raise ValueError("URL 不能超过 2000 个字符")
    return normalized


def clean_tags(value: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        name = item.strip()
        if not name:
            raise ValueError("标签不能为空白")
        if len(name) > 30:
            raise ValueError("每个标签不能超过 30 个字符")
        if name not in seen:
            cleaned.append(name)
            seen.add(name)
    return cleaned


class BookmarkCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return normalize_url(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return clean_tags(value)


class BookmarkUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        return clean_tags(value) if value is not None else None


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BookmarkTagResponse(BaseModel):
    id: int
    name: str
    source: TagSource


class BookmarkResponse(BaseModel):
    id: int
    url: str
    title: str | None
    summary: str | None
    content: str | None
    status: BookmarkStatus
    fail_reason: str | None
    note: str | None
    source_domain: str | None
    fetched_at: datetime | None
    tags: list[BookmarkTagResponse]
    created_at: datetime
    updated_at: datetime


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
    total: int
    page: int
    page_size: int


class TagListResponse(BaseModel):
    items: list[TagResponse]


class ManualContentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("正文不能为空白")
        return cleaned


class SummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=150)
    tags: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return clean_tags(value)


class WeeklyDigestResponse(BaseModel):
    id: int
    week_start: date
    content_md: str
    bookmark_count: int
    created_at: datetime
