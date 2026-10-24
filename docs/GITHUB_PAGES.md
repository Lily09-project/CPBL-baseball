# GitHub Pages

[開啟線上實驗室](https://lily09-project.github.io/CPBL-baseball/)

## 發布流程

`.github/workflows/pages.yml` 在合併到 `main` 時執行：

1. 以鎖定的 Python 環境驗證公開發布清單（`src.verify_public_release`）。
2. `python -m src.export_web` 由已驗證快照產生確定性 JSON 與 manifest。
3. `npm ci && npm run build && npm run size` 建置靜態網站並檢查效能預算。
4. 只上傳 `web/dist/`，不發布儲存庫根目錄。
5. 部署後的冒煙測試確認首頁與 `data/manifest.json` 可讀取。

PR 階段由 `release-quality.yml` 跑完整的型別、lint、單元、E2E 與無障礙檢查。

## 網站邊界

- 純靜態，作者的電腦不必開機；不執行任何後端程式。
- 所有資料檔在瀏覽器端以 SHA-256 驗證；不符時停止顯示。
- 執行期不呼叫任何第三方網址；外部連結只有 CPBL 官方頁面。
- 非 CPBL 官方服務，也不是即時戰績；資料停在快照時間。
