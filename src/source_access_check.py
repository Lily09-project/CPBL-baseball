"""Bounded, read-only source access diagnostics; never publish or verify a release."""
from __future__ import annotations

import hashlib
import json

import requests

from src.fetch_cpbl_data import build_cpbl_session, fetch_text
from src.source_contract import CPBL_FETCH_BASE_URL, OFFICIAL_SOURCE_PATHS


def probe_source_access() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    # Keep the truthful application User-Agent. Compare standard HTML content
    # negotiation, not browser impersonation, credentials, proxies, or redirects.
    for mode, headers in (
        ("application-default", {}),
        ("html-content-negotiation", {"Accept": "text/html,application/xhtml+xml", "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.5"}),
    ):
        with build_cpbl_session(retries=0) as session:
            session.headers.update(headers)
            for source in ("roster", "standings", "statistics"):
                url = f"{CPBL_FETCH_BASE_URL}{OFFICIAL_SOURCE_PATHS[source]}"
                result: dict[str, object] = {"mode": mode, "source": source, "url": url}
                try:
                    text = fetch_text(session, url, timeout=10)
                except requests.HTTPError as exc:
                    result["status"] = exc.response.status_code if exc.response is not None else "http-error"
                except (requests.RequestException, RuntimeError) as exc:
                    # Do not print response bodies, cookies, tokens, or exception
                    # strings that could contain unexpected upstream content.
                    result["status"] = type(exc).__name__
                else:
                    encoded = text.encode("utf-8")
                    result.update(status=200, decoded_bytes=len(encoded), sha256=hashlib.sha256(encoded).hexdigest())
                results.append(result)
    return results


def main() -> int:
    print(json.dumps({"purpose": "access-diagnostic-only", "results": probe_source_access()}, ensure_ascii=False))
    # Diagnostics are supplementary. The preceding failed health step remains
    # failed; this function cannot approve or publish a data release.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
