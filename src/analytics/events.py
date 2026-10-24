"""Plate-appearance event probabilities for the in-browser lineup simulator.

The simulator draws one of seven outcomes per plate appearance. Batter and
pitcher probabilities are regressed toward the league with a fixed number of
league-average plate appearances, then combined in the browser with the
generalised log5 (odds-ratio) method.
"""
from __future__ import annotations

from typing import Mapping

EVENTS = ("single", "double", "triple", "home_run", "walk", "strikeout", "out")
BATTER_STABILIZER_PA = 120.0
PITCHER_STABILIZER_BF = 150.0


def _clean(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return number if number == number and number > 0 else 0.0


def batter_counts(row: Mapping[str, object]) -> dict[str, float]:
    """Partition plate appearances into the seven simulated outcomes.

    The public batting line has no hit-by-pitch column, but the official OBP
    includes it. Times on base implied by OBP beyond hits and walks are
    folded into the "walk" outcome (both put the batter on first by force).
    """
    pa = _clean(row.get("pa"))
    hits = _clean(row.get("hits"))
    doubles = _clean(row.get("doubles"))
    triples = _clean(row.get("triples"))
    home_runs = _clean(row.get("home_runs"))
    implied_on_base = round(_clean(row.get("obp")) * pa)
    walks = _clean(row.get("walks"))
    walks += max(implied_on_base - hits - walks, 0.0)
    strikeouts = _clean(row.get("strikeouts"))
    singles = max(hits - doubles - triples - home_runs, 0.0)
    counted = singles + doubles + triples + home_runs + walks + strikeouts
    return {
        "single": singles,
        "double": doubles,
        "triple": triples,
        "home_run": home_runs,
        "walk": walks,
        "strikeout": strikeouts,
        "out": max(pa - counted, 0.0),
    }


def innings_to_outs(innings_pitched: float) -> float:
    """Official innings are already decimal thirds (e.g. 0.333 = one out)."""
    return round(_clean(innings_pitched) * 3)


def pitcher_counts(row: Mapping[str, object], league_hit_mix: Mapping[str, float]) -> dict[str, float]:
    """Split pitcher hits into hit types using the league mix of non-HR hits."""
    outs = innings_to_outs(_clean(row.get("innings_pitched")))
    hits = _clean(row.get("hits_allowed"))
    walks = _clean(row.get("walks"))
    strikeouts = _clean(row.get("strikeouts"))
    home_runs = _clean(row.get("home_runs_allowed"))
    non_hr_hits = max(hits - home_runs, 0.0)
    return {
        "single": non_hr_hits * league_hit_mix["single"],
        "double": non_hr_hits * league_hit_mix["double"],
        "triple": non_hr_hits * league_hit_mix["triple"],
        "home_run": home_runs,
        "walk": walks,
        "strikeout": strikeouts,
        "out": max(outs - strikeouts, 0.0),
    }


def league_rates(batter_rows: list[Mapping[str, object]]) -> dict[str, float]:
    totals = {event: 0.0 for event in EVENTS}
    for row in batter_rows:
        for event, count in batter_counts(row).items():
            totals[event] += count
    total = sum(totals.values())
    if total <= 0:
        raise ValueError("league totals require at least one plate appearance")
    return {event: totals[event] / total for event in EVENTS}


def league_hit_mix(rates: Mapping[str, float]) -> dict[str, float]:
    non_hr = rates["single"] + rates["double"] + rates["triple"]
    return {key: rates[key] / non_hr for key in ("single", "double", "triple")}


def regressed_probabilities(
    counts: Mapping[str, float],
    league: Mapping[str, float],
    stabilizer: float,
) -> dict[str, float]:
    """Add ``stabilizer`` league-average trials, then normalise to sum to one."""
    total = sum(counts.values())
    raw = {event: counts.get(event, 0.0) + stabilizer * league[event] for event in EVENTS}
    denominator = total + stabilizer
    return {event: round(raw[event] / denominator, 6) for event in EVENTS}


def combine_log5(
    batter: Mapping[str, float],
    pitcher: Mapping[str, float],
    league: Mapping[str, float],
) -> dict[str, float]:
    """Generalised log5: P(event) is proportional to batter * pitcher / league.

    Kept in Python so the TypeScript implementation can be checked against it.
    """
    weights = {event: batter[event] * pitcher[event] / league[event] for event in EVENTS}
    total = sum(weights.values())
    return {event: weights[event] / total for event in EVENTS}
