from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils import project_path


PUBLIC_RELEASE_SCHEMA_VERSION = "1.0"
PUBLIC_RELEASE_MANIFEST_PATH = Path("reports/metrics/public_release_manifest.json")
PUBLIC_RELEASE_ARTIFACTS = (
    "data/processed/teams.csv",
    "data/processed/roster.csv",
    "data/processed/batters_scored.csv",
    "data/processed/pitchers_scored.csv",
    "data/processed/players_scored.csv",
    "data/processed/player_movements.csv",
    "data/processed/snapshot_history.csv",
    "data/processed/player_metric_history.csv",
    "reports/metrics/data_quality_report.json",
    "reports/metrics/analysis_validation.json",
    "reports/metrics/release_health.json",
)
MAX_PUBLIC_RELEASE_MANIFEST_BYTES = 2 * 1024 * 1024
_REQUIRED_FIELDS = frozenset(
    {"release_id", "schema_version", "generated_at", "snapshot_id", "artifact_count", "artifacts"}
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_metadata(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    if path.is_symlink():
        raise ValueError(f"公開發布檔案禁止使用 symlink：{relative_path}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"公開發布檔案不可離開專案根目錄：{relative_path}") from exc
    if not path.is_file():
        raise ValueError(f"缺少公開發布檔案：{relative_path}")
    metadata: dict[str, Any] = {
        "path": relative_path,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    if path.suffix.lower() == ".csv":
        try:
            frame = pd.read_csv(path)
        except (OSError, UnicodeError, pd.errors.ParserError) as exc:
            raise ValueError(f"公開 CSV 無法讀取：{relative_path}") from exc
        metadata["row_count"] = int(len(frame))
        metadata["columns"] = [str(column) for column in frame.columns]
    else:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError(f"公開 JSON 無法讀取：{relative_path}") from exc
        if not isinstance(payload, Mapping):
            raise ValueError(f"公開 JSON 頂層必須是 object：{relative_path}")
    return metadata


def _manifest_identity(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "release_id"}


def _release_id(identity: Mapping[str, Any]) -> str:
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "rel-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def build_public_release_manifest(
    root: Path,
    *,
    generated_at: str,
    snapshot_id: str,
) -> dict[str, Any]:
    """Build a deterministic integrity manifest for the public release bundle."""
    project_root = Path(root).resolve()
    artifacts = [_artifact_metadata(project_root, path) for path in PUBLIC_RELEASE_ARTIFACTS]
    identity = {
        "schema_version": PUBLIC_RELEASE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "snapshot_id": snapshot_id,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    return {"release_id": _release_id(identity), **identity}


def write_public_release_manifest(
    manifest: Mapping[str, Any],
    path: Path | None = None,
) -> Path:
    output_path = path or project_path(str(PUBLIC_RELEASE_MANIFEST_PATH))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dict(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _validate_artifact_inventory(artifacts: object) -> list[Mapping[str, Any]]:
    if not isinstance(artifacts, list):
        raise ValueError("Manifest 的 artifacts 必須是 JSON 陣列")
    if not all(isinstance(item, Mapping) for item in artifacts):
        raise ValueError("Manifest 的 artifacts 每一項都必須是 JSON object")
    paths = [str(item.get("path", "")) for item in artifacts]
    if paths != list(PUBLIC_RELEASE_ARTIFACTS) or len(paths) != len(set(paths)):
        raise ValueError("Manifest 公開檔案清單與允許發布的 allowlist 不一致")
    return artifacts


def verify_public_release_manifest(
    manifest: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Verify manifest identity and every public artifact without modifying files."""
    if not isinstance(manifest, Mapping):
        raise ValueError("Manifest 頂層內容必須是 JSON object")
    missing = sorted(_REQUIRED_FIELDS.difference(manifest))
    if missing:
        raise ValueError("Manifest 缺少必要欄位：" + ", ".join(missing))
    if manifest.get("schema_version") != PUBLIC_RELEASE_SCHEMA_VERSION:
        raise ValueError("Manifest schema_version 不相容")

    generated_at = str(manifest.get("generated_at", ""))
    try:
        datetime.fromisoformat(generated_at)
    except ValueError as exc:
        raise ValueError("Manifest generated_at 不是有效 ISO-8601 時間") from exc
    snapshot_id = str(manifest.get("snapshot_id", "")).strip()
    if not snapshot_id:
        raise ValueError("Manifest snapshot_id 不可為空")

    artifacts = _validate_artifact_inventory(manifest.get("artifacts"))
    if manifest.get("artifact_count") != len(PUBLIC_RELEASE_ARTIFACTS):
        raise ValueError("Manifest artifact_count 與公開檔案清單不一致")

    release_id = manifest.get("release_id")
    expected_release_id = _release_id(_manifest_identity(manifest))
    if not isinstance(release_id, str) or not re.fullmatch(r"rel-[0-9a-f]{24}", release_id):
        raise ValueError("Manifest release_id 格式不正確")
    if release_id != expected_release_id:
        raise ValueError(f"Manifest release_id 不一致：檔案 {release_id}；重算結果 {expected_release_id}")

    project_root = Path(root).resolve()
    for artifact in artifacts:
        relative_path = str(artifact["path"])
        observed = _artifact_metadata(project_root, relative_path)
        if artifact.get("sha256") != observed["sha256"]:
            raise ValueError(f"公開檔案 SHA-256 不一致：{relative_path}")
        if artifact.get("size_bytes") != observed["size_bytes"]:
            raise ValueError(f"公開檔案大小不一致：{relative_path}")
        if relative_path.endswith(".csv"):
            if artifact.get("row_count") != observed["row_count"]:
                raise ValueError(f"公開 CSV 列數不一致：{relative_path}")
            if artifact.get("columns") != observed["columns"]:
                raise ValueError(f"公開 CSV 欄位不一致：{relative_path}")

    return {
        "valid": True,
        "release_id": release_id,
        "schema_version": PUBLIC_RELEASE_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "artifact_count": len(artifacts),
    }


def verify_public_release_manifest_file(
    path: str | Path,
    root: Path | None = None,
) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        file_size = manifest_path.stat().st_size
    except OSError as exc:
        raise ValueError(f"Manifest 無法讀取：{manifest_path.name}") from exc
    if file_size > MAX_PUBLIC_RELEASE_MANIFEST_BYTES:
        raise ValueError(f"Manifest 檔案過大：上限 {MAX_PUBLIC_RELEASE_MANIFEST_BYTES} bytes")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"Manifest JSON 無法讀取：{manifest_path.name}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Manifest 頂層內容必須是 JSON object")
    return verify_public_release_manifest(payload, Path(root) if root is not None else project_path())
