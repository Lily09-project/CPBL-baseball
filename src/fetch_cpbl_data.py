from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from io import StringIO
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils import ensure_dirs, project_path, safe_divide


CPBL_BASE_URL = "https://www.cpbl.com.tw"
CURRENT_SEASON = date.today().year
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CPBL analytics dashboard)"}
PLAYER_MARKERS = {"*", "#", "＃", "◎", "✽", "▲"}
PLAYER_STATUS_LABELS = {
    "*": "合約所屬球員（二軍）",
    "✽": "合約所屬球員（二軍）",
    "#": "註銷註冊（二軍）",
    "＃": "註銷註冊（二軍）",
    "◎": "自主培訓或尚未註冊（二軍）",
    "▲": "CPBL 官方名單特殊標記",
}


class PlayerListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.players: list[dict[str, str]] = []
        self._in_players_list = False
        self._in_dt = False
        self._in_a = False
        self._div_depth = 0
        self._current_team = ""
        self._text_parts: list[str] = []
        self._href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "div" and "PlayersList" in (attr.get("class") or ""):
            self._in_players_list = True
            self._div_depth = 1
            return
        if self._in_players_list and tag == "div":
            self._div_depth += 1
        if not self._in_players_list:
            return
        if tag == "dt":
            self._in_dt = True
            self._text_parts = []
        elif tag == "a" and "/team/person" in (attr.get("href") or ""):
            self._in_a = True
            self._href = attr.get("href") or ""
            self._text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._in_players_list and tag == "dt" and self._in_dt:
            self._current_team = normalize_space("".join(self._text_parts))
            self._in_dt = False
            self._text_parts = []
        elif self._in_players_list and tag == "a" and self._in_a:
            raw_name = normalize_space("".join(self._text_parts))
            player_name, status = clean_player_name(raw_name)
            player_id = parse_query_value(self._href, "acnt")
            if player_name and self._current_team and player_id:
                self.players.append(
                    {
                        "season": str(CURRENT_SEASON),
                        "player_id": player_id,
                        "player_name": player_name,
                        "team": self._current_team,
                        "roster_status": status,
                        "profile_url": absolute_url(self._href),
                        "source_note": "CPBL 官方球員點將錄",
                    }
                )
            self._in_a = False
            self._href = ""
            self._text_parts = []
        elif self._in_players_list and tag == "div":
            self._div_depth -= 1
            if self._div_depth <= 0:
                self._in_players_list = False

    def handle_data(self, data: str) -> None:
        if self._in_dt or self._in_a:
            self._text_parts.append(data)


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def absolute_url(path: str) -> str:
    candidate = urljoin(f"{CPBL_BASE_URL}/", path)
    try:
        parsed = urlparse(candidate)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "www.cpbl.com.tw"
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.path != "/team/person"
            or parsed.fragment
        ):
            return ""
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) != {"acnt"} or len(query["acnt"]) != 1:
            return ""
        account = query["acnt"][0]
        if not re.fullmatch(r"\d{10}", account):
            return ""
    except ValueError:
        return ""
    return f"{CPBL_BASE_URL}/team/person?{urlencode({'acnt': account})}"


