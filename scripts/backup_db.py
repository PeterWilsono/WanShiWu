"""使用 SQLite Online Backup API 创建一致性备份，不覆盖已有文件。"""

import argparse
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def backup_database(source_path: Path, destination_path: Path) -> Path:
    """备份运行中的 SQLite 数据库，校验成功后原子改名；从不覆盖旧备份。"""
    source = source_path.expanduser().resolve()
    destination = destination_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"数据库不存在：{source}")
    if source == destination:
        raise ValueError("备份文件不能覆盖源数据库")
    if destination.exists():
        raise FileExistsError(f"备份文件已存在，未覆盖：{destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"临时备份已存在，请先人工检查：{temporary}")

    try:
        with (
            closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True, timeout=30)) as source_db,
            closing(sqlite3.connect(temporary, timeout=30)) as destination_db,
        ):
            source_db.backup(destination_db)
        with closing(sqlite3.connect(temporary)) as check_db:
            result = check_db.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise RuntimeError(f"备份完整性检查失败：{result[0] if result else '无结果'}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def main() -> None:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    parser = argparse.ArgumentParser(description="备份万事屋 SQLite 数据库")
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "backend/data/wanshiwu.db")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "backups" / f"wanshiwu-{timestamp}.db",
    )
    args = parser.parse_args()
    result = backup_database(args.source, args.output)
    print(f"备份完成并通过完整性检查：{result}")


if __name__ == "__main__":
    main()
