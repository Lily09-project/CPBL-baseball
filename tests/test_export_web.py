from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src import export_web


@pytest.fixture(scope="module")
def exported(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("web-data")
    export_web.export(out)
    return out


def _load(path: Path, name: str):
    return json.loads((path / name).read_text(encoding="utf-8"))


def test_export_is_byte_for_byte_reproducible(exported: Path, tmp_path: Path) -> None:
    export_web.export(tmp_path)
    for name in ("league.json", "players.json", "player-details.json", "sim.json", "provenance.json", "manifest.json"):
        assert (exported / name).read_bytes() == (tmp_path / name).read_bytes(), name


def test_manifest_hashes_match_files(exported: Path) -> None:
    manifest = _load(exported, "manifest.json")
    assert manifest["schema_version"] == export_web.SCHEMA_VERSION
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((exported / name).read_bytes()).hexdigest() == digest


def test_league_payload(exported: Path) -> None:
    league = _load(exported, "league.json")
    assert len(league["teams"]) == 6
    assert sum(t["simulation"]["first_place_probability"] for t in league["teams"]) == pytest.approx(1.0)
    for team in league["teams"]:
        assert 0 < team["pythag_win_pct"] < 1
        assert team["simulation"]["games_remaining"] == league["segment_games"] - team["games"]
    assert league["runs_per_game"] > 0


def test_players_index_and_details_agree(exported: Path) -> None:
    index = _load(exported, "players.json")
    details = _load(exported, "player-details.json")
    assert len(index) == len(details)
    ids = {p["player_id"] + ":" + p["type"] for p in index}
    assert ids == set(details)
    for record in details.values():
        talent = record["talent"]
        for interval in talent.values():
            assert interval["low"] <= interval["mean"] <= interval["high"]
        for similar in record["similar"]:
            assert similar["player_id"] != record["player_id"]
            assert similar["player_id"] + ":" + record["type"] in details
        for note in record["notes"]:
            assert note["evidence"] and "{" not in note["text"]


def test_sim_inputs_are_probability_vectors(exported: Path) -> None:
    sim = _load(exported, "sim.json")
    assert sum(sim["league"].values()) == pytest.approx(1.0, abs=1e-5)
    for group in ("batters", "pitchers"):
        assert sim[group]
        for probabilities in sim[group].values():
            assert set(probabilities) == set(sim["events"])
            assert sum(probabilities.values()) == pytest.approx(1.0, abs=1e-4)


def test_provenance_matches_release_manifest(exported: Path) -> None:
    provenance = _load(exported, "provenance.json")
    release = json.loads(Path("reports/metrics/public_release_manifest.json").read_text(encoding="utf-8"))
    assert provenance["release_id"] == release["release_id"]
    assert provenance["snapshot_id"] == release["snapshot_id"]
    assert len(provenance["snapshots"]) >= 1
    assert provenance["snapshots"] == sorted(provenance["snapshots"], key=lambda s: s["captured_at"])


def test_cli_writes_into_requested_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["export_web", "--out", str(tmp_path / "out")])
    export_web.main()
    assert (tmp_path / "out" / "manifest.json").exists()
    assert "league.json" in capsys.readouterr().out


def test_pitcher_with_strikeouts_but_no_outs_does_not_crash_export() -> None:
    # A 0 IP / 1 K line (batter reached on a wild third strike) has more
    # strikeouts than outs + hits + walks; trials must still cover it.
    base = {"role": "投手", "earned_runs": 0, "home_runs_allowed": 0, "era": 0.0, "whip": 1.0, "k_bb_ratio": 2.0}
    rows = [
        {**base, "player_id": f"P{i}", "player_name": f"投手{i}", "team": "測試隊", "innings_pitched": 30.0,
         "hits_allowed": 25, "walks": 10, "strikeouts": 20, "earned_runs": 10}
        for i in range(4)
    ]
    rows.append({**base, "player_id": "P9", "player_name": "投手9", "team": "測試隊", "innings_pitched": 0.0,
                 "hits_allowed": 0, "walks": 0, "strikeouts": 1, "k_bb_ratio": float("nan")})
    out, _, _ = export_web.build_pitchers(pd.DataFrame(rows))
    record = next(r for r in out if r["player_id"] == "P9")
    assert record["stats"]["batters_faced"] == 1
    assert record["trials"] >= 1
