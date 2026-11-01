"""SQLite 在线备份的一致性、完整性与禁止覆盖测试。"""

import runpy
import sqlite3
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "backup_db.py"
backup_database = runpy.run_path(str(SCRIPT))["backup_database"]


def test_backup_preserves_committed_data_and_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backups" / "copy.db"
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE notes (body TEXT NOT NULL)")
        db.execute("INSERT INTO notes VALUES ('需要保留的内容')")

    result = backup_database(source, destination)
    assert result == destination
    assert destination.is_file()
    assert not destination.with_name(f"{destination.name}.tmp").exists()
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT body FROM notes").fetchone() == ("需要保留的内容",)
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    with pytest.raises(FileExistsError, match="未覆盖"):
        backup_database(source, destination)
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT COUNT(*) FROM notes").fetchone() == (1,)


def test_backup_rejects_missing_source_and_source_as_destination(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError, match="数据库不存在"):
        backup_database(missing, tmp_path / "copy.db")

    source = tmp_path / "source.db"
    sqlite3.connect(source).close()
    with pytest.raises(ValueError, match="不能覆盖源数据库"):
        backup_database(source, source)
