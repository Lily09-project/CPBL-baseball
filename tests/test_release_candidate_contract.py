from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_check_runs_the_full_release_gate() -> None:
    launcher = (ROOT / "run_project.bat").read_text(encoding="ascii")

    for command in [
        "%PYTHON_CMD% -m pip check",
        "%PYTHON_CMD% -m compileall -q app.py src run_all.py tests",
        "%PYTHON_CMD% -m src.release_gate",
        "%PYTHON_CMD% -m src.verify_public_release reports\\metrics\\public_release_manifest.json",
        "%PYTHON_CMD% -B src\\smoke_test.py",
    ]:
        assert command in launcher


def test_release_documents_and_pr_template_are_present() -> None:
    checklist = (ROOT / "docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8-sig")
    template = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8-sig")

    for term in [
        "User Acceptance",
        "Reviewer Acceptance",
        "requirements.lock",
        "data-refresh.yml",
        "Stop Conditions",
    ]:
        assert term in checklist
    for term in [
        "python -m pytest -q",
        "python -m src.release_gate",
        "No raw HTML",
        "Public deployment was not bundled",
    ]:
        assert term in template
