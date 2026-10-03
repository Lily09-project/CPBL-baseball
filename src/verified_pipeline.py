"""Run the verified pipeline with an explicit temporary-source exit code."""
from __future__ import annotations

import traceback
from collections.abc import Callable

from run_all import main
from src.source_failure import TemporaryOfficialSourceError

TEMPORARY_SOURCE_EXIT_CODE = 75


def run_verified_pipeline(runner: Callable[[], None] = main) -> int:
    try:
        runner()
    except TemporaryOfficialSourceError:
        traceback.print_exc()
        return TEMPORARY_SOURCE_EXIT_CODE
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_verified_pipeline())
