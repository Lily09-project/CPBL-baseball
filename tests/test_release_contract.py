from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_locked_environment_and_quality_gate_are_declared() -> None:
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8-sig")
    workflow = (ROOT / ".github/workflows/release-quality.yml").read_text(encoding="utf-8-sig")

    assert "streamlit==1.60.0" in lock
    assert "pandas==3.0.5" in lock
    assert "requirements.lock" in workflow
    assert "python -m pip check" in workflow
    assert "python -m src.release_gate" in workflow
    assert "permissions:\n  contents: read" in workflow


def test_data_refresh_only_opens_a_reviewable_pr_for_verified_outputs() -> None:
    workflow = (ROOT / ".github/workflows/data-refresh.yml").read_text(encoding="utf-8-sig")

    for required in [
        "workflow_dispatch",
        "python run_all.py --mode api",
        "python -m pytest -q",
        "python -m src.release_gate",
        "permissions:\n  contents: write\n  pull-requests: write",
        "git add data/processed reports/metrics",
        "gh pr create",
    ]:
        assert required in workflow
    assert "git push origin main" not in workflow
    assert "data/raw" not in workflow
    assert "run_all.py --mode sample" not in workflow
