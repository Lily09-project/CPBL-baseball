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
python run_all.py --mode api
python -m pytest -q
run_project.bat --check
```

確認以下公開產物已更新且沒有本機路徑或秘密資訊：

- `data/processed/*.csv`
- `reports/metrics/data_quality_report.json`
- `data/processed/player_movements.csv`

不要發布 `data/raw/`、`data/snapshots/`、`.env`、`.streamlit/secrets.toml`、`.venv/` 或本機執行日誌。

## 資料健康監控

`.github/workflows/data-health.yml` 每日執行一次，也可由 GitHub Actions 手動觸發。工作流程只有 `contents: read` 權限，會：

1. 連線 CPBL 官方公開頁面並重建處理後資料。
2. 執行資料品質閘門與球員變化資料檢查。
3. 執行完整 pytest 測試。
4. 輸出品質狀態、球員數與變化資料筆數。

此工作流程不會自行提交或推送資料。正式發布前仍要人工檢查品質報告與變更內容。

## 上線驗收

- 桌機與 375px 行動版沒有頁面水平溢位。
- 七個分析頁面均可開啟，沒有 Streamlit exception 或瀏覽器 console error。
- 側欄可搜尋完整球員總表並開啟球員頁。
- 球員網址包含 `page=球員個人頁` 與 `player=<CPBL player_id>`，重新整理後仍顯示同一球員。
- 頁面顯示資料來源、更新時間、新鮮度、分析限制與「非 CPBL 官方服務」聲明。
