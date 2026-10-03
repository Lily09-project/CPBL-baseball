"""The platform-specific launcher integration must execute on Windows."""
from pathlib import Path


def test_windows_ci_does_not_skip_the_launcher_boundary():
    source = Path(".github/workflows/windows-launcher.yml").read_text(encoding="utf-8")
    assert "runs-on: windows-latest" in source
    assert "call run_project.bat --validate" in source
    assert "continue-on-error" not in source
    assert "persist-credentials: false" in source
