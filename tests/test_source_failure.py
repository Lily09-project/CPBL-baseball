import json
from datetime import datetime, timedelta, timezone

import requests
import pytest

from src.source_contract import OFFICIAL_SOURCE_URLS
from src.source_failure import (
    OfficialSourceBlockedError,
    TemporaryOfficialSourceError,
    is_temporary_transport_error,
    source_block_reason,
)
from src.verified_pipeline import (
    MAX_DEFERRED_RELEASE_AGE_DAYS,
    SOURCE_BLOCKED_EXIT_CODE,
    TEMPORARY_SOURCE_EXIT_CODE,
    run_verified_pipeline,
)

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def _manifest(tmp_path, generated_at):
    path = tmp_path / "public_release_manifest.json"
    path.write_text(json.dumps({"generated_at": generated_at}), encoding="utf-8")
    return path


@pytest.mark.parametrize("status,expected", [
    (403, True), (429, True), (500, True), (503, True), (599, True),
    (400, False), (401, False), (404, False), (302, False),
])
def test_http_status_classification(status, expected):
    response = requests.Response()
    response.status_code = status
    response.url = "https://example.invalid/unrelated"
    assert is_temporary_transport_error(requests.HTTPError("upstream failure", response=response)) is expected


@pytest.mark.parametrize("url", OFFICIAL_SOURCE_URLS)
def test_404_on_contracted_official_source_url_is_not_temporary(url):
    # A month of daily 404s was once deferred as "temporary" and stayed green.
    response = requests.Response()
    response.status_code = 404
    response.url = url
    error = requests.HTTPError("404 from official source", response=response)
    assert is_temporary_transport_error(error) is False


def _response(status, url="https://www.cpbl.com.tw/player", **headers):
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.headers.update(headers)
    return response


@pytest.mark.parametrize("response", [
    _response(404, **{"X-Cache": "RULE", "x-request-id": "abc"}),
    _response(404, **{"x-cache": "rule"}),
    _response(308, Location="/player", **{"Set-Cookie": "__chtcdn=x; path=/"}),
    _response(302, Location="https://www.cpbl.com.tw/player/", **{"Set-Cookie": "__chtcdn=x"}),
])
def test_cdn_block_signals_are_recognised(response):
    assert source_block_reason(response)


@pytest.mark.parametrize("response", [
    _response(200, **{"X-Cache": "HIT"}),
    _response(404, **{"X-Cache": "MISS"}),
    _response(404),
    _response(308, Location="/player"),
    _response(308, Location="/stats/recordall", **{"Set-Cookie": "__chtcdn=x"}),
    _response(503, **{"X-Cache": "RULE"}),
])
def test_ordinary_responses_are_not_cdn_blocks(response):
    assert source_block_reason(response) is None


def test_checked_response_rejects_cdn_block_before_status_handling():
    from src.fetch_cpbl_data import _checked_response_text
    with pytest.raises(OfficialSourceBlockedError, match="X-Cache: RULE"):
        _checked_response_text(_response(404, **{"X-Cache": "RULE"}), "CPBL 官方頁面")


@pytest.mark.parametrize("error,expected", [
    (requests.Timeout("read"), True),
    (requests.ConnectionError("connection reset"), True),
    (requests.exceptions.SSLError("certificate verification failed"), False),
    (requests.HTTPError("503 Server Error without response"), False),
    (RuntimeError("Timeout 403 Client Error Max retries exceeded"), False),
    (ValueError("ConnectionError in malformed table"), False),
])
def test_only_typed_transport_errors_can_be_temporary(error, expected):
    assert is_temporary_transport_error(error) is expected


@pytest.mark.parametrize("error,expected", [
    (TemporaryOfficialSourceError("temporary"), TEMPORARY_SOURCE_EXIT_CODE),
    (OfficialSourceBlockedError("CDN rule"), SOURCE_BLOCKED_EXIT_CODE),
    (RuntimeError("CPBL redirect timeout=timeout"), 1),
    (RuntimeError("table parsing failed: Timeout"), 1),
    (ValueError("schema validation failed"), 1),
])
def test_pipeline_exit_code_preserves_real_failures(error, expected, capsys, tmp_path):
    def runner():
        raise error
    manifest = _manifest(tmp_path, (NOW - timedelta(days=1)).isoformat())
    assert run_verified_pipeline(runner, manifest_path=manifest, now=NOW) == expected
    assert type(error).__name__ in capsys.readouterr().err


@pytest.mark.parametrize("generated_at,expected", [
    ((NOW - timedelta(days=MAX_DEFERRED_RELEASE_AGE_DAYS - 0.5)).isoformat(), TEMPORARY_SOURCE_EXIT_CODE),
    ((NOW - timedelta(days=MAX_DEFERRED_RELEASE_AGE_DAYS + 0.5)).isoformat(), 1),
    ("2026-09-29T20:48:33+00:00", 1),
    ("2026-10-31T12:00:00", 1),
    ("not-a-date", 1),
])
def test_temporary_failure_stops_deferring_once_release_is_stale(generated_at, expected, tmp_path, capsys):
    def runner():
        raise TemporaryOfficialSourceError("temporary")
    manifest = _manifest(tmp_path, generated_at)
    assert run_verified_pipeline(runner, manifest_path=manifest, now=NOW) == expected
    if expected == 1:
        assert "can no longer defer" in capsys.readouterr().err


def test_missing_release_manifest_never_defers(tmp_path):
    def runner():
        raise TemporaryOfficialSourceError("temporary")
    assert run_verified_pipeline(runner, manifest_path=tmp_path / "missing.json", now=NOW) == 1


def test_successful_pipeline_exit_code():
    assert run_verified_pipeline(lambda: None) == 0


@pytest.mark.parametrize("temporary", [True, False])
def test_fetch_retry_exhaustion_retains_typed_final_cause(monkeypatch, temporary):
    import src.fetch_cpbl_data as fetcher
    error = requests.Timeout("upstream") if temporary else RuntimeError("malformed timeout=timeout")
    def fetch_once(timeout):
        raise error
    monkeypatch.setattr(fetcher, "_fetch_cpbl_official_data_once", fetch_once)
    monkeypatch.setattr(fetcher, "sleep", lambda _: None)
    expected = TemporaryOfficialSourceError if temporary else RuntimeError
    with pytest.raises(expected) as caught:
        fetcher.fetch_cpbl_official_data()
    assert caught.value.__cause__ is error
    assert isinstance(caught.value, TemporaryOfficialSourceError) is temporary


def test_fetch_does_not_retry_a_cdn_block(monkeypatch):
    import src.fetch_cpbl_data as fetcher
    calls = []
    def fetch_once(timeout):
        calls.append(timeout)
        raise OfficialSourceBlockedError("CDN rule")
    monkeypatch.setattr(fetcher, "_fetch_cpbl_official_data_once", fetch_once)
    monkeypatch.setattr(fetcher, "sleep", lambda _: None)
    with pytest.raises(OfficialSourceBlockedError):
        fetcher.fetch_cpbl_official_data()
    assert len(calls) == 1


def test_workflows_defer_only_explicit_temporary_exit_code():
    from pathlib import Path
    for path in (".github/workflows/data-health.yml", ".github/workflows/data-refresh.yml"):
        source = Path(path).read_text(encoding="utf-8")
        assert "grep -Eiq" not in source
        assert "python -m src.verified_pipeline --mode api" in source
        assert 'event_name }}\" = \"schedule\"' in source
        assert "-eq 75" in source
        assert "-eq 77" in source
