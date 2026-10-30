"""业务异常与全局异常处理。

依据 PROJECT_SPEC.md 8.2 / 8.3：
- 业务错误抛 AppError(code, message, http_status)，由全局处理器转统一响应；
- 不得把堆栈信息返回给前端，堆栈只写入日志。
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("wanshiwu")


class ErrorCode:
    """业务错误码，与 PROJECT_SPEC.md 8.3 一一对应。"""

    OK = 0
    VALIDATION_ERROR = 40001  # 参数校验失败
    UNAUTHORIZED = 40101  # 未登录或令牌无效 / 过期
    BAD_CREDENTIALS = 40102  # 用户名或密码错误
    NOT_FOUND = 40401  # 资源不存在（含无权访问）
    CONFLICT = 40901  # 冲突（重复收藏、重复确认等）
    BUSINESS_RULE_VIOLATION = 42201  # 业务规则不满足（库存不足、日期冲突等）
    LLM_DAILY_LIMIT = 42901  # 超过每日 LLM 调用上限
    INTERNAL_ERROR = 50001  # 服务器内部错误
    LLM_CALL_FAILED = 50201  # LLM 服务调用失败或超时
    LLM_INVALID_OUTPUT = 50202  # LLM 输出无法解析或校验失败


class AppError(Exception):
    """业务异常：在 service 层抛出，由全局异常处理器转为统一响应。

    为什么不返回错误字典（14.1）：异常能穿过任意调用层级直达处理器，
    业务代码无需每层检查返回值，错误路径不会被静默吞掉。
    """

    def __init__(self, code: int, message: str, http_status: int, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data


def _error_body(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """统一错误响应体（与成功响应同为 code / message / data 三字段）。"""
    return {"code": code, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，把所有错误统一为 8.2 的响应格式。"""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_body(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # FastAPI 默认 422 错误体改为项目统一格式，字段级校验细节放 data.errors
        return JSONResponse(
            status_code=422,
            content=_error_body(
                ErrorCode.VALIDATION_ERROR,
                "参数校验失败",
                # Pydantic 自定义校验的 ctx 可能含 ValueError 对象，不能直接 json.dumps。
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 框架层异常（路由不存在 404、方法不允许 405 等）也走统一格式。
        # 8.3 未逐一覆盖框架状态码，映射约定：404 → 40401；其余 4xx → 40001；5xx → 50001
        if exc.status_code == 404:
            code, message = ErrorCode.NOT_FOUND, "资源不存在"
        elif exc.status_code >= 500:
            code, message = ErrorCode.INTERNAL_ERROR, "服务器内部错误"
        else:
            code, message = ErrorCode.VALIDATION_ERROR, str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # 堆栈只进日志（含请求上下文），绝不返回给前端（8.3）
        logger.exception("unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body(ErrorCode.INTERNAL_ERROR, "服务器内部错误"),
        )
