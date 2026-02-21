@echo off
echo ========================================
echo AI Hand Builder - Python Version
echo Quick Start Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Check if dependencies are installed
python -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    echo This may take a few minutes...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo.
)

REM Run the application
echo ========================================
echo Starting AI Hand Builder...
echo ========================================
echo.
python main.py

REM Deactivate virtual environment
deactivate

echo.
echo ========================================
echo Application closed
echo ========================================
pause
