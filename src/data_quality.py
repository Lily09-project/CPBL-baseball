from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pandas as pd

from src.utils import ensure_dirs, project_path

REQUIRED_FILES = ["teams.csv", "roster.csv", "batters_scored.csv", "pitchers_scored.csv", "players_scored.csv"]


def _missing_ratio(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {}
    return {col: round(float(df[col].isna().mean()), 4) for col in df.columns}


def generate_data_quality_report(mode: str = "api", fallback_reason: str = "CPBL official API") -> dict:
    ensure_dirs()
    processed_dir = project_path("data/processed")
    report: dict = {
        "mode": mode,
        "fallback_reason": fallback_reason,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": {},
        "available_team_count": 0,
        "available_player_count": 0,
        "available_hitter_count": 0,
        "available_pitcher_count": 0,
        "official_roster_count": 0,
        "player_summary_count": 0,
        "model_status": "official-derived scoring ready",
        "quality_status": "pass",
    }
    warnings = []
    failed = False
    for file_name in REQUIRED_FILES:
        csv_path = processed_dir / file_name
        if not csv_path.exists():
            warnings.append(f"{file_name} is missing")
            failed = True
            continue
        df = pd.read_csv(csv_path)
        report["files"][csv_path.name] = {"row_count": int(len(df)), "missing_ratio": _missing_ratio(df)}
        if len(df) == 0:
            warnings.append(f"{csv_path.name} is empty")
            failed = True
        if csv_path.name == "teams.csv" and "team" in df:
            report["available_team_count"] = int(df["team"].nunique())
        if csv_path.name == "roster.csv" and "player_id" in df:
            report["official_roster_count"] = int(df["player_id"].nunique())
        elif csv_path.name == "players_scored.csv" and "player_id" in df:
            report["player_summary_count"] = int(df["player_id"].nunique())
        elif csv_path.name == "batters_scored.csv" and "player_id" in df:
            report["available_hitter_count"] = int(df["player_id"].nunique())
            report["available_player_count"] += report["available_hitter_count"]
        elif csv_path.name == "pitchers_scored.csv" and "player_id" in df:
            report["available_pitcher_count"] = int(df["player_id"].nunique())
            report["available_player_count"] += report["available_pitcher_count"]
    report["available_player_count"] = max(
        report["available_player_count"],
        report["official_roster_count"],
        report["player_summary_count"],
    )
    minimum_counts = {
        "available_team_count": 6,
        "official_roster_count": 200,
        "available_hitter_count": 50,
        "available_pitcher_count": 50,
        "player_summary_count": 200,
    }
    for field, minimum in minimum_counts.items():
        if report[field] < minimum:
            warnings.append(f"{field}={report[field]} is below expected minimum {minimum}")
    if not report["files"]:
        report["quality_status"] = "failed"
        warnings.append("No processed CSV files found")
    elif failed:
        report["quality_status"] = "failed"
    elif warnings:
        report["quality_status"] = "warning"
    report["warnings"] = warnings
    out_path = project_path("reports/metrics/data_quality_report.json")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def load_data_quality_report() -> dict:
    path = project_path("reports/metrics/data_quality_report.json")
    if not path.exists():
        return generate_data_quality_report()
    return json.loads(path.read_text(encoding="utf-8"))
