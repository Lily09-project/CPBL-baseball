from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_quality import REQUIRED_FILES, UNIQUE_ID_FILES
from src.public_release_manifest import (
    PUBLIC_RELEASE_MANIFEST_PATH,
    verify_public_release_manifest,
)
from src.release_health import (
    RELEASE_HEALTH_REPORT_PATH,
    RELEASE_HEALTH_SCHEMA_VERSION,
    build_release_health_report,
)
from src.utils import project_path


QUALITY_REPORT_PATH = Path("reports/metrics/data_quality_report.json")
ANALYSIS_REPORT_PATH = Path("reports/metrics/analysis_validation.json")
ANALYSIS_SCHEMA_VERSION = "1.0"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} 必須是 JSON object")
    return payload


def run_release_gate(root: Path | None = None) -> dict[str, Any]:
    project_root = root or project_path()
    failures: list[str] = []
    warnings: list[str] = []
    quality_path = project_root / QUALITY_REPORT_PATH
    analysis_path = project_root / ANALYSIS_REPORT_PATH

    if not quality_path.exists():
        failures.append(f"缺少品質報告：{QUALITY_REPORT_PATH}")
        quality: dict[str, Any] = {}
    else:
        try:
            quality = _read_json(quality_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"品質報告無法讀取：{exc}")
            quality = {}

    if quality.get("quality_status") not in {"pass", "warning"}:
        failures.append("quality_status 必須是 pass 或 warning")
    if quality.get("mode") != "api":
        failures.append("資料管線 mode 必須是 api，禁止以 sample 或未知來源發布")
    generated_at = str(quality.get("generated_at", ""))
    try:
        datetime.fromisoformat(generated_at)
    except ValueError:
        failures.append("品質報告 generated_at 不是有效 ISO-8601 時間")

    for file_name in REQUIRED_FILES:
        csv_path = project_root / "data" / "processed" / file_name
        if not csv_path.exists():
            failures.append(f"缺少處理後資料：data/processed/{file_name}")
            continue
        try:
            frame = pd.read_csv(csv_path, dtype={"player_id": "string"})
        except (OSError, UnicodeError, pd.errors.ParserError) as exc:
            failures.append(f"無法讀取 {file_name}：{exc}")
            continue
        if frame.empty:
            failures.append(f"處理後資料不可為空：{file_name}")
        if file_name in UNIQUE_ID_FILES and "player_id" in frame.columns:
            if frame["player_id"].isna().any() or frame["player_id"].duplicated().any():
                failures.append(f"{file_name} 的 player_id 不唯一或存在空值")

    if not analysis_path.exists():
        failures.append(f"缺少分析驗證報告：{ANALYSIS_REPORT_PATH}")
        analysis: dict[str, Any] = {}
    else:
        try:
            analysis = _read_json(analysis_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"分析驗證報告無法讀取：{exc}")
            analysis = {}

    if analysis:
        analysis_generated_at = str(analysis.get("generated_at", ""))
        try:
            datetime.fromisoformat(analysis_generated_at)
        except ValueError:
            failures.append("分析驗證報告 generated_at 不是有效 ISO-8601 時間")
        if analysis_generated_at != generated_at:
            failures.append("品質報告與分析驗證報告的 generated_at 不一致")
        if analysis.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
            failures.append("分析驗證報告 schema_version 不相容")
        if int(analysis.get("snapshot_count", 0)) < 1:
            failures.append("分析驗證報告沒有可稽核快照")
        if not analysis.get("limitations") or not analysis.get("interpretation"):
            failures.append("分析驗證報告缺少限制或解讀說明")
        if int(analysis.get("snapshot_count", 0)) < 2:
            warnings.append("目前歷史快照少於兩版，尚無法計算相鄰版本穩定性")

    embedded = quality.get("analysis_validation")
    if isinstance(embedded, dict) and analysis:
        if embedded.get("schema_version") != analysis.get("schema_version"):
            failures.append("品質報告內嵌的分析驗證版本與 JSON 報告不一致")
        if embedded.get("snapshot_count") != analysis.get("snapshot_count"):
            failures.append("品質報告內嵌的快照數與分析驗證報告不一致")

    health_path = project_root / RELEASE_HEALTH_REPORT_PATH
    if not health_path.exists():
        failures.append(f"缺少發布健康報告：{RELEASE_HEALTH_REPORT_PATH}")
        health: dict[str, Any] = {}
    else:
        try:
            health = _read_json(health_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"發布健康報告無法讀取：{exc}")
            health = {}

    if health:
        expected_health = build_release_health_report(quality)
        if health.get("schema_version") != RELEASE_HEALTH_SCHEMA_VERSION:
            failures.append("發布健康報告 schema_version 不相容")
        if str(health.get("generated_at", "")) != generated_at:
            failures.append("品質報告與發布健康報告的 generated_at 不一致")
        snapshot_payload = quality.get("snapshot")
        expected_snapshot_id = (
            str(snapshot_payload.get("snapshot_id", ""))
            if isinstance(snapshot_payload, dict)
            else ""
        )
        if str(health.get("snapshot_id", "")) != expected_snapshot_id:
            failures.append("品質報告與發布健康報告的 snapshot_id 不一致")
        if health.get("status") != expected_health.get("status"):
            failures.append("發布健康報告與品質報告重新計算結果不一致")
        if expected_health.get("status") == "failed":
            failures.extend(
                "發布健康檢查失敗：" + str(check.get("summary", check.get("name", "unknown")))
                for check in expected_health.get("checks", [])
                if check.get("status") == "failed"
            )
        elif expected_health.get("status") == "warning":
            warnings.extend(
                "發布健康提醒：" + str(check.get("summary", check.get("name", "unknown")))
                for check in expected_health.get("checks", [])
                if check.get("status") == "warning"
            )

    public_manifest_path = project_root / PUBLIC_RELEASE_MANIFEST_PATH
    if not public_manifest_path.exists():
        failures.append(f"缺少公開發布 Manifest：{PUBLIC_RELEASE_MANIFEST_PATH.as_posix()}")
        public_manifest: dict[str, Any] = {}
    else:
        try:
            public_manifest = _read_json(public_manifest_path)
            verify_public_release_manifest(public_manifest, project_root)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"公開發布 Manifest 驗證失敗：{exc}")
            public_manifest = {}

    if public_manifest:
        if str(public_manifest.get("generated_at", "")) != generated_at:
            failures.append("品質報告與公開發布 Manifest 的 generated_at 不一致")
        snapshot_payload = quality.get("snapshot")
        expected_snapshot_id = (
            str(snapshot_payload.get("snapshot_id", ""))
            if isinstance(snapshot_payload, dict)
            else ""
        )
        if str(public_manifest.get("snapshot_id", "")) != expected_snapshot_id:
            failures.append("品質報告與公開發布 Manifest 的 snapshot_id 不一致")

    return {
        "status": "failed" if failures else "passed",
        "failures": failures,
        "warnings": warnings,
        "quality_report": str(QUALITY_REPORT_PATH),
        "analysis_report": str(ANALYSIS_REPORT_PATH),
        "public_release_manifest": PUBLIC_RELEASE_MANIFEST_PATH.as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CPBL 專案發布前品質門檻")
    parser.parse_args()
    result = run_release_gate()
    for warning in result["warnings"]:
        print(f"warning: {warning}")
    for failure in result["failures"]:
        print(f"error: {failure}")
    print(f"release gate: {result['status']}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
