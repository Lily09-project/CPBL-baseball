@echo off
setlocal
cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "from importlib.metadata import version; [version(name) for name in ('lxml', 'numpy', 'pandas', 'plotly', 'pytest', 'requests', 'streamlit')]" >nul 2>nul
    if not errorlevel 1 (
        "%VENV_PY%" -c "from importlib.metadata import version; from pathlib import Path; from packaging.requirements import Requirement; reqs=[Requirement(line) for line in Path('requirements.txt').read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]; raise SystemExit(0 if all(req.specifier.contains(version(req.name), prereleases=True) for req in reqs) else 1)" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD="%VENV_PY%""
            goto runtime_ready
        )
    )
)

set "BOOTSTRAP_CMD="
if exist "%BUNDLED_PY%" (
    set "BOOTSTRAP_CMD="%BUNDLED_PY%""
) else (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        set "BOOTSTRAP_CMD=py -3"
    ) else (
        python --version >nul 2>nul
        if not errorlevel 1 (
            set "BOOTSTRAP_CMD=python"
        ) else (
            echo ERROR: Python was not found.
            echo Install Python 3.12, then run this file again.
            goto fail
        )
    )
)

:prepare_runtime
if not exist "%VENV_PY%" (
    echo Creating project environment: %VENV_DIR%
    %BOOTSTRAP_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto runtime_fail
)

echo Updating secure packaging tools...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade "pip>=26.1.2"
if errorlevel 1 goto dependency_fail

echo Installing project requirements...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade -r requirements.txt
if errorlevel 1 goto dependency_fail

"%VENV_PY%" -c "import lxml, numpy, pandas, plotly, pytest, requests, streamlit" >nul 2>nul
if errorlevel 1 goto dependency_fail
set "PYTHON_CMD="%VENV_PY%""

:runtime_ready
echo Using Python: %PYTHON_CMD%
if /I "%~1"=="--runtime-check" (
    %PYTHON_CMD% -c "import streamlit; print('runtime check passed')"
    if errorlevel 1 goto fail
    exit /b 0
)

%PYTHON_CMD% run_all.py --mode api
if errorlevel 1 goto fail

set "PYTEST_PARENT=%TEMP%\cpbl-analytics-dashboard_pytest_tmp"
if not exist "%PYTEST_PARENT%" mkdir "%PYTEST_PARENT%"
set "PYTEST_TMP=%PYTEST_PARENT%\run_%RANDOM%_%RANDOM%"
%PYTHON_CMD% -m pytest -p no:cacheprovider --basetemp "%PYTEST_TMP%"
if errorlevel 1 goto fail
if exist "%PYTEST_TMP%" rmdir /s /q "%PYTEST_TMP%" >nul 2>nul

if /I "%~1"=="--check" (
    %PYTHON_CMD% -B src\smoke_test.py
    if errorlevel 1 goto fail
    echo done
    exit /b 0
)

echo Starting CPBL dashboard at http://127.0.0.1:8501
echo Press Ctrl+C to stop the dashboard. This window must stay open.
%PYTHON_CMD% -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
if errorlevel 1 goto fail
echo done
exit /b 0

:runtime_fail
echo.
echo ERROR: Could not create the project Python environment.
goto fail

:dependency_fail
echo.
echo ERROR: Could not install or import the required Python packages.
echo Check the internet connection, then run this file again.
goto fail

:fail
echo.
echo ERROR: run_project.bat failed.
if "%~1"=="" pause
exit /b 1
