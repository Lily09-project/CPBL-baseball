# CPBL Snapshot Trend Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public, reproducible snapshot trend and player version comparison workspace from official CPBL-derived data.

**Architecture:** Add a focused `src/history.py` module that converts ignored local snapshots into two tracked processed datasets and compares any two published versions. Integrate generation into `run_all.py`, then add one Streamlit page that consumes only processed outputs so deployment does not require internal snapshot archives.

**Tech Stack:** Python 3.12, pandas, Streamlit, Plotly, pytest

## Global Constraints

- Only official CPBL-derived processed data may be published.
- Preserve `player_id` as a string with leading zeroes.
- Do not expose raw HTML, credentials, absolute paths, or internal snapshot files.
- Lower-is-better metrics must invert `favorable_delta`.
- UI must remain responsive at 375px, 768px, and 1440px.

---

### Task 1: Snapshot history core

**Files:**
- Create: `src/history.py`
- Create: `tests/test_history.py`

**Interfaces:**
- Produces: `build_snapshot_history(snapshot_root: Path) -> pd.DataFrame`
- Produces: `build_player_metric_history(snapshot_root: Path) -> pd.DataFrame`
- Produces: `compare_metric_versions(history: pd.DataFrame, baseline_id: str, current_id: str, player_type: str, metric: str) -> pd.DataFrame`
- Produces: `generate_history_outputs(snapshot_root: Path, processed_dir: Path) -> dict[str, object]`

- [ ] Write failing tests for ordered manifests, public schemas, player IDs, missing files, duplicate IDs, and comparison states.
- [ ] Run `python -m pytest tests/test_history.py -q` and confirm the module is missing.
- [ ] Implement the minimal history builder and comparator.
- [ ] Run `python -m pytest tests/test_history.py -q` and confirm all tests pass.

### Task 2: Pipeline integration

**Files:**
- Modify: `run_all.py`
- Modify: `tests/test_run_all.py`

**Interfaces:**
- Consumes: `generate_history_outputs(...)`
- Produces: `report["history"]` and output paths for both processed CSV files.

- [ ] Extend the run-all tests first and verify the new assertions fail.
- [ ] Call history generation after movement generation and before saving the quality report.
- [ ] Run `python -m pytest tests/test_run_all.py -q`.

### Task 3: Version trend page

**Files:**
- Modify: `app.py`
- Modify: `src/theme.py`
- Modify: `tests/test_streamlit_pages.py`

**Interfaces:**
- Consumes: `snapshot_history.csv`, `player_metric_history.csv`, and `compare_metric_versions(...)`.
- Produces: sidebar route `版本趨勢`, lineage summary, player trend chart, pair comparison, and safe CSV export.

- [ ] Add failing page, interaction, terminology, chart-summary, and responsive-style tests.
- [ ] Load the two processed history files through the existing cached data loader.
- [ ] Implement page controls, chart, tables, empty states, and export.
- [ ] Add only the styling required for timeline status and responsive layout.
- [ ] Run focused Streamlit tests.

### Task 4: Public data and documentation

**Files:**
- Modify: `README.md`
- Modify: `reports/metrics/data_quality_report.json`
- Create: `data/processed/snapshot_history.csv`
- Create: `data/processed/player_metric_history.csv`

- [ ] Run `python run_all.py --mode api` against current official CPBL pages.
- [ ] Verify quality status, snapshot lineage, output row counts, and absence of local paths.
- [ ] Document the user workflow, data contract, limits, and reproducible commands.

### Task 5: Complete verification

**Files:**
- Modify only files required by defects found during verification.

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m src.smoke_test` and `run_project.bat --check`.
- [ ] Run Bandit, detect-secrets, and pip-audit.
- [ ] Start Streamlit and inspect 375px, 768px, and 1440px views.
- [ ] Run `git diff --check`, inspect `git status`, and move only disposable artifacts to `C:\Users\user\Documents\Codex\多餘`.
