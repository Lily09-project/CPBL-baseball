from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd


REPORT_COLUMNS = (
    "player_id",
    "player_name",
    "team",
    "role_or_position",
    "usage_label",
    "usage_value",
    "priority_score",
    "qualified_percentile",
    "evidence_strengths",
    "evidence_risks",
    "evidence_notes",
)

_USAGE_COLUMNS = {"打者": ("pa", "PA", "position"), "投手": ("innings_pitched", "IP", "role")}
_TYPE_SLUGS = {"打者": "hitter", "投手": "pitcher"}
MANIFEST_SCHEMA_VERSION = "1.1"
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {"1.0", MANIFEST_SCHEMA_VERSION}
MANIFEST_REQUIRED_FIELDS = frozenset(
    {"report_id", "schema_version", "data_provenance", "analysis", "players", "methodology"}
)
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_PLAYERS = 4


def _empty_report() -> pd.DataFrame:
    return pd.DataFrame(columns=list(REPORT_COLUMNS))


def build_watchlist_report(
    candidates: pd.DataFrame,
    selected_player_ids: Sequence[object],
    player_type: str,
) -> pd.DataFrame:
    """Build a stable, ordered report frame from ranked official candidates."""
    if player_type not in _USAGE_COLUMNS:
        raise ValueError(f"不支援的球員類型：{player_type}")
    if candidates.empty or not selected_player_ids:
        return _empty_report()

    usage_column, usage_label, role_column = _USAGE_COLUMNS[player_type]
    required = {
        "player_id",
        "player_name",
        "team",
        usage_column,
        "priority_score",
        "qualified_percentile",
        "evidence_strengths",
        "evidence_risks",
        "evidence_notes",
    }
    missing = sorted(required.difference(candidates.columns))
    if missing:
        raise ValueError("球探報告缺少必要欄位：" + ", ".join(missing))

    indexed = candidates.copy()
    indexed["player_id"] = indexed["player_id"].astype("string")
    indexed = indexed.drop_duplicates(subset=["player_id"], keep="first")
    indexed = indexed.set_index("player_id", drop=False)

    ordered_ids: list[str] = []
    for raw_id in selected_player_ids:
        player_id = str(raw_id).strip()
        if player_id and player_id in indexed.index and player_id not in ordered_ids:
            ordered_ids.append(player_id)
        if len(ordered_ids) == 4:
            break
    if not ordered_ids:
        return _empty_report()

    selected = indexed.reindex(ordered_ids).copy()
    if role_column not in selected.columns:
        selected[role_column] = "未記錄"
    selected["role_or_position"] = selected[role_column].fillna("未記錄").replace("", "未記錄")
    report = selected.rename(columns={usage_column: "usage_value"})[
        [
            "player_id",
            "player_name",
            "team",
            "role_or_position",
            "usage_value",
            "priority_score",
            "qualified_percentile",
            "evidence_strengths",
            "evidence_risks",
            "evidence_notes",
        ]
    ].reset_index(drop=True)
    report.insert(4, "usage_label", usage_label)
    return report[list(REPORT_COLUMNS)]


def _markdown_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "未記錄"
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("|", r"\|").replace("\n", "<br>")
    return text


def _markdown_number(value: object) -> str:
    if value is None or pd.isna(value):
        return "未記錄"
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return _markdown_value(value)
    return f"{float(number):.1f}" if float(number) % 1 else str(int(number))


def _json_value(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            pass
    return value


def _validate_report_columns(report: pd.DataFrame) -> None:
    invalid = sorted(set(REPORT_COLUMNS).difference(report.columns))
    if invalid and not report.empty:
        raise ValueError("球探報告輸出缺少欄位：" + ", ".join(invalid))


def _report_methodology() -> dict[str, object]:
    return {
        "score_source": "src.scouting.PRIORITY_WEIGHTS",
        "percentile_scope": "qualified_population(player_type, threshold)",
        "evidence_source": "src.scouting.build_evidence_signals",
        "limitations": [
            "目前官方累計成績不代表傷勢、戰術、守備細節或未來表現。",
            "本報告不是逐場對戰資料，也不是未來表現預測。",
        ],
    }


def _manifest_identity(
    report: pd.DataFrame,
    metadata: Mapping[str, object],
) -> dict[str, object]:
    _validate_report_columns(report)
    players: list[dict[str, object]] = []
    if not report.empty:
        for row in report[list(REPORT_COLUMNS)].to_dict(orient="records"):
            players.append({column: _json_value(row.get(column)) for column in REPORT_COLUMNS})

    analysis = {
        "player_type": _json_value(metadata.get("player_type")),
        "team": _json_value(metadata.get("team", "全部")),
        "qualification": _json_value(metadata.get("qualification")),
        "priority": _json_value(metadata.get("priority")),
        "qualified_count": _json_value(metadata.get("qualified_count")),
        "population_definition": "同一球員類型與資格門檻下的官方累計成績母體",
    }
    provenance = {
        "source": "CPBL 官方處理後資料",
        "snapshot_id": _json_value(metadata.get("snapshot_id")),
        "quality_status": _json_value(metadata.get("quality_status")),
    }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "data_provenance": provenance,
        "analysis": analysis,
        "players": players,
        "methodology": _report_methodology(),
    }


