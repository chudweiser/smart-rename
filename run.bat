@echo off
cd /d "%~dp0"
start /b "" ollama serve >nul 2>nul
timeout /t 2 /nobreak >nul
venv\Scripts\python watcher.py
