from pathlib import Path


def test_streamlit_runtime_does_not_request_usage_metrics():
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8-sig")

    assert "[browser]" in config
    assert "gatherUsageStats = false" in config
