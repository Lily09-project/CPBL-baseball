# Audited CPBL Snapshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Preserve each verified CPBL refresh as a local, inspectable snapshot and expose evidence of its lineage and change set in the dashboard.

**Architecture:** The preprocessing pipeline remains the single writer for current processed CSVs. A new `src/snapshots.py` records a copy of each output beneath a git-ignored timestamped directory, writes a manifest with file hashes, schemas, source URLs and quality status, and compares the current snapshot to its predecessor by stable business keys. `run_all.py` attaches the resulting snapshot summary to the quality report, which the UI renders as a compact trust fact.

**Tech Stack:** Python 3.12, pandas, pytest, Streamlit, JSON, SHA-256.

## Global Constraints

- Only official CPBL sources are represented in lineage metadata.
- Snapshot data is local runtime state and must remain git-ignored; its contracts and code are public.
- Snapshot writes are idempotent for the same input checksum set.
- Do not describe generic `野手` / `投手` labels as verified defensive positions or pitching roles.

---

### Task 1: Snapshot contract and diff engine

**Files:**
- Create: `src/snapshots.py`
- Create: `tests/test_snapshots.py`
- Modify: `.gitignore`

- [x] Write tests for SHA-256 file metadata, idempotent snapshot creation, and a key-based change report that distinguishes added, removed, changed and schema-drift columns.
- [x] Run the focused tests and confirm they fail because `src.snapshots` does not exist.
- [x] Implement the minimal snapshot module using `player_id` for player outputs and `team` for standings, with a manifest schema version and official source URL list.
- [x] Add `data/snapshots/` to `.gitignore`; run focused tests until they pass.

### Task 2: Pipeline and quality lineage

**Files:**
- Modify: `src/data_quality.py`
- Modify: `run_all.py`
- Modify: `tests/test_data_quality.py`
- Modify: `tests/test_run_all.py`

- [x] Write tests defining quality-report persistence and pipeline snapshot attachment after a passing quality report.
- [x] Run the focused tests to verify the expected missing interface failure.
- [x] Add a report save helper, attach snapshot identifier, manifest path and diff summary only after quality succeeds, and preserve the failure path without snapshot writes.
- [x] Run focused tests until they pass.

### Task 3: Explainability UI and honest filters

**Files:**
- Modify: `app.py`
- Modify: `tests/test_streamlit_pages.py`
- Modify: `README.md`

- [x] Write a UI test requiring snapshot lineage text and asserting the scouting workbench no longer renders a position / role selector derived only from generic labels.
- [x] Run the focused test and observe it fail.
- [x] Render a compact snapshot fact in the data trust surface, remove the unsupported role filter, and document snapshot scope and limits.
- [x] Run UI tests until they pass.

### Task 4: Verification and public delivery

**Files:**
- Verify: all tracked files and generated public reports

- [x] Run `run_project.bat --check`, full `pytest`, security scans, git diff review and a local Streamlit smoke check.
- [x] Confirm snapshots/raw inputs/secrets are ignored and no unnecessary generated material is staged.
- [x] Commit audited source, tests, docs and the refreshed public quality report; push only after verification succeeds.
