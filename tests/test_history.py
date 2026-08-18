from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import src.history as history_module

from src.history import (
    PLAYER_HISTORY_COLUMNS,
    SNAPSHOT_HISTORY_COLUMNS,
    build_player_metric_history,
    build_snapshot_history,
    compare_metric_versions,
    generate_history_outputs,
)


def write_snapshot(
    root: Path,
    snapshot_id: str,
    captured_at: str,
    *,
    previous_snapshot_id: str | None = None,
    hitter_ops: float = 0.8,
    pitcher_era: float = 4.0,
    extra_hitter: bool = False,
    include_pitchers: bool = True,
) -> Path:
    directory = root / "season=2026" / f"snapshot_id={snapshot_id}"
    directory.mkdir(parents=True)
    hitters = [
        {
            "season": 2026,
            "player_id": "0000000001",
            "player_name": "測試打者",
            "team": "測試隊",
            "position": "內野手",
            "pa": 100,
            "ops": hitter_ops,
            "k_rate": 0.2,
            "player_value_score": 70.0,
        }
    ]
    if extra_hitter:
        hitters.append(
            {
                "season": 2026,
                "player_id": "0000000002",
                "player_name": "新增打者",
                "team": "測試隊",
                "position": "外野手",
                "pa": 20,
                "ops": 0.9,
                "k_rate": 0.15,
                "player_value_score": 75.0,
            }
        )
    pd.DataFrame(hitters).to_csv(directory / "batters_scored.csv", index=False)
    if include_pitchers:
        pd.DataFrame(
            [
                {
                    "season": 2026,
                    "player_id": "0000000101",
                    "player_name": "測試投手",
                    "team": "測試隊",
                    "role": "先發投手",
                    "innings_pitched": 30.0,
                    "era": pitcher_era,
                    "bb_rate": 0.08,
                    "player_value_score": 68.0,
                }
            ]
        ).to_csv(directory / "pitchers_scored.csv", index=False)

    files = {
        "batters_scored.csv": {
            "row_count": len(hitters),
            "columns": list(hitters[0]),
            "sha256": "a" * 64,
            "key_column": "player_id",
        },
        "pitchers_scored.csv": {
            "row_count": 1,
            "columns": ["player_id", "era"],
            "sha256": "b" * 64,
            "key_column": "player_id",
        },
    }
    manifest = {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "season": 2026,
        "relative_path": f"season=2026/snapshot_id={snapshot_id}",
        "quality_status": "pass",
        "previous_snapshot_id": previous_snapshot_id,
        "files": files,
        "diff": {
            "added_rows": 1 if extra_hitter else 0,
            "removed_rows": 0,
            "changed_rows": 2,
            "schema_changed_files": [],
        }
        if previous_snapshot_id
        else None,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return directory


def test_build_snapshot_history_sorts_by_capture_time_and_keeps_public_summary(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    write_snapshot(root, "snapshot-new", "2026-08-12T02:00:00+00:00", previous_snapshot_id="snapshot-old")
    write_snapshot(root, "snapshot-old", "2026-08-10T01:00:00+00:00")

    history = build_snapshot_history(root)

    assert history.columns.tolist() == list(SNAPSHOT_HISTORY_COLUMNS)
    assert history["snapshot_id"].tolist() == ["snapshot-old", "snapshot-new"]
    assert history["total_rows"].tolist() == [2, 2]
    assert history.iloc[-1]["changed_rows"] == 2
    assert not history.astype(str).apply(lambda column: column.str.contains(str(tmp_path), regex=False)).any().any()


def test_build_player_metric_history_preserves_ids_and_player_roles(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    write_snapshot(root, "snapshot-old", "2026-08-10T01:00:00+00:00")
    write_snapshot(
        root,
        "snapshot-new",
        "2026-08-12T02:00:00+00:00",
        previous_snapshot_id="snapshot-old",
        hitter_ops=0.9,
        pitcher_era=3.0,
        extra_hitter=True,
    )

    history = build_player_metric_history(root)

    assert history.columns.tolist() == list(PLAYER_HISTORY_COLUMNS)
    assert set(history["player_type"]) == {"打者", "投手"}
    assert "0000000001" in set(history["player_id"])
    assert history["snapshot_id"].drop_duplicates().tolist() == ["snapshot-old", "snapshot-new"]
    assert history.loc[history["player_type"] == "打者", "role_or_position"].eq("內野手").any()


def test_build_player_metric_history_fails_when_manifest_file_is_missing(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    write_snapshot(root, "snapshot-old", "2026-08-10T01:00:00+00:00", include_pitchers=False)

    with pytest.raises(FileNotFoundError, match="pitchers_scored.csv"):
        build_player_metric_history(root)


def test_compare_metric_versions_handles_direction_and_membership_changes(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    write_snapshot(root, "snapshot-old", "2026-08-10T01:00:00+00:00", hitter_ops=0.8, pitcher_era=4.0)
    write_snapshot(
        root,
        "snapshot-new",
        "2026-08-12T02:00:00+00:00",
        previous_snapshot_id="snapshot-old",
        hitter_ops=0.9,
        pitcher_era=3.0,
        extra_hitter=True,
    )
    history = build_player_metric_history(root)

    hitter_changes = compare_metric_versions(history, "snapshot-old", "snapshot-new", "打者", "ops")
    pitcher_changes = compare_metric_versions(history, "snapshot-old", "snapshot-new", "投手", "era")

    changed = hitter_changes.loc[hitter_changes["player_id"] == "0000000001"].iloc[0]
    new = hitter_changes.loc[hitter_changes["player_id"] == "0000000002"].iloc[0]
    pitcher = pitcher_changes.iloc[0]
    assert changed["movement_status"] == "changed"
    assert changed["delta"] == pytest.approx(0.1)
    assert changed["favorable_delta"] == pytest.approx(0.1)
    assert new["movement_status"] == "new"
    assert pd.isna(new["previous_value"])
    assert pd.isna(new["delta"])
    assert pitcher["delta"] == pytest.approx(-1.0)
    assert pitcher["favorable_delta"] == pytest.approx(1.0)


def test_compare_metric_versions_marks_removed_and_unchanged() -> None:
    history = pd.DataFrame(
        [
            {"snapshot_id": "old", "captured_at": "2026-08-10", "player_id": "1", "player_name": "甲", "team": "A", "player_type": "打者", "ops": 0.8},
            {"snapshot_id": "old", "captured_at": "2026-08-10", "player_id": "2", "player_name": "乙", "team": "A", "player_type": "打者", "ops": 0.7},
            {"snapshot_id": "new", "captured_at": "2026-08-12", "player_id": "1", "player_name": "甲", "team": "A", "player_type": "打者", "ops": 0.8},
        ]
    )

    result = compare_metric_versions(history, "old", "new", "打者", "ops")

    assert result.set_index("player_id").loc["1", "movement_status"] == "unchanged"
    removed = result.set_index("player_id").loc["2"]
    assert removed["movement_status"] == "removed"
    assert pd.isna(removed["current_value"])


def test_generate_history_outputs_writes_deployable_csvs_and_metadata(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    processed = tmp_path / "processed"
    write_snapshot(root, "snapshot-old", "2026-08-10T01:00:00+00:00")
    write_snapshot(root, "snapshot-new", "2026-08-12T02:00:00+00:00", previous_snapshot_id="snapshot-old")

    metadata = generate_history_outputs(root, processed)

    snapshot_path = processed / "snapshot_history.csv"
    player_path = processed / "player_metric_history.csv"
    assert snapshot_path.exists()
    assert player_path.exists()
    assert metadata == {
        "snapshot_count": 2,
        "player_history_rows": 4,
        "oldest_snapshot_id": "snapshot-old",
        "latest_snapshot_id": "snapshot-new",
        "oldest_captured_at": "2026-08-10T01:00:00+00:00",
        "latest_captured_at": "2026-08-12T02:00:00+00:00",
        "snapshot_output_file": "snapshot_history.csv",
        "player_output_file": "player_metric_history.csv",
    }
    assert "output_path" not in metadata
    loaded = pd.read_csv(player_path, dtype={"player_id": "string"})
    assert loaded["player_id"].str.len().min() == 10


def test_generate_history_outputs_indexes_manifests_once(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "snapshots"
    processed = tmp_path / "processed"
    write_snapshot(root, "snapshot-old", "2026-08-10T01:00:00+00:00")
    write_snapshot(
        root,
        "snapshot-new",
        "2026-08-12T02:00:00+00:00",
        previous_snapshot_id="snapshot-old",
    )
    original = history_module._read_manifests
    calls = 0

    def counted(snapshot_root: Path):
        nonlocal calls
        calls += 1
        return original(snapshot_root)

    monkeypatch.setattr(history_module, "_read_manifests", counted)

    generate_history_outputs(root, processed)

    assert calls == 1

def test_generate_history_outputs_preserves_committed_history_without_local_snapshots(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    processed = tmp_path / "processed"
    write_snapshot(root, "snapshot-current", "2026-08-14T02:00:00+00:00")
    processed.mkdir(parents=True)

    existing_snapshot_history = pd.DataFrame(
        [
            {
                "snapshot_id": "snapshot-previous",
                "captured_at": "2026-08-12T02:00:00+00:00",
                "season": 2026,
                "quality_status": "pass",
                "previous_snapshot_id": "",
                "file_count": 5,
                "total_rows": 4,
                "hitter_rows": 1,
                "pitcher_rows": 1,
                "roster_rows": 2,
                "added_rows": 0,
                "removed_rows": 0,
                "changed_rows": 0,
                "schema_changed_files": "",
            }
        ],
        columns=SNAPSHOT_HISTORY_COLUMNS,
    )
    existing_snapshot_history.to_csv(processed / "snapshot_history.csv", index=False)

    existing_player_history = pd.DataFrame(
        [
            {
                "snapshot_id": "snapshot-previous",
                "captured_at": "2026-08-12T02:00:00+00:00",
                "season": 2026,
                "player_id": "0000000001",
                "player_name": "甲",
                "team": "A",
                "player_type": "打者",
                "role_or_position": "內野手",
                "ops": 0.8,
            }
        ]
    ).reindex(columns=PLAYER_HISTORY_COLUMNS)
    existing_player_history.to_csv(processed / "player_metric_history.csv", index=False)

    metadata = generate_history_outputs(root, processed)

    assert metadata["snapshot_count"] == 2
    assert metadata["oldest_snapshot_id"] == "snapshot-previous"
    assert metadata["latest_snapshot_id"] == "snapshot-current"
    assert set(pd.read_csv(processed / "snapshot_history.csv")["snapshot_id"]) == {
        "snapshot-previous",
        "snapshot-current",
    }
    loaded = pd.read_csv(processed / "player_metric_history.csv", dtype={"player_id": "string"})
    assert set(loaded["snapshot_id"]) == {"snapshot-previous", "snapshot-current"}

def test_later_snapshot_ids_only_returns_valid_comparison_versions() -> None:
    versions = ["v1", "v2", "v3", "v4"]

    assert history_module.later_snapshot_ids(versions, "v1") == ["v2", "v3", "v4"]
    assert history_module.later_snapshot_ids(versions, "v3") == ["v4"]
    assert history_module.later_snapshot_ids(versions, "v4") == []
    assert history_module.later_snapshot_ids(versions, "missing") == []
    assert history_module.later_snapshot_ids([], "v1") == []
