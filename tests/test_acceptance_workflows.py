from __future__ import annotations

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.public_release_manifest import verify_public_release_manifest_file


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


def _visible_text(app: AppTest) -> str:
    values: list[str] = []
    for attr in ["title", "header", "subheader", "caption", "markdown", "info", "warning", "text"]:
        for element in getattr(app, attr):
            value = getattr(element, "value", "")
            if value and not str(value).lstrip().startswith("<style>"):
                values.append(str(value))
    for element in app.metric:
        values.extend(str(getattr(element, attr, "")) for attr in ["label", "value", "delta"])
    for element in app.selectbox:
        values.append(str(element.label))
    for element in app.radio:
        values.append(str(element.label))
        values.extend(str(option) for option in element.options)
    for element in app.number_input:
        values.append(str(element.label))
    return "\n".join(values)


def _assert_no_exception(app: AppTest) -> None:
    assert len(app.exception) == 0, [str(item.value) for item in app.exception]


def test_user_can_switch_analysis_validation_modes_and_metrics() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)
    app.sidebar.radio[0].set_value("分析驗證")
    app.run(timeout=30)
    _assert_no_exception(app)
    text = _visible_text(app)
    for term in ["排名穩定性", "資料分布變化", "權重敏感度", "Top-K", "Spearman ρ"]:
        assert term in text

    player_type = next(element for element in app.radio if element.label == "球員類型")
    player_type.set_value("投手")
    app.run(timeout=30)
    _assert_no_exception(app)
    stability_metric = next(element for element in app.selectbox if element.label == "穩定性指標")
    stability_metric.set_value("era")
    app.run(timeout=30)
    _assert_no_exception(app)
    assert "防禦率 (ERA)" in _visible_text(app)


def test_user_can_change_scouting_threshold_and_export_report() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)
    app.sidebar.radio[0].set_value("球探報告")
    app.run(timeout=30)
    _assert_no_exception(app)

    threshold = next(element for element in app.number_input if "最低打席" in element.label)
    threshold.set_value(50.0)
    app.run(timeout=30)
    _assert_no_exception(app)

    watchlist = next(element for element in app.multiselect if element.label == "觀察名單")
    watchlist.set_value(list(watchlist.options[:2]))
    app.run(timeout=30)
    _assert_no_exception(app)
    assert "評估報告" in _visible_text(app)
    download_labels = {str(element.label) for element in app.download_button}
    assert {"下載球探報告 Markdown", "下載球探報告 CSV", "下載稽核 Manifest JSON"}.issubset(download_labels)


def test_reviewer_can_trace_public_artifacts_to_quality_and_analysis_reports() -> None:
    quality_path = ROOT / "reports/metrics/data_quality_report.json"
    analysis_path = ROOT / "reports/metrics/analysis_validation.json"
    health_path = ROOT / "reports/metrics/release_health.json"
    public_manifest_path = ROOT / "reports/metrics/public_release_manifest.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8-sig"))
    analysis = json.loads(analysis_path.read_text(encoding="utf-8-sig"))
    health = json.loads(health_path.read_text(encoding="utf-8-sig"))
    public_manifest = json.loads(public_manifest_path.read_text(encoding="utf-8-sig"))
    verification = verify_public_release_manifest_file(public_manifest_path, root=ROOT)

    assert quality["mode"] == "api"
    assert quality["quality_status"] in {"pass", "warning"}
    assert quality["snapshot"]["snapshot_id"] == analysis["latest_snapshot_id"]
    assert quality["analysis_validation"]["schema_version"] == analysis["schema_version"]
    assert health["status"] in {"passed", "warning"}
    assert health["snapshot_id"] == quality["snapshot"]["snapshot_id"]
    assert quality["release_health"]["status"] == health["status"]
    assert verification["valid"] is True
    assert verification["release_id"] == public_manifest["release_id"]
    assert public_manifest["snapshot_id"] == quality["snapshot"]["snapshot_id"]
    assert public_manifest["generated_at"] == quality["generated_at"]
    assert public_manifest["artifact_count"] == 11
    assert analysis["limitations"]
    assert analysis["interpretation"]
    for path in [ROOT / "docs/MODEL_CARD.md", ROOT / "docs/ARCHITECTURE.md", ROOT / "docs/REVIEW_GUIDE.md"]:
        assert path.exists()
        assert path.stat().st_size > 500
