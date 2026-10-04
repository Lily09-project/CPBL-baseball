# CPBL — 中職成績年鑑與資料分析

[![CI](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml/badge.svg?branch=main)](https://github.com/Lily09-project/CPBL-baseball/actions/workflows/release-quality.yml)

以核對通過的 CPBL 公開快照建立可追溯的成績分析；公開展示版以球隊戰績與球員榜單為核心。

[開啟互動展示網站](https://lily09-project.github.io/CPBL-baseball/) · 不需登入，也不需作者的裝置開機。

## 展示版重點

- 閱讀球隊快照戰績、OPS 與 ERA 榜單，依球隊及最低樣本篩選。
- 查看球員完整欄位、保留官方 ID 與局數分數；支援完整球員名單。
- 最多三筆紀錄比較與 CSV／JSON 匯出；保留來源時間、更新歷程與過期提醒。

非 CPBL 官方服務，也不是即時戰績。球員成績以發布快照呈現，不推定跨球季資料；分析分數非官方評分。Python／Streamlit 的球探工作台功能另見文件。

## 介面

![球队戰績與成績榜：桌面](docs/screenshots/pages-desktop.png)
![球队戰績與成績榜：手機](docs/screenshots/pages-mobile.png)

## 本機啟動

需求：Python 3.12；Windows 可使用專案啟動器。

```powershell
git clone https://github.com/Lily09-project/CPBL-baseball.git
cd CPBL-baseball
.\run_project.bat
```

## 測試與安全

```powershell
python -m pytest -q
```

CI 執行品質、安全與 Pages 瀏覽器驗收。公開展示只發布經允許的靜態檔案與欄位；金鑰、個人資料和本機暫存不應提交。SHA-256 用於內容完整性核對，不代表來源身分認證。

部署與功能邊界見 [GitHub Pages 指南](docs/GITHUB_PAGES.md)，安全通報見 [SECURITY.md](SECURITY.md)。
