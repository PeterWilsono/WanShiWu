"""统一响应格式。

依据 PROJECT_SPEC.md 8.2：所有接口返回 {"code": 0, "message": "ok", "data": ...}。
错误响应（AppError / 全局异常处理器）在阶段 1 实现。
"""

from typing import Any


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    """构造统一成功响应体。

    为什么用普通 dict 而不是 Pydantic 模型：data 的结构随接口变化，
    统一格式本身只需要三个固定字段，dict 足够且不引入多余校验开销。
    """
    return {"code": 0, "message": message, "data": data}
