"""万事屋后端应用入口。

依据 PROJECT_SPEC.md 6.1：应用入口、路由注册、生命周期。
阶段 0 仅提供健康检查（附录 C），业务路由随阶段推进逐个注册。
"""

from fastapi import FastAPI

from app.core.config import settings
from app.core.response import ok

app = FastAPI(
    title="万事屋 API",
    description="个人生活效率平台：统一 AI 入口 + 生活管家 / 食材管家 / 收藏箱 / 旅行规划",
    version="0.1.0",
)


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    """健康检查（无需登录，见 PROJECT_SPEC.md 8.4）。"""
    return ok({"status": "ok", "app_env": settings.app_env})