def parse_query_value(url: str, key: str) -> str:
    match = re.search(rf"[?&]{re.escape(key)}=([^&]+)", url, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def clean_player_name(raw_name: str) -> tuple[str, str]:
    markers = []
    name = raw_name.strip()
    while name and name[0] in PLAYER_MARKERS:
        markers.append(name[0])
        name = name[1:].strip()
    while name and name[-1] in PLAYER_MARKERS:
        markers.append(name[-1])
        name = name[:-1].strip()
    status_labels = list(dict.fromkeys(PLAYER_STATUS_LABELS.get(marker, f"CPBL 標記 {marker}") for marker in markers))
    status = "、".join(status_labels) if status_labels else "現役"
    return name, status


def parse_rank_team_player(value: Any) -> tuple[int, str, str]:
    text = normalize_space(value)
    match = re.match(r"^(\d+)\s+(.+?)\s+(.+)$", text)
    if not match:
        player_name, _ = clean_player_name(text)
        return 0, "", player_name
    player_name, _ = clean_player_name(match.group(3))
    return int(match.group(1)), match.group(2), player_name


def to_number(value: Any, default: float = 0.0) -> float:
    text = normalize_space(value).replace(",", "")
    text = text.replace("（", "").replace("）", "")
    if text in {"", "-", "nan", "None"}:
        return default
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    return int(round(to_number(value, float(default))))


def parse_innings(value: Any) -> float:
    text = normalize_space(value)
    if not text or text == "-":
        return 0.0
    whole, _, frac = text.partition(".")
    innings = to_int(whole)
    if frac == "1":
        return innings + 1 / 3
    if frac == "2":
        return innings + 2 / 3
    return to_number(text)


def split_wtl(value: Any) -> tuple[int, int, int]:
    parts = [to_int(part) for part in normalize_space(value).split("-")]
    if len(parts) != 3:
        return 0, 0, 0
    wins, ties, losses = parts
    return wins, ties, losses


def fetch_text(session: requests.Session, url: str, timeout: int) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def build_cpbl_session(retries: int = 3) -> requests.Session:
    retry_policy = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry_policy)
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_roster(session: requests.Session, timeout: int = 20) -> pd.DataFrame:
    html = fetch_text(session, f"{CPBL_BASE_URL}/player", timeout)
    project_path("data/raw/cpbl_player.html").write_text(html, encoding="utf-8")
    parser = PlayerListParser()
    parser.feed(html)
    roster = pd.DataFrame(parser.players).drop_duplicates(subset=["player_id"])
    if roster.empty:
        raise RuntimeError("CPBL 官方球員點將錄沒有解析到現役球員。")
    roster["season"] = pd.to_numeric(roster["season"], errors="coerce").fillna(CURRENT_SEASON).astype(int)
    return roster.sort_values(["team", "player_name"]).reset_index(drop=True)


def extract_verification_token(html: str) -> str:
    match = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
    if not match:
        raise RuntimeError("CPBL recordall 頁面缺少 __RequestVerificationToken。")
    return match.group(1)


def parse_html_table(html: str) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    if not tables:
        return pd.DataFrame()
    return tables[0]


def fetch_recordall(session: requests.Session, position: str, sortby: str, timeout: int = 20, page_size: int = 60) -> pd.DataFrame:
    start_url = f"{CPBL_BASE_URL}/stats/recordall?year={CURRENT_SEASON}&kindcode=A&position={position}&sortby={sortby}"
    page = session.get(start_url, timeout=timeout)
    page.raise_for_status()
    token = extract_verification_token(page.text)
    rows: list[pd.DataFrame] = []
    total_pages = 1
    page_index = 0
    while page_index < total_pages:
        data = {
            "__RequestVerificationToken": token,
            "ExecAction": "Q",
            "IndexOfPages": str(page_index),
            "Sortby": sortby,
            "KindCode": "A",
            "Year": str(CURRENT_SEASON),
            "Online": "01",
            "Position": position,
            "DefenceType": "99",
            "PageSize": str(page_size),
        }
        response = session.post(
            f"{CPBL_BASE_URL}/stats/recordallaction",
            data=data,
            timeout=timeout,
            headers={"Referer": page.url},
        )
        response.raise_for_status()
        raw_path = project_path(f"data/raw/cpbl_recordall_position_{position}_page_{page_index + 1}.html")
        raw_path.write_text(response.text, encoding="utf-8")
        table = parse_html_table(response.text)
        if table.empty:
            raise RuntimeError(
                f"CPBL recordall position={position} 第 {page_index + 1} 頁分頁資料不完整。"
            )
        rows.append(table)
        page_matches = re.findall(r'total-paging="(\d+)"', response.text)
        if not page_matches:
            raise RuntimeError(f"CPBL recordall position={position} 缺少分頁資訊。")
        reported_pages = int(page_matches[0])
        if reported_pages < 1:
            raise RuntimeError(f"CPBL recordall position={position} 分頁數量無效：{reported_pages}。")
        if page_index > 0 and reported_pages != total_pages:
            raise RuntimeError(
                f"CPBL recordall position={position} 分頁數量不一致：{total_pages} -> {reported_pages}。"
            )
        total_pages = reported_pages
        page_index += 1
    if not rows:
        raise RuntimeError(f"CPBL recordall position={position} 沒有回傳表格。")
    return pd.concat(rows, ignore_index=True)


