from __future__ import annotations

import pytest

from src.analytics import league


def _records(games: tuple[int, ...] = (57, 54, 56, 55, 55, 55)) -> list[league.TeamRecord]:
    base = [
        ("A", 33, 24, 278, 221),
        ("B", 31, 23, 196, 173),
        ("C", 30, 26, 218, 184),
        ("D", 25, 30, 172, 196),
        ("E", 24, 31, 183, 216),
        ("F", 23, 32, 210, 267),
    ]
    return [
        league.TeamRecord(team=t, games=g, wins=w, losses=l, ties=0, runs_scored=rs, runs_allowed=ra)
        for (t, w, l, rs, ra), g in zip(base, games)
    ]


def test_pythagorean_expectation() -> None:
    assert league.pythagorean_win_pct(100, 100) == pytest.approx(0.5)
    assert league.pythagorean_win_pct(0, 0) == 0.5
    expected = 278**1.83 / (278**1.83 + 221**1.83)
    assert league.pythagorean_win_pct(278, 221) == pytest.approx(expected)
    assert league.pythagorean_win_pct(300, 200) > 0.5
    with pytest.raises(ValueError):
        league.pythagorean_win_pct(-1, 3)


def test_log5_is_symmetric_and_handles_equal_teams() -> None:
    assert league.log5_win_probability(0.5, 0.5) == pytest.approx(0.5)
    p = league.log5_win_probability(0.6, 0.4)
    assert p + league.log5_win_probability(0.4, 0.6) == pytest.approx(1.0)
    assert league.log5_win_probability(1.0, 1.0) == 0.5


def test_remaining_schedule_uses_every_game_and_is_deterministic() -> None:
    remaining = {"A": 3, "B": 6, "C": 4, "D": 5, "E": 5, "F": 5}
    schedule = league.build_remaining_schedule(remaining)
    assert schedule == league.build_remaining_schedule(dict(reversed(list(remaining.items()))))
    counts = {team: 0 for team in remaining}
    for home, away in schedule:
        assert home != away
        counts[home] += 1
        counts[away] += 1
    assert all(counts[t] <= remaining[t] for t in remaining)
    assert sum(remaining.values()) - sum(counts.values()) <= 1


def test_first_place_probabilities_sum_to_one() -> None:
    rows = league.simulate_segment(_records(), segment_games=60, simulations=2000, seed=7)
    assert sum(r["first_place_probability"] for r in rows) == pytest.approx(1.0, abs=1e-9)
    assert all(0 <= r["first_place_probability"] <= 1 for r in rows)


def test_simulation_is_reproducible_with_a_seed() -> None:
    a = league.simulate_segment(_records(), simulations=1500, seed=11)
    b = league.simulate_segment(_records(), simulations=1500, seed=11)
    c = league.simulate_segment(_records(), simulations=1500, seed=12)
    assert a == b
    assert a != c


def test_completed_teams_keep_their_wins() -> None:
    rows = league.simulate_segment(_records(games=(60, 60, 60, 60, 60, 60)), segment_games=60, simulations=500)
    for row in rows:
        assert row["games_remaining"] == 0
        assert row["projected_wins_mean"] == row["current_wins"]
        assert row["additional_wins_histogram"] == [500]
    leader = max(rows, key=lambda r: r["current_wins"])
    assert leader["first_place_probability"] == pytest.approx(1.0)


def test_projected_wins_stay_within_possible_range() -> None:
    for row in league.simulate_segment(_records(), simulations=800, seed=3):
        assert row["current_wins"] <= row["projected_wins_p10"] <= row["projected_wins_p90"]
        assert row["projected_wins_p90"] <= row["current_wins"] + row["games_remaining"]
        assert sum(row["additional_wins_histogram"]) == 800


def test_empty_league_simulation() -> None:
    assert league.simulate_segment([]) == []
