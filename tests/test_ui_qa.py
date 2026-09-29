from __future__ import annotations

import json
from pathlib import Path

from tools.ui_qa import (
    focus_issues,
    CORE_VIEWPORTS,
    EXTENDED_VIEWPORTS,
    MIN_INTERACTIVE_TARGET_PX,
    interaction_smoke,
    PAGE_CONTRACTS,
    STREAMLIT_EXCEPTION_SELECTOR,
    TEXT_SCALE_CSS,
    VIEWPORTS,
    layout_issues,
    viewport_matrix,
    write_failure_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


def test_ui_qa_covers_every_public_page() -> None:
    assert len(PAGE_CONTRACTS) == 10
    assert len(set(PAGE_CONTRACTS)) == len(PAGE_CONTRACTS)
    assert "資料訊號總覽" in PAGE_CONTRACTS
    assert "球員個人頁" in PAGE_CONTRACTS
    assert "投打對決" in PAGE_CONTRACTS


def test_ui_qa_covers_desktop_small_phone_and_landscape() -> None:
    viewports = {name: (width, height) for name, width, height in VIEWPORTS}
    assert viewports["desktop"] == (1440, 1000)
    assert viewports["small-mobile"] == (375, 812)
    assert viewports["tablet"] == (768, 1024)
    assert viewports["landscape"][0] > viewports["landscape"][1]
    assert viewports["wide-tablet"] == (1024, 768)
    assert viewport_matrix() == CORE_VIEWPORTS
    assert viewport_matrix(extended=True) == CORE_VIEWPORTS + EXTENDED_VIEWPORTS
    assert STREAMLIT_EXCEPTION_SELECTOR == '[data-testid="stException"]'
    assert "200%" in TEXT_SCALE_CSS


def test_layout_issues_is_fail_closed_for_browser_contract() -> None:
    assert callable(layout_issues)
    assert callable(focus_issues)
    assert callable(interaction_smoke)
    assert MIN_INTERACTIVE_TARGET_PX == 44


def test_browser_qa_is_wired_into_ci_and_kept_out_of_release_artifacts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release-quality.yml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-e2e.txt").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "python tools/ui_qa.py --url http://127.0.0.1:8852" in workflow
    assert (
        "python tools/ui_qa.py --url http://127.0.0.1:8852 --extended --text-scale"
        in workflow
    )
    assert "python -m playwright install --with-deps chromium" in workflow
    assert "playwright==1.58.0" in requirements
    assert "docs/screenshots/ui-qa/" in gitignore


def test_focus_audit_uses_real_keyboard_tab_navigation() -> None:
    source = Path("tools/ui_qa.py").read_text(encoding="utf-8")

    assert 'page.keyboard.press("Tab")' in source
    assert "keyboard focus did not reach the skip link" in source
    assert ".focus({preventScroll: true})" not in source

    app_source = Path("app.py").read_text(encoding="utf-8")
    assert '<a class="skip-link" href="#cpbl-main" tabindex="0">' in app_source


def test_focus_audit_validates_radio_proxy_and_mobile_controls() -> None:
    source = Path("tools/ui_qa.py").read_text(encoding="utf-8")
    start = source.index("def focus_issues(page)")
    focus_source = source[start:source.index(chr(10) + "def ", start + 1)]

    assert 'page.keyboard.press("Tab")' in focus_source
    assert "page.wait_for_function(" in focus_source
    assert "DOMMatrixReadOnly" in focus_source
    assert "document.body.setAttribute('tabindex', '-1')" in focus_source
    assert "page.wait_for_timeout(300)" not in focus_source
    assert 'input[type="radio"]' in focus_source
    assert "keyboard-focused radio proxy lacks a visible focus indicator" in focus_source

    theme = Path("src/theme.py").read_text(encoding="utf-8")
    assert ':has(input[type="radio"]:focus-visible)' in theme
    assert 'data-testid="stExpandSidebarButton"' in theme
    assert 'data-testid="stSidebarCollapseButton"' in theme
    assert 'visibility: hidden !important;' in theme
    assert '[data-testid="stSidebar"][aria-expanded="false"] *' in theme

    app_source = Path("app.py").read_text(encoding="utf-8")
    assert app_source.index("st.markdown(STREAMLIT_LIGHT_CSS") < app_source.index(
        "st.markdown(STREAMLIT_LAYOUT_CSS"
    )


def test_browser_failure_evidence_is_structured_and_atomic(tmp_path: Path) -> None:
    (tmp_path / "failure-player-mobile.png").write_bytes(b"png")
    (tmp_path / "player-mobile.png").write_bytes(b"png")
    path = write_failure_evidence("http://127.0.0.1:8852", tmp_path, "mobile/player: console error")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["status"] == "failed"
    assert "mobile/player" in payload["error"]
    assert payload["screenshots"] == ["failure-player-mobile.png", "player-mobile.png"]
    assert not (tmp_path / "failure-evidence.json.tmp").exists()
