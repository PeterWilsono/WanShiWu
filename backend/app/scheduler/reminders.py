"""每分钟触发生效提醒；扫描规则位于 life.service，便于独立测试。"""

import logging
from datetime import UTC

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.modules.life.service import fire_due_reminders

logger = logging.getLogger("wanshiwu.scheduler")


def run_reminder_scan() -> None:
    """每次任务使用独立数据库会话，异常不蔓延到调度器线程。"""
    db = SessionLocal()
    try:
        fired_count = fire_due_reminders(db)
        if fired_count:
            logger.info("reminders fired", extra={"fired_count": fired_count})
    except Exception:
        logger.exception("reminder scan failed")
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        run_reminder_scan,
        trigger="interval",
        minutes=1,
        id="fire_due_reminders",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    return scheduler
