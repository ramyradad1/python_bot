@echo off
SETLOCAL EnableDelayedExpansion

echo [1/4] Checking Python Virtual Environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment exists.
)

echo [2/4] Activating Virtual Environment...
call .\venv\Scripts\activate

echo [3/4] Ensuring requirements are installed...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements_seo_bot.txt
pip install flask

echo [4/4] Starting Nerve Center Dashboard...
echo Dashboard will be available at http://127.0.0.1:5050

:: Wait 2 seconds then open the default browser
start "" http://localhost:5050

python dashboard_server.py

pause

