import pandas as pd

from src.data_quality import generate_data_quality_report
from src.preprocess import build_player_summary


def test_data_quality_report_fails_when_official_outputs_are_missing(monkeypatch, tmp_path):
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "reports" / "metrics").mkdir(parents=True)
    monkeypatch.setattr("src.data_quality.project_path", lambda *parts: tmp_path.joinpath(*parts))

    report = generate_data_quality_report(mode="api", fallback_reason="test")

    assert report["quality_status"] == "failed"
    assert "generated_at" in report
    assert any("is missing" in warning for warning in report["warnings"])


def test_build_player_summary_keeps_complete_roster_and_pitcher_scores():
    roster = pd.DataFrame(
        [
            {"season": 2026, "player_id": "A01", "player_name": "打者甲", "team": "測試隊", "roster_status": "現役", "profile_url": "", "source_note": "官方"},
            {"season": 2026, "player_id": "P01", "player_name": "投手乙", "team": "測試隊", "roster_status": "現役", "profile_url": "", "source_note": "官方"},
            {"season": 2026, "player_id": "R01", "player_name": "名單丙", "team": "測試隊", "roster_status": "現役", "profile_url": "", "source_note": "官方"},
        ]
    )
    batters = pd.DataFrame(
        [
            {
                "player_id": "A01",
                "season": 2026,
                "player_name": "打者甲",
                "team": "測試隊",
                "position": "內野手",
                "player_value_score": 70.0,
                "source_note": "CPBL 官方全記錄查詢",
            },
            {
                "player_id": "BAT9999",
                "season": 2026,
                "player_name": "成績表丁",
                "team": "測試隊",
                "position": "外野手",
                "player_value_score": 66.0,
                "source_note": "CPBL 官方全記錄查詢",
            }
        ]
    )
    pitchers = pd.DataFrame(
        [
            {
                "player_id": "P01",
                "season": 2026,
                "player_name": "投手乙",
                "team": "測試隊",
                "role": "先發投手",
                "player_value_score": 90.0,
            }
        ]
    )

    summary = build_player_summary(roster, batters, pitchers)

    assert len(summary) == 4
    pitcher = summary[summary["player_id"] == "P01"].iloc[0]
    roster_only = summary[summary["player_id"] == "R01"].iloc[0]
    stat_only = summary[summary["player_id"] == "BAT9999"].iloc[0]
    assert pitcher["player_type"] == "投手"
    assert pitcher["role_or_position"] == "先發投手"
    assert pitcher["player_value_score"] == 90.0
    assert roster_only["player_type"] == "名單"
    assert roster_only["role_or_position"] == "官方現役名單"
    assert stat_only["player_type"] == "打者"
    assert stat_only["role_or_position"] == "外野手"
    assert stat_only["roster_status"] == "官方成績表"
    assert stat_only["source_note"] == "CPBL 官方全記錄查詢"
    assert not any(col.endswith("_x") or col.endswith("_y") for col in summary.columns)
    assert not {"recent_hot_score", "news_heat_score", "under_the_radar_score"}.intersection(summary.columns)


