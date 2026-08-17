from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.preprocess import preprocess
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


def ensure_processed_data() -> None:
    if any(not project_path("data/processed", name).exists() for name in REQUIRED_PROCESSED_FILES):
        preprocess(mode="api")


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


def load_csv(name: str) -> pd.DataFrame:
    ensure_processed_data()
    path = project_path("data/processed", name)
    if not path.exists():
        return pd.DataFrame()
    columns = pd.read_csv(path, nrows=0).columns
    dtypes = {column: "string" for column in ["player_id"] if column in columns}
    return pd.read_csv(path, dtype=dtypes)


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
