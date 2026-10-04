# GitHub Pages

公開展示版使用 HTML、CSS 與 JavaScript，原有 Python／Streamlit 分析工具保持不變。訪客不需要登入，也不需要作者的裝置開機。

## 功能與資料

- 搜尋、分類與日期篩選、排序及手機版；展示版使用固定配色，不提供主題切換。
- 資料圖表、個別明細、最多三筆比較、CSV／JSON 下載。
- 篩選、明細與比較清單可以用網址分享；下載反映目前篩選結果。
- CPBL 使用核對通過的公開快照，保留官方球員 ID 前導零與原始更新日期；過期資料顯示提醒。只有成績資料而未對應官方名單的球員，使用既有穩定代碼，不產生官方球員連結。

公開版不執行即時 API 查詢、Python 模型或訓練，也不載入 joblib。完整分析流程仍使用原本的 Python 版本。

## 建置與驗證

Python 3.12，依專案的鎖定依賴安裝。

```bash
python -m pip install -r requirements-e2e.txt -c requirements.lock.txt
python -m src.verify_public_release reports/metrics/public_release_manifest.json
python -m pytest -q tests/test_pages_export.py
python scripts/build_pages.py
python -m http.server 8874 --bind 127.0.0.1
# 另開終端機；安裝此驗收腳本使用的 Chromium、Firefox 與 WebKit
python -m playwright install chromium firefox webkit
python tests/pages_browser_qa.py --url http://127.0.0.1:8874/pages-dist/
```

只發布 `pages-dist/` 的 HTML、CSS、JavaScript、allowlist JSON、完整性 manifest 與 `.nojekyll`。生成物、測試截圖、原始輸入、模型、secrets、repository 根目錄均不直接發布。瀏覽器先核對 JSON 雜湊，再顯示資料；雜湊用於內容完整性，不代表來源身分認證。

## 啟用與發布

1. Repository **Settings → Pages → Source** 選擇 **GitHub Actions**。
2. 檢查 PR 的 Static Pages、安全與原有功能測試，通過後合併到 `main`。
3. `Static Pages` 工作流程只在 `main`、非 PR 事件通過完整建置與 browser QA 後部署。
4. 由成功 deployment 的 `page_url` 取得實際網址；確認 HTTPS、公開無登入開啟、手機版與下載後再放入 README。

PR 分支只建置與測試，不覆寫公開網站。部署 job 使用 OIDC 與最小 Pages 權限，不需要新增 PAT 或提交金鑰。更新失敗時不部署，保留先前已發布版本；回復採 revert PR 並重新通過測試。
