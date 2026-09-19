# Review Guide

This guide is the shortest path for evaluating the project as a data-engineering and analytics-engineering side project. It is written for a reviewer who wants evidence rather than a feature tour.

## 1. What to inspect first

1. Read the 60-second overview in README.md.
2. Open the live Streamlit app and start at 資料訊號總覽.
3. Check the source ribbon, freshness, quality status, snapshot ID, and stated analytical limits before reading any ranking.
4. Follow 球探工作台 to 球員個人頁, then compare the same player in 版本趨勢.
5. Generate a 球探報告 and validate its downloaded Manifest outside Streamlit.

## 2. Reproduce the evidence locally

Run from the repository root with Python 3.12 and network access to the official CPBL site:

~~~powershell
run_project.bat --runtime-check
run_project.bat --offline-check
python run_all.py --mode api
python -m pytest -q
python -m compileall -q app.py src tests
python -m src.smoke_test
.venv\Scripts\python.exe quality\run_acceptance.py release
.venv\Scripts\python.exe quality\run_benchmarks.py
~~~

`quality\run_acceptance.py release` is the authoritative machine-readable local release decision: it preserves gate-level logs and browser failure evidence and fails closed after a required gate failure. The benchmark command runs release integrity, AppTest, and all 10 routes across three viewports three times; do not replace the environment-specific baseline merely to silence a regression.

run_project.bat --offline-check is the network-free reviewer command. It leaves published data unchanged and verifies dependencies, the complete test suite, compilation, release gate, public release manifest, and smoke test against the checked-out artifacts.

run_project.bat --check is the Windows release-style acceptance command. It first refreshes official data, then performs the same repository verification. Use it when freshness, rather than reproducibility of the checked-out release, is under review.

## 3. Source and lineage contract

The pipeline reads CPBL's public server-rendered pages:

- /player for the current roster.
- /standings/season for team standings.
- /stats/recordall for the statistics page and its verification token.
- /stats/recordallaction for the official form-pagination request used by that page.

The project intentionally does not describe this as an official API integration. The existing --mode api name is retained for command compatibility with CI and deployment instructions; it means the official-data ingestion pipeline, not an API key or private endpoint.

### Frontend failure boundary

The Streamlit frontend is intentionally offline and read-only. It only reads validated files under data/processed/ and the quality report. If a required CSV is missing or corrupt, or the quality report cannot be trusted, the app stops with an actionable message instead of fetching external data implicitly. Run run_project.bat --check to rebuild and validate the published artifacts.

After a successful refresh, the report and snapshot evidence includes:

- source URLs and capture time;
- schema, required-column, duplicate-ID, numeric-range, and minimum-coverage checks;
- processed row counts;
- a content-derived snapshot ID and SHA-256 file fingerprints;
- previous snapshot ID and row-level change summary.

## 4. Product and engineering signals

| Review question | Where to verify it |
| --- | --- |
| Is the data source explicit? | Home page source status and src/source_contract.py |
| Does bad data stop publication? | src/data_quality.py, run_all.py, and quality tests |
| Can a refresh be explained? | data/snapshots/ locally and 版本趨勢 |
| Are player comparisons interpretable? | 球探工作台, 球員個人頁, and src/scouting.py |
| Are outputs independently checkable? | src/verify_report_manifest.py |
| Is the app usable on mobile? | Responsive theme rules and browser smoke screenshots |
| Is the public repository constrained? | 公開儲存庫政策 in README.md |

## 5. Deliberate limitations

This product uses season-to-date aggregate data. It does not claim to provide pitch-by-pitch opponent history, injury context, tactical context, calibrated game prediction, future performance forecasting, or roster decisions. LOG5 is explicitly presented as a constrained scenario calculation.

Those limits are part of the product contract: a reviewer should see what the system refuses to infer, not only what it can display.
