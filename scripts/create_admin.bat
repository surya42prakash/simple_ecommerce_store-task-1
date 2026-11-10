@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment not found. Run scripts\setup_windows.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python manage.py createsuperuser
pause
