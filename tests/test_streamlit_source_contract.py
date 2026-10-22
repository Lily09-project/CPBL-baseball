from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_source_candidate_is_immutable_complete_and_dependency_only() -> None:
    workflow = (ROOT / ".github/workflows/streamlit-source.yml").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts/verify_streamlit_candidate.py").read_text(encoding="utf-8")
    assert "repository: streamlit/streamlit" in workflow
    assert "ref: 81bdb8a8a207691f17ec94df9eabc96b6b50ea7a" in workflow
    assert "id: upstream" in workflow
    assert "steps.upstream.outputs.commit" in workflow
    assert "--expected-commit" in workflow
    assert "persist-credentials: false" in workflow
    assert "contents: read" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert workflow.count("contents: write") == 1
    assert "needs: [build-and-audit, integration]" in workflow
    assert "--prerelease --latest=false" in workflow
    assert "github.actor == github.repository_owner" in workflow
    assert "make package" in workflow
    assert "patch_streamlit_frontend.py --source upstream" in workflow
    assert "yarn test --maxWorkers=2" in workflow
    assert "self-built-official-source-with-frontend-security-patches" in verifier
    assert "Unexpected frontend patch scope" in verifier
    assert "--frontend-patch" in workflow
    assert "uv lock --check" in workflow
    assert "yarn npm audit --all --recursive --environment production --json" in workflow
    assert "Pillow==13.0.0" in workflow
    assert "pip_audit --local --strict" in workflow
    assert "--ignore-vuln" not in workflow
    assert "continue-on-error:" not in workflow
    assert "streamlit/static/index.html" in verifier
    assert "streamlit/static/static/js/" in verifier
    assert "streamlit/static/static/css/" in verifier
    assert "_pb2.py" in verifier
    assert '"release_approved": False' in verifier
    assert '"official_pypi_release": False' in verifier
    assert "product_release_approved" in workflow


def test_frontend_audit_uses_the_canonical_registry_before_expensive_builds() -> None:
    workflow = (ROOT / ".github/workflows/streamlit-source.yml").read_text(encoding="utf-8")
    assert "YARN_NPM_AUDIT_REGISTRY: https://registry.npmjs.org" in workflow
    assert "yarn config get npmAuditRegistry" in workflow
    assert workflow.index("yarn npm audit") < workflow.index("make package")
    assert "npmAuditIgnoreAdvisories" not in workflow
    assert "npmAuditExcludePackages" not in workflow
