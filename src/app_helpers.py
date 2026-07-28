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


def ensure_processed_data() -> None:
    if any(not project_path("data/processed", name).exists() for name in REQUIRED_PROCESSED_FILES):
        preprocess(mode="api")


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
