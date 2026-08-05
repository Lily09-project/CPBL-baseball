import pandas as pd
import pytest

from src.scouting import (
    DEFAULT_QUALIFICATION,
    build_evidence_signals,
    comparison_frame,
    percentile_rank,
    qualified_population,
    qualification_upper_bound,
    rank_scouting_candidates,
)


@pytest.fixture
def hitter_population() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player_id": "0000000001", "player_name": "A", "pa": 20, "obp": 0.400, "era": 4.0},
            {"player_id": "0000000002", "player_name": "B", "pa": 30, "obp": 0.350, "era": 3.0},
            {"player_id": "0000000003", "player_name": "C", "pa": 45, "obp": 0.300, "era": 2.0},
        ]
    )


def test_qualified_population_uses_hitter_pa_threshold(hitter_population: pd.DataFrame) -> None:
    qualified = qualified_population(hitter_population, "打者", 30)
    assert qualified["player_id"].tolist() == ["0000000002", "0000000003"]
    assert qualified["player_id"].dtype.name == "string"


def test_qualified_population_uses_pitcher_ip_threshold() -> None:
    pitchers = pd.DataFrame(
        [
            {"player_id": "0000000011", "innings_pitched": 9.2},
            {"player_id": "0000000012", "innings_pitched": 10.0},
        ]
    )
    qualified = qualified_population(pitchers, "投手", 10)
    assert qualified["player_id"].tolist() == ["0000000012"]


def test_qualification_upper_bound_falls_back_for_non_numeric_usage() -> None:
    pitcher_type = min(DEFAULT_QUALIFICATION, key=DEFAULT_QUALIFICATION.get)
    pitchers = pd.DataFrame({"innings_pitched": [None, "not-a-number"]})

    assert qualification_upper_bound(pitchers, pitcher_type) == DEFAULT_QUALIFICATION[pitcher_type]


def test_percentile_rank_handles_direction_ties_missing_values_and_singleton(hitter_population: pd.DataFrame) -> None:
    middle = hitter_population.iloc[1]
    assert percentile_rank(hitter_population, middle, "obp") == 66.7
    assert percentile_rank(hitter_population, middle, "era", lower_is_better=True) == 66.7
    assert percentile_rank(hitter_population, middle, "missing_metric") is None
    assert percentile_rank(hitter_population.iloc[[0]], hitter_population.iloc[0], "obp") == 100.0


def test_qualified_population_rejects_unknown_type_and_negative_threshold(hitter_population: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="球員類型"):
        qualified_population(hitter_population, "捕手", 30)
    with pytest.raises(ValueError, match="門檻"):
        qualified_population(hitter_population, "打者", -1)


@pytest.fixture
def scored_hitters() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": "0000000001",
                "player_name": "A",
                "team": "T1",
                "position": "外野手",
                "pa": 20,
                "obp": 0.400,
                "iso": 0.250,
                "k_rate": 0.400,
                "contact_score": 88.0,
                "power_score": 90.0,
                "discipline_score": 70.0,
                "hitter_value_score": 85.0,
                "player_value_score": 85.0,
            },
            {
                "player_id": "0000000002",
                "player_name": "B",
                "team": "T1",
                "position": "外野手",
                "pa": 40,
                "obp": 0.350,
                "iso": 0.200,
                "k_rate": 0.300,
                "contact_score": 72.0,
                "power_score": 75.0,
                "discipline_score": 80.0,
                "hitter_value_score": 77.0,
                "player_value_score": 77.0,
            },
            {
                "player_id": "0000000003",
                "player_name": "C",
                "team": "T2",
                "position": "內野手",
                "pa": 50,
                "obp": 0.300,
                "iso": 0.150,
                "k_rate": 0.200,
                "contact_score": 68.0,
                "power_score": 55.0,
                "discipline_score": 75.0,
                "hitter_value_score": 65.0,
                "player_value_score": 65.0,
            },
            {
                "player_id": "0000000004",
                "player_name": "D",
                "team": "T2",
                "position": "內野手",
                "pa": 60,
                "obp": 0.250,
                "iso": 0.100,
                "k_rate": 0.100,
                "contact_score": 55.0,
                "power_score": 40.0,
                "discipline_score": 60.0,
                "hitter_value_score": 50.0,
                "player_value_score": 50.0,
            },
        ]
    )


def test_hitter_evidence_is_bounded_numeric_and_marks_limited_sample(scored_hitters: pd.DataFrame) -> None:
    qualified = qualified_population(scored_hitters, "打者", 30)
    evidence = build_evidence_signals(scored_hitters.iloc[0], qualified, "打者", 30)
    assert len(evidence["strengths"]) <= 3
    assert len(evidence["risks"]) <= 2
    assert any("OBP 第" in text and "75" in text for text in evidence["strengths"])
    assert any("ISO 第" in text and "75" in text for text in evidence["strengths"])
    assert any("K% 有利百分位" in text and "25" in text for text in evidence["risks"])
    assert any("PA 20" in text and "30" in text for text in evidence["notes"])


