# CPBL Scouting Workbench Design

## Purpose

Turn the dashboard into an auditable player-evaluation product rather than a collection of league tables. The product must let a user trace every player signal from official CPBL data through data-quality checks and deterministic feature calculations.

The interview narrative is:

`official CPBL sources -> validated processed data -> reproducible features -> explainable player signals -> scouting comparison`

## Target User And Primary Job

The primary user is an analyst who needs to create a defensible shortlist of CPBL hitters or pitchers. They need to answer these questions without exporting data to a spreadsheet:

- Which players meet a stated playing-time threshold?
- What skills drive a player's value score?
- How does the player compare with the qualified league population?
- What data limitations should change the confidence of that conclusion?

## Product Scope

### Data Signal Overview

Replace the generic project introduction on the home page with a concise overview of:

- official source and latest verified update time;
- available teams, rostered players, hitters, and pitchers;
- data-quality status and missing-data warnings;
- the analytical questions the current data can and cannot answer.

### Scouting Workbench

Add a dedicated page that supports a repeatable screening workflow.

1. Select hitter or pitcher population.
2. Filter by team, position or role, and a configurable PA or IP qualification threshold.
3. Choose a scouting priority: balanced value, contact and discipline, power, run prevention, or command.
4. Review the ranked candidate table with score components, qualified-population percentile, and deterministic evidence signals.
5. Select up to four candidates for a side-by-side comparison table.

The workbench does not claim to predict future performance or make roster recommendations. It exposes current-season evidence for a user decision.

### Explainable Player Evidence

Extend the player page with an evidence section. Each signal must name the metric, the qualified-population percentile, and the threshold that produced it.

Example hitter signals:

- `Above-average on-base profile`: OBP percentile is at least 75.
- `Power signal`: ISO percentile is at least 75.
- `Plate-discipline risk`: strikeout-rate percentile is at most 25, where lower is better.
- `Limited sample`: PA is below the active qualification threshold.

Example pitcher signals:

- `Run-prevention signal`: ERA and WHIP percentiles are each at least 75 after lower-is-better normalization.
- `Command signal`: K/BB percentile is at least 75.
- `Home-run risk`: home-run-allowed-rate percentile is at most 25 after lower-is-better normalization.
- `Limited workload`: IP is below the active qualification threshold.

The UI must show no more than three strengths and two risks at a time. It must use neutral labels when no threshold is met. These are deterministic labels, not generated prose.

### Data Trust Surface

Expose data lineage where a conclusion is made:

- source domain: `www.cpbl.com.tw`;
- verified update timestamp from `data_quality_report.json`;
- population counts and qualification threshold;
- quality status and warnings;
- a concise note that LOG5 is a scenario calculation, not a calibrated prediction model.

## Architecture

Create `src/scouting.py` as the application boundary for analytical decision logic. It will provide:

- `qualified_population`: filters a player dataset with an explicit PA or IP threshold;
- `percentile_rank`: returns a stable 0-100 percentile with lower-is-better support;
- `build_evidence_signals`: returns typed strengths, risks, and neutral notes from a row and qualified population;
- `rank_scouting_candidates`: ranks candidates by a selected, documented priority;
- `comparison_frame`: builds a stable side-by-side dataset for selected players.

`app.py` remains responsible for Streamlit controls and rendering. It must not duplicate scoring rules or threshold logic.

Existing modules retain their responsibilities:

- `src/fetch_cpbl_data.py`: retrieval and official URL validation;
- `src/preprocess.py` and `src/features.py`: normalized player metrics and component scores;
- `src/data_quality.py`: completeness and consistency checks;
- `src/similarity.py`: comparable-player retrieval;
- `src/log5_matchup.py`: matchup scenario calculation.

## Data Contract And Rules

- All player identifiers remain CPBL identifiers stored as strings to preserve leading zeroes.
- Processed CSV files remain the only data files committed to Git. Raw CPBL HTML and internal prompts stay ignored.
- Hitter qualification defaults to 30 PA; pitcher qualification defaults to 10 IP. Users can raise these values in the workbench.
- Percentiles are calculated only within the active player type and qualification population.
- Higher percentiles always mean better performance after applying metric direction.
- Ranked tables display the population count and applied threshold beside the result.
- Score priorities are transparent combinations of existing component scores. No additional external model or private dataset is introduced.

## Error And Empty States

- If source data is unavailable, show the existing verified-data status rather than inventing a fallback conclusion.
- If the active filters produce no qualified players, show the active threshold and offer no ranking.
- If a row lacks a metric required for a signal, omit that signal and show a data-coverage note.
- If `quality_status` is not `pass`, downgrade trust messaging and show report warnings prominently.

## Test Plan

Add focused tests for `src/scouting.py`:

- qualification thresholds for hitters and pitchers;
- percentile direction, ties, missing values, and single-player populations;
- deterministic strength, risk, neutral, and limited-sample signals;
- each priority's ranking order;
- comparison-frame order and column stability.

Extend Streamlit page tests to verify:

- the workbench renders without exceptions;
- threshold controls update candidate counts;
- evidence labels include their numeric basis;
- the trust surface exposes source, verification time, and model limitation.

Before public push, run the API refresh, data-quality check, complete pytest suite, Bandit, detect-secrets, pip-audit, Git integrity check, and the GitHub Security checks workflow.

## Non-Goals

- No unsupported player projections, injury claims, betting advice, or schedule predictions.
- No generative text used to create analysis claims.
- No raw scraped pages, credentials, local environments, cache files, or internal prompts in the public repository.
- No broad redesign unrelated to analytical workflow and evidence readability.

## Acceptance Criteria

- A user can create a hitter or pitcher shortlist using documented filters and thresholds.
- Every visible signal has a deterministic numerical basis.
- The player page distinguishes sample limitation from player performance.
- The home page communicates provenance and verified data scope in the first viewport.
- The README makes the pipeline, scoring assumptions, limitations, and reproducibility clear to an interviewer.
- All existing and new tests pass locally and in GitHub Security checks.
