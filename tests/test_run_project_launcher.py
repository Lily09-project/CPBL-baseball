from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_launcher_enforces_utf8_console_output() -> None:
    launcher = (ROOT / "run_project.bat").read_text(encoding="utf-8")

    assert "chcp 65001 >nul" in launcher
    assert 'set "PYTHONUTF8=1"' in launcher
    assert 'set "PYTHONIOENCODING=utf-8"' in launcher
    assert "%userprofile%\\.cache\\" not in launcher.lower()


def test_offline_check_skips_refresh_and_runs_existing_release_verification() -> None:
    launcher = (ROOT / "run_project.bat").read_text(encoding="utf-8")

    offline_branch = 'if /I "%~1"=="--offline-check" goto verify_project'
    assert offline_branch in launcher
    assert launcher.index(offline_branch) < launcher.index("run_all.py --mode api")
    assert "%PYTHON_CMD% -m src.verify_public_release reports\\metrics\\public_release_manifest.json" in launcher
    assert 'if /I "%~1"=="--offline-check" goto smoke_check' in launcher


def test_launcher_documents_options_and_rejects_unknown_arguments() -> None:
    launcher = (ROOT / "run_project.bat").read_text(encoding="utf-8")

    assert 'if /I "%~1"=="--help" goto usage' in launcher
    assert "ERROR: Unsupported argument: %~1" in launcher
    assert "exit /b 2" in launcher


def test_validate_mode_runs_zero_warning_release_smoke_and_security_gates() -> None:
    launcher = (ROOT / "run_project.bat").read_text(encoding="utf-8")

    for token in (
        'if /I "%~1"=="--validate" goto arguments_ready',
        '%PYTHON_CMD% -W error -m pytest',
        '%PYTHON_CMD% -m compileall -q app.py src run_all.py tests',
        'set "PYTHONPYCACHEPREFIX=%COMPILE_CACHE%"',
        '%PYTHON_CMD% -m src.release_gate',
        '%PYTHON_CMD% -m src.verify_public_release reports\\metrics\\public_release_manifest.json',
        '%PYTHON_CMD% -B src\\smoke_test.py',
        '%PYTHON_CMD% -m bandit -q -r app.py src run_all.py -ll',
        '%PYTHON_CMD% -m pip_audit --local --strict --progress-spinner off',
    ):
        assert token in launcher
    assert "Usage: run_project.bat" in launcher


@pytest.mark.integration
def test_runtime_check_uses_project_virtual_environment() -> None:
    if os.name != "nt":
        pytest.skip("run_project.bat is a Windows launcher")

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(ROOT / "run_project.bat"), "--runtime-check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, output
    assert str(ROOT) in output
    assert "\ufffd" not in output
    assert ".venv\\Scripts\\python.exe" in output
    assert "runtime check passed" in output.lower()
