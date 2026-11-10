@echo off
REM Safe first-time setup. Never deletes files or databases.
setlocal
cd /d "%~dp0.."
echo === Simple Store setup (folder: %CD%) ===

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.10-3.13 from python.org and tick "Add python.exe to PATH".
  goto :fail
)
python --version

if exist ".venv\Scripts\python.exe" (
  echo Virtual environment already exists - reusing it.
) else (
  echo Creating virtual environment .venv ...
  python -m venv .venv || goto :fail
)

call ".venv\Scripts\activate.bat" || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt || goto :fail
python manage.py migrate || goto :fail

echo.
echo Setup finished. Next steps:
echo   1. scripts\create_admin.bat     (create your admin account)
echo   2. python manage.py seed_demo_data   (load demo products)
echo   3. scripts\run_windows.bat      (start the website)
echo.
choice /m "Load demo products now"
if errorlevel 2 goto :done
python manage.py seed_demo_data
:done
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup stopped because a step failed. Read the message above.
pause
exit /b 1
