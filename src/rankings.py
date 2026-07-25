from __future__ import annotations

import pandas as pd


DISPLAY_COLUMNS = [
    "player_name",
    "team",
    "position",
    "role",
    "metric_value",
    "player_value_score",
]


def validate_ranking_metric(df: pd.DataFrame, metric: str) -> bool:
    return bool(metric) and not df.empty and metric in df.columns


def _rank(df: pd.DataFrame, metric: str, n: int = 10, ascending: bool = False) -> pd.DataFrame:
    if not validate_ranking_metric(df, metric):
        return pd.DataFrame()
    out = df.copy()
    out["metric_value"] = pd.to_numeric(out[metric], errors="coerce")
    out = out.dropna(subset=["metric_value"]).sort_values("metric_value", ascending=ascending).head(n)
    columns = [c for c in DISPLAY_COLUMNS if c in out.columns]
    return out[columns].reset_index(drop=True)


def get_top_players(df: pd.DataFrame, metric: str, n: int = 10) -> pd.DataFrame:
    return _rank(df, metric, n=n, ascending=False)


def get_bottom_players(df: pd.DataFrame, metric: str, n: int = 10) -> pd.DataFrame:
    return _rank(df, metric, n=n, ascending=True)


def get_team_rankings(df: pd.DataFrame, metric: str, n: int = 10, ascending: bool = False) -> pd.DataFrame:
    if not validate_ranking_metric(df, metric):
        return pd.DataFrame()
    out = df.copy()
    out["metric_value"] = pd.to_numeric(out[metric], errors="coerce")
    keep = [c for c in ["team", "wins", "losses", "win_pct", "run_diff", "momentum_score", "metric_value"] if c in out.columns]
    return out.dropna(subset=["metric_value"]).sort_values("metric_value", ascending=ascending).head(n)[keep].reset_index(drop=True)
