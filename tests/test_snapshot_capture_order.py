from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

import pandas as pd

from src.snapshots import create_processed_snapshot
from test_snapshots import write_processed_fixture


def test_snapshot_lineage_uses_capture_order_after_directory_copy(tmp_path: Path):
    processed = tmp_path / "processed"
    root = tmp_path / "snapshots"
    quality = {"quality_status": "pass"}
    write_processed_fixture(processed)
    old = create_processed_snapshot(processed, root, quality,
                                    captured_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    write_processed_fixture(processed, changed=True)
    recent = create_processed_snapshot(processed, root, quality,
                                       captured_at=datetime(2026, 8, 2, tzinfo=timezone.utc))
    # Copy/extraction order must not become the semantic snapshot chronology.
    os.utime(root / recent["relative_path"], (100, 100))
    os.utime(root / old["relative_path"], (200, 200))
    path = processed / "batters_scored.csv"
    frame = pd.read_csv(path, dtype={"player_id": "string"})
    frame.loc[0, "ops"] = 0.85
    frame.to_csv(path, index=False)
    current = create_processed_snapshot(processed, root, quality,
                                        captured_at=datetime(2026, 8, 3, tzinfo=timezone.utc))
    assert current["previous_snapshot_id"] == recent["snapshot_id"]
    assert current["diff"]["files"]["batters_scored.csv"]["added_rows"] == 0
    assert current["diff"]["files"]["batters_scored.csv"]["removed_rows"] == 0
    assert current["diff"]["files"]["batters_scored.csv"]["changed_rows"] == 1
