from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SNAPSHOT_HISTORY_COLUMNS = (
    "snapshot_id",
    "captured_at",
    "season",
    "quality_status",
    "previous_snapshot_id",
    "file_count",
    "total_rows",
    "hitter_rows",
    "pitcher_rows",
    "roster_rows",
    "added_rows",
    "removed_rows",
    "changed_rows",
    "schema_changed_files",
)

PLAYER_HISTORY_COLUMNS = (
    "snapshot_id",
    "captured_at",
    "season",
    "player_id",
    "player_name",
    "team",
    "player_type",
    "role_or_position",
    "pa",
    "ab",
    "hits",
    "home_runs",
    "walks",
    "strikeouts",
    "batting_average",
    "obp",
    "slg",
    "ops",
    "iso",
    "bb_rate",
    "k_rate",
    "hr_rate",
    "bb_k_ratio",
    "contact_score",
    "power_score",
    "discipline_score",
    "hitter_value_score",
    "innings_pitched",
    "earned_runs",
    "hits_allowed",
    "home_runs_allowed",
    "era",
    "whip",
    "k_bb_ratio",
    "hr_allowed_rate",
    "run_prevention_score",
    "strikeout_score",
    "command_score",
    "pitcher_value_score",
    "player_value_score",
)

VERSION_COMPARISON_COLUMNS = (
    "player_id",
    "player_name",
    "team",
    "player_type",
    "metric",
    "previous_value",
    "current_value",
    "delta",
    "favorable_delta",
    "movement_status",
    "baseline_snapshot_id",
    "current_snapshot_id",
)

LOWER_IS_BETTER_BY_TYPE = {
    "打者": {"k_rate"},
    "投手": {"era", "whip", "bb_rate", "hr_allowed_rate"},
}

DATASETS = (
    ("batters_scored.csv", "打者", "position"),
    ("pitchers_scored.csv", "投手", "role"),
)


