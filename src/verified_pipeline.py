"""Run the verified pipeline with explicit, fail-visible source exit codes."""
from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from run_all import main
from src.source_failure import OfficialSourceBlockedError, TemporaryOfficialSourceError
from src.utils import project_path

TEMPORARY_SOURCE_EXIT_CODE = 75
SOURCE_BLOCKED_EXIT_CODE = 77
# A temporary outage may defer a scheduled refresh, but only while the
# published release is still recent. Past this age the deferral turns red.
MAX_DEFERRED_RELEASE_AGE_DAYS = 3


def published_release_age_days(manifest_path: Path, now: datetime) -> float | None:
    """Return the age of the currently published release, or None if unknown."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        generated_at = datetime.fromisoformat(str(manifest["generated_at"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if generated_at.tzinfo is None:
        return None
    return (now - generated_at).total_seconds() / 86400


def run_verified_pipeline(
    runner: Callable[[], None] = main,
    *,
    manifest_path: Path | None = None,
    now: datetime | None = None,
) -> int:
    # Read the published release age before the run so a failing run can never
    # influence it; the pipeline itself never publishes partial data.
    manifest_path = manifest_path or project_path("reports/metrics/public_release_manifest.json")
    age_days = published_release_age_days(manifest_path, now or datetime.now(timezone.utc))
    try:
        runner()
    except OfficialSourceBlockedError:
        traceback.print_exc()
        return SOURCE_BLOCKED_EXIT_CODE
    except TemporaryOfficialSourceError:
        traceback.print_exc()
        if age_days is None or age_days > MAX_DEFERRED_RELEASE_AGE_DAYS:
            shown = "unknown" if age_days is None else f"{age_days:.1f}"
            print(
                f"Published release age is {shown} days (limit {MAX_DEFERRED_RELEASE_AGE_DAYS}); "
                "a temporary source failure can no longer defer this refresh.",
                file=sys.stderr,
            )
            return 1
        return TEMPORARY_SOURCE_EXIT_CODE
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_verified_pipeline())
