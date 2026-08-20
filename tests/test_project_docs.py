from pathlib import Path


def test_readme_explains_auditable_data_product_and_limits() -> None:
    readme = Path("README.md").read_text(encoding="utf-8-sig")
    required = [
        "官方 CPBL 資料來源",
        "資料管線",
        "資料品質與可稽核性",
        "球探工作台",
        "球探報告",
        "觀察名單",
        "report_threshold",
        "下載球探報告 Markdown",
        "下載稽核 Manifest JSON",
        "report_id",
        "評估公式",
        "資料限制",
        "重現與測試",
        "公開儲存庫政策",
        "部署與營運",
        "data-health.yml",
        "/_stcore/health",
        "非 CPBL 官方服務",
        "LOG5 為情境計算，非校準預測模型",
        "https://cpbl.com.tw/player",
        "https://cpbl.com.tw/standings/season",
        "https://cpbl.com.tw/stats/recordallaction",
        "data/raw/",
        "notes/source_prompt.txt",
        "PA >= 30",
        "IP >= 10",
        "player_value_score",
        "player_id",
        "0.70 * power_score + 0.30 * hitter_value_score",
        "0.55 * contact_score + 0.45 * discipline_score",
        "0.75 * run_prevention_score + 0.25 * pitcher_value_score",
        "0.70 * command_score + 0.30 * strikeout_score",
        "傷勢、戰術、未來表現或球員名單決策",
        "不預測比賽或產生名單建議",
        ".env",
        ".streamlit/secrets.toml",
        "data/processed/",
        "release_health.json",
        "public_release_manifest.json",
        "公開發布 Manifest",
        "release_id",
        "SHA-256",
        "發布健康",
        "player_movements.csv",
        "累計資料差異",
        "不是逐場表現或未來預測",
        "run_project.bat --runtime-check",
        "python run_all.py --mode api",
        "python -m pytest -q",
        "python -m src.verify_public_release reports/metrics/public_release_manifest.json",
        "run_project.bat --check",
    ]

    for term in required:
        assert term in readme
    assert readme.count("player_value_score") >= 2

    policy = readme.partition("## 公開儲存庫政策")[2]
    assert policy
    assert "可公開追蹤" in policy
    assert "永不追蹤" in policy
    for term in ["data/processed/", "data/raw/", ".env", ".streamlit/secrets.toml"]:
        assert term in policy
