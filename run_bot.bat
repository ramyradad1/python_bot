@echo off
SETLOCAL EnableDelayedExpansion
title SEO Bot - Auto Updater

echo ============================================
echo   SEO Bot - Auto Update ^& Launch
echo ============================================
echo.

echo [1/5] Pulling latest updates from GitHub...
git fetch origin master
git reset --hard origin/master
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not pull updates. Running local version...
) else (
    echo [OK] Updated to latest version from GitHub.
)
echo.

echo [2/5] Checking Python Virtual Environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment exists.
)
echo.

echo [3/5] Activating Virtual Environment...
call .\venv\Scripts\activate
echo.

echo [4/5] Ensuring requirements are installed...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install -r requirements_seo_bot.txt --quiet
pip install flask --quiet
echo [OK] All dependencies installed.
echo.

echo [5/5] Starting Nerve Center Dashboard...
echo Dashboard will be available at http://127.0.0.1:5050
echo.

:: Open the browser
start "" http://localhost:5050

python dashboard_server.py

pause
