@echo off
title VD Traffic Report Automation System
set PYTHONUNBUFFERED=1

echo ====================================================
echo   VD Traffic Report Automation Web UI
echo ====================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 goto NO_PYTHON

if exist .venv\Scripts\python.exe goto CHECK_VENV_PKGS

echo [Notice] Creating local virtual environment (.venv)...
python -m venv .venv >nul 2>nul
if %errorlevel% neq 0 goto USE_SYSTEM_PYTHON

:INSTALL_TO_VENV
echo [Notice] Installing packages into .venv...
.venv\Scripts\python.exe -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org >nul 2>nul
goto RUN_WITH_VENV

:CHECK_VENV_PKGS
.venv\Scripts\python.exe -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% neq 0 goto INSTALL_TO_VENV

:RUN_WITH_VENV
echo.
echo ====================================================
echo   VD Traffic Report Web UI Server Started!
echo   Server is running at http://localhost:8000
echo   Please keep this console window open.
echo ====================================================
echo.
start http://localhost:8000
.venv\Scripts\python.exe -u src_database/web_server.py 8000
pause
exit /b 0

:USE_SYSTEM_PYTHON
echo [Notice] venv unavailable, using system Python directly...
python -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% equ 0 goto RUN_WITH_SYSTEM_PYTHON
echo [Notice] Installing packages to system Python...
python -m pip install -r requirements.txt --user --trusted-host pypi.org --trusted-host files.pythonhosted.org
python -c "import requests, urllib3, openpyxl" >nul 2>nul
if %errorlevel% neq 0 goto FAIL_PACKAGES

:RUN_WITH_SYSTEM_PYTHON
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
exit /b 0

:NO_PYTHON
echo [Notice] Python environment is not detected on this computer.
echo [Action] Launching Windows Package Manager (winget) to install Python 3.11...
echo.
winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements
set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
where python >nul 2>nul
if %errorlevel% neq 0 goto FAIL_PYTHON
goto USE_SYSTEM_PYTHON

:FAIL_PYTHON
echo.
echo [Notice] Please restart start_ui.bat after Python installation completes.
pause
exit /b 1

:FAIL_PACKAGES
echo.
echo [Error] Failed to install packages. Please open CMD and run:
echo   pip install requests urllib3 openpyxl
pause
exit /b 1
