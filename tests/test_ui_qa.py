from __future__ import annotations

import json
from pathlib import Path

from tools.ui_qa import (
    focus_issues,
    capture_scroll_evidence,
    SCROLL_EVIDENCE_MAX_SEGMENTS,
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
    assert '[data-testid="stSidebar"][data-collapsed="true"] *' in theme

    app_source = Path("app.py").read_text(encoding="utf-8")
    assert app_source.index("st.markdown(STREAMLIT_LIGHT_CSS") < app_source.index(
        "st.markdown(STREAMLIT_LAYOUT_CSS"
    )


def test_interaction_smoke_opens_collapsed_sidebar_with_user_control() -> None:
    source = Path("tools/ui_qa.py").read_text(encoding="utf-8")

    assert 'data-testid="stExpandSidebarButton"' in source
    assert 'get_attribute("data-collapsed")' in source


def test_browser_failure_evidence_is_structured_and_atomic(tmp_path: Path) -> None:
    (tmp_path / "failure-player-mobile.png").write_bytes(b"png")
    (tmp_path / "player-mobile.png").write_bytes(b"png")
    path = write_failure_evidence("http://127.0.0.1:8852", tmp_path, "mobile/player: console error")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["status"] == "failed"
    assert "mobile/player" in payload["error"]
    assert payload["screenshots"] == ["failure-player-mobile.png", "player-mobile.png"]
    assert not (tmp_path / "failure-evidence.json.tmp").exists()

def test_browser_ci_retains_candidate_visual_evidence() -> None:
    workflow = Path(".github/workflows/release-quality.yml").read_text(encoding="utf-8")
    evidence = workflow.split("name: Retain browser visual acceptance evidence", 1)[1]
    assert "if: always()" in evidence
    assert "actions/upload-artifact@" in evidence
    assert "docs/screenshots/ui-qa/*.png" in evidence
    assert "docs/screenshots/ui-qa/failure-evidence.json" in evidence
    assert "github.run_attempt" in evidence


class _ScrollPage:
    def __init__(self, total: int = 2100, top: int = 170) -> None:
        self.total = total
        self.top = top
        self.behavior = "smooth"
        self.shots = []

    def evaluate(self, script, command):
        assert '[data-testid="stMain"]' in script
        previous = self.behavior
        if command["action"] == "start":
            self.behavior = "auto"
        elif command["action"] in {"move", "restore"}:
            self.top = min(command["top"], max(0, self.total - 1000))
        if command["action"] == "restore":
            self.behavior = command["behavior"]
        return {"top": self.top, "height": 1000, "total": self.total,
                "behavior": previous}

    def wait_for_timeout(self, duration):
        assert duration == 150

    def screenshot(self, *, path, full_page):
        assert full_page is False
        self.shots.append(path)


def test_scroll_evidence_reaches_bottom_and_restores_original_position(tmp_path: Path) -> None:
    page = _ScrollPage()
    assert capture_scroll_evidence(page, tmp_path, "route-desktop") == []
    report = json.loads((tmp_path / "route-desktop-scroll.json").read_text())
    assert report["complete"] is True
    assert report["manual_visual_acceptance"] == "pending"
    assert [part["top"] for part in report["segments"]] == [0, 800, 1100]
    assert page.top == 170
    assert page.behavior == "smooth"
    assert len(page.shots) == 3


def test_scroll_evidence_handles_pages_shorter_than_the_viewport(tmp_path: Path) -> None:
    page = _ScrollPage(total=600, top=0)
    assert capture_scroll_evidence(page, tmp_path, "short") == []
    assert len(page.shots) == 1
    assert json.loads((tmp_path / "short-scroll.json").read_text())["complete"] is True


def test_scroll_evidence_limit_is_an_explicit_failure_not_silent_truncation(tmp_path: Path) -> None:
    page = _ScrollPage(total=1_000_000)
    issues = capture_scroll_evidence(page, tmp_path, "long")
    assert issues == ["scroll evidence limit reached before the page bottom"]
    assert len(page.shots) == SCROLL_EVIDENCE_MAX_SEGMENTS
    assert json.loads((tmp_path / "long-scroll.json").read_text())["complete"] is False
    assert page.top == 170
    assert page.behavior == "smooth"


def test_scroll_evidence_restores_scrollport_when_screenshot_fails(tmp_path: Path) -> None:
    import pytest

    page = _ScrollPage()

    def fail(**kwargs):
        raise RuntimeError("Screenshot failed")

    page.screenshot = fail
    with pytest.raises(RuntimeError, match="Screenshot failed"):
        capture_scroll_evidence(page, tmp_path, "failure")
    assert page.top == 170
    assert page.behavior == "smooth"
    assert json.loads((tmp_path / "failure-scroll.json").read_text())["complete"] is False
