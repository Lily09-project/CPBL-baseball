from __future__ import annotations

import pandas as pd

from src.features import score_batters, score_pitchers


def _pitchers(k_bb_zero_walks: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"era": 3.0, "whip": 1.2, "k_rate": 0.20, "bb_rate": 0.05, "strikeouts": 20, "walks": 5, "k_bb_ratio": 4.0},
            {"era": 3.0, "whip": 1.2, "k_rate": 0.20, "bb_rate": 0.10, "strikeouts": 10, "walks": 10, "k_bb_ratio": 1.0},
            {"era": 3.0, "whip": 1.2, "k_rate": 0.20, "bb_rate": 0.00, "strikeouts": 4, "walks": 0, "k_bb_ratio": k_bb_zero_walks},
        ]
    )


def test_zero_walk_pitcher_is_not_scored_as_worst_command() -> None:
    # Both the new undefined value and the legacy stored 0 must score as elite.
    for stored in (float("nan"), 0.0):
        scored = score_pitchers(_pitchers(stored))
        assert scored.loc[2, "command_score"] == 100.0
        assert scored.loc[2, "command_score"] > scored.loc[1, "command_score"]


def test_zero_strikeout_batter_bb_k_is_not_scored_as_worst() -> None:
    base = {"batting_average": 0.3, "iso": 0.1, "hr_rate": 0.01, "ops": 0.8, "bb_rate": 0.1, "k_rate": 0.1}
    df = pd.DataFrame(
        [
            {**base, "walks": 5, "strikeouts": 10, "bb_k_ratio": 0.5},
            {**base, "walks": 2, "strikeouts": 20, "bb_k_ratio": 0.1},
            {**base, "walks": 3, "strikeouts": 0, "bb_k_ratio": float("nan")},
            {**base, "walks": 0, "strikeouts": 0, "bb_k_ratio": float("nan")},
        ]
    )
    scored = score_batters(df)
    assert scored.loc[2, "discipline_score"] == scored["discipline_score"].max()
    # No events at all stays neutral rather than best or worst.
    assert scored.loc[1, "discipline_score"] < scored.loc[3, "discipline_score"] < scored.loc[2, "discipline_score"]
