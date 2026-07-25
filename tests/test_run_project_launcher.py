from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_check_uses_project_virtual_environment() -> None:
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
    assert ".venv\\Scripts\\python.exe" in output
    assert "runtime check passed" in output.lower()
