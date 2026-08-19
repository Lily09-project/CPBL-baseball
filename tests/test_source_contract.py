from src.source_contract import (
    CPBL_BASE_URL,
    OFFICIAL_SOURCE_PATHS,
    OFFICIAL_SOURCE_URLS,
    SOURCE_DISPLAY_NAME,
    build_pipeline_source_reason,
    build_source_note,
)


def test_source_contract_matches_the_real_official_fetch_surface():
    assert CPBL_BASE_URL == "https://cpbl.com.tw"
    assert OFFICIAL_SOURCE_PATHS["statistics"] == "/stats/recordall"
    assert OFFICIAL_SOURCE_PATHS["statistics_action"] == "/stats/recordallaction"
    assert all(url.startswith(f"{CPBL_BASE_URL}/") for url in OFFICIAL_SOURCE_URLS)


def test_source_copy_is_precise_about_public_page_ingestion():
    note = build_source_note("2026-08-19")
    reason = build_pipeline_source_reason()

    assert SOURCE_DISPLAY_NAME == "CPBL 官方公開頁面擷取"
    assert "/stats/recordall" in note
    assert "資料擷取日期：2026-08-19" in note
    assert "官方公開頁面" in reason
    assert "API" not in note
    assert "官方 API" not in reason
