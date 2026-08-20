# CPBL Analytics Architecture

## Product Boundary

這是一個本機可重現的資料分析產品。它把 CPBL 官方公開頁面轉成可驗證的處理後資料、版本化快照、衍生分析與 Streamlit 介面。公開部署不在本階段交付範圍內，因此目前不放入雲端憑證、公開服務設定或部署專用密鑰。

## Data Flow

```text
CPBL official public pages
        |
        v
src/fetch_cpbl_data.py
  source host + HTTP + pagination contract
        |
        v
src/preprocess.py
  normalize, type conversion, derived metrics
        |
        v
src/data_quality.py
  schema, primary key, duplicates, ranges, coverage
        |
        +--> data/processed/*.csv
        |
        +--> src/snapshots.py
        |      manifest + SHA-256 + adjacent diff
        |
        +--> src/movements.py
        |      player_movements.csv
        |
        +--> src/history.py
               snapshot_history.csv
               player_metric_history.csv
                       |
                       v
             src/analysis_validation.py
               stability + drift + sensitivity
                       |
                       +--> reports/metrics/analysis_validation.json
                       |
                       v
                 app.py / Streamlit
```

## Ownership Boundaries

| Layer | Owns | Does not own |
| --- | --- | --- |
| Fetch | official source, pagination, response parsing | business ranking rules |
| Preprocess | stable columns, types, derived metrics | UI state |
| Quality | acceptance or rejection of processed data | visual presentation |
| Snapshot/history | lineage, hashes, version comparisons | source retrieval |
| Analysis validation | descriptive stability, drift, sensitivity | future prediction |
| Scouting | qualification, weights, evidence signals | HTTP requests |
| App | navigation, filters, display, downloads | hidden data mutation |
| Release gate | artifact consistency before release | deployment |

## Failure Behavior

1. Source or pagination contract fails: the pipeline raises an error and does not silently fall back to sample data.
2. Required files or quality rules fail: `run_all.py` stops before creating a trusted snapshot.
3. Processed data cannot be loaded: the Streamlit app stops with an actionable error instead of rendering partial data.
4. Historical inputs contain duplicate IDs or invalid timestamps: analysis validation raises a clear error.
5. Release artifacts are inconsistent: `src.release_gate` returns non-zero and CI blocks the change.

## Public Repository Boundary

Tracked outputs are limited to source code, tests, documentation, sanitized processed data and public metric summaries. Raw HTML, personal paths, local virtual environments, secrets, temporary files and generated caches are excluded by `.gitignore` and workflow checks.

## Operational Workflows

- `security.yml`: secret history scan, dependency audit, Bandit and tests.
- `data-health.yml`: scheduled official API verification with read-only repository permission.
- `data-refresh.yml`: scheduled official API refresh, quality gate and reviewable PR for data outputs only.
- `release-quality.yml`: locked environment, `pip check`, compile, tests and release artifact gate.

## Design Decisions

- **Fail closed** for source, data quality and application startup because showing stale or fabricated data is more harmful than an explicit unavailable state.
- **String player IDs** throughout the pipeline because CPBL IDs may contain leading zeroes.
- **Adjacent snapshot comparisons** because they match the operational question: what changed since the last verified refresh?
- **Description over prediction** because the current source is an official public aggregate, not a labeled future-outcome dataset.
