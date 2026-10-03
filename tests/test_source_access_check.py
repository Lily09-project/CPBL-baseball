"""Access diagnostics preserve strict ingestion safeguards."""
from types import SimpleNamespace

import requests

from src import source_access_check


def test_probe_is_bounded_and_does_not_spoof_a_browser(monkeypatch):
    calls = []
    sessions = []

    class Session:
        def __init__(self):
            self.headers = {"User-Agent": "CPBL analytics dashboard"}
            sessions.append(self)
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return None

    def build(retries):
        assert retries == 0
        return Session()

    def fetch(session, url, timeout):
        calls.append((session, url, timeout))
        if "/player" in url:
            raise requests.HTTPError(response=SimpleNamespace(status_code=404))
        return "public page"

    monkeypatch.setattr(source_access_check, "build_cpbl_session", build)
    monkeypatch.setattr(source_access_check, "fetch_text", fetch)
    results = source_access_check.probe_source_access()
    assert len(calls) == len(results) == 6
    assert all(url.startswith("https://www.cpbl.com.tw/") and timeout == 10 for _, url, timeout in calls)
    assert all(session.headers["User-Agent"] == "CPBL analytics dashboard" for session in sessions)
    assert [item["status"] for item in results] == [404, 200, 200, 404, 200, 200]
    assert all("body" not in item and "headers" not in item for item in results)
