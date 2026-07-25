from __future__ import annotations

import math


def _valid_rate(value: float | int | None) -> bool:
    if value is None:
        return False
    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def calculate_log5_probability(hitter_rate: float, pitcher_allowed_rate: float, league_rate: float) -> float | None:
    """Bill James LOG5 style probability for a simplified hitter-vs-pitcher rate."""
    if not all(_valid_rate(v) for v in [hitter_rate, pitcher_allowed_rate, league_rate]):
        return None
    h = min(max(float(hitter_rate), 0.0), 1.0)
    p = min(max(float(pitcher_allowed_rate), 0.0), 1.0)
    l = float(league_rate)
    if l <= 0 or l >= 1:
        return None
    numerator = h * p / l
    denominator = numerator + ((1 - h) * (1 - p) / (1 - l))
    if denominator == 0:
        return None
    return round(min(max(numerator / denominator, 0.0), 1.0), 4)


def summarize_matchup_probability(probability: float | None) -> str:
    if probability is None:
        return "資料不足，無法產生模擬對戰。"
    if probability >= 0.58:
        return "打者在此簡化模型中略占優勢，但結果只供資料展示。"
    if probability <= 0.42:
        return "投手在此簡化模型中略占優勢，但不代表實際比賽預測。"
    return "雙方模型估計接近五五波，適合作為觀賽輔助參考。"
