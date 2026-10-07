@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" || exit /b 1
if not exist .venv %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel || exit /b 1
python -m pip install -r requirements.txt || exit /b 1
python -m pip install -e . --no-deps || exit /b 1
if not exist .env copy .env.example .env >nul
python -m agriflow init
python -m agriflow analyze || exit /b 1
python -m pytest -q || exit /b 1
echo.
echo AgriFlow setup complete. Run run.bat
endlocal
