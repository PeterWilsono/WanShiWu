"""结构化日志。

依据 PROJECT_SPEC.md 13.6：
- 使用结构化日志（JSON），记录请求方法、路径、状态码、耗时、用户 id；
- 错误日志包含堆栈但不包含密码、令牌；
- 日志级别通过环境变量 LOG_LEVEL 控制。
"""

import json
import logging
import time
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class JsonFormatter(logging.Formatter):
    """把日志记录输出为单行 JSON，便于后续检索、统计与采集。

    自写而非引入 python-json-logger：所需字段很少，20 行可实现，
    遵守 5.2「不得擅自引入新依赖」。
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # 请求上下文字段由请求日志中间件通过 extra 注入
        for key in ("method", "path", "status_code", "duration_ms", "user_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """初始化日志：root logger 统一使用 JSON 输出到 stdout。

    为什么配置 root：让 uvicorn / sqlalchemy 等第三方日志也走同一格式，
    避免同一进程出现两种日志风格。
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件：每个请求记录方法、路径、状态码、耗时（13.6）。

    user_id 由登录鉴权依赖写入 request.state（阶段 1 后续任务），未登录时为空。
    未捕获异常由全局异常处理器记录堆栈（含 method / path），此处不重复记录。
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logging.getLogger("wanshiwu.request").info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": getattr(request.state, "user_id", None),
            },
        )
        return response
