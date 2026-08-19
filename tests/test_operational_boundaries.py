from __future__ import annotations

import pytest

import src.app_helpers as app_helpers
import src.data_quality as data_quality
from src.fetch_cpbl_data import parse_html_table


def test_frontend_data_loader_reports_missing_outputs_without_fetching(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    for name in app_helpers.REQUIRED_PROCESSED_FILES[:-1]:
        (processed / name).write_text("ready", encoding="utf-8")

    monkeypatch.setattr("src.app_helpers.project_path", lambda *parts: tmp_path.joinpath(*parts))
    monkeypatch.setattr(
        app_helpers,
        "preprocess",
        lambda mode: (_ for _ in ()).throw(AssertionError("frontend must not fetch data")),
        raising=False,
    )

    assert app_helpers.ensure_processed_data() == (app_helpers.REQUIRED_PROCESSED_FILES[-1],)


def test_frontend_csv_loader_rejects_path_traversal(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    monkeypatch.setattr("src.app_helpers.project_path", lambda *parts: tmp_path.joinpath(*parts))

    with pytest.raises(ValueError, match="processed CSV"):
        app_helpers.load_csv("../outside.csv")


def test_frontend_csv_loader_reports_corrupt_files(monkeypatch, tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "teams.csv").write_text("team,wins\n\"unterminated,1\n", encoding="utf-8")
    monkeypatch.setattr("src.app_helpers.project_path", lambda *parts: tmp_path.joinpath(*parts))

    with pytest.raises(app_helpers.ProcessedDataError, match="teams.csv"):
        app_helpers.load_csv("teams.csv")


def test_corrupt_quality_report_fails_closed(monkeypatch, tmp_path):
    report_dir = tmp_path / "reports" / "metrics"
    report_dir.mkdir(parents=True)
    (report_dir / "data_quality_report.json").write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr("src.data_quality.project_path", lambda *parts: tmp_path.joinpath(*parts))

    report = data_quality.load_data_quality_report()

    assert report["quality_status"] == "failed"
    assert any("無法讀取" in warning for warning in report["warnings"])


def test_malformed_official_table_has_a_stable_parser_error():
    with pytest.raises(RuntimeError, match="表格解析失敗"):
        parse_html_table("<html><body><p>not a table</p></body></html>")
