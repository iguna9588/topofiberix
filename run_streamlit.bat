@echo off
title TopoFiberix - Streamlit Web Edition
echo ================================================================
echo       TOPOFIBERIX - STREAMLIT WEB APP LAUNCHER
echo ================================================================
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
pause
