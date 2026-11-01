"""桌面版后端入口：固定数据目录、自动迁移并静默提供页面与 API。"""

import os
import secrets
import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config


def _resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _data_directory() -> Path:
    configured = os.environ.get("WANSHIWU_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local / "WanShiWu" / "data"
    return Path.home() / ".wanshiwu"


def _prepare_environment(root: Path, frozen: bool) -> None:
    data_dir = _data_directory()
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_file = data_dir / "jwt-secret.txt"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")

    frontend = root / ("frontend" if frozen else "frontend/dist")
    os.environ.update(
        {
            "APP_ENV": "prod",
            "DATABASE_URL": f"sqlite:///{(data_dir / 'wanshiwu.db').as_posix()}",
            "FRONTEND_DIST": str(frontend),
            "JWT_SECRET": secret_file.read_text(encoding="utf-8").strip(),
        }
    )


def _migrate(root: Path, frozen: bool) -> None:
    backend = root if frozen else root / "backend"
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(config, "head")


def main() -> None:
    frozen = hasattr(sys, "_MEIPASS")
    root = _resource_root()
    _prepare_environment(root, frozen)
    # 显式导入让 PyInstaller 收集全部业务模块，同时保证环境变量先于应用配置加载。
    from app.main import app

    _migrate(root, frozen)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ.get("WANSHIWU_PORT", "8765")),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
