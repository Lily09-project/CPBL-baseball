# Player Snapshot Movements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and display auditable player-level changes between the latest two verified CPBL snapshots.

**Architecture:** A focused `src/movements.py` module owns snapshot-pair resolution, long-form delta calculation, validation, and CSV generation. `run_all.py` invokes it only after quality passes and the base snapshot exists. `app.py` loads the optional derived output and renders compact overview and player-detail sections without adding a new page.

**Tech Stack:** Python 3, pandas, Streamlit, pytest, existing CSV snapshot manifests.

## Global Constraints

- Preserve `player_id` as a string with leading zeroes.
- Compare only verified snapshots linked by `previous_snapshot_id`.
- Do not describe cumulative snapshot deltas as game-level or predictive trends.
- Keep `data/snapshots/` and raw HTML ignored; retain only `data/processed/player_movements.csv` as the public derived artifact.
- Do not add dependencies or a new sidebar page.

---

### Task 1: Movement calculation contract

**Files:**
- Create: `src/movements.py`
- Create: `tests/test_movements.py`

**Interfaces:**
- Produces: `MOVEMENT_COLUMNS`, `compare_player_snapshots(current: dict[str, pd.DataFrame], previous: dict[str, pd.DataFrame], metadata: dict[str, str]) -> pd.DataFrame`.
- Consumes: hitter and pitcher DataFrames keyed by `player_id`.

- [ ] Write failing tests for hitter deltas, pitcher lower-is-better favorable deltas, new players, and duplicate IDs.
- [ ] Run `python -m pytest tests/test_movements.py -q` and confirm imports fail because `src.movements` does not exist.
- [ ] Implement long-form rows for the documented metric sets, numeric coercion, stable ordering, null previous values for new players, and duplicate-key rejection.
- [ ] Run the focused tests and confirm all pass.

### Task 2: Snapshot resolution and pipeline output

**Files:**
- Modify: `src/movements.py`
- Modify: `src/snapshots.py`
- Modify: `run_all.py`
- Modify: `tests/test_movements.py`
- Modify: `tests/test_run_all.py`
- Modify: `tests/test_snapshots.py`

**Interfaces:**
- Produces: `generate_player_movements(snapshot_root: Path, snapshot: dict, output_path: Path) -> dict[str, object]` returning status, row count, baseline/current IDs and timestamps.
- Consumes: the manifest returned by `create_processed_snapshot`.

- [ ] Write failing tests for predecessor resolution, schema-valid baseline-pending output, metadata attachment, and exclusion of derived CSV files from base snapshots.
- [ ] Run the focused tests and confirm the new functions/calls are missing.
- [ ] Restrict snapshots to the five base processed files, implement manifest-linked movement generation, write `player_movements.csv`, and attach movement metadata to the saved quality report.
- [ ] Add the movement path to the printed processed outputs and rerun focused tests.

### Task 3: Dashboard integration

**Files:**
- Modify: `app.py`
- Modify: `src/theme.py`
- Modify: `tests/test_streamlit_pages.py`

**Interfaces:**
- Consumes: optional `player_movements.csv` loaded through the existing `load_csv` helper.
- Produces: `movement_focus_rows`, `render_movement_focus`, and `render_player_movements` helpers.

- [ ] Write failing Streamlit tests requiring "評估分數變化焦點", "前次快照變化", snapshot-period labels, and the cumulative/non-predictive limitation.
- [ ] Run the targeted frontend tests and confirm the terms and sections are absent.
- [ ] Load movements, add metric labels/formatting, render overview focus rows and player-level metric deltas, and add only the CSS needed for equal-height movement cards and mobile stacking.
- [ ] Run targeted Streamlit tests and inspect both pages at desktop and 375px widths.

### Task 4: Documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `tests/test_project_docs.py`
- Generate: `data/processed/player_movements.csv`
- Modify: `reports/metrics/data_quality_report.json`

**Interfaces:**
- Documents: public artifact, snapshot basis, limitations, and reproduction command.

- [ ] Write a failing documentation assertion for `player_movements.csv`, snapshot comparison, and the cumulative-data limitation.
- [ ] Update README and regenerate official data through `run_project.bat --check`.
- [ ] Run full pytest, dependency/compile/diff checks, security scans, and inspect the generated movement metadata and CSV schema.
- [ ] Browser-test all seven pages, player selection, overview movement focus, no console errors, and no overflow at 375px, 844px landscape, 1024px, and default desktop widths.
