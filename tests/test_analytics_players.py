from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from src.analytics import narrative, players


def test_percentile_respects_direction_and_ties() -> None:
    population = [1.0, 2.0, 3.0, 4.0]
    assert players.percentile_of(4.0, population, True) == pytest.approx(87.5)
    assert players.percentile_of(1.0, population, False) == pytest.approx(87.5)
    assert math.isnan(players.percentile_of(float("nan"), population, True))
    assert math.isnan(players.percentile_of(1.0, [], True))


def test_similarity_excludes_self_sorted_and_contributions_sum() -> None:
    rows = [
        {"a": 1.0, "b": 2.0, "c": 0.5},
        {"a": 1.1, "b": 2.1, "c": 0.4},
        {"a": -1.0, "b": -2.0, "c": 3.0},
        {"a": 0.0, "b": 0.5, "c": 1.0},
    ]
    ids = ["p1", "p2", "p3", "p4"]
    result = players.explainable_similarity(rows, ids, ["a", "b", "c"], "p1", top_n=3)
    assert [r["player_id"] for r in result][0] == "p2"
    assert "p1" not in [r["player_id"] for r in result]
    sims = [r["similarity"] for r in result]
    assert sims == sorted(sims, reverse=True)
    for r in result:
        assert sum(r["contributions"].values()) == pytest.approx(r["similarity"], abs=1e-3)
    with pytest.raises(KeyError):
        players.explainable_similarity(rows, ids, ["a"], "missing")


def test_similarity_skips_zero_vectors() -> None:
    # p2 sits exactly on the mean, so its standardised vector is zero.
    rows = [{"a": 1.0}, {"a": 2.0}, {"a": 3.0}]
    assert players.explainable_similarity(rows, ["p1", "p2", "p3"], ["a"], "p2") == []


def test_linear_trend_and_labels() -> None:
    start = datetime(2026, 8, 1)
    falling = [(start + timedelta(days=7 * i), 0.80 - 0.02 * i) for i in range(6)]
    trend = players.linear_trend(falling)
    assert trend is not None and trend["change"] == pytest.approx(-0.10)
    assert players.trend_label(trend, 0.03, higher_is_better=True) == "declining"
    assert players.trend_label(trend, 0.03, higher_is_better=False) == "improving"
    assert players.trend_label(trend, 0.5, higher_is_better=True) == "steady"
    assert players.linear_trend(falling[:2]) is None
    assert players.trend_label(None, 0.03, True) == "insufficient"
    same_day = [(start, 0.5), (start, 0.6), (start, 0.7)]
    assert players.linear_trend(same_day) is None


def _notes(**overrides: object) -> list[dict[str, object]]:
    kwargs: dict[str, object] = dict(
        name="測試球員",
        metrics=players.BATTER_METRICS,
        percentiles={"obp_post": 92.0, "iso": 50.0, "hr_rate_post": 40.0, "bb_rate_post": 60.0, "k_rate_post": 10.0, "speed": 55.0},
        shrinkage={"obp_post": (0.420, 0.360)},
        trend="declining",
        trend_metric="ops",
        comparable_name="另一位球員",
        qualified=True,
    )
    kwargs.update(overrides)
    return narrative.scouting_notes(**kwargs)  # type: ignore[arg-type]


def test_notes_cite_evidence_and_fill_every_variable() -> None:
    notes = _notes()
    assert 2 <= len(notes) <= 5
    for note in notes:
        assert note["evidence"], note
        assert "{" not in note["text"] and "}" not in note["text"]
    texts = " ".join(n["text"] for n in notes)
    assert "上壘能力" in texts and "前 8%" in texts
    assert "三振控制" in texts
    assert "可能高估" in texts
    assert "下滑" in texts
    assert "另一位球員" in texts


def test_notes_for_unqualified_and_average_players() -> None:
    notes = _notes(
        qualified=False,
        percentiles={"obp_post": 55.0, "iso": 50.0},
        shrinkage={"obp_post": (0.300, 0.310)},
        trend="insufficient",
        comparable_name=None,
    )
    assert notes[0]["evidence"] == ["trials"]
    assert "沒有突出的單項" in notes[1]["text"]
    assert len(notes) == 2


def test_notes_skip_missing_raw_and_report_underestimates() -> None:
    texts = [n["text"] for n in _notes(shrinkage={"iso": (None, 0.1), "obp_post": (0.200, 0.300)})]
    assert any("低估" in t for t in texts)


def test_sentence_guard_rejects_unfilled_templates() -> None:
    with pytest.raises(ValueError):
        narrative._sentence("{name} 很強", ["x"])
