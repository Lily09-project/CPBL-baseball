from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils import project_path


RELEASE_HEALTH_SCHEMA_VERSION = "1.0"
RELEASE_HEALTH_REPORT_PATH = Path("reports/metrics/release_health.json")
ROW_COUNT_DROP_WARNING_RATIO = 0.10
ROW_COUNT_DROP_FAILURE_RATIO = 0.25


def _check(name: str, status: str, summary: str, details: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "details": list(details or []),
    }


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {str(check.get("status", "failed")) for check in checks}
    if "failed" in statuses or not statuses.issubset({"passed", "warning"}):
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "passed"


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_count_check(diff: dict[str, Any]) -> dict[str, Any]:
    file_diffs = diff.get("files")
    if not isinstance(file_diffs, dict):
        return _check(
            "row_count_regression",
            "warning",
            "沒有可比較的前一版本列數，已略過驟降檢查。",
        )

    warnings: list[str] = []
    failures: list[str] = []
    checked = 0
    for file_name, metadata in file_diffs.items():
        if not isinstance(metadata, dict):
            failures.append(f"{file_name}: diff 格式無效")
            continue
        previous = _safe_int(metadata.get("previous_row_count"))
        current = _safe_int(metadata.get("current_row_count"))
        if previous is None or current is None:
            continue
        if previous <= 0:
            continue
        checked += 1
        drop_ratio = (previous - current) / previous
        if drop_ratio >= ROW_COUNT_DROP_FAILURE_RATIO:
            failures.append(f"{file_name}: 列數由 {previous} 降至 {current}（-{drop_ratio:.1%}）")
        elif drop_ratio >= ROW_COUNT_DROP_WARNING_RATIO:
            warnings.append(f"{file_name}: 列數由 {previous} 降至 {current}（-{drop_ratio:.1%}）")

    if failures:
        return _check(
            "row_count_regression",
            "failed",
            "偵測到可能由分頁遺漏或來源異常造成的資料列數驟降。",
            failures + warnings,
        )
    if warnings:
        return _check(
            "row_count_regression",
            "warning",
            "部分資料表列數下降，需在 PR 中確認是否為真實名單或統計變化。",
            warnings,
        )
    if checked == 0:
        return _check(
            "row_count_regression",
            "warning",
            "沒有足夠的前一版本資料可比較列數。",
        )
    return _check("row_count_regression", "passed", "所有可比較資料表均未達列數驟降門檻。")


def build_release_health_report(quality_report: dict[str, Any]) -> dict[str, Any]:
    generated_at = str(quality_report.get("generated_at", ""))
    snapshot = quality_report.get("snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    snapshot_id = str(snapshot.get("snapshot_id", ""))
    diff = snapshot.get("diff")
    diff = diff if isinstance(diff, dict) else {}
    checks: list[dict[str, Any]] = []

    quality_status = str(quality_report.get("quality_status", ""))
    if quality_status == "pass":
        checks.append(_check("base_quality", "passed", "schema、主鍵、數值範圍與最低涵蓋量均通過。"))
    elif quality_status == "warning":
        quality_warnings = quality_report.get("warnings", [])
        details = [str(item) for item in quality_warnings] if isinstance(quality_warnings, list) else [str(quality_warnings)]
        checks.append(_check("base_quality", "warning", "基礎品質有警示，需在發布前人工確認。", details))
    else:
        checks.append(_check("base_quality", "failed", "基礎資料品質未通過，禁止發布。"))

    if str(quality_report.get("mode", "")) == "api":
        checks.append(_check("official_source", "passed", "資料來源模式為 CPBL 官方公開頁面。"))
    else:
        checks.append(_check("official_source", "failed", "資料來源不是允許發布的 api mode。"))

    if snapshot_id:
        checks.append(_check("snapshot_lineage", "passed", f"已建立可追溯資料快照 {snapshot_id}。"))
    else:
        checks.append(_check("snapshot_lineage", "failed", "缺少 snapshot_id，無法稽核本次資料版本。"))

    schema_changed = diff.get("schema_changed_files")
    schema_changed = schema_changed if isinstance(schema_changed, list) else []
    if schema_changed:
        checks.append(
            _check(
                "schema_drift",
                "failed",
                "偵測到資料表 schema 變更，需先更新 parser 與測試。",
                [str(item) for item in schema_changed],
            )
        )
    else:
        checks.append(_check("schema_drift", "passed", "相鄰快照沒有新增或移除欄位。"))

    checks.append(_row_count_check(diff))

    previous_snapshot_id = str(snapshot.get("previous_snapshot_id", ""))
    if previous_snapshot_id:
        checks.append(_check("baseline_lineage", "passed", f"已與前一版本 {previous_snapshot_id} 建立差異比較。"))
    else:
        checks.append(_check("baseline_lineage", "warning", "這是第一份快照，尚無前一版本可比較。"))

    history = quality_report.get("history")
    history = history if isinstance(history, dict) else {}
    analysis = quality_report.get("analysis_validation")
    analysis = analysis if isinstance(analysis, dict) else {}
    lineage_ids = {
        "snapshot": snapshot_id,
        "history": str(history.get("latest_snapshot_id", "")),
        "analysis": str(analysis.get("latest_snapshot_id", "")),
    }
    missing_lineage = [name for name, value in lineage_ids.items() if not value]
    mismatched_lineage = [value for value in lineage_ids.values() if value and value != snapshot_id]
    if missing_lineage:
        checks.append(
            _check(
                "artifact_lineage",
                "failed",
                "快照、歷史與分析報告缺少最新版本 ID。",
                [f"缺少：{', '.join(missing_lineage)}"],
            )
        )
    elif mismatched_lineage:
        checks.append(
            _check(
                "artifact_lineage",
                "failed",
                "快照、歷史與分析報告指向不同資料版本。",
                [f"snapshot={snapshot_id}", f"history={lineage_ids['history']}", f"analysis={lineage_ids['analysis']}"],
            )
        )
    else:
        checks.append(_check("artifact_lineage", "passed", "快照、歷史與分析驗證報告指向同一最新版本。"))

    failed_count = sum(check["status"] == "failed" for check in checks)
    warning_count = sum(check["status"] == "warning" for check in checks)
    passed_count = sum(check["status"] == "passed" for check in checks)
    return {
        "schema_version": RELEASE_HEALTH_SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": _overall_status(checks),
        "snapshot_id": snapshot_id,
        "thresholds": {
            "row_count_drop_warning_ratio": ROW_COUNT_DROP_WARNING_RATIO,
            "row_count_drop_failure_ratio": ROW_COUNT_DROP_FAILURE_RATIO,
        },
        "summary": {
            "passed": passed_count,
            "warnings": warning_count,
            "failed": failed_count,
            "total": len(checks),
        },
        "checks": checks,
    }


def write_release_health_report(report: dict[str, Any], path: Path | None = None) -> Path:
    output_path = path or project_path(str(RELEASE_HEALTH_REPORT_PATH))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
