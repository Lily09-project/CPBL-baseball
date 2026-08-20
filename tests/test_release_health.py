from __future__ import annotations

from src.release_health import build_release_health_report


def _quality_report(*, current_rows: int = 100, previous_rows: int = 100, schema_changed: bool = False) -> dict:
    snapshot_id = "snapshot-current"
    return {
        "mode": "api",
        "generated_at": "2026-08-20T19:30:31+08:00",
        "quality_status": "pass",
        "warnings": [],
        "snapshot": {
            "snapshot_id": snapshot_id,
            "previous_snapshot_id": "snapshot-previous",
            "diff": {
                "schema_changed_files": ["players_scored.csv"] if schema_changed else [],
                "files": {
                    "players_scored.csv": {
                        "previous_row_count": previous_rows,
                        "current_row_count": current_rows,
                    }
                },
            },
        },
        "history": {"latest_snapshot_id": snapshot_id},
        "analysis_validation": {"latest_snapshot_id": snapshot_id},
    }


def _checks(report: dict) -> dict[str, dict]:
    return {str(check["name"]): check for check in report["checks"]}


def test_release_health_passes_for_consistent_snapshot() -> None:
    report = build_release_health_report(_quality_report())

    assert report["status"] == "passed"
    assert report["summary"] == {"passed": 7, "warnings": 0, "failed": 0, "total": 7}
    assert _checks(report)["row_count_regression"]["status"] == "passed"


def test_release_health_warns_on_moderate_row_count_drop() -> None:
    report = build_release_health_report(_quality_report(current_rows=90))

    assert report["status"] == "warning"
    assert _checks(report)["row_count_regression"]["status"] == "warning"


def test_release_health_fails_on_large_row_count_drop() -> None:
    report = build_release_health_report(_quality_report(current_rows=70))

    assert report["status"] == "failed"
    assert _checks(report)["row_count_regression"]["status"] == "failed"


def test_release_health_fails_on_schema_drift() -> None:
    report = build_release_health_report(_quality_report(schema_changed=True))

    assert report["status"] == "failed"
    assert _checks(report)["schema_drift"]["status"] == "failed"


def test_release_health_fails_when_artifacts_point_to_different_snapshots() -> None:
    quality = _quality_report()
    quality["analysis_validation"]["latest_snapshot_id"] = "snapshot-old"

    report = build_release_health_report(quality)

    assert report["status"] == "failed"
    assert _checks(report)["artifact_lineage"]["status"] == "failed"
