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
if /I "%~1"=="--refresh-check" goto arguments_ready
if /I "%~1"=="--validate" goto arguments_ready
echo ERROR: Unsupported argument: %~1
goto usage_error

:arguments_ready

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "from importlib.metadata import version; [version(name) for name in ('lxml', 'numpy', 'pandas', 'pytest', 'requests')]" >nul 2>nul
    if not errorlevel 1 (
        "%VENV_PY%" -c "from importlib.metadata import version; from pathlib import Path; from packaging.requirements import Requirement; reqs=[Requirement(line) for line in Path('requirements.lock.txt').read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]; raise SystemExit(0 if all(req.specifier.contains(version(req.name), prereleases=True) for req in reqs) else 1)" >nul 2>nul
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
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "BOOTSTRAP_CMD=python"
    ) else (
        echo ERROR: Python 3.12 was not found.
        echo Install Python 3.12, then run this file again.
        goto fail
    )
)

if not exist "%VENV_PY%" (
    echo Creating project environment: %VENV_DIR%
    %BOOTSTRAP_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto runtime_fail
)

echo Updating secure packaging tools...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade "pip>=26.1.2"
if errorlevel 1 goto dependency_fail

echo Installing locked project requirements...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade -r requirements.lock.txt
if errorlevel 1 goto dependency_fail

"%VENV_PY%" -c "import lxml, numpy, pandas, pytest, requests" >nul 2>nul
if errorlevel 1 goto dependency_fail
set "PYTHON_CMD="%VENV_PY%""

:runtime_ready
echo Using Python: %PYTHON_CMD%
if /I "%~1"=="--runtime-check" (
    %PYTHON_CMD% -c "import pandas, numpy; print('runtime check passed')"
    if errorlevel 1 goto fail
    exit /b 0
)

if /I "%~1"=="--validate" (
    "%VENV_PY%" -m pip install --disable-pip-version-check -r requirements-security.txt
    if errorlevel 1 goto dependency_fail
)

%PYTHON_CMD% -m pip check
if errorlevel 1 goto fail

if /I "%~1"=="--refresh-check" goto refresh_project
goto verify_project

:refresh_project
echo Refreshing official CPBL data before verification...
%PYTHON_CMD% run_all.py --mode api
if errorlevel 1 goto fail

:verify_project
set "PYTEST_PARENT=%TEMP%\cpbl-scouting-lab_pytest_tmp"
if not exist "%PYTEST_PARENT%" mkdir "%PYTEST_PARENT%"
set "PYTEST_TMP=%PYTEST_PARENT%\run_%RANDOM%_%RANDOM%"
%PYTHON_CMD% -W error -m pytest -p no:cacheprovider --basetemp "%PYTEST_TMP%"
if errorlevel 1 goto fail
if exist "%PYTEST_TMP%" rmdir /s /q "%PYTEST_TMP%" >nul 2>nul

set "COMPILE_CACHE=%TEMP%\cpbl-scouting-lab_compile_%RANDOM%_%RANDOM%"
set "PYTHONPYCACHEPREFIX=%COMPILE_CACHE%"
%PYTHON_CMD% -m compileall -q src run_all.py tests
set "COMPILE_EXIT=%ERRORLEVEL%"
set "PYTHONPYCACHEPREFIX="
if exist "%COMPILE_CACHE%" rmdir /s /q "%COMPILE_CACHE%" >nul 2>nul
if not "%COMPILE_EXIT%"=="0" goto fail
%PYTHON_CMD% -m src.release_gate
if errorlevel 1 goto fail
%PYTHON_CMD% -m src.verify_public_release reports\metrics\public_release_manifest.json
if errorlevel 1 goto fail

echo Exporting verified data for the web app...
%PYTHON_CMD% -m src.export_web
if errorlevel 1 goto fail

if /I "%~1"=="--validate" (
    %PYTHON_CMD% -m bandit -q -r src run_all.py -ll
    if errorlevel 1 goto fail
    %PYTHON_CMD% -m pip_audit --local --strict --progress-spinner off
    if errorlevel 1 goto fail
)

if /I "%~1"=="--check" goto done
if /I "%~1"=="--offline-check" goto done
if /I "%~1"=="--refresh-check" goto done

where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js 22 or newer was not found.
    echo Install Node.js from https://nodejs.org/, then run this file again.
    goto fail
)

pushd web
echo Installing locked web dependencies...
call npm ci --no-audit --no-fund
if errorlevel 1 goto web_fail
if /I "%~1"=="--validate" (
    call npm run typecheck
    if errorlevel 1 goto web_fail
    call npm run lint
    if errorlevel 1 goto web_fail
    call npm run coverage
    if errorlevel 1 goto web_fail
)
call npm run build
if errorlevel 1 goto web_fail
if /I "%~1"=="--validate" (
    call npm run size
    if errorlevel 1 goto web_fail
    popd
    goto done
)

echo Starting CPBL Scouting Lab at http://127.0.0.1:4173
echo Press Ctrl+C to stop the site. This window must stay open.
call npm run preview -- --host 127.0.0.1
popd
exit /b 0

:done
echo done
exit /b 0

:web_fail
popd
echo.
echo ERROR: The web app could not be installed, checked or built.
goto fail

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
echo Usage: run_project.bat [--runtime-check ^| --check ^| --refresh-check ^| --offline-check ^| --validate ^| --help]
echo   no argument       Verify the checked-out data, build the web app and open it locally (no network refresh).
echo   --check           Verify checked-out artifacts without refreshing or writing release data.
echo   --refresh-check   Refresh official data, then run the full acceptance checks.
echo   --runtime-check   Verify the project Python runtime only.
echo   --offline-check   Verify checked-out artifacts without network refresh.
echo   --validate        Run every offline Python and web quality gate without starting the site.
exit /b 0

:usage_error
echo Use run_project.bat --help for supported options.
exit /b 2
