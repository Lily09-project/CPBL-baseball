"""Export verified CPBL snapshots and analytics as JSON for the web app.

The export is deterministic: it reads only committed, verified files, uses
the snapshot timestamp instead of the wall clock, sorts every collection and
rounds every float, so two runs on the same inputs produce byte-identical
files and identical SHA-256 hashes.

Usage: python -m src.export_web [--out web/public/data]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics import bayes, events, league, narrative, players
from src.utils import project_path

SCHEMA_VERSION = "2.0"
DEFAULT_OUT = Path("web/public/data")
TREND_THRESHOLDS = {"ops": 0.030, "era": 0.50}


def _read(name: str) -> pd.DataFrame:
    frame = pd.read_csv(project_path("data/processed", name), dtype={"player_id": "string"}, encoding="utf-8-sig")
    return frame


def _num(value: Any, digits: int = 4) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _write_json(path: Path, payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _interval(post: bayes.Posterior, digits: int = 4) -> dict[str, float | None]:
    return {
        "raw": _num(post.raw, digits),
        "mean": _num(post.mean, digits),
        "low": _num(post.low, digits),
        "high": _num(post.high, digits),
    }


def build_batters(batters: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = batters.to_dict("records")
    pa = [float(r["pa"] or 0) for r in rows]
    specs = {
        "obp": [round(float(r["obp"] or 0) * float(r["pa"] or 0)) for r in rows],
        "k_rate": [float(r["strikeouts"] or 0) for r in rows],
        "bb_rate": [float(r["walks"] or 0) for r in rows],
        "hr_rate": [float(r["home_runs"] or 0) for r in rows],
    }
    priors: dict[str, Any] = {}
    posts: dict[str, list[bayes.Posterior]] = {}
    for key, successes in specs.items():
        prior, post = bayes.shrink_all(successes, pa, min_trials_for_prior=players.BATTER_QUALIFIER_PA)
        priors[key] = {"alpha": _num(prior.alpha), "beta": _num(prior.beta), "mean": _num(prior.mean), "equivalent_pa": _num(prior.concentration, 1)}
        posts[key] = post
    out = []
    for i, r in enumerate(rows):
        record = {
            "player_id": str(r["player_id"]),
            "name": r["player_name"],
            "team": r["team"],
            "type": "batter",
            "position": r["position"],
            "trials": int(pa[i]),
            "qualified": pa[i] >= players.BATTER_QUALIFIER_PA,
            "stats": {
                k: _num(r[k], 3)
                for k in ["pa", "ab", "hits", "doubles", "triples", "home_runs", "walks", "strikeouts", "stolen_bases", "batting_average", "obp", "slg", "ops", "iso"]
            },
            "talent": {key: _interval(posts[key][i]) for key in specs},
            "metrics": {
                "obp_post": _num(posts["obp"][i].mean),
                "iso": _num(r["iso"]),
                "hr_rate_post": _num(posts["hr_rate"][i].mean),
                "bb_rate_post": _num(posts["bb_rate"][i].mean),
                "k_rate_post": _num(posts["k_rate"][i].mean),
                "speed": _num(float(r["stolen_bases"] or 0) / pa[i] if pa[i] else 0.0),
            },
        }
        out.append(record)
    return out, priors


def _batters_faced(outs: int, row: dict[str, Any]) -> float:
    """Estimate batters faced so every rate's successes stay within its trials.

    Outs + hits + walks (+ HBP when the source has it) misses batters who
    reached on a strikeout, so it is floored at strikeouts + hits + walks + HBP:
    each of those is a separate plate appearance.
    """
    hits, walks, strikeouts = (float(row.get(key) or 0) for key in ("hits_allowed", "walks", "strikeouts"))
    hbp = float(row.get("hit_by_pitch") or 0)
    return max(outs + hits + walks + hbp, strikeouts + hits + walks + hbp)


def build_pitchers(pitchers: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, float]]:
    rows = pitchers.to_dict("records")
    outs = [events.innings_to_outs(r["innings_pitched"]) for r in rows]
    bf = [_batters_faced(outs[i], r) for i, r in enumerate(rows)]
    ip = [o / 3 for o in outs]
    lg_ip = sum(ip)
    lg_bf = sum(bf)
    lg_hr = sum(float(r["home_runs_allowed"] or 0) for r in rows)
    lg_bb = sum(float(r["walks"] or 0) for r in rows)
    lg_k = sum(float(r["strikeouts"] or 0) for r in rows)
    lg_er = sum(float(r["earned_runs"] or 0) for r in rows)
    lg_era = 9 * lg_er / lg_ip
    fip_constant = lg_era - (13 * lg_hr + 3 * lg_bb - 2 * lg_k) / lg_ip
    min_bf = players.PITCHER_QUALIFIER_IP * 3 + 0.0
    specs = {
        "k_rate": [float(r["strikeouts"] or 0) for r in rows],
        "bb_rate": [float(r["walks"] or 0) for r in rows],
        "hr_rate": [float(r["home_runs_allowed"] or 0) for r in rows],
    }
    priors: dict[str, Any] = {}
    posts: dict[str, list[bayes.Posterior]] = {}
    for key, successes in specs.items():
        prior, post = bayes.shrink_all(successes, bf, min_trials_for_prior=min_bf)
        priors[key] = {"alpha": _num(prior.alpha), "beta": _num(prior.beta), "mean": _num(prior.mean), "equivalent_bf": _num(prior.concentration, 1)}
        posts[key] = post
    out = []
    for i, r in enumerate(rows):
        k, bb, hr = (posts[key][i].mean for key in ("k_rate", "bb_rate", "hr_rate"))
        fip_post = (13 * hr + 3 * bb - 2 * k) * (lg_bf / lg_ip) + fip_constant
        fip_raw = (
            (13 * float(r["home_runs_allowed"] or 0) + 3 * float(r["walks"] or 0) - 2 * float(r["strikeouts"] or 0)) / ip[i] + fip_constant
            if ip[i] > 0
            else None
        )
        out.append(
            {
                "player_id": str(r["player_id"]),
                "name": r["player_name"],
                "team": r["team"],
                "type": "pitcher",
                "position": r["role"],
                "trials": int(bf[i]),
                "qualified": ip[i] >= players.PITCHER_QUALIFIER_IP,
                "stats": {
                    "innings_pitched": _num(ip[i], 2),
                    **{k2: _num(r[k2], 3) for k2 in ["earned_runs", "hits_allowed", "walks", "strikeouts", "home_runs_allowed", "era", "whip", "k_bb_ratio"]},
                    "fip": _num(fip_raw, 2),
                    "batters_faced": int(bf[i]),
                },
                "talent": {key: _interval(posts[key][i]) for key in specs},
                "metrics": {
                    "k_rate_post": _num(k),
                    "bb_rate_post": _num(bb),
                    "hr_rate_post": _num(hr),
                    "fip_post": _num(fip_post, 3),
                    "whip": _num(r["whip"], 3),
                },
            }
        )
    league_info = {"era": round(lg_era, 3), "fip_constant": round(fip_constant, 3), "bf_per_ip": round(lg_bf / lg_ip, 4)}
    return out, priors, league_info


def attach_percentiles_and_similarity(records: list[dict[str, Any]], metric_defs: tuple[players.Metric, ...]) -> None:
    qualified = [r for r in records if r["qualified"]]
    for record in records:
        record["percentiles"] = {
            m.key: _num(players.percentile_of(record["metrics"][m.key], [q["metrics"][m.key] for q in qualified], m.higher_is_better), 1)
            for m in metric_defs
        }
    keys = [m.key for m in metric_defs]
    pool = [q for q in qualified if all(q["metrics"][k] is not None for k in keys)]
    ids = [q["player_id"] for q in pool]
    vectors = [{k: q["metrics"][k] for k in keys} for q in pool]
    for record in records:
        if record["player_id"] in ids:
            record["similar"] = players.explainable_similarity(vectors, ids, keys, record["player_id"])
        else:
            record["similar"] = []


def attach_trajectories(records: list[dict[str, Any]], history: pd.DataFrame) -> None:
    history = history.drop_duplicates(subset=["snapshot_id", "player_id", "player_type"]).copy()
    history["captured"] = pd.to_datetime(history["captured_at"], utc=True)
    history = history.sort_values(["captured", "snapshot_id"])
    type_map = {"batter": "打者", "pitcher": "投手"}
    for record in records:
        metric = "ops" if record["type"] == "batter" else "era"
        workload = "pa" if record["type"] == "batter" else "innings_pitched"
        rows = history[(history["player_id"] == record["player_id"]) & (history["player_type"] == type_map[record["type"]])]
        series = [
            {"t": row["captured"].strftime("%Y-%m-%d"), "v": _num(row[metric], 3), "w": _num(row[workload], 1)}
            for row in rows.to_dict("records")
            if _num(row[metric], 3) is not None
        ]
        points = [(datetime.strptime(p["t"], "%Y-%m-%d"), p["v"]) for p in series]
        trend = players.linear_trend(points)
        record["trajectory"] = {
            "metric": metric,
            "series": series,
            "trend": players.trend_label(trend, TREND_THRESHOLDS[metric], higher_is_better=metric == "ops"),
            "change": _num(trend["change"], 3) if trend else None,
        }


def attach_notes(records: list[dict[str, Any]], metric_defs: tuple[players.Metric, ...]) -> None:
    names = {r["player_id"]: r["name"] for r in records}
    for record in records:
        shrink_key = "obp" if record["type"] == "batter" else "k_rate"
        metric_key = "obp_post" if record["type"] == "batter" else "k_rate_post"
        talent = record["talent"][shrink_key]
        comparable = names.get(record["similar"][0]["player_id"]) if record["similar"] else None
        record["notes"] = narrative.scouting_notes(
            name=record["name"],
            metrics=metric_defs,
            percentiles={k: (v if v is not None else float("nan")) for k, v in record["percentiles"].items()},
            shrinkage={metric_key: (talent["raw"], talent["mean"])},
            trend=record["trajectory"]["trend"],
            trend_metric=record["trajectory"]["metric"],
            comparable_name=comparable,
            qualified=record["qualified"],
        )


def build_league(teams: pd.DataFrame, segment_games: int) -> dict[str, Any]:
    records = [
        league.TeamRecord(
            team=r.team, games=int(r.games), wins=int(r.wins), losses=int(r.losses), ties=int(r.ties),
            runs_scored=float(r.runs_scored), runs_allowed=float(r.runs_allowed),
        )
        for r in teams.itertuples(index=False)
    ]
    simulation = {row["team"]: row for row in league.simulate_segment(records, segment_games=segment_games)}
    team_rows = []
    for r in teams.sort_values(["win_pct", "team"], ascending=[False, True]).itertuples(index=False):
        expected = league.pythagorean_win_pct(float(r.runs_scored), float(r.runs_allowed))
        decided = int(r.wins) + int(r.losses)
        sim = simulation[r.team]
        team_rows.append(
            {
                "team": r.team,
                "games": int(r.games),
                "wins": int(r.wins),
                "losses": int(r.losses),
                "ties": int(r.ties),
                "win_pct": _num(r.win_pct, 3),
                "runs_scored": int(r.runs_scored),
                "runs_allowed": int(r.runs_allowed),
                "run_diff": int(r.run_diff),
                "games_behind": _num(r.games_behind, 1),
                "streak": str(r.streak),
                "recent": f"{int(r.recent_wins)}-{int(r.recent_losses)}",
                "pythag_win_pct": _num(expected, 3),
                "luck_wins": _num(int(r.wins) - expected * decided, 1),
                "simulation": {k: v for k, v in sim.items() if k != "team"},
            }
        )
    total_runs = float(teams["runs_scored"].sum())
    total_games = float(teams["games"].sum())
    return {
        "teams": team_rows,
        "runs_per_game": round(total_runs / total_games, 3),
        "segment_games": segment_games,
        "simulations": league.DEFAULT_SIMULATIONS,
        "seed": league.DEFAULT_SEED,
        "pythagorean_exponent": league.PYTHAGOREAN_EXPONENT,
    }


def build_sim_inputs(batters: pd.DataFrame, pitchers: pd.DataFrame) -> dict[str, Any]:
    batter_rows = batters.to_dict("records")
    lg = events.league_rates(batter_rows)
    mix = events.league_hit_mix(lg)
    return {
        "events": list(events.EVENTS),
        "league": {k: round(v, 6) for k, v in lg.items()},
        "batters": {
            str(r["player_id"]): events.regressed_probabilities(events.batter_counts(r), lg, events.BATTER_STABILIZER_PA)
            for r in sorted(batter_rows, key=lambda x: str(x["player_id"]))
            if float(r["pa"] or 0) > 0
        },
        "pitchers": {
            str(r["player_id"]): events.regressed_probabilities(events.pitcher_counts(r, mix), lg, events.PITCHER_STABILIZER_BF)
            for r in sorted(pitchers.to_dict("records"), key=lambda x: str(x["player_id"]))
            if events.innings_to_outs(r["innings_pitched"]) > 0
        },
        "stabilizers": {"batter_pa": events.BATTER_STABILIZER_PA, "pitcher_bf": events.PITCHER_STABILIZER_BF},
    }


def build_provenance() -> dict[str, Any]:
    manifest = json.loads(project_path("reports/metrics/public_release_manifest.json").read_text(encoding="utf-8"))
    quality = json.loads(project_path("reports/metrics/data_quality_report.json").read_text(encoding="utf-8"))
    snapshots = pd.read_csv(project_path("data/processed/snapshot_history.csv"), encoding="utf-8-sig")
    return {
        "release_id": manifest["release_id"],
        "snapshot_id": manifest["snapshot_id"],
        "generated_at": manifest["generated_at"],
        "quality_status": quality.get("quality_status"),
        "warnings": quality.get("warnings", []),
        "artifacts": [
            {"path": a["path"], "rows": a.get("row_count"), "sha256": a["sha256"]}
            for a in sorted(manifest["artifacts"], key=lambda a: a["path"])
        ],
        "snapshots": [
            {
                "snapshot_id": r.snapshot_id,
                "captured_at": r.captured_at,
                "quality_status": r.quality_status,
                "total_rows": int(r.total_rows),
                "added_rows": int(r.added_rows),
                "removed_rows": int(r.removed_rows),
                "changed_rows": int(r.changed_rows),
            }
            for r in snapshots.sort_values("captured_at").itertuples(index=False)
        ],
        "sources": [
            {"label": "CPBL 官方球員名單", "url": "https://www.cpbl.com.tw/player"},
            {"label": "CPBL 官方戰績", "url": "https://www.cpbl.com.tw/standings/season"},
            {"label": "CPBL 官方全紀錄", "url": "https://www.cpbl.com.tw/stats/recordall"},
        ],
    }


def export(out_dir: Path, segment_games: int = league.DEFAULT_SEGMENT_GAMES) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    batters = _read("batters_scored.csv").sort_values("player_id")
    pitchers = _read("pitchers_scored.csv").sort_values("player_id")
    teams = _read("teams.csv")
    history = _read("player_metric_history.csv")

    batter_records, batter_priors = build_batters(batters)
    pitcher_records, pitcher_priors, pitching_league = build_pitchers(pitchers)
    attach_percentiles_and_similarity(batter_records, players.BATTER_METRICS)
    attach_percentiles_and_similarity(pitcher_records, players.PITCHER_METRICS)
    all_records = batter_records + pitcher_records
    attach_trajectories(all_records, history)
    attach_notes(batter_records, players.BATTER_METRICS)
    attach_notes(pitcher_records, players.PITCHER_METRICS)

    summary_keys = ("player_id", "name", "team", "type", "position", "trials", "qualified", "metrics", "percentiles", "talent")
    index = [{k: r[k] for k in summary_keys} | {"trend": r["trajectory"]["trend"]} for r in all_records]
    details = {r["player_id"] + ":" + r["type"]: r for r in all_records}
    league_payload = build_league(teams, segment_games)
    league_payload["pitching"] = pitching_league
    league_payload["priors"] = {"batter": batter_priors, "pitcher": pitcher_priors}
    league_payload["metric_definitions"] = {
        "batter": [m.__dict__ for m in players.BATTER_METRICS],
        "pitcher": [m.__dict__ for m in players.PITCHER_METRICS],
    }

    files = {
        "league.json": league_payload,
        "players.json": index,
        "player-details.json": details,
        "sim.json": build_sim_inputs(batters, pitchers),
        "provenance.json": build_provenance(),
    }
    hashes = {name: _write_json(out_dir / name, payload) for name, payload in files.items()}
    _write_json(out_dir / "manifest.json", {"schema_version": SCHEMA_VERSION, "files": hashes})
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else project_path(str(args.out))
    for name, digest in export(out).items():
        print(f"{name} {digest}")


if __name__ == "__main__":
    main()
