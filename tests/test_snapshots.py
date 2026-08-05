from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

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
    assert (snapshots / first["relative_path"] / "manifest.json").exists()
    assert len(list(snapshots.rglob("manifest.json"))) == 1