def fetch_standings(session: requests.Session, timeout: int = 20) -> pd.DataFrame:
    html = fetch_text(session, f"{CPBL_BASE_URL}/standings/season", timeout)
    project_path("data/raw/cpbl_standings_season.html").write_text(html, encoding="utf-8")
    tables = pd.read_html(StringIO(html))
    if len(tables) < 3:
        raise RuntimeError("CPBL 球隊戰績頁表格不足。")
    standings = tables[0].copy()
    pitching = tables[1].copy()
    batting = tables[2].copy()
    pitch_by_team = pitching.set_index("球隊").to_dict("index")
    bat_by_team = batting.set_index("球隊").to_dict("index")
    rows = []
    for _, row in standings.iterrows():
        _, team = parse_standing_team(row.iloc[0])
        wins, ties, losses = split_wtl(row.get("勝-和-敗", "0-0-0"))
        home_wins, home_ties, home_losses = split_wtl(row.get("主場戰績", "0-0-0"))
        away_wins, away_ties, away_losses = split_wtl(row.get("客場戰績", "0-0-0"))
        recent_wins, _, recent_losses = split_wtl(row.get("近十場戰績", "0-0-0"))
        scored = to_int(bat_by_team.get(team, {}).get("得分", 0))
        allowed = to_int(pitch_by_team.get(team, {}).get("失分", 0))
        run_diff = scored - allowed
        rows.append(
            {
                "season": CURRENT_SEASON,
                "team": team,
                "games": to_int(row.get("出賽數", 0)),
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "win_pct": to_number(row.get("勝率", 0)),
                "runs_scored": scored,
                "runs_allowed": allowed,
                "run_diff": run_diff,
                "home_wins": home_wins,
                "home_losses": home_losses,
                "away_wins": away_wins,
                "away_losses": away_losses,
                "recent_wins": recent_wins,
                "recent_losses": recent_losses,
                "games_behind": 0 if normalize_space(row.get("勝差", "")) == "-" else to_number(row.get("勝差", 0)),
                "streak": normalize_space(row.get("連勝/連敗", "")),
                "source_note": "CPBL 官方目前戰績頁",
                "momentum_score": round(50 + (recent_wins - recent_losses) * 5 + run_diff / 6, 1),
            }
        )
    return pd.DataFrame(rows)


def parse_standing_team(value: Any) -> tuple[int, str]:
    text = normalize_space(value)
    match = re.match(r"^(\d+)\s+(.+)$", text)
    if not match:
        return 0, text
    return int(match.group(1)), match.group(2)


