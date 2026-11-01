"""万事屋后端应用入口。

依据 PROJECT_SPEC.md 6.1：应用入口、路由注册、生命周期。
业务路由随阶段推进逐个注册；当前已具备统一响应、统一异常、结构化日志与认证接口。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.assistant.router import router as assistant_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestLogMiddleware, setup_logging
from app.core.response import ok
from app.modules.auth.router import router as auth_router
from app.modules.inbox.router import router as inbox_router
from app.modules.life.router import router as life_router
from app.modules.pantry.router import router as pantry_router
from app.modules.trip.router import router as trip_router
from app.scheduler.reminders import create_scheduler

setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """进程启动时开启提醒调度，关闭时释放调度器线程。"""
    scheduler = create_scheduler() if settings.scheduler_enabled else None
    if scheduler is not None:
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title="万事屋 API",
    description="个人生活效率平台：统一 AI 入口 + 生活管家 / 食材管家 / 收藏箱 / 旅行规划",
    version="0.1.0",
    lifespan=lifespan,
)

# 先注册异常处理器再加中间件：中间件在更外层，能记录到异常转换后的真实状态码
register_exception_handlers(app)
app.add_middleware(RequestLogMiddleware)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(inbox_router, prefix="/api/v1")
app.include_router(life_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(pantry_router, prefix="/api/v1")
app.include_router(trip_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    """健康检查（无需登录，见 PROJECT_SPEC.md 8.4）。"""
    return ok({"status": "ok", "app_env": settings.app_env})
