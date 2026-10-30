# CPBL Scouting Lab

[![Release quality](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml)
[![Security](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/security.yml)

以中華職棒公開資料建置的互動式棒球分析網站，結合球員評估、打線模擬與賽季情境分析。

**[開啟線上展示](https://lily09-project.github.io/CPBL-baseball/)**

![CPBL Scouting Lab 桌面畫面](docs/screenshots/pages-desktop.png)

## 功能

- 球員能力估計、趨勢、相似度與比較
- Empirical Bayes 小樣本修正、log5 對戰估計與 Monte Carlo 模擬
- 可篩選、比較及下載的球員資料
- 資料快照與 SHA-256 完整性驗證

## 資料與評估邊界

官方 CPBL 資料來源包含[球員](https://www.cpbl.com.tw/player)、[戰績](https://www.cpbl.com.tw/standings/season)及[成績統計](https://www.cpbl.com.tw/stats/recordall)等公開頁面。資料經過資料品質與可稽核性檢查後保存為版本化快照；網站使用靜態資料，不是即時服務。這是非 CPBL 官方服務，估計與模擬僅供研究和情境比較，不代表官方預測。

## 技術與畫面

Python 資料處理與分析、React、TypeScript、Vite、Web Worker；GitHub Pages 提供靜態網站。介面採黑白運動報刊風格，設計原則見 [DESIGN.md](DESIGN.md)。

| 打線實驗室 | 真實實力估計 |
| --- | --- |
| ![打線實驗室](docs/screenshots/lineup-lab.png) | ![真實實力估計](docs/screenshots/talent.png) |
| **球員檔案** | **季末戰績模擬** |
| ![球員檔案](docs/screenshots/player-profile.png) | ![季末戰績模擬](docs/screenshots/season.png) |

## 本機執行與驗證

需求：Python 3.12、Node.js 22。

```powershell
.\run_project.bat
.\run_project.bat --validate
.\run_project.bat --check
.\run_project.bat --offline-check
```

```bash
python -m pytest -q
python -m src.verify_public_release reports/metrics/public_release_manifest.json
```

細節：[驗收](docs/ACCEPTANCE.md) · [模型卡](docs/MODEL_CARD.md) · [架構](docs/ARCHITECTURE.md) · [部署](docs/DEPLOYMENT.md) · [發布清單](docs/RELEASE_CHECKLIST.md) · [審查指南](docs/REVIEW_GUIDE.md) · [GitHub Pages](docs/GITHUB_PAGES.md) · [安全政策](SECURITY.md)

## 公開儲存庫政策

可公開追蹤：程式碼、測試、`data/processed/`、`reports/metrics/`、必要文件與介面截圖。
永不追蹤：`data/raw/`、`.env`、金鑰、憑證、`web/node_modules/`、本機建置產物與使用者資料。
