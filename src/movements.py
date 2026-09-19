from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd


MOVEMENT_COLUMNS = (
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
    "baseline_captured_at",
    "current_captured_at",
)

PLAYER_METRICS = {
    "batters": (
        "打者",
        ("pa", "home_runs", "batting_average", "obp", "slg", "ops", "player_value_score"),
    ),
    "pitchers": (
        "投手",
        ("innings_pitched", "strikeouts", "era", "whip", "k_bb_ratio", "player_value_score"),
    ),
}

LOWER_IS_BETTER = {"era", "whip"}


def _number(value: Any) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(numeric) else float(numeric)


def _validate_player_ids(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    if "player_id" not in frame.columns:
        raise ValueError(f"{label} is missing player_id")
    normalized = frame.copy()
    normalized["player_id"] = normalized["player_id"].astype("string")
    if normalized["player_id"].isna().any():
        raise ValueError(f"{label} contains missing player_id")
    if normalized["player_id"].duplicated().any():
        raise ValueError(f"{label} contains duplicate player_id")
    return normalized


def compare_player_snapshots(
    current: dict[str, pd.DataFrame],
    previous: dict[str, pd.DataFrame],
    metadata: dict[str, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset_name, (player_type, metrics) in PLAYER_METRICS.items():
        current_frame = _validate_player_ids(current.get(dataset_name, pd.DataFrame()), f"current {dataset_name}")
        previous_frame = _validate_player_ids(previous.get(dataset_name, pd.DataFrame()), f"previous {dataset_name}")
        if current_frame.empty:
            continue
        previous_by_id = previous_frame.set_index("player_id", drop=False) if not previous_frame.empty else None
        available_metrics = [metric for metric in metrics if metric in current_frame.columns]
        for _, current_row in current_frame.iterrows():
            player_id = str(current_row["player_id"])
            previous_row = None
            if previous_by_id is not None and player_id in previous_by_id.index:
                previous_row = previous_by_id.loc[player_id]
            for metric in available_metrics:
                current_value = _number(current_row.get(metric))
                if current_value is None:
                    continue
                previous_value = _number(previous_row.get(metric)) if previous_row is not None and metric in previous_row else None
                if previous_value is None:
                    delta = None
                    favorable_delta = None
                    status = "new"
                else:
                    delta = round(current_value - previous_value, 6)
                    favorable_delta = round(-delta if metric in LOWER_IS_BETTER else delta, 6)
                    status = "unchanged" if math.isclose(delta, 0.0, abs_tol=1e-9) else "changed"
                rows.append(
                    {
                        "player_id": player_id,
                        "player_name": str(current_row.get("player_name", "")),
                        "team": str(current_row.get("team", "")),
                        "player_type": player_type,
                        "metric": metric,
                        "previous_value": previous_value,
                        "current_value": current_value,
                        "delta": delta,
                        "favorable_delta": favorable_delta,
                        "movement_status": status,
                        **{column: metadata.get(column, "") for column in MOVEMENT_COLUMNS[-4:]},
                    }
                )
    if not rows:
        return pd.DataFrame(columns=MOVEMENT_COLUMNS)
    result = pd.DataFrame(rows, columns=MOVEMENT_COLUMNS)
    return result.sort_values(
        ["player_type", "team", "player_name", "player_id", "metric"],
        kind="stable",
    ).reset_index(drop=True)

def _snapshot_frames(directory: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for dataset_name, file_name in {
        "batters": "batters_scored.csv",
        "pitchers": "pitchers_scored.csv",
    }.items():
        path = directory / file_name
        if not path.exists():
            raise FileNotFoundError(f"snapshot is missing {file_name}: {directory}")
        frames[dataset_name] = pd.read_csv(path, dtype={"player_id": "string"})
    return frames


def _safe_snapshot_path(snapshot_root: Path, relative_path: str) -> Path:
    root = snapshot_root.resolve()
    candidate = (root / Path(relative_path)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("snapshot path must remain within the snapshot root") from exc
    if candidate == root:
        raise ValueError("snapshot path must identify a directory below the snapshot root")
    return candidate


def _snapshot_directory(snapshot_root: Path, snapshot_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", snapshot_id):
        raise ValueError("snapshot_id has an unsafe format")
    root = snapshot_root.resolve()
    matches = list(root.rglob(f"snapshot_id={snapshot_id}/manifest.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one manifest for snapshot {snapshot_id}, found {len(matches)}")
    return matches[0].parent


def _write_movements(frame: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.reindex(columns=MOVEMENT_COLUMNS).to_csv(output_path, index=False, encoding="utf-8-sig")


def _preserved_movement_metadata(output_path: Path) -> dict[str, object] | None:
    if not output_path.exists():
        return None
    existing = pd.read_csv(output_path, dtype={"player_id": "string"})
    missing = [column for column in MOVEMENT_COLUMNS if column not in existing.columns]
    if missing:
        raise ValueError(f"existing movement output is missing columns: {missing}")
    if existing.empty:
        return None
    first = existing.iloc[0]
    return {
        "status": "preserved",
        "row_count": int(len(existing)),
        "changed_player_count": int(existing.loc[existing["movement_status"] == "changed", "player_id"].nunique()),
        "new_player_count": int(existing.loc[existing["movement_status"] == "new", "player_id"].nunique()),
        "baseline_snapshot_id": str(first["baseline_snapshot_id"]),
        "current_snapshot_id": str(first["current_snapshot_id"]),
        "baseline_captured_at": str(first["baseline_captured_at"]),
        "current_captured_at": str(first["current_captured_at"]),
        "output_file": output_path.name,
    }


def generate_player_movements(
    snapshot_root: Path,
    snapshot: dict[str, Any],
    output_path: Path,
) -> dict[str, object]:
    current_snapshot_id = str(snapshot.get("snapshot_id", ""))
    current_relative_path = str(snapshot.get("relative_path", ""))
    if not current_snapshot_id or not current_relative_path:
        raise ValueError("current snapshot manifest is missing snapshot_id or relative_path")
    current_directory = _safe_snapshot_path(snapshot_root, current_relative_path)
    if not current_directory.exists():
        raise FileNotFoundError(f"current snapshot directory does not exist: {current_directory}")

    baseline_snapshot_id = snapshot.get("previous_snapshot_id")
    base_metadata: dict[str, object] = {
        "baseline_snapshot_id": baseline_snapshot_id,
        "current_snapshot_id": current_snapshot_id,
        "baseline_captured_at": "",
        "current_captured_at": str(snapshot.get("captured_at", "")),
        "output_file": output_path.name,
    }
    if not baseline_snapshot_id:
        preserved = _preserved_movement_metadata(output_path)
        if preserved is not None:
            return preserved
        empty = pd.DataFrame(columns=MOVEMENT_COLUMNS)
        _write_movements(empty, output_path)
        return {
            "status": "baseline_pending",
            "row_count": 0,
            "changed_player_count": 0,
            "new_player_count": 0,
            **base_metadata,
        }

    baseline_directory = _snapshot_directory(snapshot_root, str(baseline_snapshot_id))
    baseline_manifest = json.loads((baseline_directory / "manifest.json").read_text(encoding="utf-8"))
    metadata = {
        "baseline_snapshot_id": str(baseline_snapshot_id),
        "current_snapshot_id": current_snapshot_id,
        "baseline_captured_at": str(baseline_manifest.get("captured_at", "")),
        "current_captured_at": str(snapshot.get("captured_at", "")),
    }
    movements = compare_player_snapshots(
        _snapshot_frames(current_directory),
        _snapshot_frames(baseline_directory),
        metadata,
    )
    _write_movements(movements, output_path)
    return {
        "status": "ready",
        "row_count": int(len(movements)),
        "changed_player_count": int(movements.loc[movements["movement_status"] == "changed", "player_id"].nunique()),
        "new_player_count": int(movements.loc[movements["movement_status"] == "new", "player_id"].nunique()),
        **metadata,
        "output_file": output_path.name,
    }
