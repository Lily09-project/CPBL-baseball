import pandas as pd

from src.preprocess import build_player_summary


def roster_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season": 2026,
                "player_id": "0000000001",
                "player_name": "野手登板",
                "team": "測試隊",
                "roster_status": "現役",
                "profile_url": "",
                "source_note": "CPBL 官方球員點將錄",
            },
            {
                "season": 2026,
                "player_id": "0000000002",
                "player_name": "投手打擊",
                "team": "測試隊",
                "roster_status": "現役",
                "profile_url": "",
                "source_note": "CPBL 官方球員點將錄",
            },
        ]
    )


def test_build_player_summary_uses_primary_workload_for_two_way_records() -> None:
    batters = pd.DataFrame(
        [
            {"player_id": "0000000001", "position": "野手", "pa": 40, "player_value_score": 70.0},
            {"player_id": "0000000002", "position": "野手", "pa": 1, "player_value_score": 20.0},
        ]
    )
    pitchers = pd.DataFrame(
        [
            {"player_id": "0000000001", "role": "投手", "innings_pitched": 1.0, "player_value_score": 30.0},
            {"player_id": "0000000002", "role": "投手", "innings_pitched": 30.0, "player_value_score": 80.0},
        ]
    )

    players = build_player_summary(roster_fixture(), batters, pitchers).set_index("player_id")

    assert players.loc["0000000001", "player_type"] == "打者"
    assert players.loc["0000000001", "role_or_position"] == "野手"
    assert players.loc["0000000001", "player_value_score"] == 70.0
    assert players.loc["0000000002", "player_type"] == "投手"
    assert players.loc["0000000002", "role_or_position"] == "投手"
    assert players.loc["0000000002", "player_value_score"] == 80.0


def test_build_player_summary_does_not_expose_internal_workload_columns() -> None:
    batters = pd.DataFrame(
        [{"player_id": "0000000001", "position": "野手", "pa": 10, "player_value_score": 60.0}]
    )
    pitchers = pd.DataFrame(
        [{"player_id": "0000000001", "role": "投手", "innings_pitched": 1.0, "player_value_score": 50.0}]
    )

    players = build_player_summary(roster_fixture().head(1), batters, pitchers)

    assert all(not column.startswith(("hitter_", "pitcher_")) for column in players.columns)

def test_published_player_summary_matches_primary_workload_rule() -> None:
    batters = pd.read_csv("data/processed/batters_scored.csv", dtype={"player_id": "string"})
    pitchers = pd.read_csv("data/processed/pitchers_scored.csv", dtype={"player_id": "string"})
    players = pd.read_csv("data/processed/players_scored.csv", dtype={"player_id": "string"})
    dual = batters[["player_id", "pa"]].merge(
        pitchers[["player_id", "innings_pitched"]], on="player_id", how="inner"
    )
    dual["expected_type"] = dual.apply(
        lambda row: "投手" if row["innings_pitched"] * 4.25 > row["pa"] else "打者",
        axis=1,
    )
    published = dual.merge(players[["player_id", "player_type"]], on="player_id", how="left")

    assert not published.empty
    assert published["player_type"].notna().all()
    assert (published["player_type"] == published["expected_type"]).all()
