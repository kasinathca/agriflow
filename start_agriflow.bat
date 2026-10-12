@echo off
setlocal EnableExtensions EnableDelayedExpansion

title AgriFlow - Setup and Run
cd /d "%~dp0"

echo ============================================================
echo   AgriFlow - One-Click Setup and Run
echo ============================================================
echo Project: %CD%
echo.

rem 1. Reuse the project-local virtual environment if available.
rem    Otherwise create one with Python 3.12, 3.11, or 3.10.
if exist ".venv\Scripts\python.exe" (
    echo [OK] Existing .venv found.
) else (
    echo [INFO] No .venv found. Creating an isolated environment...
    set "BASEPY="

    py -3.12 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    if not errorlevel 1 set "BASEPY=py -3.12"

    if not defined BASEPY (
        py -3.11 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
        if not errorlevel 1 set "BASEPY=py -3.11"
    )

    if not defined BASEPY (
        py -3.10 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
        if not errorlevel 1 set "BASEPY=py -3.10"
    )

    if not defined BASEPY (
        python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
        if not errorlevel 1 set "BASEPY=python"
    )

    if not defined BASEPY (
        echo [ERROR] Python 3.10 or newer was not found.
        echo Install Python 3.10+ and run this file again.
        pause
        exit /b 1
    )

    echo [INFO] Creating .venv using !BASEPY! ...
    !BASEPY! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        pause
        exit /b 1
    )
)

set "PY=%CD%\.venv\Scripts\python.exe"

echo.
echo [INFO] AgriFlow Python:
"%PY%" --version
if errorlevel 1 (
    echo [ERROR] The project virtual environment is not usable.
    pause
    exit /b 1
)

rem 2. Install/update dependencies only when needed.
rem    A SHA-256 marker tracks changes to pyproject.toml.
set "NEED_INSTALL=0"

"%PY%" -c "import agriflow, dash, plotly, pandas, numpy, scipy, networkx, statsmodels, sklearn, requests, dotenv" >nul 2>nul
if errorlevel 1 set "NEED_INSTALL=1"

"%PY%" -c "from pathlib import Path; import hashlib; p=Path('pyproject.toml'); print(hashlib.sha256(p.read_bytes()).hexdigest())" > ".venv\pyproject.current.sha256"
if errorlevel 1 (
    echo [ERROR] Could not calculate pyproject.toml checksum.
    pause
    exit /b 1
)

if not exist ".venv\pyproject.installed.sha256" (
    set "NEED_INSTALL=1"
) else (
    fc /b ".venv\pyproject.current.sha256" ".venv\pyproject.installed.sha256" >nul 2>nul
    if errorlevel 1 set "NEED_INSTALL=1"
)

if "!NEED_INSTALL!"=="1" (
    echo.
    echo [INFO] Installing/updating AgriFlow dependencies inside .venv...
    "%PY%" -m pip install --upgrade pip setuptools wheel
    if errorlevel 1 goto :setup_error

    "%PY%" -m pip install -e ".[dev]"
    if errorlevel 1 goto :setup_error

    copy /y ".venv\pyproject.current.sha256" ".venv\pyproject.installed.sha256" >nul
    echo [OK] Dependencies installed.
) else (
    echo [OK] Dependencies already satisfied.
)

del /q ".venv\pyproject.current.sha256" >nul 2>nul

rem 3. Create local environment configuration if absent.
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] Created .env from .env.example.
        echo      Add CEDA/API credentials there later if required.
    ) else (
        echo [WARN] .env.example was not found; continuing without .env.
    )
) else (
    echo [OK] Existing .env preserved.
)

rem 4. Ensure deterministic DEMO fixture exists.
rem    This does NOT overwrite REAL processed market data.
if not exist "data\demo\demo_market_daily.csv" goto :init_demo
if not exist "data\demo\demo_weather_daily.csv" goto :init_demo
if not exist "data\demo\demo_markets.csv" goto :init_demo
goto :demo_ready

:init_demo
echo.
echo [INFO] Generating deterministic DEMO fixture...
"%PY%" -m agriflow init --no-geojson
if errorlevel 1 goto :setup_error

:demo_ready
echo [OK] DEMO fixture available.

rem 5. Ensure India state GeoJSON exists for the choropleth.
rem    Network failure here is non-fatal; dashboard can still start.
if exist "data\cache\india_states.geojson" (
    echo [OK] India state GeoJSON already cached.
) else (
    echo.
    echo [INFO] India state GeoJSON is missing. Attempting download...
    "%PY%" -m agriflow fetch-geojson
    if errorlevel 1 (
        echo [WARN] GeoJSON download failed. Dashboard will still launch.
    ) else (
        echo [OK] India state GeoJSON cached.
    )
)

rem 6. Print a lightweight local readiness report.
echo.
echo [INFO] AgriFlow environment/data status:
"%PY%" -m agriflow doctor
if errorlevel 1 goto :setup_error

rem 7. Launch the browser shortly after the server starts.
echo.
echo ============================================================
echo   Starting AgriFlow
echo   URL: http://127.0.0.1:8050
echo   Press CTRL+C in this window to stop the server.
echo ============================================================
echo.

start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8050'"

"%PY%" -m agriflow run
set "APP_EXIT=%ERRORLEVEL%"

echo.
if not "%APP_EXIT%"=="0" (
    echo [ERROR] AgriFlow exited with code %APP_EXIT%.
) else (
    echo AgriFlow stopped.
)

pause
exit /b %APP_EXIT%

:setup_error
echo.
echo [ERROR] AgriFlow setup failed. Review the error shown above.
pause
exit /b 1
