from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def project_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def ensure_dirs() -> None:
    for rel in [
        "data/raw",
        "data/processed",
        "reports/metrics",
        "reports/figures",
        "models",
        "notes",
    ]:
        project_path(rel).mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    path = project_path("config.yaml")
    if not path.exists():
        return {}
    config: dict[str, Any] = {}
    current_section: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not raw_line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1]
            config[current_section] = {}
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            value = value.strip().strip('"')
            if current_section:
                config[current_section][key.strip()] = value
            else:
                config[key.strip()] = value
    return config


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator in (0, 0.0, None):
        return default
    try:
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return default


def coalesce(row: dict[str, Any], aliases: list[str], default: Any = None) -> Any:
    for key in aliases:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return default
