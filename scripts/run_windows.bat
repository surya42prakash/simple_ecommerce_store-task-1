@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment not found. Run scripts\setup_windows.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Starting server at http://127.0.0.1:8000/  (press Ctrl+C to stop)
python manage.py runserver
pause