def test_pitcher_evidence_uses_lower_is_better_percentiles() -> None:
    pitchers = pd.DataFrame(
        [
            {
                "player_id": "0000000101",
                "innings_pitched": 18.0,
                "era": 1.5,
                "whip": 0.90,
                "k_bb_ratio": 5.0,
                "hr_allowed_rate": 0.04,
            },
            {
                "player_id": "0000000102",
                "innings_pitched": 18.0,
                "era": 2.2,
                "whip": 1.10,
                "k_bb_ratio": 3.0,
                "hr_allowed_rate": 0.03,
            },
            {
                "player_id": "0000000103",
                "innings_pitched": 18.0,
                "era": 3.4,
                "whip": 1.30,
                "k_bb_ratio": 2.0,
                "hr_allowed_rate": 0.02,
            },
            {
                "player_id": "0000000104",
                "innings_pitched": 18.0,
                "era": 4.6,
                "whip": 1.50,
                "k_bb_ratio": 1.0,
                "hr_allowed_rate": 0.01,
            },
        ]
    )
    strength_evidence = build_evidence_signals(pitchers.iloc[0], pitchers, "投手", 10)
    risk_evidence = build_evidence_signals(pitchers.iloc[0], pitchers, "投手", 10)
    assert any("ERA 第" in text and "WHIP 第" in text for text in strength_evidence["strengths"])
    assert any("被 HR% 有利百分位" in text for text in risk_evidence["risks"])
    basis = next(note for note in strength_evidence["notes"] if note.startswith("百分位依據："))
    assert "ERA 有利百分位 100.0" in basis
    assert "WHIP 有利百分位 100.0" in basis
    assert "K/BB 有利百分位 100.0" in basis
    assert "被 HR% 有利百分位 25.0" in basis


def test_neutral_hitter_evidence_includes_numeric_percentile_basis() -> None:
    hitters = pd.DataFrame(
        [
            {"player_id": "0000000201", "pa": 40, "obp": 0.360, "iso": 0.220, "k_rate": 0.100},
            {"player_id": "0000000202", "pa": 40, "obp": 0.340, "iso": 0.180, "k_rate": 0.200},
            {"player_id": "0000000203", "pa": 40, "obp": 0.320, "iso": 0.140, "k_rate": 0.300},
            {"player_id": "0000000204", "pa": 40, "obp": 0.300, "iso": 0.100, "k_rate": 0.400},
        ]
    )

    evidence = build_evidence_signals(hitters.iloc[2], hitters, "打者", 30)

    assert evidence["strengths"] == []
    assert evidence["risks"] == []
    basis = next(note for note in evidence["notes"] if note.startswith("百分位依據："))
    assert "OBP 有利百分位 50.0" in basis
    assert "ISO 有利百分位 50.0" in basis
    assert "K% 有利百分位 50.0" in basis
    assert any("中性判讀" in note for note in evidence["notes"])


def test_missing_hitter_evidence_keeps_basis_and_coverage_note() -> None:
    hitters = pd.DataFrame(
        [
            {"player_id": "0000000301", "pa": 40, "obp": 0.340, "iso": 0.180},
            {"player_id": "0000000302", "pa": 40, "obp": 0.320, "iso": 0.140},
        ]
    )

    evidence = build_evidence_signals(hitters.iloc[0], hitters, "打者", 30)

    basis = next(note for note in evidence["notes"] if note.startswith("百分位依據："))
    assert "OBP 有利百分位 100.0" in basis
    assert "ISO 有利百分位 100.0" in basis
    assert "K% 有利百分位" not in basis
    assert any("資料涵蓋不足" in note and "K_RATE" in note for note in evidence["notes"])

def test_ranking_and_comparison_preserve_documented_order(scored_hitters: pd.DataFrame) -> None:
    ranked = rank_scouting_candidates(scored_hitters, "打者", 30, "長打")
    assert ranked["player_id"].tolist() == ["0000000002", "0000000003", "0000000004"]
    assert ranked["qualified_percentile"].between(0, 100).all()
    compared = comparison_frame(ranked, ["0000000003", "0000000002"], "打者")
    assert compared["player_id"].tolist() == ["0000000003", "0000000002"]
    assert compared.columns.tolist() == [
        "player_id",
        "player_name",
        "team",
        "pa",
        "priority_score",
        "qualified_percentile",
        "contact_score",
        "power_score",
        "discipline_score",
        "hitter_value_score",
    ]
