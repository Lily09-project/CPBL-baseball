from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import app as dashboard
from src.data_quality import load_data_quality_report
from src.fetch_cpbl_data import MAX_OFFICIAL_RESPONSE_BYTES, _checked_response_text, fetch_recordall, fetch_text
from src.movements import generate_player_movements
from src.scouting_report import (
    build_report_manifest,
    verify_report_manifest,
    verify_report_manifest_file,
)


class _FakeResponse:
    def __init__(self, text: str, url: str = "https://cpbl.com.tw/stats/recordall") -> None:
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, page: str) -> None:
        self.page = page

    def get(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse('<input name="__RequestVerificationToken" value="token">')

    def post(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(self.page)


def test_source_status_panel_escapes_untrusted_quality_report_fields(monkeypatch):
    rendered: list[str] = []
    malicious_report = {
        "generated_at": "<script>alert(1)</script>",
        "quality_status": "pass",
        "available_team_count": 6,
        "player_summary_count": 1,
        "official_roster_count": 1,
        "available_hitter_count": 1,
        "available_pitcher_count": 1,
    }
    monkeypatch.setattr(dashboard, "QUALITY_REPORT", malicious_report)
    monkeypatch.setattr(dashboard.st, "markdown", lambda body, **kwargs: rendered.append(body))

    dashboard.source_status_panel()

    combined = "\n".join(rendered)
    assert "<script>" not in combined
    assert "&lt;script&gt;" in combined


def test_recordall_rejects_untrusted_pagination_above_safety_limit(monkeypatch, tmp_path):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    page = (
        '<div total-paging="101"></div>'
        "<table><tr><th>球員</th></tr><tr><td>1 測試隊 球員甲</td></tr></table>"
    )
    monkeypatch.setattr("src.fetch_cpbl_data.project_path", lambda *parts: tmp_path.joinpath(*parts))

    with pytest.raises(RuntimeError, match="安全上限"):
        fetch_recordall(_FakeSession(page), position="01", sortby="02")


def test_official_response_rejects_external_host_and_oversized_body():
    with pytest.raises(RuntimeError, match="官方網域"):
        _checked_response_text(_FakeResponse("ok", url="https://evil.invalid/page"), "測試")

    oversized = "x" * (MAX_OFFICIAL_RESPONSE_BYTES + 1)
    with pytest.raises(RuntimeError, match="回應內容超過安全上限"):
        _checked_response_text(_FakeResponse(oversized), "測試")


def test_fetch_text_rejects_external_url_before_network_call():
    class _NoRequestSession:
        def get(self, *args, **kwargs):
            raise AssertionError("external request must not be sent")

    with pytest.raises(RuntimeError, match="官方 HTTPS"):
        fetch_text(_NoRequestSession(), "https://evil.invalid/page", timeout=1)


def test_recordall_rejects_query_parameter_injection_before_network_call():
    with pytest.raises(ValueError, match="查詢參數格式不正確"):
        fetch_recordall(_FakeSession(""), position="01&next=https://evil.invalid", sortby="02")


def _write_movement_frame(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [{"player_id": "1", "player_name": "測試球員", "team": "測試隊", "pa": 10}]
    )
    frame.to_csv(directory / "batters_scored.csv", index=False)
    frame[["player_id", "player_name", "team"]].to_csv(directory / "pitchers_scored.csv", index=False)


def test_movement_manifest_cannot_escape_snapshot_root(tmp_path):
    snapshot_root = tmp_path / "snapshots"
    previous = snapshot_root / "season=2026" / "snapshot_id=previous"
    _write_movement_frame(previous)
    (previous / "manifest.json").write_text(
        json.dumps({"snapshot_id": "previous", "captured_at": "2026-08-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    outside = tmp_path / "outside"
    _write_movement_frame(outside)
    current_manifest = {
        "snapshot_id": "current",
        "captured_at": "2026-08-02T00:00:00+00:00",
        "relative_path": "../outside",
        "previous_snapshot_id": "previous",
    }

    with pytest.raises(ValueError, match="snapshot root"):
        generate_player_movements(snapshot_root, current_manifest, tmp_path / "processed" / "movement.csv")


def test_manifest_verifier_rejects_oversized_file(tmp_path):
    path = tmp_path / "oversized.manifest.json"
    path.write_text("{" + '"x":"' + ("a" * (2 * 1024 * 1024)) + '"}', encoding="utf-8")

    with pytest.raises(ValueError, match="過大"):
        verify_report_manifest_file(path)


def test_quality_report_loader_fails_closed_on_oversized_file(monkeypatch, tmp_path):
    path = tmp_path / "reports" / "metrics" / "data_quality_report.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"x":"' + ("a" * (2 * 1024 * 1024)) + '"}', encoding="utf-8")
    monkeypatch.setattr("src.data_quality.project_path", lambda *parts: tmp_path.joinpath(*parts))

    report = load_data_quality_report()

    assert report["quality_status"] == "failed"
    assert "過大" in report["warnings"][0]


def test_player_header_escapes_untrusted_report_date(monkeypatch):
    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "QUALITY_REPORT",
        {"generated_at": "<script>alert(1)</script>", "quality_status": "pass"},
    )
    monkeypatch.setattr(dashboard, "PLAYERS", pd.DataFrame())
    monkeypatch.setattr(dashboard, "ROSTER", pd.DataFrame())
    monkeypatch.setattr(dashboard.st, "markdown", lambda body, **kwargs: rendered.append(body))
    monkeypatch.setattr(dashboard.st, "link_button", lambda *args, **kwargs: None)

    dashboard.render_player_header(
        pd.Series(
            {
                "player_id": "1",
                "player_name": "測試球員",
                "team": "測試隊",
                "season": 2026,
                "position": "內野手",
            }
        ),
        "打者",
    )

    combined = "\n".join(rendered)
    assert "<script>" not in combined
    assert "&lt;script&gt;" in combined


def test_manifest_verifier_rejects_more_than_four_players():
    report = pd.DataFrame(
        [
            {
                "player_id": str(index),
                "player_name": f"球員{index}",
                "team": "測試隊",
                "role_or_position": "內野手",
                "usage_label": "PA",
                "usage_value": 100,
                "priority_score": 80.0,
                "qualified_percentile": 90.0,
                "evidence_strengths": "強項",
                "evidence_risks": "風險",
                "evidence_notes": "註記",
            }
            for index in range(5)
        ]
    )
    manifest = build_report_manifest(
        report,
        {
            "player_type": "打者",
            "team": "全部",
            "qualification": "PA >= 30",
            "priority": "綜合價值",
            "qualified_count": 5,
            "snapshot_id": "snapshot-test",
            "quality_status": "通過",
            "generated_at": "2026-08-19 00:00",
        },
    )

    with pytest.raises(ValueError, match="最多 4"):
        verify_report_manifest(manifest)
