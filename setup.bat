@echo off
echo.
echo ==================================================
echo   Smart Rename — Setup
echo ==================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   [error] Python is not installed or not in PATH.
    echo.
    echo   Download it from https://python.org
    echo   Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo   [ok] Python found
for /f "tokens=2" %%i in ('python --version') do set PYVER=%%i
echo         Version: %PYVER%

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [error] Ollama is not installed.
    echo.
    echo   Download it from https://ollama.com
    echo   Run the installer, then re-run this script.
    echo.
    pause
    exit /b 1
)
echo   [ok] Ollama found

:: Check llava
ollama list 2>nul | findstr /i "llava" >nul
if errorlevel 1 (
    echo.
    echo   llava model not found. Pulling now (~4GB, may take a few minutes)...
    ollama pull llava
)
echo   [ok] llava model ready

:: Create venv
echo.
echo   Creating virtual environment...
python -m venv venv
echo   [ok] Virtual environment created

:: Install dependencies
echo.
echo   Installing dependencies...
venv\Scripts\pip install --quiet -r requirements.txt
echo   [ok] Dependencies installed

:: Create run script
echo @echo off > run.bat
echo cd /d "%%~dp0" >> run.bat
echo ollama serve ^>nul 2^>^&1 ^& timeout /t 2 /nobreak ^>nul >> run.bat
echo venv\Scripts\python watcher.py >> run.bat

echo.
echo ==================================================
echo   Setup complete!
echo.
echo   To start Smart Rename, double-click run.bat
echo   or run it from the terminal.
echo ==================================================
echo.
pause
