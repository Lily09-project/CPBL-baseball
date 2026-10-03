"""Build a minimal, allowlisted static release; never publish the repository root."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ASSETS = ("index.html", "styles.css", "app.js")
OUTPUT_FILES = frozenset((*ASSETS, "data.json", "integrity.json", ".nojekyll"))
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20000


def safe_path(root: Path, relative: str) -> Path:
    candidate = root / relative
    resolved_root = root.resolve()
    candidate.resolve().relative_to(resolved_root)
    if any(path.is_symlink() for path in (candidate, *candidate.parents) if path != resolved_root.parent):
        raise ValueError("Symlinks are not valid public inputs")
    if not candidate.is_file() or candidate.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Missing or oversized public input: " + relative)
    return candidate


def number(value: str | None) -> float | None:
    if value is None or value.strip().lower() in {"", "nan", "none", "null"}:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite public number")
    return result


def read_rows(root: Path, path: str, columns: list[tuple[str, str, str]]) -> list[dict]:
    source = safe_path(root, path)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {key for key, _, _ in columns}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing required public columns: " + path)
        rows = []
        for raw in reader:
            if len(rows) >= MAX_ROWS:
                raise ValueError("Public row limit exceeded")
            row = {}
            for key, _, kind in columns:
                value = raw.get(key)
                if kind == "number":
                    row[key] = number(value)
                else:
                    text = str(value or "").strip()
                    if len(text) > 500:
                        raise ValueError("Oversized public cell")
                    if kind == "date" and text:
                        datetime.fromisoformat(text)
                    row[key] = text or None
            rows.append(row)
    if not rows:
        raise ValueError("Empty public dataset: " + path)
    return rows


def dataset(root: Path, key: str, label: str, path: str, columns: list[tuple[str, str, str]],
            *, identity: list[str], group: str, group_label: str, value: str, date: str | None,
            chart_label: str, sort: str | None = None, name: str | None = None,
            secondary: str | None = None, minimum: dict | None = None) -> dict:
    rows = read_rows(root, path, columns)
    ids = [json.dumps([row[column] for column in identity], ensure_ascii=False) for row in rows]
    if any(any(row[column] is None for column in identity) for row in rows) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate public identity: " + key)
    return {"id": key, "label": label, "fields": [{"key": k, "label": title, "kind": kind} for k, title, kind in columns],
            "identity": identity, "group": group, "groupLabel": group_label, "value": value,
            "date": date, "chartLabel": chart_label, "sort": sort or date or value,
            "name": name or identity[-1], "secondary": secondary, "minimum": minimum, "rows": rows}


def read_json(root: Path, path: str) -> dict:
    value = json.loads(safe_path(root, path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Public metadata must be an object")
    return value


def metric_dataset(root: Path, path: str, keys: tuple[str, ...], group_key: str | None = None) -> dict:
    payload = read_json(root, path)
    rows = []
    if group_key:
        payload = payload[group_key]
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            rows.append({"model": "預先計算結果", "metric": key.upper(), "value": float(value)})
    if not rows:
        raise ValueError("Missing public evaluation metrics")
    return {"id": "metrics", "label": "模型評估", "fields": [
        {"key": "model", "label": "模型", "kind": "text"},
        {"key": "metric", "label": "指標", "kind": "text"},
        {"key": "value", "label": "指標值", "kind": "number"}],
        "identity": ["metric"], "group": "model", "groupLabel": "模型", "value": "value",
        "date": None, "chartLabel": "評估結果（各指標單位不同，請以明細解讀）", "sort": "metric",
        "name": "metric", "secondary": None, "minimum": None, "rows": rows}


def validate_payload(payload: dict) -> None:
    if payload["schema_version"] != "pages-data/1" or not payload["datasets"]:
        raise ValueError("Invalid public schema")
    for item in payload["datasets"]:
        keys = {field["key"] for field in item["fields"]}
        if not {item["group"], item["value"], *item["identity"]}.issubset(keys):
            raise ValueError("Dataset configuration references unpublished columns")
        if item["date"] and item["date"] not in keys:
            raise ValueError("Missing public date")
        for row in item["rows"]:
            if set(row) != keys:
                raise ValueError("Row violates public column allowlist")
    json.dumps(payload, allow_nan=False)


def write_release(root: Path, payload: dict) -> Path:
    validate_payload(payload)
    destination = root / "pages-dist"
    if destination.is_symlink():
        raise ValueError("Invalid output symlink")
    destination.mkdir(exist_ok=True)
    if any(path.name not in OUTPUT_FILES or path.is_symlink() or not path.is_file() for path in destination.iterdir()):
        raise ValueError("Unexpected output inventory; refusing to publish")
    for name in ASSETS:
        shutil.copyfile(safe_path(root, "web/" + name), destination / name)
    content = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("Public bundle too large")
    (destination / "data.json").write_text(content, encoding="utf-8", newline="\n")
    integrity = {"schema_version": "pages-integrity/1",
                 "data_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                 "files": list((*ASSETS, "data.json", ".nojekyll"))}
    (destination / "integrity.json").write_text(json.dumps(integrity, indent=2) + "\n", encoding="utf-8")
    (destination / ".nojekyll").write_text("", encoding="utf-8")
    if {path.name for path in destination.iterdir()} != OUTPUT_FILES:
        raise ValueError("Incomplete public output")
    return destination


def build_payload(root: Path) -> dict:
    from src.public_release_manifest import verify_public_release_manifest_file
    manifest_path = safe_path(root, "reports/metrics/public_release_manifest.json")
    verify_public_release_manifest_file(manifest_path, root=root)
    manifest = read_json(root, "reports/metrics/public_release_manifest.json")
    teams_columns = [("season", "球季", "number"), ("team", "球隊", "text"), ("games", "場次", "number"),
                     ("wins", "勝", "number"), ("losses", "敗", "number"), ("win_pct", "勝率", "number")]
    teams = dataset(root, "teams", "球隊戰績", "data/processed/teams.csv", teams_columns,
                    identity=["season", "team"], group="team", group_label="球隊",
                    value="win_pct", date=None, name="team", chart_label="球隊勝率")
    batters_columns = [("player_id", "球員 ID", "text"), ("player_name", "球員", "text"),
                       ("team", "球隊", "text"), ("pa", "打席", "number"),
                       ("batting_average", "打擊率", "number"), ("ops", "OPS", "number"),
                       ("home_runs", "全壘打", "number"), ("player_value_score", "分析分數", "number")]
    batters = dataset(root, "batters", "打者分析", "data/processed/batters_scored.csv", batters_columns,
                      identity=["player_id"], group="team", group_label="球隊", name="player_name",
                      value="player_value_score", date=None, chart_label="打者分析分數（非官方評分）",
                      minimum={"key": "pa", "label": "最低打席", "value": 50})
    pitchers_columns = [("player_id", "球員 ID", "text"), ("player_name", "球員", "text"),
                        ("team", "球隊", "text"), ("innings_pitched", "局數", "number"),
                        ("era", "防禦率", "number"), ("whip", "WHIP", "number"),
                        ("strikeouts", "三振", "number"), ("player_value_score", "分析分數", "number")]
    pitchers = dataset(root, "pitchers", "投手分析", "data/processed/pitchers_scored.csv", pitchers_columns,
                       identity=["player_id"], group="team", group_label="球隊", name="player_name",
                       value="player_value_score", date=None, chart_label="投手分析分數（非官方評分）",
                       minimum={"key": "innings_pitched", "label": "最低局數", "value": 20})
    roster_columns = [("player_id", "球員 ID", "text"), ("player_name", "球員", "text"),
                      ("team", "球隊", "text"), ("roster_status", "名單狀態", "text"),
                      ("player_type", "類型", "text"), ("player_value_score", "分析分數", "number")]
    roster = dataset(root, "roster", "完整球員名單", "data/processed/players_scored.csv", roster_columns,
                     identity=["player_id", "team", "player_type"], group="team", group_label="球隊",
                     value="player_value_score", date=None, name="player_name", chart_label="具統計紀錄球員的分析分數")
    history_columns = [("season", "球季", "number"), ("snapshot_id", "快照 ID", "text"), ("captured_at", "資料時間", "date"),
                       ("roster_rows", "名單人數", "number"), ("hitter_rows", "打者筆數", "number"),
                       ("pitcher_rows", "投手筆數", "number"), ("total_rows", "總筆數", "number")]
    history = dataset(root, "history", "更新歷程", "data/processed/snapshot_history.csv", history_columns,
                      identity=["snapshot_id"], group="season", group_label="球季",
                      value="total_rows", date="captured_at", chart_label="公開快照筆數", sort="captured_at")
    for item in (batters, pitchers, roster):
        if any(not row["player_id"].isdigit() or len(row["player_id"]) != 10 for row in item["rows"]):
            raise ValueError("Invalid public player identity")
    return {"schema_version": "pages-data/1", "kind": "cpbl", "project": "CPBL-baseball",
            "title": "中職球探資料室", "brand": "CPBL SCOUTING DESK",
            "source": {"mode": "官方資料快照", "range": manifest["generated_at"][:10],
                       "captured_at": manifest["generated_at"], "release_id": manifest["release_id"]},
            "notice": "使用已核對的公開快照，非即時戰績；分析分數由本專案計算。",
            "disclaimer": "非 CPBL 官方服務。資料以 CPBL 官方公告為準；分數僅供分析參考。",
            "quality": {"來源": "CPBL 官方公開資料", "資料完整性": "發布 Manifest 與逐檔 SHA-256 核對通過",
                        "資料更新": manifest["generated_at"], "發布版本": manifest["release_id"],
                        "球員 ID": "保留十位數字與前導零", "更新限制": "官方來源存取異常時保留上一份核對快照，不改寫更新日期"},
            "datasets": [teams, batters, pitchers, roster, history]}

def build(root: Path = ROOT) -> Path:
    return write_release(root, build_payload(root))


if __name__ == "__main__":
    print("Built verified static release:", build())
