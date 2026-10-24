from __future__ import annotations

import pytest

import src.data_quality as data_quality
from src.fetch_cpbl_data import parse_html_table


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
