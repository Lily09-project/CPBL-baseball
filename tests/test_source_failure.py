import requests
import pytest

from src.source_contract import OFFICIAL_SOURCE_URLS
from src.source_failure import TemporaryOfficialSourceError, is_temporary_transport_error
from src.verified_pipeline import run_verified_pipeline


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
def test_404_on_exact_contracted_official_source_url_is_temporary(url):
    response = requests.Response()
    response.status_code = 404
    response.url = url
    error = requests.HTTPError("404 from official source", response=response)
    assert is_temporary_transport_error(error) is True


@pytest.mark.parametrize("url", [
    "https://www.cpbl.com.tw/not-a-contracted-page",
    "https://evil.example/player",
    "http://www.cpbl.com.tw/player",
])
def test_404_outside_exact_official_https_contract_remains_permanent(url):
    response = requests.Response()
    response.status_code = 404
    response.url = url
    error = requests.HTTPError("404", response=response)
    assert is_temporary_transport_error(error) is False


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
    (TemporaryOfficialSourceError("temporary"), 75),
    (RuntimeError("CPBL redirect timeout=timeout"), 1),
    (RuntimeError("table parsing failed: Timeout"), 1),
    (ValueError("schema validation failed"), 1),
])
def test_pipeline_exit_code_preserves_real_failures(error, expected, capsys):
    def runner():
        raise error
    assert run_verified_pipeline(runner) == expected
    assert type(error).__name__ in capsys.readouterr().err


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


def test_workflows_defer_only_explicit_temporary_exit_code():
    from pathlib import Path
    for path in (".github/workflows/data-health.yml", ".github/workflows/data-refresh.yml"):
        source = Path(path).read_text(encoding="utf-8")
        assert "grep -Eiq" not in source
        assert "python -m src.verified_pipeline --mode api" in source
        assert 'event_name }}\" = \"schedule\"' in source
        assert "-eq 75" in source
