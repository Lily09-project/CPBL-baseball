from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import pandas as pd


SNAPSHOT_SCHEMA_VERSION = "1.0"
OFFICIAL_SOURCE_URLS = [
    "https://www.cpbl.com.tw/player",
    "https://www.cpbl.com.tw/standings/season",
    "https://www.cpbl.com.tw/stats/recordallaction",
]
KEY_COLUMNS = {
    "teams.csv": "team",
    "roster.csv": "player_id",
    "batters_scored.csv": "player_id",
    "pitchers_scored.csv": "player_id",
    "players_scored.csv": "player_id",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    columns = pd.read_csv(path, nrows=0).columns
    dtypes = {"player_id": "string"} if "player_id" in columns else None
    return pd.read_csv(path, dtype=dtypes)


def _file_metadata(path: Path) -> dict[str, Any]:
    frame = _read_csv(path)
    return {
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
        "sha256": sha256_file(path),
        "key_column": KEY_COLUMNS.get(path.name),
    }


def _frame_by_key(frame: pd.DataFrame, key_column: str) -> pd.DataFrame:
    if key_column not in frame.columns:
        return pd.DataFrame()
    normalized = frame.copy()
    normalized[key_column] = normalized[key_column].astype("string")
    normalized = normalized.dropna(subset=[key_column]).drop_duplicates(subset=[key_column], keep="last")
    return normalized.set_index(key_column, drop=False).sort_index()


def _row_signature(row: pd.Series, columns: list[str]) -> tuple[str, ...]:
    return tuple("<NULL>" if pd.isna(row[column]) else str(row[column]) for column in columns)


def _diff_frame(previous: pd.DataFrame, current: pd.DataFrame, key_column: str | None) -> dict[str, Any]:
    previous_columns = list(previous.columns)
    current_columns = list(current.columns)
    previous_set = set(previous_columns)
    current_set = set(current_columns)
    summary: dict[str, Any] = {
        "previous_row_count": int(len(previous)),
        "current_row_count": int(len(current)),
        "row_count_delta": int(len(current) - len(previous)),
        "schema_added_columns": sorted(current_set - previous_set),
        "schema_removed_columns": sorted(previous_set - current_set),
        "added_rows": 0,
        "removed_rows": 0,
        "changed_rows": 0,
        "key_column": key_column,
    }
    if not key_column or key_column not in previous_set or key_column not in current_set:
        summary["changed_rows"] = int(len(current)) if not previous.equals(current) else 0
        return summary

    previous_by_key = _frame_by_key(previous, key_column)
    current_by_key = _frame_by_key(current, key_column)
    previous_keys = set(previous_by_key.index)
    current_keys = set(current_by_key.index)
    summary["added_rows"] = len(current_keys - previous_keys)
    summary["removed_rows"] = len(previous_keys - current_keys)
    common_columns = sorted((previous_set & current_set) - {key_column})
    summary["changed_rows"] = sum(
        _row_signature(previous_by_key.loc[key], common_columns)
        != _row_signature(current_by_key.loc[key], common_columns)
        for key in previous_keys & current_keys
    )
    return summary


def compare_processed_directories(previous_dir: Path, current_dir: Path) -> dict[str, Any]:
    names = sorted({path.name for path in previous_dir.glob("*.csv")} | {path.name for path in current_dir.glob("*.csv")})
    files: dict[str, dict[str, Any]] = {}
    for name in names:
        files[name] = _diff_frame(
            _read_csv(previous_dir / name),
            _read_csv(current_dir / name),
            KEY_COLUMNS.get(name),
        )
    return {
        "files": files,
        "added_rows": sum(item["added_rows"] for item in files.values()),
        "removed_rows": sum(item["removed_rows"] for item in files.values()),
        "changed_rows": sum(item["changed_rows"] for item in files.values()),
        "schema_changed_files": sorted(
            name
            for name, item in files.items()
            if item["schema_added_columns"] or item["schema_removed_columns"]
        ),
    }


def _snapshot_fingerprint(files: dict[str, dict[str, Any]]) -> str:
    payload = "|".join(f"{name}:{meta['sha256']}" for name, meta in sorted(files.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _season_from_files(processed_dir: Path, fallback: int) -> int:
    for path in sorted(processed_dir.glob("*.csv")):
        frame = _read_csv(path)
        if "season" not in frame.columns:
            continue
        values = pd.to_numeric(frame["season"], errors="coerce").dropna().unique()
        if len(values) == 1:
            return int(values[0])
    return fallback


def _existing_snapshot_for_files(snapshot_root: Path, files: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    expected = {name: metadata["sha256"] for name, metadata in files.items()}
    for manifest_path in snapshot_root.rglob("manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        observed = {
            name: metadata.get("sha256")
            for name, metadata in manifest.get("files", {}).items()
        }
        if manifest.get("schema_version") == SNAPSHOT_SCHEMA_VERSION and observed == expected:
            return manifest
    return None

def _latest_snapshot_directory(snapshot_root: Path, exclude: Path) -> Path | None:
    candidates = [path.parent for path in snapshot_root.rglob("manifest.json") if path.parent != exclude]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def create_processed_snapshot(
    processed_dir: Path,
    snapshot_root: Path,
    quality_report: dict[str, Any],
    *,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    if quality_report.get("quality_status") not in {"pass", "warning"}:
        raise ValueError("Only quality-checked processed data can be snapshotted")
    source_files = sorted(processed_dir.glob("*.csv"))
    if not source_files:
        raise FileNotFoundError("No processed CSV files available for snapshot")

    captured_at = captured_at or datetime.now(timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    captured_at = captured_at.astimezone(timezone.utc)
    files = {path.name: _file_metadata(path) for path in source_files}
    existing = _existing_snapshot_for_files(snapshot_root, files)
    if existing is not None:
        return existing
    snapshot_id = f"{captured_at.strftime('%Y%m%dT%H%M%SZ')}-{_snapshot_fingerprint(files)}"
    season = _season_from_files(processed_dir, captured_at.year)
    destination = snapshot_root / f"season={season}" / f"snapshot_id={snapshot_id}"
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    previous = _latest_snapshot_directory(snapshot_root, destination)
    diff = compare_processed_directories(previous, processed_dir) if previous else None
    destination.mkdir(parents=True, exist_ok=True)
    for source in source_files:
        shutil.copy2(source, destination / source.name)

    manifest = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "captured_at": captured_at.isoformat(timespec="seconds"),
        "season": season,
        "relative_path": destination.relative_to(snapshot_root).as_posix(),
        "source_urls": OFFICIAL_SOURCE_URLS,
        "quality_status": quality_report["quality_status"],
        "quality_report_generated_at": quality_report.get("generated_at", ""),
        "files": files,
        "previous_snapshot_id": previous.name.removeprefix("snapshot_id=") if previous else None,
        "diff": diff,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
