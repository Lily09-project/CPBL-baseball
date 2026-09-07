# 部署與營運手冊

## 支援環境

- Python 3.12
- 入口檔：`app.py`
- 套件來源：`requirements.txt`
- 公開資料：`data/processed/*.csv`
- 不需要 API 金鑰、帳號密碼或 Streamlit secrets

## Streamlit Community Cloud

1. 在 Streamlit Community Cloud 建立新應用程式並選擇此 GitHub 儲存庫。
2. Branch 選擇 `main`，Main file path 設為 `app.py`。
3. Advanced settings 的 Python 版本選擇 3.12；Secrets 保持空白。
4. 部署完成後，確認首頁顯示「官方資料已核對」與資料新鮮度。
5. 開啟 `https://<app-host>/_stcore/health`，應回傳健康狀態。

平台提供的 `STREAMLIT_SERVER_ADDRESS` 與 `PORT` 會覆寫本機 `.streamlit/config.toml`。本機 `run_project.bat` 仍只綁定 `127.0.0.1`，避免在開發電腦意外開放網路存取。

## 發布前檢查

```powershell
run_project.bat --runtime-check
run_project.bat --offline-check
python run_all.py --mode api
python -m pytest -q
python -m src.release_gate
python -m src.verify_public_release reports/metrics/public_release_manifest.json
run_project.bat --check
.venv\Scripts\python.exe quality\run_acceptance.py release
.venv\Scripts\python.exe quality\run_benchmarks.py
```

發布判定以 acceptance `release` profile 的 JSON 報告為準；散列命令用於定位單一失敗。效能報告採相同環境三次中位數，涵蓋 release integrity、AppTest 與 10×3 browser QA，baseline 只能在確認覆蓋與錯誤閘門未被放寬後更新。

確認以下公開產物已更新且沒有本機路徑或秘密資訊：

- `data/processed/*.csv`
- `reports/metrics/data_quality_report.json`
- `reports/metrics/release_health.json`
- `reports/metrics/public_release_manifest.json`
- `data/processed/player_movements.csv`

不要發布 `data/raw/`、`data/snapshots/`、`.env`、`.streamlit/secrets.toml`、`.venv/` 或本機執行日誌。

## 資料健康監控

`.github/workflows/data-health.yml` 每日執行一次，也可由 GitHub Actions 手動觸發。工作流程只有 `contents: read` 權限，會：

1. 連線 CPBL 官方公開頁面並重建處理後資料。
2. 執行資料品質閘門與球員變化資料檢查。
3. 執行 Release Health，檢查 schema 漂移、列數驟降與跨報告血緣。
4. 執行完整 pytest 測試。
5. 以獨立 CLI 驗證公開發布 Manifest 的 allowlist、release_id、逐檔 SHA-256 與 CSV 結構。
6. 輸出品質狀態、發布健康、release_id、球員數與變化資料筆數。

此工作流程不會自行提交或推送資料。正式發布前仍要人工檢查品質報告與變更內容。

## 上線驗收

- 桌機與 375px 行動版沒有頁面水平溢位。
- 七個分析頁面均可開啟，沒有 Streamlit exception 或瀏覽器 console error。
- 側欄可搜尋完整球員總表並開啟球員頁。
- 球員網址包含 `page=球員個人頁` 與 `player=<CPBL player_id>`，重新整理後仍顯示同一球員。
- 頁面顯示資料來源、更新時間、新鮮度、分析限制與「非 CPBL 官方服務」聲明。
- `python -m src.verify_public_release reports/metrics/public_release_manifest.json` 輸出 `valid: true`，且 snapshot_id 與品質報告一致。
