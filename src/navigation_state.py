from __future__ import annotations

from collections.abc import Collection


def resolve_navigation_page(
    requested_page: str,
    session_page: object,
    last_synced_page: object,
    valid_pages: Collection[str],
    default_page: str,
) -> str:
    """Resolve navigation without overriding a fresh widget selection."""

    valid = tuple(valid_pages)
    if default_page not in valid:
        raise ValueError("default_page must be included in valid_pages")

    requested = requested_page if requested_page in valid else default_page
    session = session_page if isinstance(session_page, str) and session_page in valid else None
    last_synced = last_synced_page if isinstance(last_synced_page, str) else None

    if session is None:
        return requested
    if last_synced is None:
        return requested if requested_page in valid else session
    if requested_page != last_synced:
        return requested
    return session
