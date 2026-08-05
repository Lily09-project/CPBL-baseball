from __future__ import annotations

import argparse

from src.data_quality import generate_data_quality_report, save_data_quality_report
from src.preprocess import preprocess
from src.snapshots import create_processed_snapshot
from src.utils import project_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["api"], default="api")
    args = parser.parse_args()
    fallback_reason = "api mode: 使用 CPBL 官方 /player、/standings/season、/stats/recordallaction"
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
    save_data_quality_report(report)
    print("processed files:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")
    print(f"quality_status: {report['quality_status']}")
    print("done")


if __name__ == "__main__":
    main()
