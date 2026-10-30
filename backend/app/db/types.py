"""自定义数据库字段类型。"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """保证读写均为带 UTC 时区的 DateTime（PROJECT_SPEC.md 7.1）。

    为什么需要它：SQLite 没有原生时区类型，方言读回的是 naive datetime，
    与 now_utc()（aware）比较时会抛
    "TypeError: can't compare offset-naive and offset-aware datetimes"。
    约定：写入统一转为 UTC，读出统一补回 UTC 时区，业务代码拿到的永远是
    aware UTC 时间，展示层再按用户时区转换。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            # naive 写入值一律按 UTC 解释，不允许混入本地时间
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
