# CPBL 球探報告功能實作計畫

## Goal

把現有球探工作台的候選人比較結果，提升為可保存、可回訪、可下載與可分享的球探報告。報告只使用已通過品質閘門的 CPBL 官方處理後資料，並保留資料版本、資格門檻、評估重點與判讀限制。

## Architecture

- `src/scouting_report.py`：純資料轉換與 Markdown 報告輸出，不依賴 Streamlit，也不寫入專案檔案。
- `app.py`：新增「球探報告」頁面，沿用 `src.scouting.py` 的資格門檻、評估分數與 evidence 訊號；用 `st.query_params` 保存可分享的觀察名單條件。
- `tests/test_scouting_report.py`：測試選取順序、未知 ID、上限、穩定欄位與 Markdown escaping。
- `tests/test_streamlit_pages.py`：測試新頁面、深連結、下載控制與無例外渲染。
- `README.md`：記錄使用流程、輸出內容、限制與資料版本意義。

## Implementation Tasks

1. 先建立球探報告資料模組的失敗測試，固定輸入輸出契約。
2. 實作最多四位球員、保留選取順序、忽略無效 ID 的報告資料轉換，以及安全的 Markdown 文字輸出。
3. 接入 Streamlit 頁面：球員類型、資格門檻、評估重點、候選選取、觀察名單深連結、清除操作、Markdown 與 CSV 下載。
4. 補齊頁面測試與文件，確保新功能仍符合既有繁體中文、棒球術語大寫、資料來源揭露與 responsive UI 規範。
5. 執行純模組、Streamlit AppTest、完整 pytest、compileall、smoke test、`git diff --check` 與 secrets 掃描；發現問題直接修正後重跑。

## Verification Commands

```powershell
python -m pytest -q tests/test_scouting_report.py tests/test_streamlit_pages.py
python -m pytest -q
python -m compileall -q app.py src tests
python -B src/smoke_test.py
git diff --check
```

## Constraints

- 不引入 Sample Data、Mock Data 或新的未驗證資料來源。
- 不修改既有資料契約與分析公式。
- 不把使用者操作寫入本機資料庫；分享狀態只放在網址參數，報告由目前資料版本即時重建。
- 不推送 GitHub；本次只在本地完成實作與驗證。
