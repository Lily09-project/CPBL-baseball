from __future__ import annotations

import json
from pathlib import Path

from src.public_release_manifest import build_public_release_manifest, write_public_release_manifest
from src.verify_public_release import main
from tests.test_public_release_manifest import GENERATED_AT, SNAPSHOT_ID, write_public_release_fixture


def _write_manifest(root: Path) -> Path:
    write_public_release_fixture(root)
    manifest = build_public_release_manifest(
        root,
        generated_at=GENERATED_AT,
        snapshot_id=SNAPSHOT_ID,
    )
    return write_public_release_manifest(
        manifest,
        root / "reports" / "metrics" / "public_release_manifest.json",
    )


def test_cli_reports_valid_public_release(tmp_path: Path, capsys) -> None:
    manifest_path = _write_manifest(tmp_path)

    exit_code = main([str(manifest_path), "--root", str(tmp_path)])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["valid"] is True
    assert output["snapshot_id"] == SNAPSHOT_ID
    assert output["artifact_count"] == 11


def test_cli_returns_nonzero_after_artifact_tampering(tmp_path: Path, capsys) -> None:
    manifest_path = _write_manifest(tmp_path)
    roster_path = tmp_path / "data" / "processed" / "roster.csv"
    roster_path.write_text(roster_path.read_text(encoding="utf-8") + "2026,9999,竄改,測試隊\n", encoding="utf-8")

    exit_code = main([str(manifest_path), "--root", str(tmp_path)])

    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert exit_code == 1
    assert error["valid"] is False
    assert "SHA-256 不一致" in error["error"]
