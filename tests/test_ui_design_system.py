from __future__ import annotations

from src.theme import STREAMLIT_CSS, STREAMLIT_LAYOUT_CSS, STREAMLIT_LIGHT_CSS


def test_ui_pro_max_layout_contract_is_shared_by_dark_and_light_modes() -> None:
    layout = STREAMLIT_LAYOUT_CSS
    for token in (
        "--ui-font:",
        "--ui-data-font:",
        "box-sizing: border-box",
        "font-size: clamp(",
        "min-width: 0",
        "min-height: 44px",
        "overflow-x: auto",
        "outline: 3px solid var(--focus)",
        "prefers-reduced-motion: reduce",
    ):
        assert token in layout
    assert "color-scheme: dark" in STREAMLIT_CSS
    assert "color-scheme: light" in STREAMLIT_LIGHT_CSS
    assert "--ui-content-gutter" in layout
