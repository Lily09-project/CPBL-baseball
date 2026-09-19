from __future__ import annotations

import argparse

import pandas as pd
from src.analysis_validation import build_analysis_validation_report, write_analysis_validation_report
from src.data_quality import generate_data_quality_report, save_data_quality_report
from src.history import generate_history_outputs
from src.movements import generate_player_movements
from src.preprocess import preprocess
from src.public_release_manifest import build_public_release_manifest, write_public_release_manifest
from src.release_health import build_release_health_report, write_release_health_report
from src.snapshots import create_processed_snapshot
from src.source_contract import build_pipeline_source_reason
from src.utils import project_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["api"], default="api")
    args = parser.parse_args()
    fallback_reason = build_pipeline_source_reason(args.mode)
    outputs = preprocess(mode=args.mode)
    report = generate_data_quality_report(mode=args.mode, fallback_reason=fallback_reason)
    if report["quality_status"] == "failed":
        raise RuntimeError("資料品質檢查失敗，停止啟動前端。")
    snapshot = create_processed_snapshot(
        project_path("data/processed"),
        project_path("data/snapshots"),
        report,
    )
    report["snapshot"] = {
        key: snapshot.get(key)
        for key in [
            "schema_version",
            "snapshot_id",
            "captured_at",
            "season",
            "relative_path",
            "previous_snapshot_id",
            "diff",
        ]
    }
    movement_path = project_path("data/processed/player_movements.csv")
    movement = generate_player_movements(
        project_path("data/snapshots"),
        snapshot,
        movement_path,
    )
    outputs["player_movements"] = str(movement_path)
    report["movement"] = movement
    history = generate_history_outputs(
        project_path("data/snapshots"),
        project_path("data/processed"),
    )
    outputs["snapshot_history"] = str(project_path("data/processed/snapshot_history.csv"))
    outputs["player_metric_history"] = str(project_path("data/processed/player_metric_history.csv"))
    report["history"] = history
    history_frame = pd.read_csv(
        project_path("data/processed/player_metric_history.csv"),
        dtype={"player_id": "string"},
    )
    analysis_validation = build_analysis_validation_report(
        history_frame,
        generated_at=str(report.get("generated_at", "")) or None,
    )
    analysis_validation_path = project_path("reports/metrics/analysis_validation.json")
    write_analysis_validation_report(analysis_validation, analysis_validation_path)
    outputs["analysis_validation"] = str(analysis_validation_path)
    report["analysis_validation"] = analysis_validation
    release_health = build_release_health_report(report)
    release_health_path = write_release_health_report(release_health)
    outputs["release_health"] = str(release_health_path)
    report["release_health"] = release_health
    save_data_quality_report(report)
    if release_health["status"] == "failed":
        failed_checks = [
            str(check.get("summary", check.get("name", "unknown")))
            for check in release_health.get("checks", [])
            if check.get("status") == "failed"
        ]
        detail = "；".join(failed_checks) or "未提供詳細原因"
        raise RuntimeError(f"資料發布健康檢查失敗：{detail}")
    public_release = build_public_release_manifest(
        project_path(),
        generated_at=str(report.get("generated_at", "")),
        snapshot_id=str(report.get("snapshot", {}).get("snapshot_id", "")),
    )
    public_release_path = write_public_release_manifest(public_release)
    outputs["public_release_manifest"] = str(public_release_path)
    print("processed files:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")
    print(f"quality_status: {report['quality_status']}")
    print("done")


if __name__ == "__main__":
    main()
