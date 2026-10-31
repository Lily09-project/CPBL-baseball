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


def _ratio_for_scoring(df: pd.DataFrame, ratio: str, numerator: str, denominator: str) -> pd.Series:
    """Rank an undefined ratio (zero denominator) as the best observed value.

    Zero walks with strikeouts is the best possible K/BB, so it scores like the
    league's best defined ratio; with no events at all the ratio is missing and
    ``_norm`` treats it as neutral. Older rows stored such ratios as 0, so the
    counts, not the stored value, decide.
    """
    values = pd.to_numeric(df[ratio], errors="coerce")
    if numerator not in df.columns or denominator not in df.columns:
        return values
    zero_denominator = pd.to_numeric(df[denominator], errors="coerce").eq(0)
    unbounded = zero_denominator & pd.to_numeric(df[numerator], errors="coerce").gt(0)
    best = values[~zero_denominator].max()
    return values.mask(zero_denominator, float("nan")).mask(unbounded, best)


def score_batters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["contact_score"] = _norm(out["batting_average"])
    out["power_score"] = (_norm(out["iso"]) * 0.65 + _norm(out["hr_rate"]) * 0.35).round(1)
    out["discipline_score"] = (
        _norm(out["bb_rate"]) * 0.45
        + _norm(out["k_rate"], higher_is_better=False) * 0.35
        + _norm(_ratio_for_scoring(out, "bb_k_ratio", "walks", "strikeouts")) * 0.20
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
    k_bb = _ratio_for_scoring(out, "k_bb_ratio", "strikeouts", "walks")
    out["command_score"] = (_norm(out["bb_rate"], False) * 0.50 + _norm(k_bb) * 0.50).round(1)
    out["pitcher_value_score"] = (
        out["run_prevention_score"] * 0.45 + out["strikeout_score"] * 0.25 + out["command_score"] * 0.30
    ).round(1)
    out["player_value_score"] = out["pitcher_value_score"]
    out["player_type"] = "投手"
    return out
