# CPBL 中職資料分析平台

以 CPBL 官方公開資料建立的可稽核球員評估資料產品。它不預測比賽或產生名單建議；每個結論都可追溯到官方資料、資格門檻、衍生分數與百分位。

## 官方 CPBL 資料來源

- [現役球員名單](https://www.cpbl.com.tw/player)
- [球隊戰績](https://www.cpbl.com.tw/standings/season)
- [打者與投手全記錄](https://www.cpbl.com.tw/stats/recordallaction)

`reports/metrics/data_quality_report.json` 會記錄抓取時間、列數、欄位完整度、重複 ID 與數值範圍檢查結果。資料流程只接受 `www.cpbl.com.tw` 的官方來源，取得或解析失敗時不以展示資料取代。

## 資料管線

```text
CPBL 官方公開頁面
  -> src/fetch_cpbl_data.py
  -> src/preprocess.py
  -> data/processed/*.csv
  -> src/data_quality.py
  -> src/scouting.py
  -> Streamlit 介面
```

`player_id` 全程保留為字串，避免前導零在讀取、篩選、排序與比較時遺失。前端僅讀取版本控制中的 `data/processed/` 成品；`data/raw/` 是暫存的官方原始回應，不作公開或前端資料來源。

## 資料品質與可稽核性

- 僅允許官方主機、要求完整分頁，並檢查資料綱要、重複 ID 與合理數值範圍。
- 匯出的 CSV 會中和試算表公式前綴；本機服務僅綁定 `127.0.0.1`。
- `notes/source_prompt.txt`、原始回應、私有環境資訊與本機暫存物不納入分析結果或公開儲存庫。
- 品質報告與處理後 CSV 可讓每次資料刷新、筆數與檢核結論被重現和審查。

## 球探工作台

球探工作台提供以固定規則產生的短名單與最多四名球員比較。打者預設資格為 `PA >= 30`，投手預設資格為 `IP >= 10`；分析者可提高門檻，並以球隊、守備位置或投手角色篩選。百分位先在符合該球員類型與資格門檻的母體計算，再套用篩選條件，避免把小範圍篩選誤當成聯盟基準。

顯示的優勢、風險與百分位依據都由當季官方累積成績與固定門檻產生；樣本不足會被獨立標記，不等同於表現好壞。

## 評估公式

| 類型 | 評估重點 | 公式 |
| --- | --- | --- |
| 打者 | 綜合價值 | `player_value_score` |
| 打者 | 接觸與選球 | `0.55 * contact_score + 0.45 * discipline_score` |
| 打者 | 長打 | `0.70 * power_score + 0.30 * hitter_value_score` |
| 投手 | 綜合價值 | `player_value_score` |
| 投手 | 失分壓制 | `0.75 * run_prevention_score + 0.25 * pitcher_value_score` |
| 投手 | 控球能力 | `0.70 * command_score + 0.30 * strikeout_score` |

分數為同一資料版本內的可重現排序訊號，不是跨賽季、跨聯盟或未來價值的保證。

## 資料限制

本專案使用當季官方累積成績，不足以建立傷勢、戰術、未來表現或球員名單決策的結論。LOG5 為情境計算，非校準預測模型；不可視為勝負、投注或未來表現預測。

## 重現與測試

在專案根目錄執行：

```powershell
run_project.bat --runtime-check
python run_all.py --mode api
python -m pytest -q
run_project.bat --check
```

一般啟動可使用 `run_project.bat`。資料刷新需要可連線至 CPBL 官方網站；若官方欄位或分頁參數異動，請先調整 `src/fetch_cpbl_data.py` 後再刷新。

## 公開儲存庫政策

可公開追蹤的內容包括原始碼、測試、`data/processed/` CSV、品質報告、文件、GitHub 工作流程與設定檔。永不追蹤 `data/raw/`、`notes/source_prompt.txt`、`.env`、`.streamlit/secrets.toml`、憑證、私鑰、本機資料庫、執行日誌、快取、偵錯輸出與 `.venv/`。

## 可稽核資料快照

每次 `python run_all.py --mode api` 在品質檢查通過後，都會將當前 `data/processed/` 的 CSV 複本保存為本機快照，並建立 `manifest.json`。Manifest 包含：

- CPBL 官方來源 URL、擷取時間與球季
- 每個輸出檔的列數、欄位、業務主鍵與 SHA-256 校驗碼
- 品質檢查結果與前一份快照的新增、移除、變更列數及 schema 漂移摘要

快照寫入 `data/snapshots/`，此目錄與原始 HTML 一樣不會上傳 GitHub。相同輸出校驗碼會重用既有快照，避免因重跑產生重複歷史。儀表板的資料信任列會顯示快照 ID，以及和前一份不同的資料摘要。

此版本保存的是官方球季累計名單、球隊戰績、打者與投手成績輸出；它不宣稱提供逐場事件資料、近十場趨勢、守備位置細分或先發／後援角色。工作台僅保留可由目前官方來源驗證的球隊、PA／IP 資格與評估維度。
