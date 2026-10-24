"""League-level analytics: Pythagorean expectation and season simulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

PYTHAGOREAN_EXPONENT = 1.83
DEFAULT_SEGMENT_GAMES = 60
DEFAULT_SIMULATIONS = 10_000
DEFAULT_SEED = 20261024


def pythagorean_win_pct(runs_scored: float, runs_allowed: float, exponent: float = PYTHAGOREAN_EXPONENT) -> float:
    """Expected winning percentage from run differential (Bill James)."""
    if runs_scored < 0 or runs_allowed < 0:
        raise ValueError("runs must be non-negative")
    if runs_scored == 0 and runs_allowed == 0:
        return 0.5
    rs, ra = runs_scored**exponent, runs_allowed**exponent
    return rs / (rs + ra)


def log5_win_probability(p_a: float, p_b: float) -> float:
    """Probability that team A beats team B given their true win rates."""
    denominator = p_a * (1 - p_b) + p_b * (1 - p_a)
    if denominator == 0:
        return 0.5
    return p_a * (1 - p_b) / denominator


@dataclass(frozen=True)
class TeamRecord:
    team: str
    games: int
    wins: int
    losses: int
    ties: int
    runs_scored: float
    runs_allowed: float


def build_remaining_schedule(remaining: dict[str, int]) -> list[tuple[str, str]]:
    """Pair teams' remaining games deterministically.

    The official remaining schedule is not part of the public snapshot, so
    games are paired greedily: the team with the most games left plays the
    opponent with the most games left that it has met least so far. Ties are
    broken by name, so the schedule never depends on dict ordering.
    """
    left = {team: int(count) for team, count in remaining.items() if count > 0}
    met: dict[tuple[str, str], int] = {}
    schedule: list[tuple[str, str]] = []
    while True:
        candidates = sorted((t for t in left if left[t] > 0), key=lambda t: (-left[t], t))
        if len(candidates) < 2:
            break
        home = candidates[0]
        opponents = sorted(
            candidates[1:],
            key=lambda t: (met.get(tuple(sorted((home, t))), 0), -left[t], t),
        )
        away = opponents[0]
        schedule.append((home, away))
        key = tuple(sorted((home, away)))
        met[key] = met.get(key, 0) + 1
        left[home] -= 1
        left[away] -= 1
    return schedule


def simulate_segment(
    records: Sequence[TeamRecord],
    segment_games: int = DEFAULT_SEGMENT_GAMES,
    simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, float | int | str | list[int]]]:
    """Monte Carlo the rest of the season segment.

    Returns one row per team with the projected wins distribution and the
    probability of finishing first. A tie for first is shared equally, so the
    first-place probabilities always sum to exactly one.
    """
    if not records:
        return []
    teams = [r.team for r in records]
    index = {team: i for i, team in enumerate(teams)}
    strength = np.array([pythagorean_win_pct(r.runs_scored, r.runs_allowed) for r in records])
    remaining = {r.team: max(segment_games - r.games, 0) for r in records}
    schedule = build_remaining_schedule(remaining)
    rng = np.random.default_rng(seed)
    wins = np.tile(np.array([r.wins for r in records], dtype=float), (simulations, 1))
    if schedule:
        home_idx = np.array([index[h] for h, _ in schedule])
        away_idx = np.array([index[a] for _, a in schedule])
        p_home = np.array([log5_win_probability(strength[h], strength[a]) for h, a in zip(home_idx, away_idx)])
        draws = rng.random((simulations, len(schedule)))
        home_won = draws < p_home
        for game, (h, a) in enumerate(zip(home_idx, away_idx)):
            wins[:, h] += home_won[:, game]
            wins[:, a] += ~home_won[:, game]
    best = wins.max(axis=1, keepdims=True)
    leaders = wins == best
    share = leaders / leaders.sum(axis=1, keepdims=True)
    first_prob = share.mean(axis=0)
    rows: list[dict[str, float | int | str | list[int]]] = []
    for i, record in enumerate(records):
        team_wins = wins[:, i]
        low, mid, high = np.percentile(team_wins, [10, 50, 90])
        counts = np.bincount(team_wins.astype(int) - record.wins, minlength=remaining[record.team] + 1)
        rows.append(
            {
                "team": record.team,
                "games_played": record.games,
                "games_remaining": remaining[record.team],
                "current_wins": record.wins,
                "strength": round(float(strength[i]), 4),
                "projected_wins_mean": round(float(team_wins.mean()), 2),
                "projected_wins_p10": int(low),
                "projected_wins_p50": int(mid),
                "projected_wins_p90": int(high),
                "first_place_probability": float(first_prob[i]),
                "additional_wins_histogram": [int(c) for c in counts],
            }
        )
    return rows
