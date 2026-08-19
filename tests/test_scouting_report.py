import pandas as pd

from src.scouting_report import (
    REPORT_COLUMNS,
    build_watchlist_report,
    report_filename,
    report_markdown,
)


def sample_candidates() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": "0000000003",
                "player_name": "王三",
                "team": "測試隊",
                "position": "SS",
                "pa": 130,
                "priority_score": 82.4,
                "qualified_percentile": 100.0,
                "evidence_strengths": "上壘訊號",
                "evidence_risks": "無",
                "evidence_notes": "樣本足夠",
            },
            {
                "player_id": "0000000002",
                "player_name": "王二|外野",
                "team": "測試隊",
                "position": "OF",
                "pa": 90,
                "priority_score": 75.1,
                "qualified_percentile": 75.0,
                "evidence_strengths": "長打訊號",
                "evidence_risks": "K% 偏高",
                "evidence_notes": "需搭配完整成績",
            },
            {
                "player_id": "0000000001",
                "player_name": "王一",
                "team": "測試隊",
                "position": "1B",
                "pa": 50,
                "priority_score": 61.2,
                "qualified_percentile": 50.0,
                "evidence_strengths": "無",
                "evidence_risks": "無",
                "evidence_notes": "中性判讀",
            },
            {
                "player_id": "0000000004",
                "player_name": "王四",
                "team": "測試隊",
                "position": "C",
                "pa": 35,
                "priority_score": 45.0,
                "qualified_percentile": 25.0,
                "evidence_strengths": "無",
                "evidence_risks": "樣本風險",
                "evidence_notes": "資料限制",
            },
            {
                "player_id": "0000000005",
                "player_name": "王五",
                "team": "測試隊",
                "position": "2B",
                "pa": 31,
                "priority_score": 40.0,
                "qualified_percentile": 10.0,
                "evidence_strengths": "無",
                "evidence_risks": "無",
                "evidence_notes": "補充觀察",
            },
        ]
    )


def test_build_watchlist_report_preserves_selection_order_and_limits_to_four() -> None:
    report = build_watchlist_report(
        sample_candidates(),
        ["0000000003", "unknown", "0000000002", "0000000001", "0000000004", "0000000005"],
        "打者",
    )

    assert list(report.columns) == list(REPORT_COLUMNS)
    assert report["player_id"].tolist() == ["0000000003", "0000000002", "0000000001", "0000000004"]
    assert report["usage_label"].tolist() == ["PA"] * 4
    assert report["usage_value"].tolist() == [130, 90, 50, 35]
    assert report["role_or_position"].tolist() == ["SS", "OF", "1B", "C"]


def test_build_watchlist_report_supports_pitcher_ip_and_empty_selection() -> None:
    pitchers = sample_candidates().rename(columns={"position": "role", "pa": "innings_pitched"})
    report = build_watchlist_report(pitchers, ["0000000002"], "投手")
    empty = build_watchlist_report(pitchers, [], "投手")

    assert report.iloc[0]["usage_label"] == "IP"
    assert report.iloc[0]["usage_value"] == 90
    assert report.iloc[0]["role_or_position"] == "OF"
    assert empty.empty
    assert list(empty.columns) == list(REPORT_COLUMNS)


def test_report_markdown_contains_metadata_and_escapes_table_values() -> None:
    report = build_watchlist_report(sample_candidates(), ["0000000002"], "打者")
    markdown = report_markdown(
        report,
        {
            "player_type": "打者",
            "qualification": "PA ≥ 30",
            "priority": "長打",
            "qualified_count": 128,
            "snapshot_id": "snapshot-20260818-abcd",
            "generated_at": "2026-08-18 22:13",
            "quality_status": "pass",
        },
    )

    assert markdown.startswith("# CPBL 球探報告")
    assert "資料快照 | snapshot-20260818-abcd" in markdown
    assert "資格門檻 | PA ≥ 30" in markdown
    assert "王二\\|外野" in markdown
    assert "## 判讀限制" in markdown
    assert "不是逐場對戰資料，也不是未來表現預測" in markdown


def test_report_filename_is_stable_and_does_not_accept_path_segments() -> None:
    assert report_filename("打者", "snapshot/2026:08") == "cpbl_scouting_report_hitter_snapshot-2026-08.md"
    assert report_filename("投手", "") == "cpbl_scouting_report_pitcher_latest.md"
