# CPBL Scouting Lab

[![Release quality](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml)
[![Security](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/security.yml)

以中華職棒公開資料建置的互動式棒球分析網站，結合統計估計、球員比較與情境模擬。

**[開啟線上展示](https://lily09-project.github.io/CPBL-baseball/)**

![CPBL Scouting Lab 桌面畫面](docs/screenshots/pages-desktop.png)

## 功能

- 球員能力估計、趨勢與可解釋的相似度比較
- 打線模擬與賽季情境分析
- 可篩選、比較並下載的球員資料
- 資料快照、來源與 SHA-256 完整性驗證

## 資料與限制

資料來自 [CPBL 球員資料](https://www.cpbl.com.tw/player)、[戰績](https://www.cpbl.com.tw/standings/season)及[成績統計](https://www.cpbl.com.tw/stats/recordall)等官方公開頁面，經檢查後保存為版本化快照。網站使用靜態資料，不是即時服務，也不是 CPBL 官方產品；資料日期會顯示在網站中。統計估計與模擬供探索使用，不代表官方預測。

## 技術

Python 資料處理與分析、React、TypeScript、Vite、Web Worker；以 GitHub Pages 提供靜態網站。

![打線實驗室](docs/screenshots/lineup-lab.png)

## 本機執行與驗證

需求：Python 3.12、Node.js 22。

```powershell
.\run_project.bat
.\run_project.bat --validate
```

驗收標準與技術細節見 [驗收文件](docs/ACCEPTANCE.md)、[模型卡](docs/MODEL_CARD.md)、[架構](docs/ARCHITECTURE.md)及[安全政策](SECURITY.md)。

公開儲存庫只保留程式碼、測試、驗證過的發布資料、文件與截圖；不提交金鑰、原始暫存資料或本機建置產物。
