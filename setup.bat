@echo off
if not "%1"=="RUNNING" (
    cmd /k "%~f0" RUNNING
    exit /b
)

echo.
echo ==================================================
echo   Smart Rename -- Setup
echo ==================================================
echo.

:: Use py.exe - lives in C:\Windows, immune to PATH truncation
py --version >nul 2>&1
if errorlevel 1 (
    echo   [error] Python not found. Download from https://python.org
    goto :end
)
for /f "tokens=2" %%i in ('py --version') do set PYVER=%%i
echo   [ok] Python found (version %PYVER%)

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo   [error] Ollama not found. Download from https://ollama.com
    goto :end
)
echo   [ok] Ollama found

:: Pull llava - safe to run even if already present, just confirms it's ready
echo   Ensuring llava model is ready...
ollama pull llava
if errorlevel 1 (
    echo   [error] Failed to pull llava model.
    goto :end
)
echo   [ok] llava model ready

:: Create venv
echo.
echo   Creating virtual environment...
py -m venv venv
if errorlevel 1 (
    echo   [error] Failed to create virtual environment.
    echo   Make sure this folder is not inside OneDrive.
    goto :end
)
echo   [ok] Virtual environment created

:: Install dependencies
echo.
echo   Installing dependencies...
venv\Scripts\pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo   [error] Failed to install dependencies.
    goto :end
)
echo   [ok] Dependencies installed

:: Write run.bat
echo @echo off> run.bat
echo cd /d "%%~dp0">> run.bat
echo start /b "" ollama serve ^>nul 2^>nul>> run.bat
echo timeout /t 2 /nobreak ^>nul>> run.bat
echo venv\Scripts\python watcher.py>> run.bat
echo   [ok] run.bat created

echo.
echo ==================================================
echo   Setup complete!
echo.
echo   To start Smart Rename, double-click run.bat
echo ==================================================

:end
echo.
echo   Press any key to close...
pause >nul
