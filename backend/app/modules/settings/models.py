"""按用户保存模型配置；数据库只保存加密后的 API Key。"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UserOwnedMixin
from app.db.types import UTCDateTime


class LLMProvider(StrEnum):
    MIMO = "mimo"
    DEEPSEEK = "deepseek"


class UserLLMConfig(UserOwnedMixin, TimestampMixin, Base):
    __tablename__ = "user_llm_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_llm_configs_user_provider"),
    )

    provider: Mapped[LLMProvider] = mapped_column(
        Enum(
            LLMProvider,
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda items: [item.value for item in items],
        )
    )
    base_url: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(100))
    api_key_ciphertext: Mapped[str] = mapped_column(Text)
    key_hint: Mapped[str] = mapped_column(String(24))
    last_tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    last_test_success: Mapped[bool | None] = mapped_column(default=None)
    last_test_error: Mapped[str | None] = mapped_column(String(200), default=None)
