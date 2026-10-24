from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_official_streamlit_wheel_is_verified_without_a_local_fork() -> None:
    workflow = (ROOT / ".github/workflows/streamlit-source.yml").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts/verify_streamlit_candidate.py").read_text(encoding="utf-8")
    integration = (ROOT / "scripts/test_streamlit_integration.py").read_text(encoding="utf-8")

    assert "Verified official Streamlit runtime compatibility" in workflow
    assert "https://pypi.org/simple" in workflow
    assert "streamlit==1.66.1" in workflow
    assert "streamlit-1.66.1-py3-none-any.whl" in verifier
    assert "https://pypi.org/pypi/streamlit/1.66.1/json" in verifier
    assert "official-pypi-wheel" in verifier
    assert "pillow_13_compatible" in verifier
    assert "Official wheel does not declare its Apache-2.0 license" in verifier
    assert "refs/pull/21/head" in workflow
    assert "refs/pull/19/head" in workflow
    assert 'PILLOW_VERSION = "13.0.0"' in integration
    assert "pip_audit" in integration
    assert "--strict" in integration
    assert "product_release_approved" in integration
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "npm audit" not in workflow
    assert "patch_streamlit_frontend.py" not in workflow
    assert "make package" not in workflow
    assert "--ignore-vuln" not in workflow
    assert "continue-on-error:" not in workflow


def test_integration_cannot_silently_use_a_different_project_lock() -> None:
    integration = (ROOT / "scripts/test_streamlit_integration.py").read_text(encoding="utf-8")
    assert "lock_version(lines, \"streamlit\")" in integration
    assert "lock_version(lines, \"pillow\")" in integration
    assert "Project lock does not pin the verified official Streamlit release" in integration
    assert "Project lock does not pin the audited Pillow release" in integration
    assert 'run([python, "-m", "pip_audit", "--local", "--strict"' in integration
