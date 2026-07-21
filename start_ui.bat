@echo off
title VD Traffic Report Automation System
set PYTHONUNBUFFERED=1

echo ====================================================
echo   VD Traffic Report Automation Web UI
echo ====================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 goto :NO_PYTHON

python -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% neq 0 goto :INSTALL_PACKAGES

goto :START_SERVER

:NO_PYTHON
echo [訊息] 檢測到尚未安裝 Python，啟動自動安裝程序...
winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements
set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo 請於 Python 安裝完成後，重新開啟 start_ui.bat。
    pause
    exit /b 1
)

:INSTALL_PACKAGES
echo [訊息] 正在自動安裝套件 (requests, urllib3, openpyxl)...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [錯誤] 套件安裝失敗，請檢查網路連線。
    pause
    exit /b 1
)

:START_SERVER
echo.
echo ====================================================
echo   VD Traffic Report Web UI Server Started!
echo   伺服器已成功啟動並運行中！(請保持此控制台視窗開啟)
echo   請使用瀏覽器開啟: http://localhost:8000
echo ====================================================
echo.

start http://localhost:8000
python -u src_database/web_server.py 8000

pause
