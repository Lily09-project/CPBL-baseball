# 審查指南：5 分鐘看懂這個專案

## 1 分鐘：打開線上網站

1. [首頁](https://lily09-project.github.io/CPBL-baseball/)：戰績表多了「畢氏勝率」與「運氣差」兩欄。
2. 按 `⌘K`（或 `/`）搜尋任一球員，例如「郭天信」。
3. 在球員檔案把滑鼠移到「依據：…」標籤，右邊對應的百分位條會亮起來。

## 2 分鐘：看創新點

- **真實實力**：切到「原始數據」排序再切回「收縮後估計」，看排名怎麼變；右側「小樣本陷阱」列出最容易誤導人的數字。
- **打線實驗室**：按「模擬 5,000 場」，再按一次結果完全相同（固定種子）；按「搜尋更好的棒次」看建議與 95% 區間。
- **資料可信度**：5 個資料檔在你的瀏覽器裡重新計算 SHA-256。

## 2 分鐘：看工程

| 想確認 | 看這裡 |
| --- | --- |
| 統計方法與假設 | [MODEL_CARD.md](MODEL_CARD.md)、`src/analytics/bayes.py` |
| 模擬引擎與測試 | `web/src/lib/sim.ts`、`web/src/lib/sim.test.ts` |
| 驗收標準怎麼訂、怎麼驗 | [ACCEPTANCE.md](ACCEPTANCE.md)、`.github/workflows/release-quality.yml` |
| E2E 與無障礙 | `web/e2e/journeys.spec.ts`、`web/e2e/quality.spec.ts` |
| 資料血緣與發布 | [ARCHITECTURE.md](ARCHITECTURE.md)、`src/public_release_manifest.py` |

## 常見問題

- **為什麼不用機器學習預測？** 公開資料只有賽季彙總，沒有逐打席資料；誠實的做法是把不確定性量化（可信區間、模擬分布），而不是給一個看似精準的預測。
- **模擬準不準？** 聯盟平均打線的模擬得分與實際每場得分差 2.6%；但它刻意不模擬守備與盜壘，適合比較相對差異。
- **為什麼是靜態網站？** 面試官點連結就能用，不需要維護伺服器；運算量（數千場模擬）用 Web Worker 在瀏覽器就能完成。
