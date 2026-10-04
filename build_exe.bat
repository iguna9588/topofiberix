@echo off
title TopoFiberix - Network Designer - Executable Builder
echo ================================================================
echo       TOPOFIBERIX - NETWORK DESIGNER (.EXE) BUILDER
echo ================================================================
echo Menyiapkan lingkungan Python...
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXEC=.venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

echo Menggunakan Python: %PYTHON_EXEC%
%PYTHON_EXEC% build_exe.py

echo.
pause
