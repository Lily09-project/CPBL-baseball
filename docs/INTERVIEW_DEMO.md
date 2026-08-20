# Interview Demo Script

## Two-Minute Flow

### 1. Establish trust

開啟「資料訊號總覽」，先指出來源網域、最後驗證時間、品質狀態、資料新鮮度與限制。重點是：產品先讓使用者知道資料是否可回答問題，再展示排名。

### 2. Show the analytical workflow

進入「球探工作台」：

- 切換打者／投手。
- 調整 `PA` 或 `IP` 資格門檻。
- 選擇評估重點與球隊。
- 選兩位球員比較，說明百分位母體與強項／風險訊號。

強調這些不是硬編碼樣本，而是由 CPBL 官方資料管線產生的完整候選範圍。

### 3. Show a deliverable

在「球探報告」建立最多四人的觀察名單，下載 Markdown、CSV 與稽核 Manifest。說明 Manifest 包含 report ID、資料快照、品質狀態、條件、方法與限制，離開畫面後仍能驗證。

### 4. Show time and robustness

進入「版本趨勢」，展示資料血緣與兩個時間順序有效版本的新增、移除、變動與未變動結果。再進入「分析驗證」：

- 排名穩定性：Top-K 重疊率與 Spearman ρ。
- 資料分布變化：中位數、涵蓋量與版本差異。
- 權重敏感度：±10% 權重擾動後的排序變化。

最後明確說明：這是資料與分析假設的壓力測試，不是把結果包裝成預測模型。

## Reviewer Checklist

- `python -m pytest -q` 是否通過？
- `python -m src.release_gate` 是否通過？
- `reports/metrics/data_quality_report.json` 是否為 `mode=api` 且品質通過？
- `reports/metrics/analysis_validation.json` 是否有 schema、限制與解讀說明？
- 是否能從 `player_id`、`snapshot_id` 與 `report_id` 回溯一次分析？
- `.github/workflows/data-refresh.yml` 是否只對 `data/processed` 與 `reports/metrics` 開 PR？
- 是否沒有追蹤 `.env`、`.streamlit/secrets.toml`、原始 HTML、本機路徑或虛擬環境？
