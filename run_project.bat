@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"

if /I "%~1"=="--help" goto usage
if "%~1"=="" goto arguments_ready
if /I "%~1"=="--runtime-check" goto arguments_ready
if /I "%~1"=="--offline-check" goto arguments_ready
if /I "%~1"=="--check" goto arguments_ready
if /I "%~1"=="--validate" goto arguments_ready
echo ERROR: Unsupported argument: %~1
goto usage_error

:arguments_ready

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "from importlib.metadata import version; [version(name) for name in ('lxml', 'numpy', 'pandas', 'plotly', 'pytest', 'requests', 'streamlit')]" >nul 2>nul
    if not errorlevel 1 (
        "%VENV_PY%" -c "from importlib.metadata import version; from pathlib import Path; from packaging.requirements import Requirement; reqs=[Requirement(line) for line in Path('requirements.lock').read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]; raise SystemExit(0 if all(req.specifier.contains(version(req.name), prereleases=True) for req in reqs) else 1)" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD="%VENV_PY%""
            goto runtime_ready
        )
    )
)

set "BOOTSTRAP_CMD="
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
    set "BOOTSTRAP_CMD=py -3.12"
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

echo Installing locked project requirements...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade -r requirements.lock
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

if /I "%~1"=="--validate" (
    "%VENV_PY%" -m pip install --disable-pip-version-check -r requirements-security.txt
    if errorlevel 1 goto dependency_fail
)

%PYTHON_CMD% -m pip check
if errorlevel 1 goto fail

if /I "%~1"=="--offline-check" goto verify_project
if /I "%~1"=="--validate" goto verify_project

%PYTHON_CMD% run_all.py --mode api
if errorlevel 1 goto fail

:verify_project
set "PYTEST_PARENT=%TEMP%\cpbl-analytics-dashboard_pytest_tmp"
if not exist "%PYTEST_PARENT%" mkdir "%PYTEST_PARENT%"
set "PYTEST_TMP=%PYTEST_PARENT%\run_%RANDOM%_%RANDOM%"
%PYTHON_CMD% -W error -m pytest -p no:cacheprovider --basetemp "%PYTEST_TMP%"
if errorlevel 1 goto fail
if exist "%PYTEST_TMP%" rmdir /s /q "%PYTEST_TMP%" >nul 2>nul

set "COMPILE_CACHE=%TEMP%\cpbl-analytics-dashboard_compile_%RANDOM%_%RANDOM%"
set "PYTHONPYCACHEPREFIX=%COMPILE_CACHE%"
%PYTHON_CMD% -m compileall -q app.py src run_all.py tests
set "COMPILE_EXIT=%ERRORLEVEL%"
set "PYTHONPYCACHEPREFIX="
if exist "%COMPILE_CACHE%" rmdir /s /q "%COMPILE_CACHE%" >nul 2>nul
if not "%COMPILE_EXIT%"=="0" goto fail
%PYTHON_CMD% -m src.release_gate
if errorlevel 1 goto fail
%PYTHON_CMD% -m src.verify_public_release reports\metrics\public_release_manifest.json
if errorlevel 1 goto fail

if /I "%~1"=="--check" goto smoke_check
if /I "%~1"=="--offline-check" goto smoke_check
if /I "%~1"=="--validate" goto smoke_check

echo Starting CPBL dashboard at http://127.0.0.1:8501
echo Press Ctrl+C to stop the dashboard. This window must stay open.
%PYTHON_CMD% -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
if errorlevel 1 goto fail
echo done
exit /b 0

:smoke_check
    %PYTHON_CMD% -B src\smoke_test.py
    if errorlevel 1 goto fail
    if /I "%~1"=="--validate" (
        %PYTHON_CMD% -m bandit -q -r app.py src run_all.py -ll
        if errorlevel 1 goto fail
        %PYTHON_CMD% -m pip_audit --local --strict --progress-spinner off
        if errorlevel 1 goto fail
    )
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

:usage
echo Usage: run_project.bat [--runtime-check ^| --offline-check ^| --check ^| --validate ^| --help]
echo   no argument       Refresh official data, verify it, and start Streamlit.
echo   --runtime-check   Verify the project Python runtime only.
echo   --offline-check   Verify checked-out artifacts without network refresh.
echo   --check           Refresh official data and run full acceptance checks.
echo   --validate        Run offline zero-warning, compile, release, smoke, and security checks.
exit /b 0

:usage_error
echo Use run_project.bat --help for supported options.
exit /b 2
