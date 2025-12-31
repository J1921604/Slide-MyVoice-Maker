@echo off
chcp 65001 > nul
title Slide Voice Maker Server
cd /d "%~dp0"

REM 仮想環境の確認と作成
if exist ".venv\Scripts\activate.bat" (
    echo 既存の仮想環境を使用します...
    call .venv\Scripts\activate.bat
) else (
    echo 仮想環境を作成しています...
    py -3.10 -m venv .venv
    call .venv\Scripts\activate.bat
    echo 依存関係をインストールしています...
    pip install -r requirements.txt
)

REM サーバー起動
echo.
echo ========================================
echo   Slide Voice Maker Server
echo   http://127.0.0.1:8000
echo ========================================
echo.
echo サーバーを起動しています...
echo ブラウザで http://127.0.0.1:8000 を開いてください。
echo 終了するには Ctrl+C を押してください。
echo.

py -3.10 -m uvicorn src.server:app --host 127.0.0.1 --port 8000

pause
