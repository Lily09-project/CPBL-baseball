# 部署與本機執行

## 環境需求

- Python 3.12（資料管線與分析）
- Node.js 22（網站建置與測試）

## Windows 一鍵啟動

```powershell
.\run_project.bat                 # 驗證已提交資料 → 匯出 → 建置 → 開啟 http://127.0.0.1:4173
.\run_project.bat --check         # 只驗證已提交的資料與發布產物（不刷新、不啟動）
.\run_project.bat --offline-check # 同 --check，明確的離線別名
.\run_project.bat --refresh-check # 先從官方頁面刷新資料，再跑完整驗證（會寫入發布資料）
.\run_project.bat --validate      # 全部離線品質閘門：pytest、bandit、pip-audit、型別、lint、單元測試、建置、效能預算
.\run_project.bat --runtime-check # 只檢查 Python 環境
```

啟動器只綁定 `127.0.0.1`，不需要任何金鑰。

## macOS／Linux

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m src.export_web
cd web
npm ci
npm run typecheck && npm run lint && npm run coverage
npm run build && npm run size
npx playwright install chromium && npm run e2e
npm run preview
```

## 刷新官方資料

```bash
.venv/bin/python run_all.py --mode api
.venv/bin/python -m src.release_gate
.venv/bin/python -m src.verify_public_release reports/metrics/public_release_manifest.json
```

刷新會改寫 `data/processed/` 與 `reports/metrics/`，提交前請檢查 `git diff`。GitHub 上由 `data-refresh.yml` 排程執行，並只以 reviewable PR 的方式提出更新。

## GitHub Pages

見 [GITHUB_PAGES.md](GITHUB_PAGES.md)。
