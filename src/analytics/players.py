"""Player-level analytics: percentiles, explainable similarity, trajectories."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence

BATTER_QUALIFIER_PA = 50.0
PITCHER_QUALIFIER_IP = 15.0


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    higher_is_better: bool
    fmt: str
    short: str


BATTER_METRICS: tuple[Metric, ...] = (
    Metric("obp_post", "上壘能力", True, "rate3", "上壘率"),
    Metric("iso", "長打力 ISO", True, "rate3", "ISO"),
    Metric("hr_rate_post", "全壘打產出", True, "pct1", "全壘打率"),
    Metric("bb_rate_post", "選球保送", True, "pct1", "保送率"),
    Metric("k_rate_post", "三振控制", False, "pct1", "三振率"),
    Metric("speed", "跑壘積極度", True, "pct1", "盜壘頻率"),
)

PITCHER_METRICS: tuple[Metric, ...] = (
    Metric("k_rate_post", "三振能力", True, "pct1", "三振率"),
    Metric("bb_rate_post", "控球", False, "pct1", "保送率"),
    Metric("hr_rate_post", "壓制全壘打", False, "pct1", "被全壘打率"),
    Metric("fip_post", "防禦本質 FIP", False, "num2", "FIP"),
    Metric("whip", "壓制上壘 WHIP", False, "num2", "WHIP"),
)


def percentile_of(value: float, population: Sequence[float], higher_is_better: bool) -> float:
    """Share of the population this value beats, in [0, 100] (mid-rank ties)."""
    values = [v for v in population if v is not None and not math.isnan(v)]
    if not values or value is None or math.isnan(value):
        return float("nan")
    below = sum(1 for v in values if (v < value if higher_is_better else v > value))
    equal = sum(1 for v in values if v == value)
    return 100.0 * (below + 0.5 * equal) / len(values)


def zscores(rows: Sequence[Mapping[str, float]], keys: Sequence[str]) -> list[list[float]]:
    columns = []
    for key in keys:
        values = [float(r[key]) for r in rows]
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
        sd = math.sqrt(var) or 1.0
        columns.append([(v - mean) / sd for v in values])
    return [list(vector) for vector in zip(*columns)]


def explainable_similarity(
    rows: Sequence[Mapping[str, float]],
    ids: Sequence[str],
    keys: Sequence[str],
    target_id: str,
    top_n: int = 5,
) -> list[dict[str, object]]:
    """Cosine similarity on standardised features with per-feature contributions.

    The contributions of all features sum to the cosine similarity, so the
    interface can say *why* two players look alike.
    """
    if target_id not in ids:
        raise KeyError(target_id)
    vectors = zscores(rows, keys)
    target = vectors[ids.index(target_id)]
    target_norm = math.sqrt(sum(x * x for x in target))
    results = []
    for player_id, vector in zip(ids, vectors):
        if player_id == target_id:
            continue
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0 or target_norm == 0:
            continue
        contributions = {k: (a * b) / (norm * target_norm) for k, a, b in zip(keys, target, vector)}
        results.append(
            {
                "player_id": player_id,
                "similarity": round(sum(contributions.values()), 4),
                "contributions": {k: round(v, 4) for k, v in contributions.items()},
            }
        )
    results.sort(key=lambda r: (-r["similarity"], r["player_id"]))  # type: ignore[operator]
    return results[:top_n]


def linear_trend(points: Iterable[tuple[datetime, float]]) -> dict[str, float] | None:
    """Least-squares slope per 30 days and the change across the window."""
    series = [(t, v) for t, v in points if v is not None and not math.isnan(v)]
    if len(series) < 3:
        return None
    t0 = series[0][0]
    xs = [(t - t0).total_seconds() / 86400 for t, _ in series]
    ys = [v for _, v in series]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx
    return {"slope_per_30d": slope * 30, "change": ys[-1] - ys[0], "span_days": xs[-1]}


def trend_label(trend: dict[str, float] | None, threshold: float, higher_is_better: bool) -> str:
    """Classify a trend as improving, declining or steady.

    ``threshold`` is the smallest change across the window that is treated
    as meaningful for this metric (e.g. 0.030 OPS).
    """
    if trend is None:
        return "insufficient"
    change = trend["change"]
    if abs(change) < threshold:
        return "steady"
    improving = change > 0 if higher_is_better else change < 0
    return "improving" if improving else "declining"
