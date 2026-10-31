"""LLM 调用审计日志；默认不保存 Prompt 或响应全文。"""

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UserOwnedMixin


class LLMCallLog(UserOwnedMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "llm_call_logs"
    __table_args__ = (
        Index("ix_llm_call_logs_user_created_at", "user_id", "created_at"),
        CheckConstraint("prompt_tokens >= 0", name="ck_llm_logs_prompt_tokens_non_negative"),
        CheckConstraint("completion_tokens >= 0", name="ck_llm_logs_completion_non_negative"),
        CheckConstraint("latency_ms >= 0", name="ck_llm_logs_latency_non_negative"),
    )

    module: Mapped[str] = mapped_column(String(30))
    purpose: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(50))
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    success: Mapped[bool] = mapped_column()
    error_type: Mapped[str | None] = mapped_column(String(50))
