from pathlib import Path


def test_readme_summarizes_product_boundaries_and_links_deep_docs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8-sig")
    required = [
        "官方 CPBL 資料來源",
        "資料管線",
        "資料品質與可稽核性",
        "球探工作台",
        "球探報告",
        "report_id",
        "report_threshold",
        "player_id",
        "SHA-256",
        "評估邊界",
        "player_value_score",
        "描述性排序",
        "LOG5 僅供情境比較",
        "不是校準預測模型",
        "非 CPBL 官方服務",
        "docs/MODEL_CARD.md",
        "docs/DEPLOYMENT.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/REVIEW_GUIDE.md",
        "docs/GITHUB_PAGES.md",
        "SECURITY.md",
        "run_project.bat --check",
        "run_project.bat --offline-check",
        "python -m pytest -q",
        "python -m src.verify_public_release reports/metrics/public_release_manifest.json",
        "docs/screenshots/ui-pages.jpg",
    ]
    for term in required:
        assert term in readme
    assert readme.count("player_value_score") == 1

    policy = readme.partition("## 公開儲存庫政策")[2]
    assert policy
    assert "可公開追蹤" in policy
    assert "永不追蹤" in policy
    for term in ["data/processed/", "data/raw/", ".env", ".streamlit/secrets.toml"]:
        assert term in policy