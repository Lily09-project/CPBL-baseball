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


def _staff() -> pd.DataFrame:
    rows = [
        {"innings_pitched": 60.0, "era": 2.00, "whip": 1.00},
        {"innings_pitched": 45.0, "era": 3.50, "whip": 1.30},
        {"innings_pitched": 30.0, "era": 5.00, "whip": 1.60},
    ]
    base = {"k_rate": 0.20, "bb_rate": 0.08, "strikeouts": 20, "walks": 8, "k_bb_ratio": 2.5}
    return pd.DataFrame([{**base, **row} for row in rows])


def test_tiny_sample_perfect_era_does_not_score_as_elite() -> None:
    staff = _staff()
    cameo = {**staff.iloc[0].to_dict(), "innings_pitched": 0.667, "era": 0.0, "whip": 0.0}
    scored = score_pitchers(pd.concat([staff, pd.DataFrame([cameo])], ignore_index=True))
    cameo_score = scored.loc[3, "run_prevention_score"]
    # 0.667 / 15 IP of the way from neutral 50 toward the clipped 100.
    assert cameo_score < 55
    assert cameo_score < scored.loc[0, "run_prevention_score"]
    assert scored.loc[0, "run_prevention_score"] == 100.0


def test_unqualified_outlier_does_not_move_qualified_scores() -> None:
    staff = _staff()
    outlier = {**staff.iloc[0].to_dict(), "innings_pitched": 0.333, "era": 108.0, "whip": 9.0}
    alone = score_pitchers(staff)
    with_outlier = score_pitchers(pd.concat([staff, pd.DataFrame([outlier])], ignore_index=True))
    pd.testing.assert_series_equal(alone["run_prevention_score"], with_outlier["run_prevention_score"].iloc[:3])
    assert with_outlier.loc[3, "run_prevention_score"] > 45


def test_small_sample_batter_shrinks_toward_neutral() -> None:
    base = {"iso": 0.1, "hr_rate": 0.01, "bb_rate": 0.1, "k_rate": 0.2, "walks": 5, "strikeouts": 10, "bb_k_ratio": 0.5}
    df = pd.DataFrame(
        [
            {**base, "pa": 300, "batting_average": 0.250, "ops": 0.650},
            {**base, "pa": 300, "batting_average": 0.320, "ops": 0.900},
            {**base, "pa": 25, "batting_average": 1.000, "ops": 2.000},
        ]
    )
    scored = score_batters(df)
    # Half the 50-PA qualifier: halfway from 50 to the clipped 100.
    assert scored.loc[2, "contact_score"] == 75.0
    assert scored.loc[1, "contact_score"] == 100.0
