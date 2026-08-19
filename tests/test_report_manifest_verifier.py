from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.scouting_report import (
    build_report_manifest,
    report_manifest_json,
    verify_report_manifest,
    verify_report_manifest_file,
)


ROOT = Path(__file__).resolve().parents[1]


def build_sample_manifest() -> dict[str, object]:
    report = pd.DataFrame(
        [
            {
                "player_id": "0000000001",
                "player_name": "測試球員",
                "team": "測試隊",
                "role_or_position": "SS",
                "usage_label": "PA",
                "usage_value": 120,
                "priority_score": 81.5,
                "qualified_percentile": 92.0,
                "evidence_strengths": "上壘訊號",
                "evidence_risks": "樣本限制",
                "evidence_notes": "僅供測試",
            }
        ]
    )
    return build_report_manifest(
        report,
        {
            "player_type": "打者",
            "team": "全部",
            "qualification": "PA ≥ 30",
            "priority": "綜合價值",
            "qualified_count": 42,
            "snapshot_id": "snapshot-20260818-abcd",
            "quality_status": "通過",
            "generated_at": "2026-08-19 09:00",
        },
    )


def test_verify_report_manifest_returns_reproducibility_summary() -> None:
    manifest = build_sample_manifest()

    result = verify_report_manifest(manifest)

    assert result == {
        "valid": True,
        "report_id": manifest["report_id"],
        "schema_version": "1.1",
        "snapshot_id": "snapshot-20260818-abcd",
        "player_count": 1,
    }


def test_verify_report_manifest_supports_original_schema_version() -> None:
    manifest = build_sample_manifest()
    legacy_identity = {
        "schema_version": "1.0",
        "data_provenance": manifest["data_provenance"],
        "analysis": manifest["analysis"],
        "players": manifest["players"],
    }
    canonical = json.dumps(legacy_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest["schema_version"] = "1.0"
    manifest["report_id"] = "rpt-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    result = verify_report_manifest(manifest)

    assert result["valid"] is True
    assert result["schema_version"] == "1.0"


def test_verify_report_manifest_rejects_tampered_player_content() -> None:
    manifest = json.loads(report_manifest_json(build_sample_manifest()))
    manifest["players"][0]["priority_score"] = 99.9

    with pytest.raises(ValueError, match="報告 ID 不一致"):
        verify_report_manifest(manifest)


def test_verify_report_manifest_rejects_tampered_methodology() -> None:
    manifest = json.loads(report_manifest_json(build_sample_manifest()))
    manifest["methodology"]["score_source"] = "tampered"

    with pytest.raises(ValueError, match="報告 ID 不一致"):
        verify_report_manifest(manifest)

def test_verify_report_manifest_rejects_missing_required_fields() -> None:
    manifest = build_sample_manifest()
    manifest.pop("methodology")

    with pytest.raises(ValueError, match="缺少必要欄位"):
        verify_report_manifest(manifest)


def test_verify_report_manifest_file_round_trips_utf8_json(tmp_path: Path) -> None:
    path = tmp_path / "report.manifest.json"
    path.write_text(report_manifest_json(build_sample_manifest()), encoding="utf-8")

    result = verify_report_manifest_file(path)

    assert result["valid"] is True
    assert result["player_count"] == 1


def test_verify_report_manifest_cli_has_machine_readable_success_and_failure(tmp_path: Path) -> None:
    valid_path = tmp_path / "valid.manifest.json"
    valid_path.write_text(report_manifest_json(build_sample_manifest()), encoding="utf-8")
    valid = subprocess.run(
        [sys.executable, "-m", "src.verify_report_manifest", str(valid_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert valid.returncode == 0
    assert json.loads(valid.stdout)["valid"] is True

    invalid_payload = json.loads(valid_path.read_text(encoding="utf-8"))
    invalid_payload["analysis"]["priority"] = "長打"
    invalid_path = tmp_path / "invalid.manifest.json"
    invalid_path.write_text(json.dumps(invalid_payload, ensure_ascii=False), encoding="utf-8")
    invalid = subprocess.run(
        [sys.executable, "-m", "src.verify_report_manifest", str(invalid_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert invalid.returncode == 1
    assert "報告 ID 不一致" in invalid.stderr
