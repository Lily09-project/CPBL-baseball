"""Template-based scouting notes where every sentence cites its evidence.

No language model is involved: each sentence is chosen by explicit rules
from the player's numbers, and carries the metric keys that justify it, so
the interface can highlight the supporting data next to the text.
"""
from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

from src.analytics.players import Metric

STRONG_PERCENTILE = 80.0
WEAK_PERCENTILE = 20.0
SMALL_SAMPLE_GAP = 0.025

TREND_TEXT = {
    "improving": "近期快照呈上升趨勢",
    "declining": "近期快照呈下滑趨勢",
    "steady": "近期快照表現穩定",
}

_PLACEHOLDER = re.compile(r"\{[^}]*\}")


def _pct_text(percentile: float) -> str:
    return f"聯盟前 {max(1, round(100 - percentile))}%"


def _sentence(text: str, evidence: Sequence[str]) -> dict[str, object]:
    if _PLACEHOLDER.search(text):
        raise ValueError(f"unfilled template variable in: {text}")
    return {"text": text, "evidence": list(evidence)}


def scouting_notes(
    name: str,
    metrics: Sequence[Metric],
    percentiles: Mapping[str, float],
    shrinkage: Mapping[str, tuple[float | None, float]],
    trend: str,
    trend_metric: str,
    comparable_name: str | None,
    qualified: bool,
) -> list[dict[str, object]]:
    """Build 2–5 evidence-linked sentences describing a player.

    ``shrinkage`` maps a metric key to (raw rate, posterior mean) so the
    notes can warn when a small sample flatters or hides a player.
    """
    notes: list[dict[str, object]] = []
    labels = {m.key: m.label for m in metrics}
    shorts = {m.key: m.short for m in metrics}
    ranked = sorted(
        ((k, v) for k, v in percentiles.items() if k in labels and not math.isnan(v)),
        key=lambda kv: kv[1],
        reverse=True,
    )
    if not qualified:
        notes.append(_sentence(f"{name} 的樣本數尚未達到比較門檻，以下判讀以收縮後的估計為主。", ["trials"]))
    if ranked and ranked[0][1] >= STRONG_PERCENTILE:
        key, pct = ranked[0]
        notes.append(_sentence(f"最大強項是{labels[key]}，位居{_pct_text(pct)}。", [key]))
    elif ranked:
        key, pct = ranked[0]
        notes.append(_sentence(f"沒有突出的單項，相對最好的是{labels[key]}（第 {round(pct)} 百分位）。", [key]))
    if ranked and ranked[-1][1] <= WEAK_PERCENTILE and ranked[-1][0] != ranked[0][0]:
        key, pct = ranked[-1]
        notes.append(_sentence(f"需要留意的是{labels[key]}，只在第 {round(pct)} 百分位。", [key]))
    for key, (raw, post) in shrinkage.items():
        if raw is None or key not in labels:
            continue
        gap = raw - post
        if abs(gap) >= SMALL_SAMPLE_GAP:
            direction = "高估" if gap > 0 else "低估"
            notes.append(
                _sentence(
                    f"{shorts[key]}原始值 {raw:.3f} 可能{direction}了實力，收縮後估計為 {post:.3f}。",
                    [key],
                )
            )
            break
    if trend in TREND_TEXT:
        notes.append(_sentence(f"{TREND_TEXT[trend]}。", [trend_metric]))
    if comparable_name:
        notes.append(_sentence(f"數據輪廓最接近的球員是 {comparable_name}。", ["similar"]))
    return notes[:5]
