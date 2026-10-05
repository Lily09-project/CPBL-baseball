"""Typed upstream failures; never classify traceback text as a network outage."""
from __future__ import annotations

from urllib.parse import urlparse

import requests

from src.source_contract import OFFICIAL_SOURCE_URLS


class TemporaryOfficialSourceError(RuntimeError):
    """Official source is unavailable to this runner, not a parsing failure."""


def _is_known_official_page_not_found(error: requests.HTTPError) -> bool:
    """Treat a 404 as an upstream availability failure only for contracted CPBL URLs.

    CPBL's indexed public pages currently return 404 to GitHub-hosted runners.
    Scope this exception to exact official ingestion URLs; ordinary 404s and
    malformed or changed paths must remain product/source-contract failures.
    Scheduled jobs can then defer without marking stale data as verified.
    """
    response = error.response
    if response is None or response.status_code != 404:
        return False
    try:
        parsed = urlparse(str(response.url or ""))
    except ValueError:
        return False
    normalized_url = parsed._replace(query="", fragment="").geturl().rstrip("/")
    contracted_urls = {url.rstrip("/") for url in OFFICIAL_SOURCE_URLS}
    return normalized_url in contracted_urls


def is_temporary_transport_error(error: BaseException) -> bool:
    if isinstance(error, requests.exceptions.SSLError):
        return False
    if isinstance(error, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(error, requests.HTTPError) and error.response is not None:
        status = error.response.status_code
        return (
            status in (403, 429)
            or 500 <= status <= 599
            or _is_known_official_page_not_found(error)
        )
    return False