def test_data_quality_uses_complete_official_output_set(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (tmp_path / "reports" / "metrics").mkdir(parents=True)

    pd.DataFrame([{"season": 2026, "team": "測試隊", "wins": 1, "losses": 0, "win_pct": 1.0}]).to_csv(processed / "teams.csv", index=False)
    pd.DataFrame(
        [
            {"season": 2026, "player_id": "A01", "player_name": "打者甲", "team": "測試隊"},
            {"season": 2026, "player_id": "P01", "player_name": "投手乙", "team": "測試隊"},
            {"season": 2026, "player_id": "R01", "player_name": "名單丙", "team": "測試隊"},
        ]
    ).to_csv(processed / "roster.csv", index=False)
    pd.DataFrame([{"season": 2026, "player_id": "A01", "player_name": "打者甲", "team": "測試隊", "obp": 0.3, "slg": 0.4, "ops": 0.7}]).to_csv(processed / "batters_scored.csv", index=False)
    pd.DataFrame([{"season": 2026, "player_id": "P01", "player_name": "投手乙", "team": "測試隊", "era": 3.0, "whip": 1.2, "k_bb_ratio": 2.0}]).to_csv(processed / "pitchers_scored.csv", index=False)
    pd.DataFrame([
        {"season": 2026, "player_id": "A01", "player_name": "打者甲", "team": "測試隊", "player_type": "打者", "player_value_score": 70.0},
        {"season": 2026, "player_id": "P01", "player_name": "投手乙", "team": "測試隊", "player_type": "投手", "player_value_score": 80.0},
        {"season": 2026, "player_id": "R01", "player_name": "名單丙", "team": "測試隊", "player_type": "名單", "player_value_score": 0.0},
        {"season": 2026, "player_id": "BAT9999", "player_name": "成績表丁", "team": "測試隊", "player_type": "打者", "player_value_score": 66.0},
    ]).to_csv(
        processed / "players_scored.csv", index=False
    )
    monkeypatch.setattr("src.data_quality.project_path", lambda *parts: tmp_path.joinpath(*parts))

    report = generate_data_quality_report(mode="api", fallback_reason="official")

    assert report["available_player_count"] == 4
    assert report["available_hitter_count"] == 1
    assert report["available_pitcher_count"] == 1
    assert report["official_roster_count"] == 3
    assert report["player_summary_count"] == 4
    assert report["quality_status"] == "warning"
    assert "generated_at" in report
    assert set(report["files"]) == {"teams.csv", "roster.csv", "batters_scored.csv", "pitchers_scored.csv", "players_scored.csv"}
    assert "optional_empty_files" not in report


def test_data_quality_fails_for_schema_duplicate_and_range_errors(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (tmp_path / "reports" / "metrics").mkdir(parents=True)
    pd.DataFrame([{"season": 2026, "team": "測試隊", "wins": 1, "losses": 0, "win_pct": 1.5}]).to_csv(
        processed / "teams.csv", index=False
    )
    pd.DataFrame([
        {"season": 2026, "player_id": "A01", "player_name": "甲", "team": "測試隊"},
        {"season": 2026, "player_id": "A01", "player_name": "甲", "team": "測試隊"},
    ]).to_csv(processed / "roster.csv", index=False)
    for name in ["batters_scored.csv", "pitchers_scored.csv", "players_scored.csv"]:
        pd.DataFrame([{"player_id": "A01"}]).to_csv(processed / name, index=False)
    monkeypatch.setattr("src.data_quality.project_path", lambda *parts: tmp_path.joinpath(*parts))

    report = generate_data_quality_report(mode="api", fallback_reason="test")

    assert report["quality_status"] == "failed"
    assert any("missing required columns" in warning for warning in report["warnings"])
    assert any("duplicate player_id" in warning for warning in report["warnings"])
    assert any("outside" in warning for warning in report["warnings"])


def test_official_player_summary_matches_roster_and_stats_union():
    base = "data/processed"
    roster = pd.read_csv(f"{base}/roster.csv", dtype={"player_id": "string"})
    batters = pd.read_csv(f"{base}/batters_scored.csv", dtype={"player_id": "string"})
    pitchers = pd.read_csv(f"{base}/pitchers_scored.csv", dtype={"player_id": "string"})
    players = pd.read_csv(f"{base}/players_scored.csv", dtype={"player_id": "string"})

    expected_ids = set(roster["player_id"]) | set(batters["player_id"]) | set(pitchers["player_id"])
    assert set(players["player_id"]) == expected_ids
    assert not players["player_id"].duplicated().any()
    assert players["source_note"].str.contains("CPBL 官方").all()
    assert players["player_value_score"].between(0, 100).all()
    forbidden_columns = {"recent_hot_score", "news_heat_score", "under_the_radar_score"}
    all_columns = set(players.columns) | set(batters.columns) | set(pitchers.columns)
    assert not forbidden_columns.intersection(all_columns)
