@echo off
@chcp 65001 > nul
title VD Traffic Report Web UI

echo ====================================================
echo   VD Traffic Report Automation Web UI
echo   Starting server & opening browser at http://localhost:8000 ...
echo ====================================================
echo.

start http://localhost:8000
python src_database/web_server.py 8000

pause
