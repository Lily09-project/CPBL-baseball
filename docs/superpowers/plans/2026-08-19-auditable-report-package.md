# CPBL 可稽核報告封裝實作計畫

## Goal

在既有球探報告的 Markdown／CSV 下載之外，增加一份穩定、機器可讀的 JSON Manifest。使用者可以用它確認報告由哪個資料快照、哪組資格門檻、哪個評估重點與哪些球員產生，讓分析結果可重建、可審查、可交接。

## Design

- `src/scouting_report.py`：建立報告 Manifest、穩定報告 ID 與 JSON 輸出；報告 ID 只由資料快照、查詢條件與報告列內容計算，不包含產生時間。
- `app.py`：在球探報告頁顯示報告 ID，新增 Manifest JSON 下載；既有 Markdown／CSV 下載保持不變。
- `tests/test_scouting_report.py`：測試 Manifest schema、穩定性、不同條件產生不同 ID，以及 JSON 可解析性。
- `tests/test_streamlit_pages.py`：測試 Manifest 下載控制與報告 ID 顯示。
- `README.md`：說明 Manifest 的用途、欄位與不包含秘密的公開政策。

## Verification

```powershell
python -m pytest -q tests/test_scouting_report.py tests/test_streamlit_pages.py
python -m pytest -q
python -m compileall -q app.py src tests
python -B src/smoke_test.py
git diff --check
```

## Constraints

- 只使用 CPBL 官方處理後資料與既有 `src.scouting.py` 評估規則。
- Manifest 不寫入本機資料庫、不包含 API key、token、密碼或本機路徑。
- 不改變既有 Markdown／CSV 格式與網址深連結契約。
- 通過測試與安全檢查後，只提交適合公開的程式、測試、文件與資料成果。
