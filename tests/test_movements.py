from __future__ import annotations

import pandas as pd
import pytest

from src.movements import MOVEMENT_COLUMNS, compare_player_snapshots, generate_player_movements


def snapshot_frames(*, current: bool) -> dict[str, pd.DataFrame]:
    if current:
        batters = pd.DataFrame(
            [
                {
                    "player_id": "0000000001",
                    "player_name": "打者甲",
                    "team": "測試隊",
                    "pa": 120,
                    "home_runs": 6,
                    "batting_average": 0.300,
                    "obp": 0.380,
                    "slg": 0.500,
                    "ops": 0.880,
                    "player_value_score": 74.0,
                },
                {
                    "player_id": "0000000002",
                    "player_name": "新打者",
                    "team": "測試隊",
                    "pa": 8,
                    "home_runs": 1,
                    "batting_average": 0.250,
                    "obp": 0.300,
                    "slg": 0.500,
                    "ops": 0.800,
                    "player_value_score": 61.0,
                },
            ]
        )
        pitchers = pd.DataFrame(
            [
                {
                    "player_id": "0000000101",
                    "player_name": "投手甲",
                    "team": "測試隊",
                    "innings_pitched": 42.0,
                    "strikeouts": 45,
                    "era": 3.00,
                    "whip": 1.10,
                    "k_bb_ratio": 3.20,
                    "player_value_score": 78.0,
                }
            ]
        )
    else:
        batters = pd.DataFrame(
            [
                {
                    "player_id": "0000000001",
                    "player_name": "打者甲",
                    "team": "測試隊",
                    "pa": 100,
                    "home_runs": 4,
                    "batting_average": 0.280,
                    "obp": 0.350,
                    "slg": 0.450,
                    "ops": 0.800,
                    "player_value_score": 69.5,
                }
            ]
        )
        pitchers = pd.DataFrame(
            [
                {
                    "player_id": "0000000101",
                    "player_name": "投手甲",
                    "team": "測試隊",
                    "innings_pitched": 36.0,
                    "strikeouts": 36,
                    "era": 4.00,
                    "whip": 1.30,
                    "k_bb_ratio": 2.40,
                    "player_value_score": 70.0,
                }
            ]
        )
    return {"batters": batters, "pitchers": pitchers}


def movement_metadata() -> dict[str, str]:
    return {
        "baseline_snapshot_id": "snapshot-old",
        "current_snapshot_id": "snapshot-new",
        "baseline_captured_at": "2026-08-06T14:44:58+00:00",
        "current_captured_at": "2026-08-09T11:14:07+00:00",
    }


def test_compare_player_snapshots_builds_long_form_deltas_and_direction() -> None:
    result = compare_player_snapshots(
        snapshot_frames(current=True),
        snapshot_frames(current=False),
        movement_metadata(),
    )

    assert list(result.columns) == list(MOVEMENT_COLUMNS)
    hitter_ops = result[(result["player_id"] == "0000000001") & (result["metric"] == "ops")].iloc[0]
    pitcher_era = result[(result["player_id"] == "0000000101") & (result["metric"] == "era")].iloc[0]
    assert hitter_ops["previous_value"] == pytest.approx(0.800)
    assert hitter_ops["current_value"] == pytest.approx(0.880)
    assert hitter_ops["delta"] == pytest.approx(0.080)
    assert hitter_ops["favorable_delta"] == pytest.approx(0.080)
    assert hitter_ops["movement_status"] == "changed"
    assert pitcher_era["delta"] == pytest.approx(-1.0)
    assert pitcher_era["favorable_delta"] == pytest.approx(1.0)


def test_compare_player_snapshots_marks_new_players_without_fake_deltas() -> None:
    result = compare_player_snapshots(
        snapshot_frames(current=True),
        snapshot_frames(current=False),
        movement_metadata(),
    )

    new_rows = result[result["player_id"] == "0000000002"]
    assert not new_rows.empty
    assert set(new_rows["movement_status"]) == {"new"}
    assert new_rows["previous_value"].isna().all()
    assert new_rows["delta"].isna().all()
    assert new_rows["favorable_delta"].isna().all()


