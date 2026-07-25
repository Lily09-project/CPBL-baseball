from src.log5_matchup import calculate_log5_probability


def test_log5_probability_range():
    prob = calculate_log5_probability(0.35, 0.32, 0.33)
    assert prob is not None
    assert 0 <= prob <= 1


def test_log5_invalid_league_rate_returns_none():
    assert calculate_log5_probability(0.35, 0.32, 1.0) is None
    assert calculate_log5_probability(None, 0.32, 0.33) is None
