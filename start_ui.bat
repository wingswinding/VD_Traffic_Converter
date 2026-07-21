@echo off
title VD Traffic Report Automation System
set PYTHONUNBUFFERED=1

echo ====================================================
echo   VD Traffic Report Automation Web UI
echo ====================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 goto NO_PYTHON

python -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% equ 0 goto START_SERVER

goto INSTALL_PACKAGES

:NO_PYTHON
echo [Notice] Python environment is not detected on this computer.
echo [Action] Launching Windows Package Manager (winget) to install Python 3.11...
echo.
winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements
set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
where python >nul 2>nul
if %errorlevel% neq 0 goto FAIL_PYTHON
goto INSTALL_PACKAGES

:FAIL_PYTHON
echo.
echo [Notice] Please restart start_ui.bat after Python installation completes.
pause
exit /b 1

:INSTALL_PACKAGES
echo [Notice] Installing required packages (requests, urllib3, openpyxl)...
python -m pip install --user requests urllib3 openpyxl --trusted-host pypi.org --trusted-host files.pythonhosted.org
python -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% equ 0 goto START_SERVER
goto FAIL_PACKAGES

:FAIL_PACKAGES
echo [Error] Failed to install packages. Please check internet connection.
pause
exit /b 1

:START_SERVER
echo.
echo ====================================================
echo   VD Traffic Report Web UI Server Started!
echo   Server is running at http://localhost:8000
echo   Please keep this console window open.
echo ====================================================
echo.

start http://localhost:8000
python -u src_database/web_server.py 8000

pause
