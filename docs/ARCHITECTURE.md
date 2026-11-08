# CPBL Scouting Lab 架構

## 產品邊界

一個可重現的資料分析產品：把 CPBL 官方公開頁面轉成經驗證的處理後資料、版本化快照與衍生分析，再發布成純靜態的互動網站。網站不需要後端，所有模擬都在瀏覽器裡執行。

## 資料流

```text
CPBL 官方公開頁面
  └─ src/fetch_cpbl_data.py      來源主機、HTTP 與分頁契約
      └─ src/preprocess.py       正規化、型別轉換、衍生指標
          └─ src/data_quality.py schema、主鍵、重複、範圍、涵蓋量
              ├─ data/processed/*.csv
              ├─ src/snapshots.py + movements.py + history.py   快照、SHA-256、差異、歷史
              ├─ src/analysis_validation.py                      穩定性與敏感度
              ├─ src/release_health.py                           schema 漂移、列數、血緣
              └─ src/public_release_manifest.py                  公開清單與 release_id
                  └─ src/analytics/*            Empirical Bayes、事件機率、季末模擬、相似度、敘事
                      └─ src/export_web.py      確定性 JSON + manifest（SHA-256）
                          └─ web/               React + TypeScript 靜態網站
                              ├─ src/lib/       純函式：模擬、log5、路由、CSV、搜尋、資料驗證
                              ├─ src/workers/   Web Worker（Monte Carlo、棒次搜尋）
                              └─ src/routes/    頁面（延遲載入）
```

## 責任邊界

| 層 | 負責 | 不負責 |
| --- | --- | --- |
| Fetch | 官方來源、分頁、回應解析 | 業務排名規則 |
| Preprocess／Quality | 穩定欄位、型別、接受或拒絕資料 | 呈現 |
| Snapshot／History | 血緣、雜湊、版本比較 | 來源擷取 |
| Release health／Manifest | schema 漂移、列數、公開清單 | 變更業務指標 |
| Analytics | 統計推論、模擬、相似度、敘事 | HTTP、UI |
| Export | 只讀已驗證檔案、確定性輸出、manifest | 抓取資料、寫入發布資料 |
| Web | 導覽、互動、模擬、下載、完整性驗證 | 修改資料 |

## 確定性與可重現

- `export_web` 不讀系統時間，時間戳取自快照；所有集合排序、浮點數固定位數、JSON 以排序鍵輸出。CI 連跑兩次並 `diff -r`。
- 季末模擬使用 numpy `default_rng(20261024)`；打線模擬使用 mulberry32 與逐場衍生種子。
- 網站載入每個資料檔時以 Web Crypto 重算 SHA-256，與 manifest 不符就停止顯示並提示。

## 前端設計

- **路由**：Hash 路由（GitHub Pages 友善），所有篩選與選擇都寫進網址，可直接分享。
- **效能**：首頁只載入首頁需要的 JS（圖表函式庫 d3 只在其他頁面載入）與約 10 KB 資料，首屏資料檔在 HTML 中預先載入，與 JS 平行下載；其他頁面與球員清單延遲載入；球員詳細資料依打者／投手分成兩個檔案，球員頁只下載需要的一半；模擬在 Worker 執行，不阻塞主執行緒，可取消。
- **設計系統**：`styles/tokens.css` 定義色彩、字級、間距；網站固定使用單一淺色品牌配色，不讀取或跟隨系統外觀偏好。
- **可及性**：每張 SVG 圖都有 `role="img"` 摘要與可展開的等價資料表；可聚焦的捲動區；跳到主要內容；切頁時焦點移到主內容；觸控目標 ≥ 44px。
- **安全**：CSP 禁止 inline script 與第三方連線；外部連結 `noopener noreferrer`；CSV 匯出中和公式。

## 失敗行為

1. 來源或分頁契約失敗：管線拋出錯誤，不會悄悄改用樣本資料。
2. 品質規則失敗：`run_all.py` 在建立可信快照前停止。
3. Release health 偵測到 schema 漂移、列數驟降或血緣不一致：停止發布。
4. 網站資料檔雜湊不符：顯示錯誤狀態，不用不完整的資料計算。
5. 排程刷新遇到官方頁面暫時無法連線（逾時、403、429、5xx）：標記為 deferred，保留現有已驗證資料；但已發布資料超過 3 天未更新時改為失敗，不會一直綠燈。
6. 官方 CDN 刻意拒絕自動化存取（`X-Cache: RULE` 的 404，或只設定 cookie 的自我重新導向）：直接失敗（exit 77），不重試、不偽裝瀏覽器、不繞過，等人工決定資料來源的存取方式。
7. 資料凍結：因第 6 點的封鎖，2026 年資料凍結在最後一份已驗證快照，`data-refresh.yml` 與 `data-health.yml` 停用排程、僅保留手動執行；網站以 `web/src/lib/dataPolicy.ts` 的 `DATA_FROZEN` 標示凍結狀態，快照時間仍取自 `provenance.json`。
