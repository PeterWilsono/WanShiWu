"""首页与桌面关闭确认共用文案的数量、质量和同步检查。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_affirmations_are_unique_nonempty_and_synchronized() -> None:
    desktop = json.loads((ROOT / "desktop" / "affirmations.json").read_text(encoding="utf-8"))
    frontend = json.loads(
        (ROOT / "frontend" / "src" / "constants" / "affirmations.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(desktop) >= 40
    assert desktop == frontend
    assert len(desktop) == len(set(desktop))
    assert all(isinstance(text, str) and 6 <= len(text.strip()) <= 60 for text in desktop)
