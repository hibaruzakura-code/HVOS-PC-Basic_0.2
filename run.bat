@echo off
title HVOS Base Edition (PC)
chcp 65001 >nul 2>&1

python app_main_base_pc.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred. Press any key to exit.
    pause
)