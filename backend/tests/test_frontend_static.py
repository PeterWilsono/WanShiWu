"""桌面版与单进程部署的前端静态页面托管测试。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web import mount_frontend


def test_frontend_serves_assets_and_spa_without_capturing_api(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<main>万事屋</main>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    mount_frontend(app, tmp_path)
    client = TestClient(app)

    assert client.get("/").text == "<main>万事屋</main>"
    assert client.get("/trip/12").text == "<main>万事屋</main>"
    assert client.get("/assets/app.js").text == "console.log('ok')"
    assert client.get("/api/v1/health").json() == {"ok": True}
    assert client.get("/api/v1/not-found").status_code == 404


def test_frontend_requires_built_index(tmp_path: Path) -> None:
    app = FastAPI()

    try:
        mount_frontend(app, tmp_path)
    except RuntimeError as exc:
        assert "前端入口不存在" in str(exc)
    else:
        raise AssertionError("缺少 index.html 时应当拒绝启动")
