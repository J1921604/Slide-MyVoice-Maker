@echo off
REM Start local HTTP server for preview
REM Access: http://localhost:8000

cd /d "%~dp0"

echo ===============================================
echo  Slide Voice Maker - Local Preview Server
echo ===============================================
echo.
echo Starting HTTP server...
echo.
echo Access URL: http://localhost:8000
echo Press Ctrl+C to stop the server.
echo.

py -3.10 -m http.server 8000 --bind 127.0.0.1
