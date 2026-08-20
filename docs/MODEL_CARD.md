# CPBL Derived Scoring Model Card

## Purpose

本文件描述 CPBL 中職資料分析平台中的衍生評估分數、百分位與 LOG5 情境計算。它的目的，是讓審查者知道模型做了什麼、沒有做什麼，以及什麼情況下不應使用結果。

## Intended Use

- 用於探索 CPBL 官方公開賽季彙總資料。
- 用於建立可解釋的球員比較、觀察名單與資料品質討論。
- 用於展示資料工程、分析工程、可稽核輸出與產品化流程。

## Out of Scope

- 不預測比賽勝負、球員未來成績或受傷風險。
- 不提供投注、薪資、交易、先發、升降或醫療決策建議。
- 不把 LOG5 情境計算解讀成校準機率。
- 不宣稱官方資料涵蓋完整的逐球、逐打席、守備定位、戰術、傷勢或球探觀察。

## Data

資料只來自 CPBL 官方公開頁面：現役球員名單、球隊戰績、打者與投手全記錄。資料擷取、清理、型別轉換與品質檢查由 `run_all.py --mode api` 串接完成。

核心資料契約：

- `player_id` 是跨資料集的業務主鍵，整個流程以字串保存，避免前導零遺失。
- 輸入來源必須是允許的 CPBL 官方網域，分頁回應需通過完整性檢查。
- schema、必要欄位、唯一性、數值範圍與最低涵蓋量未通過時，不建立可追蹤快照。
- 每次通過品質檢查的結果都會保存版本時間、前一版本、SHA-256 與差異摘要。

## Qualification Rules

為避免低樣本球員被誤解為穩定排名，預設資格門檻為：

- 打者：`PA >= 30`
- 投手：`IP >= 10`

畫面允許調整門檻，但報告會寫入實際門檻、資料快照與評估重點。百分位的母體會先依球員類型與資格門檻固定，再做球隊篩選。

## Derived Scores

評估分數是由官方衍生欄位的固定加權組合，不是訓練出的黑盒模型。所有分數會限制在 `0..100` 的可讀尺度，畫面同時展示組成訊號與限制。

| 類型 | 評估重點 | 公式 |
| --- | --- | --- |
| 打者 | 綜合價值 | `1.00 * player_value_score` |
| 打者 | 接觸與選球 | `0.55 * contact_score + 0.45 * discipline_score` |
| 打者 | 長打 | `0.70 * power_score + 0.30 * hitter_value_score` |
| 投手 | 綜合價值 | `1.00 * player_value_score` |
| 投手 | 失分壓制 | `0.75 * run_prevention_score + 0.25 * pitcher_value_score` |
| 投手 | 控球能力 | `0.70 * command_score + 0.30 * strikeout_score` |

強項與風險訊號以聯盟母體百分位判讀，例如 OBP、ISO、K%、ERA、WHIP、K/BB 與被 HR% 的固定門檻。訊號是可解釋提示，不是因果結論。

## Validation

「分析驗證」頁與 `reports/metrics/analysis_validation.json` 提供三類描述性檢查：

1. **排名穩定性**：比較相鄰官方快照的 Top-K 重疊率、共同球員數、Spearman ρ 與平均排名變化。
2. **資料分布變化**：比較中位數、平均數、四分位數、有效涵蓋人數與相鄰版本的變化方向。
3. **權重敏感度**：把單一評估權重上下擾動 5%、10% 或 15%，按比例重分配其他權重，觀察 Top-K 與排名順序是否改變。

這些檢查描述資料與排序的穩定程度，不會把穩定性誤稱為預測準確率，也不會只靠一個門檻自動判定資料錯誤。

## Limitations and Risks

- 官方頁面是累積統計，更新節奏與名單狀態可能造成跨版本變化。
- 資格門檻不能消除樣本量、角色轉換、球隊變動與賽季階段造成的偏差。
- 一位球員可能同時出現在打者與投手資料集；產品會依資料類型分開解讀。
- 缺失值不會被默認補成零；缺少必要指標時不產生對應訊號。
- 目前沒有以未來賽季結果做外部校準，因此不能聲稱模型具有預測效度。
- 任何實際球員或球隊決策都應搭配完整官方資料、專業人員判斷與情境資訊。

## Monitoring and Change Policy

- 官方資料刷新由 `.github/workflows/data-refresh.yml` 執行，通過測試後只建立可審查 Pull Request，不直接推送 `main`。
- `.github/workflows/data-health.yml` 持續驗證即時官方資料管線，但保持 `contents: read`，不修改儲存庫。
- `.github/workflows/release-quality.yml` 執行鎖定依賴、`pip check`、編譯、測試與 release gate。
- 修改資料契約、資格門檻、權重、指標公式或報告 schema 時，必須同步更新測試、README 與本文件。
- 任何新快照在合併前都應檢查資料品質報告、版本差異、球員涵蓋量與分析驗證摘要。

## Reproducibility

本機執行：

```powershell
python -m pip install -r requirements.lock
python run_all.py --mode api
python -m src.release_gate
python -m pytest -q
```

正式資料與分析輸出以報告中的 `generated_at`、`snapshot_id`、`schema_version` 與檔案指紋為準。
