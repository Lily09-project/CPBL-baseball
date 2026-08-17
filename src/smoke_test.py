from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_quality import REQUIRED_FILES, load_data_quality_report
from src.log5_matchup import calculate_log5_probability
from src.preprocess import preprocess
from src.utils import project_path


def main() -> None:
    if any(not project_path("data/processed", name).exists() for name in REQUIRED_FILES):
        preprocess(mode="api")
    report = load_data_quality_report()
    checks = {
        "data source mode is api": report["mode"] == "api",
        "data quality passed": report["quality_status"] in {"pass", "warning"},
        "player coverage is complete": report["available_player_count"] >= 200,
        "LOG5 calculation returns a result": (
            calculate_log5_probability(0.36, 0.32, 0.33) is not None
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise RuntimeError(f"smoke test failed: {', '.join(failed_checks)}")
    print("smoke test passed")


if __name__ == "__main__":
    main()
