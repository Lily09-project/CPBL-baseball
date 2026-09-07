from __future__ import annotations

import json
from pathlib import Path

from tools.ui_qa import (
    PAGE_CONTRACTS,
    STREAMLIT_EXCEPTION_SELECTOR,
    VIEWPORTS,
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
    assert viewports["landscape"][0] > viewports["landscape"][1]
    assert STREAMLIT_EXCEPTION_SELECTOR == '[data-testid="stException"]'


def test_browser_qa_is_wired_into_ci_and_kept_out_of_release_artifacts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release-quality.yml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-e2e.txt").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "python tools/ui_qa.py --url http://127.0.0.1:8852" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
    assert "playwright==1.58.0" in requirements
    assert "docs/screenshots/ui-qa/" in gitignore


def test_browser_failure_evidence_is_structured_and_atomic(tmp_path: Path) -> None:
    (tmp_path / "failure-player-mobile.png").write_bytes(b"png")
    (tmp_path / "player-mobile.png").write_bytes(b"png")
    path = write_failure_evidence("http://127.0.0.1:8852", tmp_path, "mobile/player: console error")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["status"] == "failed"
    assert "mobile/player" in payload["error"]
    assert payload["screenshots"] == ["failure-player-mobile.png", "player-mobile.png"]
    assert not (tmp_path / "failure-evidence.json.tmp").exists()
