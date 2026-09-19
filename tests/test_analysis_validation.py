from __future__ import annotations

import pandas as pd
import pytest

from src.analysis_validation import (
    build_analysis_validation_report,
    priority_sensitivity,
    rank_stability,
    summarize_data_drift,
)


def _history() -> pd.DataFrame:
    rows = []
    snapshots = [
        ("s1", "2026-08-01T00:00:00+00:00", {"p1": 0.900, "p2": 0.850, "p3": 0.700}),
        ("s2", "2026-08-02T00:00:00+00:00", {"p1": 0.880, "p2": 0.860, "p3": 0.710}),
        ("s3", "2026-08-03T00:00:00+00:00", {"p1": 0.910, "p2": 0.870, "p3": 0.690}),
    ]
    for snapshot_id, captured_at, values in snapshots:
        for player_id, ops in values.items():
            rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "captured_at": captured_at,
                    "player_id": player_id,
                    "player_name": f"球員 {player_id}",
                    "team": "測試隊",
                    "player_type": "打者",
                    "ops": ops,
                    "obp": ops - 0.100,
                    "slg": ops - 0.200,
                    "player_value_score": ops * 100,
                }
            )
    return pd.DataFrame(rows)


def _scouting_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player_id": "p1", "player_name": "甲", "team": "A", "pa": 100, "contact_score": 90, "discipline_score": 60},
            {"player_id": "p2", "player_name": "乙", "team": "A", "pa": 100, "contact_score": 70, "discipline_score": 80},
            {"player_id": "p3", "player_name": "丙", "team": "B", "pa": 100, "contact_score": 50, "discipline_score": 50},
        ]
    )


def test_rank_stability_reports_adjacent_versions_and_top_k_overlap() -> None:
    result = rank_stability(_history(), "打者", "ops", top_k=2)

    assert len(result) == 2
    assert set(result["baseline_snapshot_id"]) == {"s1", "s2"}
    assert result.iloc[0]["top_k_overlap"] == 1.0
    assert result.iloc[1]["spearman_rank_correlation"] == 1.0


def test_rank_stability_rejects_duplicate_player_in_snapshot() -> None:
    history = pd.concat([_history(), _history().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="重複 player_id"):
        rank_stability(history, "打者", "ops")


def test_data_drift_is_descriptive_and_preserves_coverage_metrics() -> None:
    result = summarize_data_drift(_history(), "打者", ["ops"])

    assert len(result) == 2
    assert set(result["direction"]) == {"up"}
    assert result["baseline_count"].tolist() == [3, 3]
    assert result["current_count"].tolist() == [3, 3]


def test_priority_sensitivity_compares_weight_perturbations() -> None:
    result = priority_sensitivity(
        _scouting_frame(),
        "打者",
        threshold=30,
        priority="接觸與選球",
        perturbation=0.10,
        top_k=2,
    )

    assert set(result["scenario"]) == {"baseline", "increase", "decrease"}
    assert result["candidate_count"].eq(3).all()
    assert result["weights"].map(lambda value: sum(__import__("json").loads(value).values())).round(6).eq(1).all()


def test_analysis_validation_report_is_public_summary_only() -> None:
    report = build_analysis_validation_report(_history(), generated_at="2026-08-03T00:00:00+00:00")

    assert report["schema_version"] == "1.0"
    assert report["snapshot_count"] == 3
    assert report["latest_snapshot_id"] == "s3"
    assert report["player_types"]["打者"]["stability"]["ops"]["comparison_count"] == 2
    assert report["limitations"]
