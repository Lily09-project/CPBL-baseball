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
    assert report["mode"] == "api"
    assert report["quality_status"] in {"pass", "warning"}
    assert report["available_player_count"] >= 200
    assert calculate_log5_probability(0.36, 0.32, 0.33) is not None
    print("smoke test passed")


if __name__ == "__main__":
    main()
