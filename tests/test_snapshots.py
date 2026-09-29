from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import src.snapshots as snapshots_module
from src.snapshots import (
    SNAPSHOT_SCHEMA_VERSION,
    compare_processed_directories,
    create_processed_snapshot,
)


def write_processed_fixture(directory: Path, *, changed: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"season": 2026, "team": "測試隊", "wins": 1, "losses": 0, "win_pct": 1.0}]
    ).to_csv(directory / "teams.csv", index=False)
    pd.DataFrame(
        [
            {"season": 2026, "player_id": "0000000001", "player_name": "打者甲", "team": "測試隊", "obp": 0.3, "slg": 0.4, "ops": 0.7},
            {"season": 2026, "player_id": "0000000002", "player_name": "打者乙", "team": "測試隊", "obp": 0.3, "slg": 0.5, "ops": 0.8},
        ]
    ).to_csv(directory / "batters_scored.csv", index=False)
    if changed:
        pd.DataFrame(
            [
                {"season": 2026, "player_id": "0000000001", "player_name": "打者甲", "team": "測試隊", "obp": 0.35, "slg": 0.45, "ops": 0.8, "iso": 0.15},
                {"season": 2026, "player_id": "0000000003", "player_name": "打者丙", "team": "測試隊", "obp": 0.4, "slg": 0.5, "ops": 0.9, "iso": 0.2},
            ]
        ).to_csv(directory / "batters_scored.csv", index=False)

    pd.DataFrame(
        [{"season": 2026, "player_id": "0000000101", "player_name": "投手甲", "team": "測試隊", "era": 3.0, "whip": 1.1, "k_bb_ratio": 3.0}]
    ).to_csv(directory / "pitchers_scored.csv", index=False)
    pd.DataFrame(
        [{"season": 2026, "player_id": "0000000001", "player_name": "打者甲", "team": "測試隊"}]
    ).to_csv(directory / "roster.csv", index=False)
    pd.DataFrame(
        [{"season": 2026, "player_id": "0000000001", "player_name": "打者甲", "team": "測試隊", "player_type": "打者", "player_value_score": 70.0}]
    ).to_csv(directory / "players_scored.csv", index=False)

def test_compare_processed_directories_reports_key_changes_and_schema_drift(tmp_path: Path) -> None:
    previous = tmp_path / "previous"
    current = tmp_path / "current"
    write_processed_fixture(previous)
    write_processed_fixture(current, changed=True)

    diff = compare_processed_directories(previous, current)

    batters = diff["files"]["batters_scored.csv"]
    assert batters["added_rows"] == 1
    assert batters["removed_rows"] == 1
    assert batters["changed_rows"] == 1
    assert batters["schema_added_columns"] == ["iso"]
    assert batters["schema_removed_columns"] == []


def test_create_processed_snapshot_is_idempotent_and_keeps_lineage(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    snapshots = tmp_path / "snapshots"
    write_processed_fixture(processed)
    pd.DataFrame([{"derived": 1}]).to_csv(processed / "player_movements.csv", index=False)
    captured_at = datetime(2026, 8, 5, 12, 30, tzinfo=timezone.utc)
    quality_report = {"quality_status": "pass", "generated_at": "2026-08-05T20:30:00+08:00"}

    first = create_processed_snapshot(
        processed,
        snapshots,
        quality_report,
        captured_at=captured_at,
    )
    second = create_processed_snapshot(
        processed,
        snapshots,
        quality_report,
        captured_at=captured_at.replace(minute=31),
    )

    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert first["quality_status"] == "pass"
    assert first["source_urls"]
    assert first["files"]["batters_scored.csv"]["sha256"]
    assert "player_movements.csv" not in first["files"]
    assert (snapshots / first["relative_path"] / "manifest.json").exists()
    assert len(list(snapshots.rglob("manifest.json"))) == 1


def test_create_processed_snapshot_uses_staged_baseline_when_store_is_empty(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    processed = tmp_path / "processed"
    snapshots = tmp_path / "snapshots"
    write_processed_fixture(baseline)
    write_processed_fixture(processed, changed=True)

    snapshot = create_processed_snapshot(
        processed,
        snapshots,
        {"quality_status": "pass", "generated_at": "2026-09-27T19:46:54+00:00"},
        captured_at=datetime(2026, 9, 27, 19, 46, 54, tzinfo=timezone.utc),
        baseline_processed_dir=baseline,
        baseline_snapshot_id="snapshot-previous",
    )

    assert snapshot["previous_snapshot_id"] == "snapshot-previous"
    assert snapshot["diff"]["files"]["batters_scored.csv"]["previous_row_count"] == 2
    assert snapshot["diff"]["files"]["batters_scored.csv"]["current_row_count"] == 2
    assert snapshot["diff"]["files"]["batters_scored.csv"]["added_rows"] == 1
    assert snapshot["diff"]["files"]["batters_scored.csv"]["removed_rows"] == 1


def test_stage_processed_baseline_copies_release_files_and_returns_latest_id(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    staged = tmp_path / "staged"
    write_processed_fixture(processed)
    pd.DataFrame(
        [
            {"snapshot_id": "snapshot-old", "captured_at": "2026-09-01T00:00:00+00:00"},
            {"snapshot_id": "snapshot-latest", "captured_at": "2026-09-27T00:00:00+00:00"},
        ]
    ).to_csv(processed / "snapshot_history.csv", index=False)

    stage_processed_baseline = getattr(snapshots_module, "stage_processed_baseline", None)
    assert callable(stage_processed_baseline)
    baseline_id = stage_processed_baseline(processed, staged)

    assert baseline_id == "snapshot-latest"
    expected_files = [
        *snapshots_module.SNAPSHOT_FILE_NAMES,
        "snapshot_history.csv",
    ]
    assert sorted(path.name for path in staged.glob("*.csv")) == sorted(
        name for name in expected_files if (processed / name).exists()
    )
