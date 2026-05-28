@echo off
setlocal
cd /d %~dp0\..
echo [CHECK] V13 API-ready file check
if exist "seg\capstone_batch_service.py" (echo [OK] batch service script) else (echo [MISS] seg\capstone_batch_service.py)
if exist "seg\config\pothole_binary_literace_train.yaml" (echo [OK] V13 config) else (echo [MISS] seg\config\pothole_binary_literace_train.yaml)
if exist "seg\runs\literace_boundary_degradation\best.pth" (echo [OK] V13 checkpoint) else (echo [MISS] seg\runs\literace_boundary_degradation\best.pth)
if exist "requirements_api.txt" (echo [OK] requirements_api.txt) else (echo [MISS] requirements_api.txt)
if exist "app\main.py" (echo [OK] app\main.py) else (echo [MISS] app\main.py)
echo.
echo If checkpoint is missing, train/copy it locally. Do not commit private weights to public GitHub.
pause
