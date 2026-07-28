from src.app_helpers import REQUIRED_PROCESSED_FILES, ensure_processed_data


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
