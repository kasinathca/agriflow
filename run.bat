@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  echo Run setup.bat first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m agriflow run
endlocal
