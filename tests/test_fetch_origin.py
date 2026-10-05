from src.fetch_cpbl_data import fetch_roster
from src.source_contract import CPBL_FETCH_BASE_URL


def test_roster_uses_canonical_host_without_allowing_redirects(monkeypatch, tmp_path):
    calls = []
    class Response:
        url = CPBL_FETCH_BASE_URL + "/player"
        status_code = 200
        headers = {}
        text = '<div class="PlayersList"><dt>測試隊</dt><a href="/team/person?acnt=0000000001">球員</a></div>'
        def raise_for_status(self):
            pass
        def close(self):
            calls.append("closed")
    class Session:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()
    monkeypatch.setattr("src.fetch_cpbl_data.project_path", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "data/raw").mkdir(parents=True)
    roster = fetch_roster(Session())
    assert len(roster) == 1
    assert calls[0][0] == f"{CPBL_FETCH_BASE_URL}/player"
    assert calls[0][1]["allow_redirects"] is False
    assert calls[-1] == "closed"
