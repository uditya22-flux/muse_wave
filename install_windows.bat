@echo off
setlocal
echo ============================================================
echo   MUSEWAVE v2.0.0 :: WINDOWS 10/11 INSTALLER
echo ============================================================

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is not installed or not in PATH.
    echo Download Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Creating Python virtual environment...
python -m venv venv

echo [2/3] Installing Python dependencies...
call venv\Scripts\pip.exe install --upgrade pip
call venv\Scripts\pip.exe install -r requirements.txt

echo [3/3] Creating run_musewave.bat launcher...
(
echo @echo off
echo cd /d "%%~dp0"
echo call venv\Scripts\python.exe main.py
echo pause
) > run_musewave.bat

echo ============================================================
echo   INSTALLATION COMPLETE!
echo   Double-click "run_musewave.bat" to launch Musewave.
echo ============================================================
pause

