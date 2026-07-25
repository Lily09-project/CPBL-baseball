from datetime import date

import pandas as pd
import pytest

from src.fetch_cpbl_data import (
    CURRENT_SEASON,
    clean_player_name,
    fetch_recordall,
    normalize_batters,
    parse_rank_team_player,
)


def test_clean_player_name_removes_cpbl_status_markers():
    assert clean_player_name("#麥斯威尼")[0] == "麥斯威尼"
    assert clean_player_name("▲邦力多")[0] == "邦力多"
    assert clean_player_name("邦力多 ▲")[0] == "邦力多"
    assert clean_player_name("*測試球員")[1] == "合約所屬球員（二軍）"
    assert clean_player_name("＃測試球員")[1] == "註銷註冊（二軍）"


def test_parse_rank_team_player_returns_clean_player_name():
    rank, team, player = parse_rank_team_player("12 富邦悍將 邦力多 ▲")

    assert rank == 12
    assert team == "富邦悍將"
    assert player == "邦力多"


def test_current_season_follows_system_year():
    assert CURRENT_SEASON == date.today().year


class _FakeResponse:
    def __init__(self, text: str, url: str = "https://www.cpbl.com.tw/stats/recordall") -> None:
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, pages: list[str]) -> None:
        self.pages = iter(pages)

    def get(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse('<input name="__RequestVerificationToken" value="token">')

    def post(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(next(self.pages))


def test_fetch_recordall_rejects_incomplete_pagination(monkeypatch, tmp_path):
    page_one = '<div total-paging="3"></div><table><tr><th>球員</th></tr><tr><td>1 測試隊 球員甲</td></tr></table>'
    empty_page = '<div total-paging="3"></div><table><tr><th>球員</th></tr></table>'
    monkeypatch.setattr("src.fetch_cpbl_data.project_path", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "data" / "raw").mkdir(parents=True)

    with pytest.raises(RuntimeError, match="分頁資料不完整"):
        fetch_recordall(_FakeSession([page_one, empty_page]), position="01", sortby="02")


def test_fetch_recordall_requires_pagination_metadata(monkeypatch, tmp_path):
    page_without_metadata = '<table><tr><th>球員</th></tr><tr><td>1 測試隊 球員甲</td></tr></table>'
    monkeypatch.setattr("src.fetch_cpbl_data.project_path", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "data" / "raw").mkdir(parents=True)

    with pytest.raises(RuntimeError, match="缺少分頁資訊"):
        fetch_recordall(_FakeSession([page_without_metadata]), position="01", sortby="02")


def test_normalize_batters_uses_fraction_fallback_when_percentage_columns_are_missing():
    raw = pd.DataFrame(
        [
            {
                "球員": "1 測試隊 測試打者",
                "打席": 100,
                "打數": 80,
                "安打": 24,
                "二安": 4,
                "三安": 1,
                "全壘打": 2,
                "四壞": 10,
                "被三振": 20,
                "打擊率": 0.300,
                "上壘率": 0.380,
                "長打率": 0.450,
                "整體攻擊指數": 0.830,
            }
        ]
    )
    roster = pd.DataFrame([{"player_id": "0000000001", "player_name": "測試打者", "team": "測試隊"}])

    result = normalize_batters(raw, roster).iloc[0]

    assert result["bb_rate"] == 0.10
    assert result["k_rate"] == 0.20
