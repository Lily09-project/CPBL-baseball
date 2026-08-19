from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils import project_path


REQUIRED_PROCESSED_FILES = (
    "teams.csv",
    "roster.csv",
    "batters_scored.csv",
    "pitchers_scored.csv",
    "players_scored.csv",
)
PUBLIC_PROCESSED_FILES = (
    *REQUIRED_PROCESSED_FILES,
    "player_movements.csv",
    "snapshot_history.csv",
    "player_metric_history.csv",
)


class ProcessedDataError(RuntimeError):
    """Raised when a tracked processed CSV cannot be read safely."""


def missing_processed_files() -> tuple[str, ...]:
    return tuple(
        name
        for name in REQUIRED_PROCESSED_FILES
        if not project_path("data/processed", name).exists()
    )


def ensure_processed_data() -> tuple[str, ...]:
    """Check local processed outputs without triggering a network refresh."""
    return missing_processed_files()


def processed_data_version() -> tuple[tuple[str, int | None, int | None], ...]:
    signatures = []
    for name in PUBLIC_PROCESSED_FILES:
        path = project_path("data/processed", name)
        if path.exists():
            stat = path.stat()
            signatures.append((name, stat.st_mtime_ns, stat.st_size))
        else:
            signatures.append((name, None, None))
    return tuple(signatures)


def _processed_csv_path(name: str) -> Path:
    root = project_path("data/processed").resolve()
    candidate = (root / name).resolve()
    name_path = Path(name)
    if (
        not name
        or name_path.name != name
        or name_path.suffix.lower() != ".csv"
        or candidate.parent != root
    ):
        raise ValueError("processed CSV path must be a direct CSV filename")
    return candidate


def load_csv(name: str) -> pd.DataFrame:
    path = _processed_csv_path(name)
    ensure_processed_data()
    if not path.exists():
        return pd.DataFrame()
    try:
        columns = pd.read_csv(path, nrows=0).columns
        dtypes = {column: "string" for column in ["player_id"] if column in columns}
        return pd.read_csv(path, dtype=dtypes)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise ProcessedDataError(f"處理後資料檔案無法讀取：{name}") from exc


def file_exists(rel: str) -> bool:
    return Path(project_path(rel)).exists()


def win_rate_series(wins: pd.Series, losses: pd.Series) -> pd.Series:
    numeric_wins = pd.to_numeric(wins, errors="coerce").fillna(0.0)
    numeric_losses = pd.to_numeric(losses, errors="coerce").fillna(0.0)
    games = numeric_wins + numeric_losses
    result = pd.Series(0.0, index=numeric_wins.index, dtype=float)
    played = games > 0
    result.loc[played] = numeric_wins.loc[played].div(games.loc[played])
    return result

def player_choice_options(frame: pd.DataFrame) -> dict[str, str]:
    required = {"player_id", "player_name", "team"}
    if frame.empty or not required.issubset(frame.columns):
        return {}

    players = frame.dropna(subset=["player_id", "player_name", "team"]).copy()
    if players.empty:
        return {}
    players["player_id"] = players["player_id"].astype("string")
    players = players.drop_duplicates("player_id", keep="last").sort_values(
        ["player_name", "team", "player_id"], kind="stable"
    )

    def role_label(row: pd.Series) -> str:
        for column in ("role_or_position", "position", "role", "player_type"):
            value = str(row.get(column, "") or "").strip()
            if value and value.lower() != "nan":
                return value
        return "未標示"

    return {
        f"{row.player_name} · {row.team} · {role_label(row)} · {row.player_id}": str(row.player_id)
        for _, row in players.iterrows()
    }
