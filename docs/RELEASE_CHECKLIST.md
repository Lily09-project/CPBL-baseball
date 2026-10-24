# Release Candidate Checklist

把變更整理成可供審查的 release candidate 時使用。完整的驗收標準見 [ACCEPTANCE.md](ACCEPTANCE.md)。

## Local Gate

```powershell
run_project.bat --validate
```

或在 macOS／Linux：

```bash
.venv/bin/python -W error -m pytest -q --cov=src.analytics --cov=src.export_web --cov-fail-under=90
.venv/bin/python -m src.release_gate
.venv/bin/python -m src.verify_public_release reports/metrics/public_release_manifest.json
.venv/bin/python -m bandit -r src run_all.py -ll
.venv/bin/python -m pip_audit --local --strict
cd web && npm run typecheck && npm run lint && npm run coverage && npm run build && npm run size && npm run e2e
git diff --check
```

## User Acceptance

- 首頁顯示官方來源、資料快照時間、資料年齡與限制。
- 真實實力頁可切換打者／投手、指標、排序依據與球隊，網址保存狀態。
- 打線實驗室可模擬、取消、以鍵盤調整棒次，並搜尋建議棒次。
- 季末模擬的奪冠機率加總為 100%，假設清楚標示。
- 球員檔案的摘要每一句都有證據標籤，相似球員可點擊前往。
- 比較頁可匯出 CSV／JSON，重新整理後狀態仍在。
- 資料可信度頁的完整性驗證為 5/5。
- 桌機、平板與手機沒有內容重疊或水平捲動；淺色與深色主題都可讀。

## Reviewer Acceptance

- `reports/metrics/data_quality_report.json` 的 `quality_status` 為 `pass` 或經人工確認的 `warning`。
- `reports/metrics/release_health.json` 不是 `failed`，且與品質報告的快照一致。
- `reports/metrics/public_release_manifest.json` 可獨立驗證，allowlist 產物都存在。
- `requirements.lock.txt` 可在乾淨的 Python 3.12 環境安裝並通過 `pip check`；`web/package-lock.json` 可 `npm ci`。
- Git diff 不包含 `.env`、secrets、raw HTML、本機路徑、`node_modules` 或建置產物。
- `data-refresh.yml` 只對驗證後的 `data/processed` 與 `reports/metrics` 建立 reviewable PR。
- 所有 workflow 的權限最小化、action 固定到 commit SHA。

## Stop Conditions

遇到以下任一情況，不應推送或合併：

- 品質閘門、release health 或公開清單驗證失敗。
- 任一測試、型別檢查、lint、覆蓋率門檻、效能預算或 E2E 失敗。
- axe 回報 serious/critical 無障礙問題。
- `export_web` 兩次輸出不一致。
- README、方法說明與實際程式公式不一致。
- 需要使用 secret 才能在本機啟動或驗證。
