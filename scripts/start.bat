@echo off
REM LLM Chat System - Windows Startup Script

echo.
echo ========================================
echo   LLM Chat System - Windows Launcher
echo ========================================
echo.

REM Change to project directory
cd /d "%~dp0\.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if requirements are installed
python -c "import openai" >nul 2>&1
if errorlevel 1 (
    echo Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install requirements
        pause
        exit /b 1
    )
)

REM Initialize system if needed
if not exist "config\default_config.json" (
    echo Initializing system...
    python scripts\init.py
    if errorlevel 1 (
        echo Error: System initialization failed
        pause
        exit /b 1
    )
)

REM Start the system
echo Starting LLM Chat System...
python scripts\start.py %*

pause
