"""健康检查接口测试（阶段 0 唯一用例，见 PROJECT_SPEC.md 附录 C）。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_unified_ok_response() -> None:
    """GET /api/v1/health 返回 200 且符合统一响应格式。"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["status"] == "ok"
