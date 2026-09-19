# Release Candidate Checklist

這份清單用於把本機完成的 CPBL 資料產品整理成可供 GitHub 審查的 release candidate。它不包含公開部署；部署是另一個需要獨立核准的工作。

## Local Gate

在 Windows 專案根目錄執行：

```powershell
run_project.bat --runtime-check
run_project.bat --offline-check
run_project.bat --check
run_project.bat --validate
.venv\Scripts\python.exe quality\run_acceptance.py release
.venv\Scripts\python.exe quality\run_benchmarks.py
```

`--check` 必須依序完成：

- 依賴安裝與 `pip check`。
- CPBL 官方資料 `--mode api` 刷新。
- 資料品質報告與已驗證快照。
- Release Health 報告：schema 漂移、列數驟降、基準版本與分析血緣。
- `pytest` 完整測試套件。
- `compileall` Python 編譯檢查。
- `src.release_gate` 公開產物一致性檢查。
- `src.verify_public_release` 公開發布 allowlist、release_id、SHA-256 與 CSV 結構檢查。
- Smoke test。

`--offline-check` 不執行官方資料刷新，其餘驗收與 `--check` 相同；用於無網路審查或確認目前 checkout 的公開交付可以獨立重現。需要驗證資料新鮮度時仍必須執行 `--check`。

`--validate` 不刷新官方資料，並在離線交付驗收上再加入零 warning pytest、Bandit 與 pip-audit。正式 release candidate 必須通過此模式。

`quality\run_acceptance.py release` 是整合資料契約、200 項 pytest、10×5 核心 browser QA、timeout、required gate 與失敗證據的機器可讀總判定。需要更窄手機、較大手機與 200% 字級重排時，另執行 `python tools\ui_qa.py --url http://127.0.0.1:8852 --extended --text-scale`（10×7）。效能比較固定執行三次取中位數；不得以減少 route／viewport、忽略 console error 或未經審查覆寫 baseline 的方式消除警告。

額外安全檢查：

```powershell
python -m pip_audit --local --strict
python -m bandit -r app.py src run_all.py -ll
python -m src.verify_public_release reports/metrics/public_release_manifest.json
git diff --check
```

瀏覽器驗收（先在 `127.0.0.1:8852` 啟動 Streamlit）：

```powershell
python -m pip install -r requirements-e2e.txt
python -m playwright install chromium
python tools\ui_qa.py --url http://127.0.0.1:8852
```

## User Acceptance

- 首頁能顯示官方來源、最後驗證時間、品質狀態與資料限制。
- 球員快速搜尋能以姓名、球隊與 CPBL player ID 區分同名球員。
- 球探工作台能切換打者／投手、資格門檻、評估重點與球隊。
- 球探報告能建立觀察名單並下載 Markdown、CSV、Manifest JSON。
- 球員個人頁能顯示完整成績、進階指標、聯盟比較、前次快照與累計差異。
- 版本趨勢只能選擇時間順序有效的版本組合。
- 分析驗證頁能切換球員類型與指標，且清楚標示描述性限制。
- 空資料、品質失敗、缺檔與無法讀取狀態會停止顯示不可信資料。
- 桌機、平板與行動版不應出現內容重疊、水平溢位或不可操作控制。

## Reviewer Acceptance

- `reports/metrics/data_quality_report.json` 的 `mode` 為 `api`，`quality_status` 為 `pass` 或經人工確認的 `warning`。
- `reports/metrics/analysis_validation.json` 的 `latest_snapshot_id` 與品質報告快照一致。
- `reports/metrics/release_health.json` 的狀態不是 `failed`，且 `snapshot_id`、`generated_at` 與品質報告一致。
- `reports/metrics/public_release_manifest.json` 可獨立驗證，11 個 allowlist 產物均存在，且 `snapshot_id`、`generated_at` 與品質報告一致。
- 列數下降達 10% 會產生警示，達 25% 會阻擋發布；需在 PR 中確認是真實資料變化還是來源／分頁異常。
- `player_id` 在公開資料表中保持字串且唯一。
- README 的驗證數字與報告、測試結果一致。
- `requirements.lock` 可在乾淨 Python 3.12 環境安裝並通過 `pip check`。
- Git diff 不包含 `.env`、secrets、raw HTML、本機路徑、`.venv` 或暫存輸出。
- `data-refresh.yml` 只對驗證後的 `data/processed` 與 `reports/metrics` 建立 reviewable PR，不直接推送 `main`。
- Security、Release quality、Data health workflow 的權限與 action 版本符合預期。

## Commit Boundary

建議分成兩個 commit：

1. `feat: add analysis validation and release quality controls`
2. `chore(data): refresh verified CPBL data`

這樣程式碼審查者可以分開閱讀功能與資料更新，未來資料刷新也能只產生第二類 commit。

## Stop Conditions

遇到以下任一情況，不應推送或合併：

- 官方來源不是 API mode、品質閘門失敗或資料量異常。
- 測試、compile、Smoke、release gate、Bandit 或 pip-audit 失敗。
- Release Health 偵測到 schema 漂移、列數驟降或跨報告血緣不一致。
- 公開發布 Manifest 缺失、release_id 不一致、出現非 allowlist 路徑，或任一公開檔案的 SHA-256／結構不一致。
- 無法說明新增、移除、變更的資料列。
- README、Model Card、報告與實際程式公式不一致。
- 需要使用 secret 才能在本機啟動或驗證。
