"""时间工具。

依据 PROJECT_SPEC.md 7.1 / 14.1：
- 时间一律存 UTC（带时区）；
- 获取当前时间通过可注入的函数，便于测试时固定时间。
"""

from datetime import UTC, datetime


def now_utc() -> datetime:
    """当前 UTC 时间（带时区）。

    全项目取"当前时间"必须经此函数：测试相对时间逻辑（提醒、临期等）时
    只需替换这一个函数，禁止在业务代码里直接写 datetime.now()。
    """
    return datetime.now(UTC)
