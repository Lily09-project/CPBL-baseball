import pandas as pd

from src.rankings import get_bottom_players, get_team_rankings, get_top_players, validate_ranking_metric


def test_rankings_handle_missing_metric():
    df = pd.DataFrame({"player_name": ["A"], "ops": [0.8]})
    assert not validate_ranking_metric(df, "missing")
    assert get_top_players(df, "missing").empty


def test_top_and_bottom_rankings():
    df = pd.DataFrame({"player_name": ["A", "B"], "team": ["X", "Y"], "ops": [0.8, 0.9]})
    assert get_top_players(df, "ops").iloc[0]["player_name"] == "B"
    assert get_bottom_players(df, "ops").iloc[0]["player_name"] == "A"


def test_team_rankings_support_both_directions():
    df = pd.DataFrame({"team": ["甲", "乙"], "wins": [5, 2], "losses": [1, 4], "win_pct": [0.833, 0.333]})
    assert get_team_rankings(df, "win_pct").iloc[0]["team"] == "甲"
    assert get_team_rankings(df, "win_pct", ascending=True).iloc[0]["team"] == "乙"
