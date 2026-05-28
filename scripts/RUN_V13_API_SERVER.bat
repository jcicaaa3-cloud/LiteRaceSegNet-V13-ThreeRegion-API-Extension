@echo off
setlocal
cd /d %~dp0\..

echo [LiteRaceSegNet V13 API Server]
echo This server must be run from the LiteRaceSegNet-V13-Portal-Clean repository root.
echo.

if not exist "seg\capstone_batch_service.py" (
  echo [ERROR] seg\capstone_batch_service.py not found.
  echo Copy this add-on into the V13 repository root first.
  pause
  exit /b 1
)

python -m pip install -r requirements_api.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
