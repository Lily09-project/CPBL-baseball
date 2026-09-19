from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.history import LOWER_IS_BETTER_BY_TYPE
from src.scouting import (
    PRIORITY_WEIGHTS,
    qualified_population,
    qualification_column,
)


ANALYSIS_VALIDATION_SCHEMA_VERSION = "1.0"
STABILITY_METRICS = {
    "打者": ("ops", "obp", "slg", "player_value_score"),
    "投手": ("era", "whip", "k_bb_ratio", "player_value_score"),
}
DRIFT_METRICS = {
    "打者": ("ops", "obp", "slg", "iso", "bb_rate", "k_rate"),
    "投手": ("era", "whip", "k_bb_ratio", "hr_allowed_rate", "bb_rate"),
}
HISTORY_REQUIRED_COLUMNS = {
    "snapshot_id",
    "captured_at",
    "player_id",
    "player_name",
    "team",
    "player_type",
}


def _clean_number(value: Any, digits: int = 4) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _ordered_history(history: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(HISTORY_REQUIRED_COLUMNS - set(history.columns))
    if missing:
        raise ValueError(f"歷史資料缺少欄位：{missing}")
    if history.empty:
        return history.copy()

    out = history.copy()
    for column in ("snapshot_id", "player_id", "player_type"):
        out[column] = out[column].astype("string")
    out["captured_at"] = out["captured_at"].astype("string")
    out["_captured_at"] = pd.to_datetime(out["captured_at"], utc=True, errors="coerce")
    if out["_captured_at"].isna().any():
        raise ValueError("歷史資料包含無法解析的 captured_at")
    duplicate_keys = ["snapshot_id", "player_type", "player_id"]
    if out.duplicated(duplicate_keys).any():
        raise ValueError("同一快照內存在重複 player_id，無法進行穩定性分析")
    return out.sort_values(
        ["_captured_at", "snapshot_id", "player_type", "player_id"],
        kind="stable",
    ).reset_index(drop=True)


def _snapshot_pairs(history: pd.DataFrame) -> list[tuple[pd.Series, pd.Series]]:
    snapshots = (
        history[["snapshot_id", "captured_at", "_captured_at"]]
        .drop_duplicates("snapshot_id")
        .sort_values(["_captured_at", "snapshot_id"], kind="stable")
        .reset_index(drop=True)
    )
    return [
        (snapshots.iloc[index], snapshots.iloc[index + 1])
        for index in range(max(0, len(snapshots) - 1))
    ]


def _rank_values(frame: pd.DataFrame, metric: str, lower_is_better: bool) -> pd.Series:
    values = pd.to_numeric(frame[metric], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return pd.Series(dtype=float)
    return valid.rank(method="average", ascending=not lower_is_better)


def _top_ids(frame: pd.DataFrame, metric: str, top_k: int, lower_is_better: bool) -> list[str]:
    values = pd.to_numeric(frame[metric], errors="coerce")
    ranked = frame.assign(_metric=values).dropna(subset=["_metric"])
    ranked = ranked.sort_values(
        ["_metric", "player_id"],
        ascending=[lower_is_better, True],
        kind="stable",
    )
    return ranked["player_id"].astype(str).head(top_k).tolist()


def rank_stability(
    history: pd.DataFrame,
    player_type: str,
    metric: str,
    *,
    top_k: int = 10,
) -> pd.DataFrame:
    """Compare adjacent snapshot rankings without treating change as an error."""
    if player_type not in STABILITY_METRICS:
        raise ValueError(f"不支援的球員類型：{player_type}")
    if top_k < 1:
        raise ValueError("top_k 必須大於 0")
    ordered = _ordered_history(history)
    if metric not in ordered.columns:
        raise ValueError(f"歷史資料缺少指標欄位：{metric}")

    population = ordered.loc[ordered["player_type"] == player_type].copy()
    lower_is_better = metric in LOWER_IS_BETTER_BY_TYPE.get(player_type, set())
    rows: list[dict[str, Any]] = []
    for previous, current in _snapshot_pairs(ordered):
        previous_frame = population.loc[population["snapshot_id"] == previous["snapshot_id"]]
        current_frame = population.loc[population["snapshot_id"] == current["snapshot_id"]]
        previous_ranks = _rank_values(previous_frame.set_index("player_id"), metric, lower_is_better)
        current_ranks = _rank_values(current_frame.set_index("player_id"), metric, lower_is_better)
        previous_top = _top_ids(previous_frame, metric, top_k, lower_is_better)
        current_top = _top_ids(current_frame, metric, top_k, lower_is_better)
        effective_top_k = min(top_k, len(previous_top), len(current_top))
        overlap_count = len(set(previous_top[:effective_top_k]) & set(current_top[:effective_top_k]))
        common_ids = previous_ranks.index.intersection(current_ranks.index)
        if len(common_ids) >= 2:
            correlation = previous_ranks.loc[common_ids].corr(current_ranks.loc[common_ids])
            mean_rank_delta = (current_ranks.loc[common_ids] - previous_ranks.loc[common_ids]).abs().mean()
        else:
            correlation = None
            mean_rank_delta = None
        rows.append(
            {
                "player_type": player_type,
                "metric": metric,
                "baseline_snapshot_id": str(previous["snapshot_id"]),
                "current_snapshot_id": str(current["snapshot_id"]),
                "baseline_captured_at": str(previous["captured_at"]),
                "current_captured_at": str(current["captured_at"]),
                "baseline_population": int(previous_ranks.size),
                "current_population": int(current_ranks.size),
                "common_population": int(len(common_ids)),
                "top_k": int(effective_top_k),
                "top_k_overlap_count": int(overlap_count),
                "top_k_overlap": _clean_number(
                    overlap_count / effective_top_k if effective_top_k else None
                ),
                "spearman_rank_correlation": _clean_number(correlation),
                "mean_abs_rank_delta": _clean_number(mean_rank_delta),
            }
        )
    return pd.DataFrame(rows)


def summarize_data_drift(
    history: pd.DataFrame,
    player_type: str,
    metrics: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Return descriptive adjacent-version distribution changes for review."""
    if player_type not in DRIFT_METRICS:
        raise ValueError(f"不支援的球員類型：{player_type}")
    ordered = _ordered_history(history)
    population = ordered.loc[ordered["player_type"] == player_type].copy()
    selected_metrics = list(metrics or DRIFT_METRICS[player_type])
    unsupported = sorted(set(selected_metrics) - set(DRIFT_METRICS[player_type]))
    if unsupported:
        raise ValueError(f"不支援的漂移指標：{unsupported}")

    rows: list[dict[str, Any]] = []
    for previous, current in _snapshot_pairs(ordered):
        previous_frame = population.loc[population["snapshot_id"] == previous["snapshot_id"]]
        current_frame = population.loc[population["snapshot_id"] == current["snapshot_id"]]
        for metric in selected_metrics:
            if metric not in population.columns:
                continue
            previous_values = pd.to_numeric(previous_frame[metric], errors="coerce").dropna()
            current_values = pd.to_numeric(current_frame[metric], errors="coerce").dropna()
            previous_median = previous_values.median() if not previous_values.empty else None
            current_median = current_values.median() if not current_values.empty else None
            previous_mean = previous_values.mean() if not previous_values.empty else None
            current_mean = current_values.mean() if not current_values.empty else None
            previous_q1 = previous_values.quantile(0.25) if not previous_values.empty else None
            current_q1 = current_values.quantile(0.25) if not current_values.empty else None
            previous_q3 = previous_values.quantile(0.75) if not previous_values.empty else None
            current_q3 = current_values.quantile(0.75) if not current_values.empty else None
            median_delta = (
                current_median - previous_median
                if previous_median is not None and current_median is not None
                else None
            )
            if median_delta is None or np.isclose(float(median_delta), 0.0, atol=1e-12):
                direction = "stable"
            elif float(median_delta) > 0:
                direction = "up"
            else:
                direction = "down"
            previous_count = int(previous_values.size)
            current_count = int(current_values.size)
            coverage_change_pct = (
                (current_count - previous_count) / previous_count * 100
                if previous_count
                else None
            )
            rows.append(
                {
                    "player_type": player_type,
                    "metric": metric,
                    "baseline_snapshot_id": str(previous["snapshot_id"]),
                    "current_snapshot_id": str(current["snapshot_id"]),
                    "baseline_captured_at": str(previous["captured_at"]),
                    "current_captured_at": str(current["captured_at"]),
                    "baseline_count": previous_count,
                    "current_count": current_count,
                    "coverage_change_pct": _clean_number(coverage_change_pct),
                    "baseline_median": _clean_number(previous_median),
                    "current_median": _clean_number(current_median),
                    "median_delta": _clean_number(median_delta),
                    "baseline_mean": _clean_number(previous_mean),
                    "current_mean": _clean_number(current_mean),
                    "baseline_q1": _clean_number(previous_q1),
                    "current_q1": _clean_number(current_q1),
                    "baseline_q3": _clean_number(previous_q3),
                    "current_q3": _clean_number(current_q3),
                    "direction": direction,
                }
            )
    return pd.DataFrame(rows)


def _weighted_score(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    if df.empty or any(column not in df.columns for column in weights):
        return pd.Series(index=df.index, dtype=float)
    score = pd.Series(0.0, index=df.index, dtype=float)
    for column, weight in weights.items():
        score = score + pd.to_numeric(df[column], errors="coerce") * float(weight)
    return score


def _rank_with_weights(
    df: pd.DataFrame,
    player_type: str,
    threshold: float,
    weights: dict[str, float],
    team: str,
) -> pd.DataFrame:
    population = qualified_population(df, player_type, threshold)
    if population.empty:
        return population
    population = population.copy()
    population["priority_score"] = _weighted_score(population, weights)
    population = population.dropna(subset=["priority_score"])
    if team != "全部":
        population = population.loc[population["team"] == team]
    return population.sort_values(
        ["priority_score", "player_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def _perturbed_weights(weights: dict[str, float], metric: str, delta: float) -> dict[str, float]:
    adjusted = {name: max(0.0, float(value)) for name, value in weights.items()}
    adjusted[metric] = min(1.0, max(0.0, adjusted[metric] + delta))
    other_metrics = [name for name in adjusted if name != metric]
    remaining = max(0.0, 1.0 - adjusted[metric])
    other_total = sum(max(0.0, float(weights[name])) for name in other_metrics)
    if other_total:
        for name in other_metrics:
            adjusted[name] = remaining * max(0.0, float(weights[name])) / other_total
    else:
        for name in other_metrics:
            adjusted[name] = 0.0
    normalizer = sum(adjusted.values())
    if normalizer:
        adjusted = {name: value / normalizer for name, value in adjusted.items()}
    return adjusted


def _rank_correlation(baseline: pd.DataFrame, scenario: pd.DataFrame) -> float | None:
    baseline_positions = pd.Series(
        range(1, len(baseline) + 1), index=baseline["player_id"].astype(str)
    )
    scenario_positions = pd.Series(
        range(1, len(scenario) + 1), index=scenario["player_id"].astype(str)
    )
    common = baseline_positions.index.intersection(scenario_positions.index)
    if len(common) < 2:
        return None
    return _clean_number(baseline_positions.loc[common].corr(scenario_positions.loc[common]))


def priority_sensitivity(
    df: pd.DataFrame,
    player_type: str,
    threshold: float,
    priority: str,
    *,
    team: str = "全部",
    perturbation: float = 0.10,
    top_k: int = 10,
) -> pd.DataFrame:
    """Measure how much the ranked list changes after small weight shifts."""
    if player_type not in PRIORITY_WEIGHTS:
        raise ValueError(f"不支援的球員類型：{player_type}")
    if priority not in PRIORITY_WEIGHTS[player_type]:
        raise ValueError(f"{player_type} 不支援評估重點：{priority}")
    if not 0 <= float(perturbation) < 1:
        raise ValueError("perturbation 必須介於 0（含）與 1（不含）之間")
    if top_k < 1:
        raise ValueError("top_k 必須大於 0")
    qualification_column(player_type)
    base_weights = {
        key: float(value) for key, value in PRIORITY_WEIGHTS[player_type][priority].items()
    }
    baseline = _rank_with_weights(df, player_type, threshold, base_weights, team)
    scenarios: list[tuple[str, str | None, float, dict[str, float]]] = [
        ("baseline", None, 0.0, base_weights)
    ]
    if len(base_weights) > 1 and perturbation:
        for metric in base_weights:
            scenarios.append(("increase", metric, float(perturbation), _perturbed_weights(base_weights, metric, perturbation)))
            scenarios.append(("decrease", metric, -float(perturbation), _perturbed_weights(base_weights, metric, -perturbation)))

    rows: list[dict[str, Any]] = []
    baseline_top = baseline["player_id"].astype(str).head(top_k).tolist() if not baseline.empty else []
    for scenario_name, changed_metric, weight_delta, weights in scenarios:
        ranked = baseline if scenario_name == "baseline" else _rank_with_weights(
            df, player_type, threshold, weights, team
        )
        scenario_top = ranked["player_id"].astype(str).head(top_k).tolist() if not ranked.empty else []
        effective_top_k = min(top_k, len(baseline_top), len(scenario_top))
        overlap = (
            len(set(baseline_top[:effective_top_k]) & set(scenario_top[:effective_top_k])) / effective_top_k
            if effective_top_k
            else None
        )
        row_by_id = ranked.set_index(ranked["player_id"].astype(str)) if not ranked.empty else ranked
        top_name = None
        if scenario_top and not row_by_id.empty and scenario_top[0] in row_by_id.index:
            top_name = str(row_by_id.loc[scenario_top[0], "player_name"])
        baseline_name = None
        if baseline_top and not baseline.empty:
            baseline_name = str(baseline.iloc[0]["player_name"])
        rows.append(
            {
                "player_type": player_type,
                "priority": priority,
                "team": team,
                "scenario": scenario_name,
                "changed_metric": changed_metric or "—",
                "weight_delta": _clean_number(weight_delta, 3),
                "weights": json.dumps(weights, ensure_ascii=False, sort_keys=True),
                "candidate_count": int(len(ranked)),
                "top_k": int(effective_top_k),
                "top_k_overlap": _clean_number(overlap),
                "rank_correlation": _rank_correlation(baseline, ranked),
                "baseline_leader": baseline_name or "—",
                "scenario_leader": top_name or "—",
            }
        )
    return pd.DataFrame(rows)


def build_analysis_validation_report(
    history: pd.DataFrame,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ordered = _ordered_history(history)
    snapshots = ordered["snapshot_id"].drop_duplicates().tolist() if not ordered.empty else []
    generated = generated_at or datetime.now(timezone.utc).isoformat()
    player_types: dict[str, Any] = {}
    for player_type, metrics in STABILITY_METRICS.items():
        stability_summary: dict[str, Any] = {}
        for metric in metrics:
            if metric not in ordered.columns:
                continue
            table = rank_stability(ordered, player_type, metric, top_k=10)
            latest = table.iloc[-1].to_dict() if not table.empty else {}
            stability_summary[metric] = {
                "comparison_count": int(len(table)),
                "latest_top_k_overlap": _clean_number(latest.get("top_k_overlap")),
                "latest_spearman_rank_correlation": _clean_number(
                    latest.get("spearman_rank_correlation")
                ),
            }
        drift = summarize_data_drift(ordered, player_type)
        latest_drift = drift.tail(len(DRIFT_METRICS[player_type])) if not drift.empty else drift
        player_types[player_type] = {
            "history_rows": int((ordered["player_type"] == player_type).sum()),
            "player_count": int(ordered.loc[ordered["player_type"] == player_type, "player_id"].nunique()),
            "stability": stability_summary,
            "latest_drift_rows": int(len(latest_drift)),
        }
    latest_snapshot_id = str(snapshots[-1]) if snapshots else None
    return {
        "schema_version": ANALYSIS_VALIDATION_SCHEMA_VERSION,
        "generated_at": generated,
        "snapshot_count": int(len(snapshots)),
        "history_rows": int(len(ordered)),
        "latest_snapshot_id": latest_snapshot_id,
        "player_types": player_types,
        "interpretation": {
            "rank_stability": "Spearman ρ 與 Top-K 重疊率描述相鄰資料快照的一致程度，不是準確率。",
            "distribution_drift": "中位數、平均數與涵蓋量描述資料分布變化，不會單獨判定資料錯誤。",
            "priority_sensitivity": "權重敏感度只評估排序對小幅權重調整的反應，不代表未來表現。",
        },
        "limitations": [
            "歷史快照是官方彙總資料，不是逐球、逐打席或完整追蹤資料。",
            "排名穩定性受球員出賽量、名單變動與官方頁面更新節奏影響。",
            "敏感度分析是描述性壓力測試，不能取代球探、教練或醫療判斷。",
        ],
    }


def write_analysis_validation_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
