import pandas as pd

import src.app_helpers as app_helpers
from src.app_helpers import REQUIRED_PROCESSED_FILES, ensure_processed_data, processed_data_version


def test_ensure_processed_data_reports_missing_outputs_without_network(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    for name in REQUIRED_PROCESSED_FILES[:-1]:
        (processed / name).write_text("ready", encoding="utf-8")

    monkeypatch.setattr("src.app_helpers.project_path", lambda *parts: tmp_path.joinpath(*parts))

    assert ensure_processed_data() == (REQUIRED_PROCESSED_FILES[-1],)

def test_processed_data_version_changes_when_public_csv_changes(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    target = processed / "teams.csv"
    target.write_text("team\n測試隊\n", encoding="utf-8")
    monkeypatch.setattr("src.app_helpers.project_path", lambda *parts: tmp_path.joinpath(*parts))

    before = processed_data_version()
    target.write_text("team\n測試隊\n另一隊\n", encoding="utf-8")
    after = processed_data_version()

    assert before != after
    assert any(item[0] == "teams.csv" for item in after)


def test_win_rate_series_vectorizes_numeric_cleanup_and_zero_games() -> None:
    wins = pd.Series([3, "2", None, "invalid"], index=[4, 5, 6, 7])
    losses = pd.Series([1, "2", None, 0], index=[4, 5, 6, 7])

    result = app_helpers.win_rate_series(wins, losses)

    assert result.index.tolist() == [4, 5, 6, 7]
    assert result.tolist() == [0.75, 0.5, 0.0, 0.0]

def test_player_choice_options_keeps_duplicate_names_unambiguous() -> None:
    players = pd.DataFrame(
        [
            {
                "player_id": "0000000001",
                "player_name": "同名球員",
                "team": "A隊",
                "player_type": "打者",
                "position": "內野手",
            },
            {
                "player_id": "0000000002",
                "player_name": "同名球員",
                "team": "A隊",
                "player_type": "打者",
                "position": "外野手",
            },
        ]
    )

    options = app_helpers.player_choice_options(players)

    assert list(options.values()) == ["0000000001", "0000000002"]
    assert len(options) == 2
    assert all("同名球員" in label and "A隊" in label for label in options)
    assert any("內野手" in label and "0000000001" in label for label in options)
    assert any("外野手" in label and "0000000002" in label for label in options)


def test_player_choice_options_rejects_incomplete_or_duplicate_ids() -> None:
    incomplete = pd.DataFrame([{"player_id": "1", "player_name": "甲"}])
    duplicated = pd.DataFrame(
        [
            {"player_id": "1", "player_name": "甲", "team": "A"},
            {"player_id": "1", "player_name": "乙", "team": "A"},
        ]
    )

    assert app_helpers.player_choice_options(incomplete) == {}
    assert len(app_helpers.player_choice_options(duplicated)) == 1
