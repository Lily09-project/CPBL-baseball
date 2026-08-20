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
    monkeypatch.setattr(
        run_all,
        "create_processed_snapshot",
        lambda processed_dir, snapshot_root, report: {"snapshot_id": "test-snapshot", "relative_path": "test", "diff": None},
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "generate_player_movements",
        lambda snapshot_root, snapshot, output_path: {"status": "ready", "row_count": 3},
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "generate_history_outputs",
        lambda snapshot_root, processed_dir: {"snapshot_count": 1, "player_history_rows": 2},
        raising=False,
    )
    monkeypatch.setattr(run_all, "save_data_quality_report", lambda report: None, raising=False)
    monkeypatch.setattr(
        run_all,
        "write_analysis_validation_report",
        lambda report, path: None,
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "build_release_health_report",
        lambda report: {"status": "passed", "checks": []},
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "write_release_health_report",
        lambda report: "release_health.json",
        raising=False,
    )

    main()

    out = capsys.readouterr().out
    assert calls["mode"] == "api"
    assert "done" in out


def test_run_all_rejects_sample_mode(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_all.py", "--mode", "sample"])
    with pytest.raises(SystemExit):
        main()


def test_run_all_stops_when_quality_report_fails(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_all.py"])
    monkeypatch.setattr(run_all, "preprocess", lambda mode: {"teams": "teams.csv"})
    monkeypatch.setattr(
        run_all,
        "generate_data_quality_report",
        lambda mode, fallback_reason: {"quality_status": "failed", "mode": mode},
    )

    with pytest.raises(RuntimeError, match="資料品質檢查失敗"):
        main()


def test_run_all_attaches_snapshot_only_after_quality_passes(monkeypatch):
    calls = {}
    monkeypatch.setattr(sys, "argv", ["run_all.py"])
    monkeypatch.setattr(run_all, "preprocess", lambda mode: {"teams": "teams.csv"})
    monkeypatch.setattr(
        run_all,
        "generate_data_quality_report",
        lambda mode, fallback_reason: {
            "quality_status": "pass",
            "mode": mode,
            "generated_at": "2026-08-05T20:30:00+08:00",
        },
    )
    monkeypatch.setattr(
        run_all,
        "create_processed_snapshot",
        lambda processed_dir, snapshot_root, report: {
            "snapshot_id": "snapshot-1",
            "relative_path": "season=2026/snapshot_id=snapshot-1",
            "diff": None,
        },
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "save_data_quality_report",
        lambda report: calls.setdefault("report", report),
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "write_analysis_validation_report",
        lambda report, path: None,
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "build_release_health_report",
        lambda report: {"status": "passed", "checks": []},
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "write_release_health_report",
        lambda report: "release_health.json",
        raising=False,
    )

    monkeypatch.setattr(
        run_all,
        "generate_player_movements",
        lambda snapshot_root, snapshot, output_path: {
            "status": "ready",
            "row_count": 12,
            "baseline_snapshot_id": "snapshot-0",
            "current_snapshot_id": snapshot["snapshot_id"],
        },
        raising=False,
    )
    monkeypatch.setattr(
        run_all,
        "generate_history_outputs",
        lambda snapshot_root, processed_dir: {
            "snapshot_count": 2,
            "player_history_rows": 636,
            "latest_snapshot_id": "snapshot-1",
            "snapshot_output_file": "snapshot_history.csv",
            "player_output_file": "player_metric_history.csv",
        },
        raising=False,
    )

    main()

    assert calls["report"]["snapshot"]["snapshot_id"] == "snapshot-1"
    assert calls["report"]["movement"]["row_count"] == 12
    assert calls["report"]["movement"]["current_snapshot_id"] == "snapshot-1"
    assert calls["report"]["history"]["snapshot_count"] == 2
    assert calls["report"]["history"]["player_history_rows"] == 636
    assert calls["report"]["release_health"]["status"] == "passed"
