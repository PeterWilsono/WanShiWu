@echo off
setlocal
cd /d "%~dp0"
set "PIP_CACHE_DIR=%~dp0.cache\pip"

if not exist "backend\.venv\Scripts\python.exe" (
  echo [ERROR] Backend environment is missing.
  echo Run: cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\python -m pip install -e ".[dev]"
  pause
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo [ERROR] Frontend dependencies are missing.
  echo Run: cd frontend ^&^& npm install
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found. Install Node.js and try again.
  pause
  exit /b 1
)

if not exist "backend\.env" (
  copy /y "backend\.env.example" "backend\.env" >nul
  echo Created backend\.env from the example. Add LLM_API_KEY later if you want to use AI.
)

pushd "backend"
".venv\Scripts\python.exe" -c "import cryptography" >nul 2>nul
if errorlevel 1 (
  echo Installing updated backend dependencies...
  ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
  if errorlevel 1 (
    popd
    echo [ERROR] Backend dependency installation failed. See the message above.
    pause
    exit /b 1
  )
)

echo Applying database migrations...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
  popd
  echo [ERROR] Database migration failed. See the message above.
  pause
  exit /b 1
)
popd

if /i "%~1"=="--check" (
  echo Environment check passed. No services were started.
  exit /b 0
)

echo Starting backend and frontend in separate windows...
start "WanShiWu Backend" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "WanShiWu Frontend" /D "%~dp0frontend" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"

echo Waiting for the frontend...
timeout /t 8 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo.
echo WanShiWu is starting at http://127.0.0.1:5173
echo Keep the Backend and Frontend windows open. Close both windows to stop.
exit /b 0
