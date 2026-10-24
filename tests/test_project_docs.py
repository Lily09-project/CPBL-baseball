from pathlib import Path


def test_readme_summarizes_innovation_boundaries_and_links_deep_docs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8-sig")
    required = [
        "官方 CPBL 資料來源",
        "資料品質與可稽核性",
        "Empirical Bayes",
        "Monte Carlo",
        "log5",
        "SHA-256",
        "評估邊界",
        "非 CPBL 官方服務",
        "docs/ACCEPTANCE.md",
        "docs/MODEL_CARD.md",
        "docs/ARCHITECTURE.md",
        "docs/DEPLOYMENT.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/REVIEW_GUIDE.md",
        "docs/GITHUB_PAGES.md",
        "SECURITY.md",
        "run_project.bat --check",
        "run_project.bat --offline-check",
        "run_project.bat --validate",
        "python -m pytest -q",
        "python -m src.verify_public_release reports/metrics/public_release_manifest.json",
        "https://lily09-project.github.io/CPBL-baseball/",
    ]
    for term in required:
        assert term in readme, term

    for screenshot in sorted(set(__import__("re").findall(r"docs/screenshots/[\w-]+\.png", readme))):
        assert Path(screenshot).is_file(), screenshot

    policy = readme.partition("## 公開儲存庫政策")[2]
    assert "可公開追蹤" in policy
    assert "永不追蹤" in policy
    for term in ["data/processed/", "data/raw/", ".env", "web/node_modules/"]:
        assert term in policy


def test_documented_formulas_match_the_code() -> None:
    model_card = Path("docs/MODEL_CARD.md").read_text(encoding="utf-8")
    from src.analytics import events, league

    assert f"指數 {league.PYTHAGOREAN_EXPONENT}" in model_card
    assert f"{league.DEFAULT_SIMULATIONS:,} 次" in model_card
    assert f"{int(events.BATTER_STABILIZER_PA)} 個聯盟平均打席" in model_card
    assert f"{int(events.PITCHER_STABILIZER_BF)} 名聯盟平均打者" in model_card
    assert f"每隊 {league.DEFAULT_SEGMENT_GAMES} 場" in model_card
