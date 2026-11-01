"""每小时检查时区，命中用户当地周日 20:00 时生成收藏周报。"""

import logging

from app.db.session import SessionLocal
from app.modules.inbox.digest_service import generate_due_weekly_digests

logger = logging.getLogger("wanshiwu.scheduler")


def run_weekly_digest_scan() -> None:
    db = SessionLocal()
    try:
        generated = generate_due_weekly_digests(db)
        if generated:
            logger.info("weekly digests generated", extra={"generated_count": generated})
    except Exception:
        logger.exception("weekly digest scan failed")
    finally:
        db.close()
