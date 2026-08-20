import json
from pathlib import Path

import pandas as pd

from src.release_health import build_release_health_report
from src.release_gate import run_release_gate


REQUIRED_PROCESSED_FILES = (
    "teams.csv",
    "roster.csv",
    "batters_scored.csv",
    "pitchers_scored.csv",
    "players_scored.csv",
)


def _write_release_fixture(root: Path, *, quality_time: str, analysis_time: str) -> None:
    processed = root / "data" / "processed"
    metrics = root / "reports" / "metrics"
    processed.mkdir(parents=True)
    metrics.mkdir(parents=True)

    frames = {
        "teams.csv": pd.DataFrame(
            [{"season": 2026, "team": "測試隊", "wins": 1, "losses": 0, "win_pct": 1.0}]
        ),
        "roster.csv": pd.DataFrame(
            [{"season": 2026, "player_id": "0001", "player_name": "測試球員", "team": "測試隊"}]
        ),
        "batters_scored.csv": pd.DataFrame(
            [{"season": 2026, "player_id": "0001", "player_name": "測試球員", "team": "測試隊"}]
        ),
        "pitchers_scored.csv": pd.DataFrame(
            [{"season": 2026, "player_id": "0002", "player_name": "測試投手", "team": "測試隊"}]
        ),
        "players_scored.csv": pd.DataFrame(
            [
                {"season": 2026, "player_id": "0001", "player_name": "測試球員", "team": "測試隊"},
                {"season": 2026, "player_id": "0002", "player_name": "測試投手", "team": "測試隊"},
            ]
        ),
    }
    for name in REQUIRED_PROCESSED_FILES:
        frames[name].to_csv(processed / name, index=False)

    quality = {
        "mode": "api",
        "generated_at": quality_time,
        "quality_status": "pass",
        "analysis_validation": {
            "schema_version": "1.0",
            "snapshot_count": 2,
            "latest_snapshot_id": "snapshot-2",
        },
        "snapshot": {
            "snapshot_id": "snapshot-2",
            "previous_snapshot_id": "snapshot-1",
            "diff": {"schema_changed_files": [], "files": {}},
        },
        "history": {"snapshot_count": 2, "latest_snapshot_id": "snapshot-2"},
    }
    health = build_release_health_report(quality)
    quality["release_health"] = health
    (metrics / "data_quality_report.json").write_text(json.dumps(quality), encoding="utf-8")
    analysis = {
        "schema_version": "1.0",
        "generated_at": analysis_time,
        "snapshot_count": 2,
        "latest_snapshot_id": "snapshot-2",
        "limitations": ["test"],
        "interpretation": {"test": "test"},
    }
    (metrics / "analysis_validation.json").write_text(json.dumps(analysis), encoding="utf-8")
    (metrics / "release_health.json").write_text(json.dumps(health), encoding="utf-8")


def test_release_gate_accepts_aligned_report_timestamps(tmp_path: Path) -> None:
    generated_at = "2026-08-20T17:58:03+08:00"
    _write_release_fixture(tmp_path, quality_time=generated_at, analysis_time=generated_at)

    result = run_release_gate(tmp_path)

    assert result["status"] == "passed"
    assert result["failures"] == []


def test_release_gate_rejects_stale_analysis_report(tmp_path: Path) -> None:
    _write_release_fixture(
        tmp_path,
        quality_time="2026-08-20T17:58:03+08:00",
        analysis_time="2026-08-05T20:30:00+08:00",
    )

    result = run_release_gate(tmp_path)

    assert result["status"] == "failed"
    assert "品質報告與分析驗證報告的 generated_at 不一致" in result["failures"]
