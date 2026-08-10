from datetime import datetime, timezone

from src.freshness import data_freshness


NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def test_data_freshness_marks_recent_verified_data_as_current() -> None:
    freshness = data_freshness("2026-08-10T00:00:00+00:00", now=NOW)

    assert freshness["status"] == "current"
    assert freshness["label"] == "資料為最新"
    assert freshness["age_hours"] == 12.0


def test_data_freshness_marks_old_data_as_stale() -> None:
    freshness = data_freshness("2026-08-06T12:00:00+00:00", now=NOW)

    assert freshness["status"] == "stale"
    assert freshness["label"] == "資料需更新"
    assert freshness["age_hours"] == 96.0


def test_data_freshness_marks_intermediate_age_as_recent() -> None:
    freshness = data_freshness("2026-08-08T12:00:00+00:00", now=NOW)

    assert freshness["status"] == "recent"
    assert freshness["label"] == "資料近期更新"
    assert freshness["age_hours"] == 48.0


def test_data_freshness_handles_missing_or_invalid_timestamp() -> None:
    assert data_freshness("", now=NOW)["status"] == "unknown"
    assert data_freshness("not-a-date", now=NOW)["label"] == "更新時間未知"