def test_compare_player_snapshots_rejects_duplicate_player_ids() -> None:
    current = snapshot_frames(current=True)
    current["batters"] = pd.concat([current["batters"], current["batters"].iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate player_id"):
        compare_player_snapshots(current, snapshot_frames(current=False), movement_metadata())

def write_snapshot(directory, frames: dict[str, pd.DataFrame], manifest: dict[str, object]) -> None:
    directory.mkdir(parents=True)
    frames["batters"].to_csv(directory / "batters_scored.csv", index=False)
    frames["pitchers"].to_csv(directory / "pitchers_scored.csv", index=False)
    (directory / "manifest.json").write_text(pd.Series(manifest).to_json(force_ascii=False), encoding="utf-8")


def test_generate_player_movements_uses_manifest_predecessor_and_writes_csv(tmp_path) -> None:
    snapshots = tmp_path / "snapshots"
    previous_dir = snapshots / "season=2026" / "snapshot_id=snapshot-old"
    current_dir = snapshots / "season=2026" / "snapshot_id=snapshot-new"
    write_snapshot(
        previous_dir,
        snapshot_frames(current=False),
        {"snapshot_id": "snapshot-old", "captured_at": "2026-08-06T14:44:58+00:00"},
    )
    current_manifest = {
        "snapshot_id": "snapshot-new",
        "captured_at": "2026-08-09T11:14:07+00:00",
        "relative_path": "season=2026/snapshot_id=snapshot-new",
        "previous_snapshot_id": "snapshot-old",
    }
    write_snapshot(current_dir, snapshot_frames(current=True), current_manifest)
    output = tmp_path / "processed" / "player_movements.csv"

    metadata = generate_player_movements(snapshots, current_manifest, output)

    saved = pd.read_csv(output, dtype={"player_id": "string"})
    assert metadata["status"] == "ready"
    assert metadata["row_count"] == len(saved)
    assert metadata["changed_player_count"] == 2
    assert metadata["new_player_count"] == 1
    assert metadata["baseline_snapshot_id"] == "snapshot-old"
    assert metadata["current_snapshot_id"] == "snapshot-new"
    assert metadata["output_file"] == "player_movements.csv"
    assert "output_path" not in metadata
    assert set(saved["player_id"]) == {"0000000001", "0000000002", "0000000101"}


def test_generate_player_movements_writes_schema_when_baseline_is_pending(tmp_path) -> None:
    snapshots = tmp_path / "snapshots"
    current_dir = snapshots / "season=2026" / "snapshot_id=snapshot-first"
    current_manifest = {
        "snapshot_id": "snapshot-first",
        "captured_at": "2026-08-09T11:14:07+00:00",
        "relative_path": "season=2026/snapshot_id=snapshot-first",
        "previous_snapshot_id": None,
    }
    write_snapshot(current_dir, snapshot_frames(current=True), current_manifest)
    output = tmp_path / "processed" / "player_movements.csv"

    metadata = generate_player_movements(snapshots, current_manifest, output)

    saved = pd.read_csv(output, dtype={"player_id": "string"})
    assert metadata["status"] == "baseline_pending"
    assert metadata["row_count"] == 0
    assert metadata["output_file"] == "player_movements.csv"
    assert "output_path" not in metadata
    assert list(saved.columns) == list(MOVEMENT_COLUMNS)

def test_generate_player_movements_preserves_public_history_without_local_baseline(tmp_path) -> None:
    snapshots = tmp_path / "snapshots"
    current_dir = snapshots / "season=2026" / "snapshot_id=snapshot-first"
    current_manifest = {
        "snapshot_id": "snapshot-first",
        "captured_at": "2026-08-10T00:00:00+00:00",
        "relative_path": "season=2026/snapshot_id=snapshot-first",
        "previous_snapshot_id": None,
    }
    write_snapshot(current_dir, snapshot_frames(current=True), current_manifest)
    output = tmp_path / "processed" / "player_movements.csv"
    output.parent.mkdir(parents=True)
    historical = pd.DataFrame(
        [
            {
                "player_id": "0000000001",
                "player_name": "打者甲",
                "team": "測試隊",
                "player_type": "打者",
                "metric": "ops",
                "previous_value": 0.8,
                "current_value": 0.85,
                "delta": 0.05,
                "favorable_delta": 0.05,
                "movement_status": "changed",
                "baseline_snapshot_id": "snapshot-old",
                "current_snapshot_id": "snapshot-public",
                "baseline_captured_at": "2026-08-06T00:00:00+00:00",
                "current_captured_at": "2026-08-09T00:00:00+00:00",
            }
        ],
        columns=MOVEMENT_COLUMNS,
    )
    historical.to_csv(output, index=False, encoding="utf-8-sig")

    metadata = generate_player_movements(snapshots, current_manifest, output)
    saved = pd.read_csv(output, dtype={"player_id": "string"})

    assert metadata["status"] == "preserved"
    assert metadata["row_count"] == 1
    assert metadata["baseline_snapshot_id"] == "snapshot-old"
    assert metadata["current_snapshot_id"] == "snapshot-public"
    pd.testing.assert_frame_equal(saved, historical.astype({"player_id": "string"}), check_dtype=False)