def add_player_ids(stats: pd.DataFrame, roster: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = stats.merge(roster[["player_id", "player_name", "team"]], on=["player_name", "team"], how="left")
    missing = out["player_id"].isna()
    out.loc[missing, "player_id"] = [f"{prefix}{idx + 1:04d}" for idx in range(int(missing.sum()))]
    return out


def normalize_batters(raw: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, raw_row in raw.iterrows():
        _, team, player = parse_rank_team_player(raw_row.iloc[0])
        pa = to_int(raw_row.get("打席", 0))
        ab = to_int(raw_row.get("打數", 0))
        hits = to_int(raw_row.get("安打", 0))
        doubles = to_int(raw_row.get("二安", 0))
        triples = to_int(raw_row.get("三安", 0))
        home_runs = to_int(raw_row.get("全壘打", 0))
        walks = to_int(raw_row.get("四壞", 0))
        strikeouts = to_int(raw_row.get("被三振", 0))
        avg = to_number(raw_row.get("打擊率", safe_divide(hits, ab)))
        obp = to_number(raw_row.get("上壘率", 0))
        slg = to_number(raw_row.get("長打率", 0))
        ops = to_number(raw_row.get("整體攻擊指數", obp + slg))
        raw_bb_pct = normalize_space(raw_row.get("BB%", ""))
        raw_k_pct = normalize_space(raw_row.get("K%", ""))
        bb_rate = safe_divide(walks, pa) if raw_bb_pct in {"", "-", "nan", "None"} else to_number(raw_bb_pct) / 100
        k_rate = safe_divide(strikeouts, pa) if raw_k_pct in {"", "-", "nan", "None"} else to_number(raw_k_pct) / 100
        rows.append(
            {
                "season": CURRENT_SEASON,
                "player_name": player,
                "team": team,
                "position": "野手",
                "pa": pa,
                "ab": ab,
                "hits": hits,
                "doubles": doubles,
                "triples": triples,
                "home_runs": home_runs,
                "walks": walks,
                "strikeouts": strikeouts,
                "stolen_bases": to_int(raw_row.get("盜壘", 0)),
                "batting_average": avg,
                "obp": obp,
                "slg": slg,
                "ops": ops,
                "iso": round(slg - avg, 3),
                "bb_rate": round(bb_rate, 4),
                "k_rate": round(k_rate, 4),
                "hr_rate": round(safe_divide(home_runs, pa), 4),
                "bb_k_ratio": to_number(raw_row.get("保送三振比", safe_divide(walks, strikeouts))),
                "source_note": "CPBL 官方全記錄查詢",
            }
        )
    return add_player_ids(pd.DataFrame(rows), roster, "BAT")


def normalize_pitchers(raw: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, raw_row in raw.iterrows():
        _, team, player = parse_rank_team_player(raw_row.iloc[0])
        ip = parse_innings(raw_row.get("投球局數", 0))
        walks = to_int(raw_row.get("四壞", 0))
        strikeouts = to_int(raw_row.get("奪三振", 0))
        pa = max(to_int(raw_row.get("打席", 0)), 1)
        rows.append(
            {
                "season": CURRENT_SEASON,
                "player_name": player,
                "team": team,
                "role": "投手",
                "innings_pitched": round(ip, 3),
                "earned_runs": to_int(raw_row.get("自責分", 0)),
                "hits_allowed": to_int(raw_row.get("被安打", 0)),
                "walks": walks,
                "strikeouts": strikeouts,
                "home_runs_allowed": to_int(raw_row.get("被全壘打", 0)),
                "era": to_number(raw_row.get("防禦率", 0)),
                "whip": to_number(raw_row.get("每局被上壘率", 0)),
                "k_bb_ratio": round(safe_divide(strikeouts, walks), 2),
                "k_rate": round(safe_divide(strikeouts, pa), 4),
                "bb_rate": round(safe_divide(walks, pa), 4),
                "hr_allowed_rate": round(safe_divide(to_int(raw_row.get("被全壘打", 0)), pa), 4),
                "source_note": "CPBL 官方全記錄查詢",
            }
        )
    return add_player_ids(pd.DataFrame(rows), roster, "PIT")


def fetch_cpbl_official_data(timeout: int = 20) -> dict[str, pd.DataFrame]:
    ensure_dirs()
    session = build_cpbl_session()
    roster = fetch_roster(session, timeout=timeout)
    teams = fetch_standings(session, timeout=timeout)
    batting_raw = fetch_recordall(session, position="01", sortby="02", timeout=timeout)
    pitching_raw = fetch_recordall(session, position="02", sortby="02", timeout=timeout)
    batters = normalize_batters(batting_raw, roster)
    pitchers = normalize_pitchers(pitching_raw, roster)
    counts = {
        "球隊": teams["team"].nunique() if "team" in teams else 0,
        "現役名單": roster["player_id"].nunique() if "player_id" in roster else 0,
        "打者": batters["player_id"].nunique() if "player_id" in batters else 0,
        "投手": pitchers["player_id"].nunique() if "player_id" in pitchers else 0,
    }
    minimums = {"球隊": 6, "現役名單": 200, "打者": 50, "投手": 50}
    incomplete = [f"{label} {counts[label]}（至少應有 {minimum}）" for label, minimum in minimums.items() if counts[label] < minimum]
    if incomplete:
        raise RuntimeError(f"CPBL 官方資料筆數異常：{'；'.join(incomplete)}")
    return {
        "teams": teams,
        "roster": roster,
        "batters": batters,
        "pitchers": pitchers,
    }
