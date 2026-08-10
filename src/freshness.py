from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


CURRENT_MAX_HOURS = 36
RECENT_MAX_HOURS = 72


def data_freshness(generated_at: object, *, now: datetime | None = None) -> dict[str, Any]:
    raw = str(generated_at or "").strip()
    if not raw:
        return {"status": "unknown", "label": "更新時間未知", "age_hours": None}
    try:
        captured = datetime.fromisoformat(raw)
    except ValueError:
        return {"status": "unknown", "label": "更新時間未知", "age_hours": None}

    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    elapsed_seconds = (
        reference.astimezone(timezone.utc) - captured.astimezone(timezone.utc)
    ).total_seconds()
    age_hours = round(max(elapsed_seconds, 0) / 3600, 1)

    if age_hours <= CURRENT_MAX_HOURS:
        status, label = "current", "資料為最新"
    elif age_hours <= RECENT_MAX_HOURS:
        status, label = "recent", "資料近期更新"
    else:
        status, label = "stale", "資料需更新"
    return {"status": status, "label": label, "age_hours": age_hours}