def _empty(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _read_manifests(snapshot_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    snapshot_ids: set[str] = set()
    for path in snapshot_root.rglob("manifest.json") if snapshot_root.exists() else []:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        snapshot_id = str(manifest.get("snapshot_id", "")).strip()
        captured_at = str(manifest.get("captured_at", "")).strip()
        if not snapshot_id or not captured_at:
            raise ValueError(f"snapshot manifest is missing snapshot_id or captured_at: {path}")
        if snapshot_id in snapshot_ids:
            raise ValueError(f"duplicate snapshot_id: {snapshot_id}")
        snapshot_ids.add(snapshot_id)
        manifests.append((path, manifest))

    def sort_key(item: tuple[Path, dict[str, Any]]) -> tuple[pd.Timestamp, str]:
        value = pd.to_datetime(item[1]["captured_at"], utc=True, errors="coerce")
        if pd.isna(value):
            raise ValueError(f"invalid captured_at for snapshot {item[1]['snapshot_id']}")
        return value, str(item[1]["snapshot_id"])

    return sorted(manifests, key=sort_key)


def build_snapshot_history(
    snapshot_root: Path,
    *,
    manifests: list[tuple[Path, dict[str, Any]]] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    entries = _read_manifests(snapshot_root) if manifests is None else manifests
    for _, manifest in entries:
        files = manifest.get("files") or {}
        diff = manifest.get("diff") or {}
        schema_changed = diff.get("schema_changed_files") or []
        rows.append(
            {
                "snapshot_id": str(manifest["snapshot_id"]),
                "captured_at": str(manifest["captured_at"]),
                "season": manifest.get("season"),
                "quality_status": str(manifest.get("quality_status", "unknown")),
                "previous_snapshot_id": manifest.get("previous_snapshot_id"),
                "file_count": len(files),
                "total_rows": sum(int(metadata.get("row_count", 0)) for metadata in files.values()),
                "hitter_rows": int((files.get("batters_scored.csv") or {}).get("row_count", 0)),
                "pitcher_rows": int((files.get("pitchers_scored.csv") or {}).get("row_count", 0)),
                "roster_rows": int((files.get("roster.csv") or {}).get("row_count", 0)),
                "added_rows": int(diff.get("added_rows", 0)),
                "removed_rows": int(diff.get("removed_rows", 0)),
                "changed_rows": int(diff.get("changed_rows", 0)),
                "schema_changed_files": ", ".join(str(name) for name in schema_changed),
            }
        )
    if not rows:
        return _empty(SNAPSHOT_HISTORY_COLUMNS)
    return pd.DataFrame(rows, columns=SNAPSHOT_HISTORY_COLUMNS)


def _read_player_snapshot(path: Path, snapshot: dict[str, Any], player_type: str, role_column: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"snapshot is missing {path.name}: {path.parent}")
    frame = pd.read_csv(path, dtype={"player_id": "string"})
    if frame.empty:
        return _empty(PLAYER_HISTORY_COLUMNS)
    required = {"player_id", "player_name", "team"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")
    if frame["player_id"].isna().any():
        raise ValueError(f"{path.name} contains missing player_id")
    if frame["player_id"].duplicated().any():
        raise ValueError(f"{path.name} contains duplicate player_id")

    frame = frame.copy()
    frame.insert(0, "snapshot_id", str(snapshot["snapshot_id"]))
    frame.insert(1, "captured_at", str(snapshot["captured_at"]))
    frame["season"] = frame.get("season", snapshot.get("season"))
    frame["player_type"] = player_type
    frame["role_or_position"] = frame.get(role_column, "未標示")
    return frame.reindex(columns=PLAYER_HISTORY_COLUMNS)


def build_player_metric_history(
    snapshot_root: Path,
    *,
    manifests: list[tuple[Path, dict[str, Any]]] | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    entries = _read_manifests(snapshot_root) if manifests is None else manifests
    for manifest_path, manifest in entries:
        for file_name, player_type, role_column in DATASETS:
            frames.append(
                _read_player_snapshot(
                    manifest_path.parent / file_name,
                    manifest,
                    player_type,
                    role_column,
                )
            )
    if not frames:
        return _empty(PLAYER_HISTORY_COLUMNS)
    result = pd.concat(frames, ignore_index=True).reindex(columns=PLAYER_HISTORY_COLUMNS)
    result["player_id"] = result["player_id"].astype("string")
    return result


def later_snapshot_ids(version_ids: list[str], baseline_id: str) -> list[str]:
    try:
        baseline_index = version_ids.index(baseline_id)
    except ValueError:
        return []
    return version_ids[baseline_index + 1 :]

def compare_metric_versions(
    history: pd.DataFrame,
    baseline_id: str,
    current_id: str,
    player_type: str,
    metric: str,
) -> pd.DataFrame:
    required = {"snapshot_id", "player_id", "player_name", "team", "player_type", metric}
    if history.empty or not required.issubset(history.columns):
        return _empty(VERSION_COMPARISON_COLUMNS)

    population = history.loc[history["player_type"] == player_type].copy()
    baseline = population.loc[population["snapshot_id"] == baseline_id]
    current = population.loc[population["snapshot_id"] == current_id]
    if baseline.empty and current.empty:
        return _empty(VERSION_COMPARISON_COLUMNS)
    for frame, label in ((baseline, "baseline"), (current, "current")):
        if frame["player_id"].duplicated().any():
            raise ValueError(f"{label} contains duplicate player_id")

    identity = ["player_id", "player_name", "team"]
    baseline = baseline[identity + [metric]].rename(
        columns={
            "player_name": "previous_player_name",
            "team": "previous_team",
            metric: "previous_value",
        }
    )
    current = current[identity + [metric]].rename(
        columns={
            "player_name": "current_player_name",
            "team": "current_team",
            metric: "current_value",
        }
    )
    merged = baseline.merge(current, on="player_id", how="outer")
    merged["previous_value"] = pd.to_numeric(merged["previous_value"], errors="coerce")
    merged["current_value"] = pd.to_numeric(merged["current_value"], errors="coerce")
    merged = merged.loc[merged[["previous_value", "current_value"]].notna().any(axis=1)].copy()
    if merged.empty:
        return _empty(VERSION_COMPARISON_COLUMNS)

    merged["player_name"] = merged["current_player_name"].fillna(merged["previous_player_name"])
    merged["team"] = merged["current_team"].fillna(merged["previous_team"])
    merged["player_type"] = player_type
    merged["metric"] = metric
    merged["delta"] = merged["current_value"] - merged["previous_value"]
    lower_is_better = metric in LOWER_IS_BETTER_BY_TYPE.get(player_type, set())
    merged["favorable_delta"] = -merged["delta"] if lower_is_better else merged["delta"]

    previous_missing = merged["previous_value"].isna()
    current_missing = merged["current_value"].isna()
    unchanged = np.isclose(
        merged["delta"].to_numpy(dtype=float),
        0.0,
        rtol=1e-9,
        atol=1e-12,
        equal_nan=False,
    )
    merged["movement_status"] = np.select(
        [previous_missing, current_missing, unchanged],
        ["new", "removed", "unchanged"],
        default="changed",
    )
    membership_change = merged["movement_status"].isin({"new", "removed"})
    merged.loc[membership_change, ["delta", "favorable_delta"]] = pd.NA
    merged["baseline_snapshot_id"] = baseline_id
    merged["current_snapshot_id"] = current_id
    status_order = pd.Categorical(
        merged["movement_status"],
        categories=["changed", "new", "removed", "unchanged"],
        ordered=True,
    )
    merged = merged.assign(_status_order=status_order).sort_values(
        ["_status_order", "favorable_delta", "player_id"],
        ascending=[True, False, True],
        na_position="last",
        kind="stable",
    )
    return merged.reindex(columns=VERSION_COMPARISON_COLUMNS).reset_index(drop=True)


def generate_history_outputs(snapshot_root: Path, processed_dir: Path) -> dict[str, object]:
    manifests = _read_manifests(snapshot_root)
    snapshots = build_snapshot_history(snapshot_root, manifests=manifests)
    players = build_player_metric_history(snapshot_root, manifests=manifests)
    processed_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = processed_dir / "snapshot_history.csv"
    player_path = processed_dir / "player_metric_history.csv"
    snapshots.to_csv(snapshot_path, index=False, encoding="utf-8-sig")
    players.to_csv(player_path, index=False, encoding="utf-8-sig")

    first = snapshots.iloc[0] if not snapshots.empty else None
    last = snapshots.iloc[-1] if not snapshots.empty else None
    return {
        "snapshot_count": int(len(snapshots)),
        "player_history_rows": int(len(players)),
        "oldest_snapshot_id": "" if first is None else str(first["snapshot_id"]),
        "latest_snapshot_id": "" if last is None else str(last["snapshot_id"]),
        "oldest_captured_at": "" if first is None else str(first["captured_at"]),
        "latest_captured_at": "" if last is None else str(last["captured_at"]),
        "snapshot_output_file": snapshot_path.name,
        "player_output_file": player_path.name,
    }
