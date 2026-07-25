import sys

import pytest

import run_all
from run_all import main


def test_run_all_defaults_to_api(monkeypatch, capsys):
    calls = {}

    def fake_preprocess(mode):
        calls["mode"] = mode
        return {"teams": "teams.csv"}

    monkeypatch.setattr(sys, "argv", ["run_all.py"])
    monkeypatch.setattr(run_all, "preprocess", fake_preprocess)
    monkeypatch.setattr(
        run_all,
        "generate_data_quality_report",
        lambda mode, fallback_reason: {"quality_status": "pass", "mode": mode, "fallback_reason": fallback_reason},
    )

    main()

    out = capsys.readouterr().out
    assert calls["mode"] == "api"
    assert "done" in out


def test_run_all_rejects_sample_mode(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_all.py", "--mode", "sample"])
    with pytest.raises(SystemExit):
        main()
