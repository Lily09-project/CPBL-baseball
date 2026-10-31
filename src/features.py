from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics.players import BATTER_QUALIFIER_PA, PITCHER_QUALIFIER_IP

# Small samples must not set or reach the 0-100 extremes (a 0.2-inning 0.00 ERA
# is not elite run prevention). The thresholds reuse the site-wide qualifiers
# that already gate Empirical Bayes priors and percentiles (50 PA / 15 IP;
# src.analytics.players). They sit well below CPBL's batting/ERA title rules
# (3.1 PA and 1 IP per team game), so most regulars still count mid-season.
NEUTRAL_SCORE = 50.0


def _sample_weight(df: pd.DataFrame, column: str, threshold: float) -> pd.Series | None:
    """Share of the qualifier reached, capped at 1; ``None`` without the column."""
    if column not in df.columns:
        return None
    sample = pd.to_numeric(df[column], errors="coerce").fillna(0).clip(lower=0)
    return (sample / threshold).clip(upper=1.0)


def _norm(series: pd.Series, higher_is_better: bool = True, weight: pd.Series | None = None) -> pd.Series:
    """Min-max scale to 0-100 using qualified players' range only.

    ``weight`` (sample / qualifier, capped at 1) picks who sets the bounds
    (weight 1) and pulls everyone else toward the neutral 50 in proportion to
    the missing sample: ``50 + weight * (scaled - 50)``. Values outside the
    qualified range are clipped first, so an unqualified outlier can neither
    move a qualified player's score nor reach 0 or 100 itself.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.empty:
        return pd.Series(dtype=float)
    reference = numeric
    if weight is not None and numeric[weight >= 1].notna().any():
        reference = numeric[weight >= 1]
    min_v = reference.min()
    max_v = reference.max()
    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        return pd.Series([NEUTRAL_SCORE] * len(numeric), index=series.index)
    scaled = (numeric - min_v) / (max_v - min_v) * 100
    if not higher_is_better:
        scaled = 100 - scaled
    scaled = scaled.fillna(NEUTRAL_SCORE).clip(0, 100)
    if weight is not None:
        scaled = NEUTRAL_SCORE + weight * (scaled - NEUTRAL_SCORE)
    return scaled


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
    w = _sample_weight(out, "pa", BATTER_QUALIFIER_PA)
    out["contact_score"] = _norm(out["batting_average"], weight=w)
    out["power_score"] = (_norm(out["iso"], weight=w) * 0.65 + _norm(out["hr_rate"], weight=w) * 0.35).round(1)
    out["discipline_score"] = (
        _norm(out["bb_rate"], weight=w) * 0.45
        + _norm(out["k_rate"], higher_is_better=False, weight=w) * 0.35
        + _norm(_ratio_for_scoring(out, "bb_k_ratio", "walks", "strikeouts"), weight=w) * 0.20
    ).round(1)
    out["hitter_value_score"] = (
        _norm(out["ops"], weight=w) * 0.45 + out["contact_score"] * 0.20 + out["power_score"] * 0.20 + out["discipline_score"] * 0.15
    ).round(1)
    out["player_value_score"] = out["hitter_value_score"]
    out["player_type"] = "打者"
    return out


def score_pitchers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    w = _sample_weight(out, "innings_pitched", PITCHER_QUALIFIER_IP)
    out["run_prevention_score"] = (_norm(out["era"], False, w) * 0.55 + _norm(out["whip"], False, w) * 0.45).round(1)
    out["strikeout_score"] = _norm(out["k_rate"], weight=w).round(1)
    k_bb = _ratio_for_scoring(out, "k_bb_ratio", "strikeouts", "walks")
    out["command_score"] = (_norm(out["bb_rate"], False, w) * 0.50 + _norm(k_bb, weight=w) * 0.50).round(1)
    out["pitcher_value_score"] = (
        out["run_prevention_score"] * 0.45 + out["strikeout_score"] * 0.25 + out["command_score"] * 0.30
    ).round(1)
    out["player_value_score"] = out["pitcher_value_score"]
    out["player_type"] = "投手"
    return out
