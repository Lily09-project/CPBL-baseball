"""Typed upstream failures; never classify traceback text as a network outage."""
from __future__ import annotations

import requests


class TemporaryOfficialSourceError(RuntimeError):
    """Official transport is temporarily unavailable, not a parsing failure."""


def is_temporary_transport_error(error: BaseException) -> bool:
    if isinstance(error, requests.exceptions.SSLError):
        return False
    if isinstance(error, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(error, requests.HTTPError) and error.response is not None:
        status = error.response.status_code
        return status in (403, 429) or 500 <= status <= 599
    return False
