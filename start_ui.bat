@echo off
chcp 65001 > nul
title VD 交通量與服務水準分析系統 Web UI

echo ====================================================
echo   VD 交通量與服務水準 (LOS) 自動化分析系統
echo   即將為您啟動 Web UI 繪圖與管理介面...
echo ====================================================
echo.

start http://localhost:8000
python src_database/web_server.py 8000

pause
