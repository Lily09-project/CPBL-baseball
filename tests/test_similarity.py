import pandas as pd

from src.similarity import find_similar_players


def test_find_similar_players_excludes_self():
    df = pd.DataFrame(
        [
            {
                "player_id": f"B{i}",
                "player_name": f"打者{i}",
                "team": "測試隊",
                "position": "野手",
                "ops": 0.70 + i * 0.03,
                "iso": 0.10 + i * 0.01,
                "bb_rate": 0.06 + i * 0.01,
                "k_rate": 0.20 - i * 0.01,
                "hr_rate": 0.02 + i * 0.005,
                "contact_score": 40 + i * 5,
                "power_score": 35 + i * 6,
                "discipline_score": 45 + i * 4,
                "player_value_score": 42 + i * 5,
            }
            for i in range(5)
        ]
    )
    target = "B0"
    result = find_similar_players(df, target, player_type="打者", n=5)
    assert not result.empty
    assert target not in set(result["player_id"])
