"""Canonical CPBL source contract shared by ingestion, snapshots, and UI."""

from __future__ import annotations


CPBL_BASE_URL = "https://cpbl.com.tw"

# The action endpoint is included because the official statistics page uses it
# for its server-rendered pagination form. It is not an API claim.
OFFICIAL_SOURCE_PATHS = {
    "roster": "/player",
    "standings": "/standings/season",
    "statistics": "/stats/recordall",
    "statistics_action": "/stats/recordallaction",
}
OFFICIAL_SOURCE_URLS = tuple(f"{CPBL_BASE_URL}{path}" for path in OFFICIAL_SOURCE_PATHS.values())
SOURCE_DISPLAY_NAME = "CPBL 官方公開頁面擷取"
SOURCE_PATH_LABEL = "、".join(
    OFFICIAL_SOURCE_PATHS[name] for name in ("roster", "standings", "statistics")
)


def build_source_note(verified_date: str) -> str:
    """Return the user-facing provenance statement for processed data."""

    return (
        "球隊戰績、現役球員名單、打擊成績與投手成績取自 CPBL 官方公開頁面 "
        f"{SOURCE_PATH_LABEL}；資料擷取日期：{verified_date}。"
    )


def build_pipeline_source_reason(mode: str = "api") -> str:
    """Describe the fetch pipeline while preserving the legacy CLI mode name."""

    return f"{mode} mode: 使用 CPBL 官方公開頁面與表單分頁擷取"
