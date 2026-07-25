from __future__ import annotations

import numpy as np
import pandas as pd


def _norm(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.empty:
        return pd.Series(dtype=float)
    min_v = numeric.min()
    max_v = numeric.max()
    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        return pd.Series([50.0] * len(numeric), index=series.index)
    scaled = (numeric - min_v) / (max_v - min_v) * 100
    if not higher_is_better:
        scaled = 100 - scaled
    return scaled.fillna(50).clip(0, 100)


def score_batters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["contact_score"] = _norm(out["batting_average"])
    out["power_score"] = (_norm(out["iso"]) * 0.65 + _norm(out["hr_rate"]) * 0.35).round(1)
    out["discipline_score"] = (
        _norm(out["bb_rate"]) * 0.45 + _norm(out["k_rate"], higher_is_better=False) * 0.35 + _norm(out["bb_k_ratio"]) * 0.20
    ).round(1)
    out["hitter_value_score"] = (
        _norm(out["ops"]) * 0.45 + out["contact_score"] * 0.20 + out["power_score"] * 0.20 + out["discipline_score"] * 0.15
    ).round(1)
    out["player_value_score"] = out["hitter_value_score"]
    out["player_type"] = "打者"
    return out


def score_pitchers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["run_prevention_score"] = (_norm(out["era"], False) * 0.55 + _norm(out["whip"], False) * 0.45).round(1)
    out["strikeout_score"] = _norm(out["k_rate"]).round(1)
    out["command_score"] = (_norm(out["bb_rate"], False) * 0.50 + _norm(out["k_bb_ratio"]) * 0.50).round(1)
    out["pitcher_value_score"] = (
        out["run_prevention_score"] * 0.45 + out["strikeout_score"] * 0.25 + out["command_score"] * 0.30
    ).round(1)
    out["player_value_score"] = out["pitcher_value_score"]
    out["player_type"] = "投手"
    return out
