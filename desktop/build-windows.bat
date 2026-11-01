@echo off
setlocal
cd /d "%~dp0\.."

set "PIP_CACHE_DIR=%CD%\.cache\pip"
set "npm_config_cache=%CD%\.cache\npm"
set "ELECTRON_CACHE=%CD%\.cache\electron"
set "ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/"
set "ELECTRON_BUILDER_CACHE=%CD%\.cache\electron-builder"
set "PYINSTALLER_CONFIG_DIR=%CD%\.cache\pyinstaller-config"
set "ELECTRON_RUN_AS_NODE="

echo [1/4] Building frontend...
call npm --prefix frontend run build || exit /b 1

echo [2/4] Generating application icon...
backend\.venv\Scripts\python.exe desktop\generate_icon.py || exit /b 1

echo [3/4] Packaging embedded backend...
backend\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath desktop\dist\backend --workpath .cache\pyinstaller desktop\pyinstaller.spec || exit /b 1

echo [4/4] Building Windows installer...
call npm --prefix desktop run dist || exit /b 1

echo.
echo Installer created in desktop\release
endlocal
