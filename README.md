# CPBL 中職資料分析平台

中華職棒資料探索儀表板，使用 Streamlit 呈現球隊戰績、球員排行榜、球員個人頁、投打對決與分項排行。

## 快速啟動

```powershell
run_project.bat
```

檢查模式：

```powershell
run_project.bat --check
```

Environment check without network access:

```powershell
run_project.bat --runtime-check
```

手動流程：

```powershell
python run_all.py --mode api
python -m pytest
python -m streamlit run app.py
```

`run_project.bat` 會優先使用 Codex bundled Python；找不到時才依序嘗試 `py -3` 與 `python`。

## Dashboard 頁面

- 首頁 / 專案介紹：資料來源狀態、核心功能入口與資料模式。
- 聯盟總覽：CPBL 官方目前戰績頁的勝差、近況、得失分差、近期戰力與主客場勝率。
- 球員排行榜：打者與投手排行榜，支援 OPS、ISO、AVG、OBP、SLG、ERA、WHIP、K/BB 等指標。
- 球員個人頁：以官方現役名單提供全體球員入口，整合本季成績、進階指標、聯盟平均比較、排行摘要、聯盟百分位、能力雷達圖、官方球員頁與相似球員推薦。
- 投打對決：使用官方打者 OBP、投手估算被上壘率與聯盟平均 OBP，透過 LOG5 模型估算上壘機率。
- 分項排行：打者、投手與球隊的 Top / Bottom 排行。

## 資料狀態

資料流程只接受 CPBL 官方網站資料；抓取或解析失敗時會直接報錯，不會改用本地展示資料：

- `https://www.cpbl.com.tw/player`：官方現役球員名單。
- `https://www.cpbl.com.tw/standings/season`：球隊戰績與攻守團隊資料。
- `https://www.cpbl.com.tw/stats/recordallaction`：打者與投手全記錄分頁資料。

球員綜合分數、聯盟百分位、相似球員與 LOG5 分析均由上述官方成績衍生。LOG5 不是官方逐打席對戰紀錄，也不是比賽結果預測。

正式 API 連線使用有限次數的 GET/POST 重試與退避；資料品質報告會檢查必要檔案、必要欄位、球員 ID 重複與核心數值範圍。任一必要處理檔案缺失時，前端啟動會重新執行官方 API 資料流程。

重要輸出：

- `data/processed/teams.csv`
- `data/processed/roster.csv`
- `data/processed/batters_scored.csv`
- `data/processed/pitchers_scored.csv`
- `data/processed/players_scored.csv`
- `reports/metrics/data_quality_report.json`

## 專案結構

```text
src/
  app_helpers.py
  data_quality.py
  features.py
  fetch_cpbl_data.py
  log5_matchup.py
  preprocess.py
  rankings.py
  similarity.py
  smoke_test.py
  theme.py
tests/
  test_streamlit_pages.py
```

## 注意事項

目前正式流程以 CPBL 官方網站為資料來源，需可連線到 `www.cpbl.com.tw`。若官方頁面欄位名稱或分頁參數異動，請先修正 `src/fetch_cpbl_data.py`，再執行 `run_all.py --mode api` 重新產生 `data/processed/*.csv`。


## 安全說明

- 本地啟動只監聽 `127.0.0.1`，不直接暴露到區域網路。
- `.env`、Streamlit secrets、私鑰、原始抓取 HTML 與內部規劃筆記不納入版本控制。
- CSV 下載會中和試算表公式前綴，避免開啟檔案時執行惡意公式。
- CPBL 球員連結只接受 `https://www.cpbl.com.tw`。
- 依賴套件設定已知漏洞修復版本下限；GitHub Dependabot 每週檢查更新。
