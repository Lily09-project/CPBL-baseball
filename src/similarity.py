from __future__ import annotations

import pandas as pd
import numpy as np


BATTER_METRICS = ["ops", "iso", "bb_rate", "k_rate", "hr_rate", "contact_score", "power_score", "discipline_score"]
PITCHER_METRICS = ["era", "whip", "k_rate", "bb_rate", "k_bb_ratio", "run_prevention_score", "command_score", "pitcher_value_score"]


def find_similar_players(df: pd.DataFrame, player_id: str, player_type: str = "打者", n: int = 5) -> pd.DataFrame:
    if df.empty or "player_id" not in df or player_id not in set(df["player_id"]):
        return pd.DataFrame()
    metrics = BATTER_METRICS if player_type == "打者" else PITCHER_METRICS
    available = [m for m in metrics if m in df.columns]
    if len(available) < 3:
        return pd.DataFrame()
    work = df.dropna(subset=available).copy()
    if player_id not in set(work["player_id"]) or len(work) < 2:
        return pd.DataFrame()
    values = work[available].astype(float).to_numpy()
    means = values.mean(axis=0)
    stds = values.std(axis=0)
    stds[stds == 0] = 1
    x = (values - means) / stds
    norms = np.linalg.norm(x, axis=1)
    norms[norms == 0] = 1
    normalized = x / norms[:, None]
    target_idx = work.index[work["player_id"] == player_id][0]
    target_pos = list(work.index).index(target_idx)
    work["similarity"] = normalized @ normalized[target_pos]
    result = work[work["player_id"] != player_id].sort_values("similarity", ascending=False).head(n)
    keep = [c for c in ["player_id", "player_name", "team", "position", "role", "player_value_score", "similarity"] if c in result.columns]
    return result[keep].reset_index(drop=True)
