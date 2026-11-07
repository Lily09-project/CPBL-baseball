import pytest

from src.analytics.narrative import scouting_notes
from src.analytics.players import BATTER_METRICS, PITCHER_METRICS


@pytest.mark.parametrize("metrics,key,raw,post,expected", [
    (BATTER_METRICS, "obp_post", 0.40, 0.30, "高估"),
    (BATTER_METRICS, "k_rate_post", 0.30, 0.20, "低估"),
    (PITCHER_METRICS, "bb_rate_post", 0.15, 0.08, "低估"),
    (PITCHER_METRICS, "bb_rate_post", 0.04, 0.08, "高估"),
])
def test_shrinkage_notes_respect_metric_direction(metrics, key, raw, post, expected):
    notes = scouting_notes("測試球員", metrics, {}, {key: (raw, post)}, "insufficient", key, None, True)
    assert len(notes) == 1
    assert expected in notes[0]["text"]
    assert notes[0]["evidence"] == [key]
