"""统一异常处理测试（PROJECT_SPEC.md 8.2 / 8.3）。

通过向 app 注册一次性测试路由来触发各类异常，
验证全局异常处理器输出的统一格式；路径以 _test_ 前缀避免与业务路由冲突。
"""

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError, ErrorCode
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    # raise_server_exceptions=False：让未捕获异常也返回统一 500 响应，而不是在测试里抛出
    return TestClient(app, raise_server_exceptions=False)


def test_app_error_returns_unified_format(client: TestClient) -> None:
    """业务异常 AppError 按自身 code / message / http_status 返回。"""

    async def boom() -> None:
        raise AppError(ErrorCode.NOT_FOUND, "资源不存在", 404)

    app.add_api_route("/api/v1/_test_app_error", boom, methods=["GET"])
    resp = client.get("/api/v1/_test_app_error")
    assert resp.status_code == 404
    assert resp.json() == {"code": 40401, "message": "资源不存在", "data": None}


def test_validation_error_returns_40001_with_details(client: TestClient) -> None:
    """入参校验失败返回 HTTP 422 + code 40001，字段细节在 data.errors。"""

    async def need_num(num: int) -> dict[str, int]:
        return {"num": num}

    app.add_api_route("/api/v1/_test_validation", need_num, methods=["GET"])
    resp = client.get("/api/v1/_test_validation", params={"num": "abc"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 40001
    assert body["message"] == "参数校验失败"
    assert body["data"]["errors"], "应包含字段级校验错误详情"


def test_unexpected_error_returns_50001_without_traceback(client: TestClient) -> None:
    """未捕获异常返回 50001，响应体不泄露堆栈与内部错误细节（8.3）。"""

    async def crash() -> None:
        raise ValueError("sensitive internal detail")

    app.add_api_route("/api/v1/_test_crash", crash, methods=["GET"])
    resp = client.get("/api/v1/_test_crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == 50001
    assert body["message"] == "服务器内部错误"
    assert "sensitive internal detail" not in resp.text
    assert "Traceback" not in resp.text


def test_unknown_route_returns_40401(client: TestClient) -> None:
    """不存在的路由同样返回统一格式，而非框架默认错误体。"""
    resp = client.get("/api/v1/not-exist")
    assert resp.status_code == 404
    assert resp.json()["code"] == 40401
