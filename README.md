# CPBL 中職資料分析平台

[![Security checks](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/security.yml)
[![CPBL data health](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/data-health.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/data-health.yml)
[![Release quality gate](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml)

以 CPBL 官方公開資料建立的可追溯資料產品，涵蓋資料品質、球員評估、球探工作台與版本差異。Streamlit UI 支援桌面／行動裝置與深色／淺色模式。

> 非 CPBL 官方服務；不預測比賽或產生名單建議，也不對傷勢或未來表現下結論。

## 介面預覽

![資料訊號總覽](docs/screenshots/ui-data-health.png)
![球探工作台](docs/screenshots/ui-scouting-workbench.png)
![球員個人頁](docs/screenshots/ui-player-profile.png)

## Highlights

- 僅接受 `cpbl.com.tw` 官方來源，驗證分頁完整性與來源限制。
- 以 `player_id` 作為跨資料表主鍵，避免同名誤選與前導零遺失。
- schema、重複 ID、數值範圍、涵蓋量與快照血緣檢查失敗時阻止發布。
- 球探工作台支援打者／投手門檻、球隊篩選與最多四人比較。
- 可下載球探報告 Markdown、CSV 與含 SHA-256 的 public release manifest。

## 可稽核資料產品

資料管線從官方 CPBL 資料來源開始，經資料品質與可稽核性檢查後產生球探工作台、球探報告與版本快照。觀察名單可下載球探報告 Markdown、下載稽核 Manifest JSON；報告以 `report_id`、`report_threshold` 與 `player_id` 連回資料血緣。

## 評估邊界

資格門檻為打者 `PA >= 30`、投手 `IP >= 10`。`player_value_score` 與球探優先分數只用於描述性排序；完整權重、驗證方式與限制見 [模型卡](docs/MODEL_CARD.md)。LOG5 僅供情境比較，不是校準預測模型。

## 官方來源與資料限制

- https://cpbl.com.tw/player
- https://cpbl.com.tw/standings/season
- https://cpbl.com.tw/stats/recordallaction

來源格式、連線與快照可能變動；流程停止於資料品質檢查失敗，不以 Mock Data 掩蓋錯誤。

## Quick start

需求：Windows 與 Python 3.12。

```powershell
git clone https://github.com/Lily09-project/CPBL-baseball.git
cd CPBL-baseball
.\run_project.bat --check
.\run_project.bat --offline-check
```

`--check` 與 `--offline-check` 都只驗證目前 checkout，不會刷新或覆寫發布資料；需要明確刷新官方資料時使用 `--refresh-check`，或直接執行資料管線。

啟動 Streamlit 或執行資料流程：

```powershell
python run_all.py --mode api
python -m streamlit run app.py
```

## 重現與測試

```powershell
.\run_project.bat --check
.\run_project.bat --offline-check
.\run_project.bat --refresh-check
.\run_project.bat --runtime-check
python run_all.py --mode api
python -m pytest -q
python -m src.verify_public_release reports/metrics/public_release_manifest.json
```

CI 會驗證 security、data-health.yml、release quality、browser UI、`/_stcore/health`、資料品質與公開發布契約。`release_health.json` 代表發布健康；`public_release_manifest.json` 是含 `release_id` 與 SHA-256 的公開發布 Manifest；`player_movements.csv` 保存累計資料差異。

## 公開儲存庫政策

### 可公開追蹤

程式碼、測試、可驗證展示資料、報告摘要、必要文件與 screenshots。

### 永不追蹤

`data/processed/`（非發布所需的衍生資料）、`data/raw/`、`notes/`、`.env`、`.streamlit/secrets.toml`、cache、測試暫存與個人資料。

完整部署與審查流程見 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)、[docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)、[docs/REVIEW_GUIDE.md](docs/REVIEW_GUIDE.md) 與 [SECURITY.md](SECURITY.md)。

## 部署與營運

部署後先檢查 `/_stcore/health`，再執行 browser UI 與下載驗證；只在平台 secrets 設定環境變數。
