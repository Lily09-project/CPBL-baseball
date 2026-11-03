"""Typed upstream failures; never classify traceback text as a network outage."""
from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests


class TemporaryOfficialSourceError(RuntimeError):
    """Official source is unavailable to this runner, not a parsing failure."""


class OfficialSourceBlockedError(RuntimeError):
    """The official CDN deliberately refuses automated access; retrying cannot help.

    The pipeline must never work around this (no browser impersonation, no
    challenge-cookie replay). An operator has to decide how to proceed.
    """


def _header(response: Any, name: str) -> str:
    headers = getattr(response, "headers", None) or {}
    value = headers.get(name)
    if value is None:
        value = next((v for k, v in headers.items() if k.lower() == name.lower()), "")
    return str(value or "")


def source_block_reason(response: Any) -> str | None:
    """Describe a deliberate CDN refusal of automated access, if this is one.

    CPBL's HiNet CDN answers blocked automated clients in two ways:
    - a synthetic ``404 NOT FOUND`` marked ``X-Cache: RULE`` (not the site's
      own 404, which is HTML served from the origin);
    - a redirect back to the same URL that only sets the ``__chtcdn``
      challenge cookie, which browsers replay automatically.
    """
    status = getattr(response, "status_code", None)
    if status is None:
        return None
    status = int(status)
    request_id = _header(response, "x-request-id") or "n/a"
    if status == 404 and _header(response, "x-cache").strip().upper() == "RULE":
        return f"CDN 規則封鎖（HTTP 404, X-Cache: RULE, x-request-id: {request_id}）"
    if 300 <= status < 400 and _header(response, "set-cookie"):
        url = str(getattr(response, "url", "") or "")
        location = _header(response, "location")
        if url and location and urljoin(url, location).rstrip("/") == url.rstrip("/"):
            return f"CDN cookie 挑戰（HTTP {status} 導回原網址並設定 cookie, x-request-id: {request_id}）"
    return None


def is_temporary_transport_error(error: BaseException) -> bool:
    if isinstance(error, requests.exceptions.SSLError):
        return False
    if isinstance(error, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(error, requests.HTTPError) and error.response is not None:
        status = error.response.status_code
        return status in (403, 429) or 500 <= status <= 599
    return False
