from __future__ import annotations

import pandas as pd

from src.features import score_batters, score_pitchers
from src.fetch_cpbl_data import fetch_cpbl_official_data
from src.utils import ensure_dirs, project_path


def preprocess(mode: str = "api") -> dict[str, str]:
    if mode != "api":
        raise ValueError("正式資料流程只支援 api 模式。")
    ensure_dirs()
    processed = project_path("data/processed")
    official = fetch_cpbl_official_data()
    teams = official["teams"]
    roster = official["roster"]
    batters = official["batters"]
    pitchers = official["pitchers"]

    batters_scored = score_batters(batters)
    pitchers_scored = score_pitchers(pitchers)
    players = build_player_summary(roster, batters_scored, pitchers_scored)

    outputs = {
        "teams": processed / "teams.csv",
        "roster": processed / "roster.csv",
        "batters_scored": processed / "batters_scored.csv",
        "pitchers_scored": processed / "pitchers_scored.csv",
        "players_scored": processed / "players_scored.csv",
    }
    teams.to_csv(outputs["teams"], index=False, encoding="utf-8-sig")
    roster.to_csv(outputs["roster"], index=False, encoding="utf-8-sig")
    batters_scored.to_csv(outputs["batters_scored"], index=False, encoding="utf-8-sig")
    pitchers_scored.to_csv(outputs["pitchers_scored"], index=False, encoding="utf-8-sig")
    players.to_csv(outputs["players_scored"], index=False, encoding="utf-8-sig")
    return {k: str(v) for k, v in outputs.items()}


def build_player_summary(roster: pd.DataFrame, batters: pd.DataFrame, pitchers: pd.DataFrame) -> pd.DataFrame:
    players = roster.copy()
    if players.empty:
        return players
    players["player_type"] = "名單"
    players["role_or_position"] = "官方現役名單"
    players["player_value_score"] = 0.0

    score_cols = ["player_value_score"]
    hitter_cols = ["player_id", "position", "pa", *score_cols]
    pitcher_cols = ["player_id", "role", "innings_pitched", *score_cols]
    if not batters.empty and "player_id" in batters:
        hitters = batters[[col for col in hitter_cols if col in batters.columns]].copy()
        hitters = hitters.drop_duplicates(subset=["player_id"])
        hitters = hitters.rename(
            columns={
                "position": "hitter_position",
                "pa": "hitter_pa",
                **{col: f"hitter_{col}" for col in score_cols},
            }
        )
        players = players.merge(hitters, on="player_id", how="left")
    if not pitchers.empty and "player_id" in pitchers:
        arms = pitchers[[col for col in pitcher_cols if col in pitchers.columns]].copy()
        arms = arms.drop_duplicates(subset=["player_id"])
        arms = arms.rename(
            columns={
                "role": "pitcher_role",
                "innings_pitched": "pitcher_innings_pitched",
                **{col: f"pitcher_{col}" for col in score_cols},
            }
        )
        players = players.merge(arms, on="player_id", how="left")

    pitcher_available = players.get("pitcher_player_value_score", pd.Series(index=players.index, dtype=float)).notna()
    hitter_available = players.get("hitter_player_value_score", pd.Series(index=players.index, dtype=float)).notna()
    empty_workload = pd.Series(0.0, index=players.index)
    hitter_workload = pd.to_numeric(players.get("hitter_pa", empty_workload), errors="coerce").fillna(0)
    pitcher_workload = pd.to_numeric(
        players.get("pitcher_innings_pitched", empty_workload), errors="coerce"
    ).fillna(0) * 4.25
    pitcher_mask = pitcher_available & (~hitter_available | (pitcher_workload > hitter_workload))
    hitter_mask = hitter_available & ~pitcher_mask
    players.loc[hitter_mask, "player_type"] = "打者"
    players.loc[pitcher_mask, "player_type"] = "投手"
    players.loc[hitter_mask, "role_or_position"] = players.loc[hitter_mask, "hitter_position"].fillna("野手")
    players.loc[pitcher_mask, "role_or_position"] = players.loc[pitcher_mask, "pitcher_role"].fillna("投手")

    for score in score_cols:
        hitter_col = f"hitter_{score}"
        pitcher_col = f"pitcher_{score}"
        if hitter_col in players:
            players.loc[hitter_mask, score] = players.loc[hitter_mask, hitter_col].fillna(0.0)
        if pitcher_col in players:
            players.loc[pitcher_mask, score] = players.loc[pitcher_mask, pitcher_col].fillna(0.0)

    drop_cols = [
        col
        for col in players.columns
        if col.endswith("_x") or col.endswith("_y") or col.startswith("hitter_") or col.startswith("pitcher_")
    ]
    players = players.drop(columns=drop_cols, errors="ignore")

    def stat_only_rows(stats: pd.DataFrame, player_type: str, role_col: str, default_role: str) -> pd.DataFrame:
        if stats.empty or "player_id" not in stats:
            return pd.DataFrame(columns=players.columns)
        existing_ids = set(players["player_id"].astype(str))
        missing = stats[~stats["player_id"].astype(str).isin(existing_ids)].copy()
        if missing.empty:
            return pd.DataFrame(columns=players.columns)
        rows = pd.DataFrame(
            {
                "season": missing["season"] if "season" in missing else pd.Timestamp.now().year,
                "player_id": missing["player_id"],
                "player_name": missing["player_name"],
                "team": missing["team"],
                "roster_status": "官方成績表",
                "profile_url": "",
                "source_note": missing["source_note"] if "source_note" in missing else "CPBL 官方全記錄查詢",
                "player_type": player_type,
                "role_or_position": missing[role_col].fillna(default_role) if role_col in missing else default_role,
            }
        )
        for score in score_cols:
            rows[score] = missing[score].fillna(0.0) if score in missing else 0.0
        return rows.reindex(columns=players.columns)

    players = pd.concat(
        [
            players,
            stat_only_rows(batters, "打者", "position", "野手"),
            stat_only_rows(pitchers, "投手", "role", "投手"),
        ],
        ignore_index=True,
    )
    return players.drop_duplicates(subset=["player_id"], keep="first")


if __name__ == "__main__":
    preprocess()
