from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from src.public_release_manifest import (
    PUBLIC_RELEASE_ARTIFACTS,
    PUBLIC_RELEASE_SCHEMA_VERSION,
    build_public_release_manifest,
    verify_public_release_manifest,
    verify_public_release_manifest_file,
    write_public_release_manifest,
)


GENERATED_AT = "2026-08-20T17:58:03+08:00"
SNAPSHOT_ID = "20260820T095803Z-test12345678"


def write_public_release_fixture(root: Path) -> None:
    processed = root / "data" / "processed"
    metrics = root / "reports" / "metrics"
    processed.mkdir(parents=True)
    metrics.mkdir(parents=True)

    frames = {
        "teams.csv": pd.DataFrame(
            [{"season": 2026, "team": "測試隊", "wins": 1, "losses": 0, "win_pct": 1.0}]
        ),
        "roster.csv": pd.DataFrame(
            [{"season": 2026, "player_id": "0001", "player_name": "測試球員", "team": "測試隊"}]
        ),
        "batters_scored.csv": pd.DataFrame(
            [{"season": 2026, "player_id": "0001", "player_name": "測試球員", "team": "測試隊"}]
        ),
        "pitchers_scored.csv": pd.DataFrame(
            [{"season": 2026, "player_id": "0002", "player_name": "測試投手", "team": "測試隊"}]
        ),
        "players_scored.csv": pd.DataFrame(
            [
                {"season": 2026, "player_id": "0001", "player_name": "測試球員", "team": "測試隊"},
                {"season": 2026, "player_id": "0002", "player_name": "測試投手", "team": "測試隊"},
            ]
        ),
        "player_movements.csv": pd.DataFrame(
            [{"player_id": "0001", "player_name": "測試球員", "change_status": "changed"}]
        ),
        "snapshot_history.csv": pd.DataFrame(
            [{"snapshot_id": SNAPSHOT_ID, "captured_at": GENERATED_AT, "season": 2026}]
        ),
        "player_metric_history.csv": pd.DataFrame(
            [{"snapshot_id": SNAPSHOT_ID, "player_id": "0001", "player_name": "測試球員"}]
        ),
    }
    for name, frame in frames.items():
        frame.to_csv(processed / name, index=False)

    for name, payload in {
        "data_quality_report.json": {
            "mode": "api",
            "generated_at": GENERATED_AT,
            "quality_status": "pass",
            "snapshot": {"snapshot_id": SNAPSHOT_ID},
        },
        "analysis_validation.json": {
            "schema_version": "1.0",
            "generated_at": GENERATED_AT,
            "latest_snapshot_id": SNAPSHOT_ID,
        },
        "release_health.json": {
            "schema_version": "1.0",
            "generated_at": GENERATED_AT,
            "status": "passed",
            "snapshot_id": SNAPSHOT_ID,
        },
    }.items():
        (metrics / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _manifest(root: Path) -> dict[str, object]:
    write_public_release_fixture(root)
    return build_public_release_manifest(
        root,
        generated_at=GENERATED_AT,
        snapshot_id=SNAPSHOT_ID,
    )


def test_build_and_verify_public_release_manifest(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)

    result = verify_public_release_manifest(manifest, tmp_path)

    assert result == {
        "valid": True,
        "release_id": manifest["release_id"],
        "schema_version": PUBLIC_RELEASE_SCHEMA_VERSION,
        "snapshot_id": SNAPSHOT_ID,
        "artifact_count": len(PUBLIC_RELEASE_ARTIFACTS),
    }
    assert [item["path"] for item in manifest["artifacts"]] == list(PUBLIC_RELEASE_ARTIFACTS)
    csv_artifact = next(item for item in manifest["artifacts"] if item["path"].endswith("roster.csv"))
    assert csv_artifact["row_count"] == 1
    assert csv_artifact["columns"] == ["season", "player_id", "player_name", "team"]


def test_manifest_verification_is_independent_of_text_line_endings(tmp_path: Path) -> None:
    write_public_release_fixture(tmp_path)
    roster_path = tmp_path / "data" / "processed" / "roster.csv"
    roster_path.write_bytes(roster_path.read_bytes().replace(b"\r\n", b"\n"))
    manifest = build_public_release_manifest(
        tmp_path,
        generated_at=GENERATED_AT,
        snapshot_id=SNAPSHOT_ID,
    )

    roster_path.write_bytes(roster_path.read_bytes().replace(b"\n", b"\r\n"))

    assert verify_public_release_manifest(manifest, tmp_path)["valid"] is True


def test_verifier_rejects_tampered_csv(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    roster_path = tmp_path / "data" / "processed" / "roster.csv"
    roster_path.write_text(roster_path.read_text(encoding="utf-8") + "2026,9999,竄改球員,測試隊\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 不一致"):
        verify_public_release_manifest(manifest, tmp_path)


def test_verifier_rejects_forged_csv_shape_metadata(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    forged = copy.deepcopy(manifest)
    roster = next(item for item in forged["artifacts"] if item["path"].endswith("roster.csv"))
    roster["row_count"] = 999

    with pytest.raises(ValueError, match="release_id 不一致"):
        verify_public_release_manifest(forged, tmp_path)


def test_verifier_rejects_release_id_tampering(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["release_id"] = "rel-" + "0" * 24

    with pytest.raises(ValueError, match="release_id 不一致"):
        verify_public_release_manifest(manifest, tmp_path)


@pytest.mark.parametrize("unsafe_path", ["../.env", "C:/Users/user/.env", "/tmp/.env"])
def test_verifier_rejects_unsafe_artifact_paths(tmp_path: Path, unsafe_path: str) -> None:
    manifest = _manifest(tmp_path)
    manifest["artifacts"][0]["path"] = unsafe_path

    with pytest.raises(ValueError, match="公開檔案清單"):
        verify_public_release_manifest(manifest, tmp_path)


def test_verifier_rejects_duplicate_or_unexpected_artifacts(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["artifacts"].append(copy.deepcopy(manifest["artifacts"][0]))

    with pytest.raises(ValueError, match="公開檔案清單"):
        verify_public_release_manifest(manifest, tmp_path)


def test_verifier_rejects_symlinked_public_artifact(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(Path, "is_symlink", lambda path: path.name == "roster.csv")

    with pytest.raises(ValueError, match="symlink"):
        verify_public_release_manifest(manifest, tmp_path)


def test_manifest_file_round_trip(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = write_public_release_manifest(
        manifest,
        tmp_path / "reports" / "metrics" / "public_release_manifest.json",
    )

    result = verify_public_release_manifest_file(manifest_path, root=tmp_path)

    assert result["valid"] is True
    assert result["release_id"] == manifest["release_id"]


def test_manifest_file_rejects_oversized_input(tmp_path: Path) -> None:
    manifest_path = tmp_path / "public_release_manifest.json"
    manifest_path.write_bytes(b"{" + b" " * (2 * 1024 * 1024) + b"}")

    with pytest.raises(ValueError, match="檔案過大"):
        verify_public_release_manifest_file(manifest_path, root=tmp_path)
