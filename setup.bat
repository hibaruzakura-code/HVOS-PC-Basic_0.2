@echo off
chcp 65001 >nul 2>&1
title HVOS Environment Setup

echo ===================================================
echo   HVOS Python ライブラリの自動セットアップ
echo ===================================================
echo.

python -m pip install --upgrade pip
pip install flask pyautogui keyboard pygetwindow pillow google-genai qrcode

echo.
echo ===================================================
echo   セットアップが完了しました！
echo   この画面は閉じて構いません。
echo ===================================================
pause