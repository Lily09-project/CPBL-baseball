# Player Snapshot Movements Design

## Objective

Turn the existing audited snapshot lineage into a user-facing temporal analysis feature. The dashboard must answer what changed for a player between the latest two verified CPBL snapshots without claiming game-level splits, future performance, or causal explanations.

## Selected Approach

Generate a public, derived long-form dataset after each verified snapshot is created. `data/processed/player_movements.csv` compares the current snapshot with its declared predecessor by stable `player_id`. This approach reuses the existing data-engineering foundation, remains reproducible, and keeps local raw snapshots out of GitHub while retaining a reviewable analytical output.

Alternatives not selected:

- Scrape roster transactions: useful, but adds another fragile external endpoint and a separate data model.
- Build a predictive trend or win model: unsupported by the current season-level source granularity.

## Data Contract

Each row represents one player and one metric. Required columns are:

`player_id`, `player_name`, `team`, `player_type`, `metric`, `previous_value`, `current_value`, `delta`, `favorable_delta`, `movement_status`, `baseline_snapshot_id`, `current_snapshot_id`, `baseline_captured_at`, `current_captured_at`.

Hitter metrics: PA, HR, AVG, OBP, SLG, OPS, and player value score.

Pitcher metrics: IP, K, ERA, WHIP, K/BB, and player value score.

`favorable_delta` reverses the sign only for lower-is-better metrics such as ERA and WHIP. New players have `movement_status=new` and null previous/delta values. Shared players are `changed` when the metric differs and `unchanged` otherwise.

## Pipeline

1. Refresh and score the five official processed outputs.
2. Run the existing quality checks.
3. Create or reuse the verified base snapshot.
4. Resolve its `previous_snapshot_id` and compare the current and previous hitter/pitcher files.
5. Write `player_movements.csv` atomically enough for the existing single-process launcher and attach movement metadata to the quality report.
6. If there is no predecessor, write an empty file with the complete schema and report `baseline_pending` without failing the official-data quality result.

Snapshots must continue to contain only the five official base outputs. The derived movement file must not enter snapshot fingerprints, preventing a circular dependency.

## Interface

The overview adds a compact "評估分數變化焦點" section after the season population cards. It lists the largest absolute score movements, labels the two snapshot timestamps, and states that score movement is descriptive rather than predictive.

The player page adds "前次快照變化" after the current-season fact cards. It shows the selected player's current value, previous value, raw delta, and favorable direction for the relevant metrics. The section is absent for roster-only players and shows a clear empty state when no baseline exists.

No new sidebar page is added. Existing card spacing, typography, source lineage, mobile stacking, and uppercase baseball terminology remain unchanged.

## Failure Handling

- Missing predecessor: schema-valid empty output and `baseline_pending` metadata.
- Missing metric columns: skip only unavailable metrics; never synthesize values.
- Duplicate player IDs in a snapshot input: fail movement generation with a clear error because the comparison key is ambiguous.
- Missing snapshot files or malformed manifests: fail the pipeline rather than silently present stale movement data.

## Verification

- Unit tests cover deltas, lower-is-better direction, new players, duplicate rejection, and missing predecessor behavior.
- Pipeline tests require movement generation only after a verified snapshot and require metadata persistence.
- Streamlit tests require both new sections and an explicit cumulative-data limitation.
- Final verification runs focused tests, full pytest, the live-data launcher check, secret checks, and browser audits at desktop and mobile widths.