def _manifest_identity_from_payload(manifest: Mapping[str, object]) -> dict[str, object]:
    schema_version = str(manifest.get("schema_version", ""))
    identity = {
        "schema_version": manifest.get("schema_version"),
        "data_provenance": manifest.get("data_provenance"),
        "analysis": manifest.get("analysis"),
        "players": manifest.get("players"),
    }
    if schema_version != "1.0":
        identity["methodology"] = manifest.get("methodology")
    return identity


def _report_id_for_identity(identity: Mapping[str, object]) -> str:
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "rpt-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def build_report_manifest(report: pd.DataFrame, metadata: Mapping[str, object]) -> dict[str, object]:
    """Build a reproducibility manifest for one rendered scouting report."""
    identity = _manifest_identity(report, metadata)
    report_id = _report_id_for_identity(identity)
    return {
        "report_id": report_id,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": _json_value(metadata.get("generated_at")),
        "data_provenance": identity["data_provenance"],
        "analysis": identity["analysis"],
        "players": identity["players"],
        "methodology": identity["methodology"],
    }


def report_manifest_json(manifest: Mapping[str, object]) -> str:
    """Serialize a manifest as deterministic, UTF-8-friendly JSON."""
    required = {"report_id", "schema_version", "data_provenance", "analysis", "players", "methodology"}
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError("報告 Manifest 缺少必要欄位：" + ", ".join(missing))
    return json.dumps(dict(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def verify_report_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    """Verify a report Manifest and return a compact machine-readable summary."""
    if not isinstance(manifest, Mapping):
        raise ValueError("Manifest 頂層內容必須是 JSON 物件")

    missing = sorted(MANIFEST_REQUIRED_FIELDS.difference(manifest))
    if missing:
        raise ValueError("Manifest 缺少必要欄位：" + ", ".join(missing))

    schema_version = str(manifest.get("schema_version", ""))
    if schema_version not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_MANIFEST_SCHEMA_VERSIONS))
        raise ValueError(f"不支援的 Manifest schema version：{schema_version}；可驗證版本：{supported}")

    report_id = manifest.get("report_id")
    if not isinstance(report_id, str) or not re.fullmatch(r"rpt-[0-9a-f]{16}", report_id):
        raise ValueError("Manifest 的 report_id 格式不正確")
    if not isinstance(manifest.get("data_provenance"), Mapping):
        raise ValueError("Manifest 的 data_provenance 必須是 JSON 物件")
    if not isinstance(manifest.get("analysis"), Mapping):
        raise ValueError("Manifest 的 analysis 必須是 JSON 物件")
    if not isinstance(manifest.get("players"), list):
        raise ValueError("Manifest 的 players 必須是 JSON 陣列")
    if len(manifest["players"]) > MAX_MANIFEST_PLAYERS:
        raise ValueError(f"Manifest 的 players 最多 {MAX_MANIFEST_PLAYERS} 位")
    if not isinstance(manifest.get("methodology"), Mapping):
        raise ValueError("Manifest 的 methodology 必須是 JSON 物件")

    for index, player in enumerate(manifest["players"]):
        if not isinstance(player, Mapping):
            raise ValueError(f"Manifest 的 players[{index}] 必須是 JSON 物件")
        player_missing = sorted(set(REPORT_COLUMNS).difference(player))
        if player_missing:
            raise ValueError(
                f"Manifest 的 players[{index}] 缺少必要欄位：" + ", ".join(player_missing)
            )

    expected_report_id = _report_id_for_identity(_manifest_identity_from_payload(manifest))
    if report_id != expected_report_id:
        raise ValueError(f"報告 ID 不一致：檔案 {report_id}；重算結果 {expected_report_id}")

    provenance = manifest["data_provenance"]
    return {
        "valid": True,
        "report_id": report_id,
        "schema_version": schema_version,
        "snapshot_id": provenance.get("snapshot_id"),
        "player_count": len(manifest["players"]),
    }


