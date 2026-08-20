import json
from pathlib import Path

import pandas as pd

from src.release_health import build_release_health_report
from src.public_release_manifest import build_public_release_manifest, write_public_release_manifest
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
    pd.DataFrame(
        [{"player_id": "0001", "player_name": "測試球員", "change_status": "changed"}]
    ).to_csv(processed / "player_movements.csv", index=False)
    pd.DataFrame(
        [{"snapshot_id": "snapshot-2", "captured_at": quality_time, "season": 2026}]
    ).to_csv(processed / "snapshot_history.csv", index=False)
    pd.DataFrame(
        [{"snapshot_id": "snapshot-2", "player_id": "0001", "player_name": "測試球員"}]
    ).to_csv(processed / "player_metric_history.csv", index=False)

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
    manifest = build_public_release_manifest(
        root,
        generated_at=quality_time,
        snapshot_id="snapshot-2",
    )
    write_public_release_manifest(manifest, metrics / "public_release_manifest.json")


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


def test_release_gate_rejects_missing_public_release_manifest(tmp_path: Path) -> None:
    generated_at = "2026-08-20T17:58:03+08:00"
    _write_release_fixture(tmp_path, quality_time=generated_at, analysis_time=generated_at)
    (tmp_path / "reports" / "metrics" / "public_release_manifest.json").unlink()

    result = run_release_gate(tmp_path)

    assert result["status"] == "failed"
    assert "缺少公開發布 Manifest：reports/metrics/public_release_manifest.json" in result["failures"]


def test_release_gate_rejects_tampered_public_artifact(tmp_path: Path) -> None:
    generated_at = "2026-08-20T17:58:03+08:00"
    _write_release_fixture(tmp_path, quality_time=generated_at, analysis_time=generated_at)
    roster_path = tmp_path / "data" / "processed" / "roster.csv"
    roster_path.write_text(roster_path.read_text(encoding="utf-8") + "2026,9999,竄改,測試隊\n", encoding="utf-8")

    result = run_release_gate(tmp_path)

    assert result["status"] == "failed"
    assert any("公開發布 Manifest 驗證失敗" in failure for failure in result["failures"])
