from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_source_candidate_is_immutable_complete_and_not_published() -> None:
    workflow = (ROOT / ".github/workflows/streamlit-source.yml").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts/verify_streamlit_candidate.py").read_text(encoding="utf-8")
    assert "repository: streamlit/streamlit" in workflow
    assert "ref: 81bdb8a8a207691f17ec94df9eabc96b6b50ea7a" in workflow
    assert "id: upstream" in workflow
    assert "steps.upstream.outputs.commit" in workflow
    assert "--expected-commit" in workflow
    assert "persist-credentials: false" in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "make package" in workflow
    assert "uv lock --check" in workflow
    assert "Pillow==13.0.0" in workflow
    assert "pip_audit --local --strict" in workflow
    assert "--ignore-vuln" not in workflow
    assert "continue-on-error:" not in workflow
    assert "streamlit/static/index.html" in verifier
    assert "streamlit/static/assets/" in verifier
    assert "_pb2.py" in verifier
    assert '"release_approved": False' in verifier
    assert '"official_pypi_release": False' in verifier
    assert "gh release" not in workflow