def verify_report_manifest_file(path: str | Path) -> dict[str, object]:
    """Read and verify one UTF-8 JSON Manifest without modifying the file."""
    manifest_path = Path(path)
    try:
        file_size = manifest_path.stat().st_size
    except OSError as exc:
        raise ValueError(f"Manifest 無法讀取：{manifest_path.name}") from exc
    if file_size > MAX_MANIFEST_BYTES:
        raise ValueError(f"Manifest 檔案過大：上限 {MAX_MANIFEST_BYTES} bytes")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest JSON 無法解析：{manifest_path.name}") from exc
    except UnicodeError as exc:
        raise ValueError(f"Manifest 必須是 UTF-8 JSON：{manifest_path.name}") from exc
    except OSError as exc:
        raise ValueError(f"Manifest 無法讀取：{manifest_path.name}") from exc
    except RecursionError as exc:
        raise ValueError(f"Manifest JSON 結構過深：{manifest_path.name}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Manifest 頂層內容必須是 JSON 物件")
    return verify_report_manifest(payload)
def report_markdown(report: pd.DataFrame, metadata: Mapping[str, object]) -> str:
    """Render a portable Markdown report with explicit provenance and limits."""
    _validate_report_columns(report)

    def meta(label: str, key: str, default: str = "未記錄") -> str:
        value = metadata.get(key, default)
        return f"| {label} | {_markdown_value(value)} |"

    lines = [
        "# CPBL 球探報告",
        "",
        "> 本報告由 CPBL 官方公開資料的目前已驗證版本產生；不預測未來表現，也不構成名單或投注建議。",
        "",
        "## 報告條件",
        "",
        "| 項目 | 內容 |",
        "| --- | --- |",
        meta("球員類型", "player_type"),
        meta("資格門檻", "qualification"),
        meta("評估重點", "priority"),
        meta("符合門檻母體", "qualified_count"),
        meta("資料快照", "snapshot_id"),
        meta("資料產生時間", "generated_at"),
        meta("品質狀態", "quality_status"),
        meta("報告 ID", "report_id"),
        "",
        "## 觀察名單",
        "",
    ]
    if report.empty:
        lines.append("目前沒有選取球員，請回到球探報告頁建立觀察名單。")
    else:
        lines.extend(
            [
                "| 球員 ID | 球員 | 球隊 | 位置 / 角色 | 資格量 | 評估分數 | 母體百分位 | 優勢訊號 | 風險訊號 | 資料註記 |",
                "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
            ]
        )
        for row in report.itertuples(index=False):
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_value(row.player_id),
                        _markdown_value(row.player_name),
                        _markdown_value(row.team),
                        _markdown_value(row.role_or_position),
                        _markdown_value(f"{_markdown_number(row.usage_value)} {row.usage_label}"),
                        _markdown_number(row.priority_score),
                        _markdown_value(f"{_markdown_number(row.qualified_percentile)} 百分位"),
                        _markdown_value(row.evidence_strengths),
                        _markdown_value(row.evidence_risks),
                        _markdown_value(row.evidence_notes),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## 判讀限制",
            "",
            "- 評估分數是固定權重的資料衍生訊號，百分位只在符合球員類型與資格門檻的聯盟母體內計算。",
            "- 優勢與風險訊號只反映目前官方累計成績，無法代表傷勢、戰術、守備細節、對手強度或未來表現。",
            "- 本報告不是逐場對戰資料，也不是未來表現預測；請搭配球員個人頁與原始官方資料解讀。",
        ]
    )
    return "\n".join(lines) + "\n"


def report_filename(player_type: str, snapshot_id: object) -> str:
    if player_type not in _TYPE_SLUGS:
        raise ValueError(f"不支援的球員類型：{player_type}")
    raw_snapshot = str(snapshot_id or "latest").strip()
    safe_snapshot = re.sub(r"[^A-Za-z0-9_-]+", "-", raw_snapshot).strip("-") or "latest"
    return f"cpbl_scouting_report_{_TYPE_SLUGS[player_type]}_{safe_snapshot}.md"


def manifest_filename(player_type: str, snapshot_id: object) -> str:
    return report_filename(player_type, snapshot_id).replace(".md", ".manifest.json")