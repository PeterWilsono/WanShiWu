# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path.cwd()
trafilatura_datas, trafilatura_binaries, trafilatura_hidden = collect_all("trafilatura")

a = Analysis(
    [str(ROOT / "desktop" / "backend_entry.py")],
    pathex=[str(ROOT / "backend")],
    binaries=trafilatura_binaries,
    datas=[
        (str(ROOT / "backend" / "alembic"), "alembic"),
        (str(ROOT / "backend" / "alembic.ini"), "."),
        (str(ROOT / "backend" / "app" / "llm" / "prompts"), "app/llm/prompts"),
        (str(ROOT / "frontend" / "dist"), "frontend"),
        *trafilatura_datas,
    ],
    hiddenimports=trafilatura_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="wanshiwu-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "desktop" / "build" / "icon.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="wanshiwu-backend",
)
