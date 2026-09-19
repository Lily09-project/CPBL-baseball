from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "app.py"


def visible_text(app: AppTest) -> str:
    values: list[str] = []
    for collection_name in ("title", "header", "subheader", "caption", "markdown", "info", "warning"):
        for element in getattr(app, collection_name):
            values.append(str(getattr(element, "value", "")))
    for button in app.button:
        values.append(str(button.label))
    return "\n".join(values)


def test_home_uses_precise_public_page_source_language_and_actionable_empty_state():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)

    text = visible_text(app)
    assert "CPBL 官方公開頁面擷取" in text
    assert "/stats/recordall" in text
    assert "CPBL 官方 API" not in text
    assert "查看版本趨勢" in text


def test_every_page_intro_keeps_a_mobile_product_identity_marker():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)

    assert any(
        "mobile-product-brand" in str(element.value)
        for element in app.markdown
    )


def test_reviewer_guide_is_linked_from_project_readme():
    readme = Path("README.md").read_text(encoding="utf-8-sig")
    assert "docs/REVIEW_GUIDE.md" in readme
