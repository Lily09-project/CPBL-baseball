from src.app_helpers import REQUIRED_PROCESSED_FILES, ensure_processed_data, processed_data_version


def test_ensure_processed_data_rebuilds_when_any_required_output_is_missing(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    for name in REQUIRED_PROCESSED_FILES[:-1]:
        (processed / name).write_text("ready", encoding="utf-8")
    calls = []

    monkeypatch.setattr("src.app_helpers.project_path", lambda *parts: tmp_path.joinpath(*parts))
    monkeypatch.setattr("src.app_helpers.preprocess", lambda mode: calls.append(mode))

    ensure_processed_data()

    assert calls == ["api"]

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
