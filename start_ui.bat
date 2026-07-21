@echo off
@chcp 65001 > nul
title VD Traffic Report Automation System

echo ====================================================
echo   VD Traffic Report Automation Web UI
echo ====================================================
echo.

:: 1. 檢查是否有安裝 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [訊息] 檢測到系統尚未安裝 Python 環境！
    echo [動作] 啟動 Windows 套件管理器 (winget) 自動下載並安裝 Python 3.11 中...
    echo.
    winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements
    
    :: 更新當前 Session PATH
    set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
    
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo ----------------------------------------------------
        echo 【注意】自動安裝 Python 完成後，請重新關閉此視窗並再次點擊 start_ui.bat。
        echo 若未安裝成功，請造訪 https://www.python.org/downloads/ 下載安裝，
        echo 且安裝時務必勾選「Add python.exe to PATH」。
        echo ----------------------------------------------------
        echo.
        pause
        exit /b 1
    )
    echo [成功] Python 3.11 自動安裝完成！
    echo.
)

:: 2. 檢查並自動安裝必要 Python 套件
echo [1/3] 檢查 Python 依賴套件 (requests, urllib3, openpyxl)...
python -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% neq 0 (
    echo [訊息] 檢測到缺少必要套件，正在自動安裝中 (pip install -r requirements.txt)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo 【錯誤】套件自動安裝失敗，請檢查網路連線或手動執行: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo [成功] 所有必要套件自動安裝完成！
) else (
    echo [成功] 必要套件已完全就緒！
)

echo.
echo [2/3] 正在啟動 Web 服務伺服器 (http://localhost:8000)...
echo [3/3] 正在自動開啟瀏覽器頁面...
echo.

:: 延遲 2 秒確保伺服器服務監聽埠號完成後再打開瀏覽器
start /b "" cmd /c "timeout /t 2 >nul && start http://localhost:8000"

:: 啟動 Web 伺服器並保持控制台運行
python src_database/web_server.py 8000

pause
