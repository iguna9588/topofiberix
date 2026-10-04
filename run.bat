@echo off
title FTTH Network Planner
echo Menjalankan FTTH Network Planner...
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
if %errorlevel% neq 0 (
    pause
)
