from __future__ import annotations

import pytest

from src.analytics import events

BATTER = {"pa": 100, "hits": 30, "doubles": 6, "triples": 1, "home_runs": 3, "walks": 10, "strikeouts": 20}


def test_batter_counts_partition_plate_appearances() -> None:
    counts = events.batter_counts(BATTER)
    assert counts["single"] == 20
    assert sum(counts.values()) == pytest.approx(100)
    assert set(counts) == set(events.EVENTS)


def test_batter_counts_tolerate_missing_and_invalid_values() -> None:
    counts = events.batter_counts({"pa": "", "hits": None, "walks": "x"})
    assert sum(counts.values()) == 0


def test_innings_to_outs_uses_decimal_thirds() -> None:
    assert events.innings_to_outs(0.333) == 1
    assert events.innings_to_outs(6.667) == 20
    assert events.innings_to_outs(None) == 0


def test_league_rates_and_hit_mix_are_probabilities() -> None:
    rates = events.league_rates([BATTER, {**BATTER, "home_runs": 0, "hits": 25}])
    assert sum(rates.values()) == pytest.approx(1.0)
    mix = events.league_hit_mix(rates)
    assert sum(mix.values()) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        events.league_rates([{"pa": 0}])


def test_pitcher_counts_split_hits_by_league_mix() -> None:
    mix = {"single": 0.8, "double": 0.18, "triple": 0.02}
    counts = events.pitcher_counts(
        {"innings_pitched": 10.0, "hits_allowed": 12, "walks": 4, "strikeouts": 9, "home_runs_allowed": 2}, mix
    )
    assert counts["single"] == pytest.approx(8.0)
    assert counts["out"] == 21
    assert counts["home_run"] == 2


def test_regression_pulls_small_samples_to_league() -> None:
    league = events.league_rates([BATTER])
    tiny = events.regressed_probabilities({"home_run": 2, "out": 0}, league, stabilizer=120)
    assert sum(tiny.values()) == pytest.approx(1.0, abs=1e-5)
    assert tiny["home_run"] < 0.1  # 2 HR in 2 PA does not mean a 100% home-run rate


def test_log5_combination_with_league_average_pitcher_returns_batter() -> None:
    league = events.league_rates([BATTER])
    batter = events.regressed_probabilities(events.batter_counts({**BATTER, "home_runs": 8, "hits": 35}), league, 10)
    combined = events.combine_log5(batter, league, league)
    for event in events.EVENTS:
        assert combined[event] == pytest.approx(batter[event] / sum(batter.values()), rel=1e-9)


def test_hit_by_pitch_implied_by_obp_is_folded_into_walks() -> None:
    # OBP .400 over 100 PA implies 40 times on base; 30 hits + 8 walks leaves 2 HBP.
    counts = events.batter_counts({**BATTER, "walks": 8, "obp": 0.400})
    assert counts["walk"] == 10
    assert sum(counts.values()) == 100
