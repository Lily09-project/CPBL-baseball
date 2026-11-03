import { describe, expect, it } from "vitest";
import { leagueHeadline, rankByFirstPlace } from "./insights";
import type { LeagueData, TeamRow } from "./types";

function team(name: string, firstPlace: number, luck: number, wins = 30): TeamRow {
  return {
    team: name,
    games: 57,
    wins,
    losses: 57 - wins,
    ties: 0,
    win_pct: wins / 57,
    runs_scored: 0,
    runs_allowed: 0,
    run_diff: 0,
    games_behind: null,
    streak: "",
    recent: "",
    pythag_win_pct: 0.5,
    luck_wins: luck,
    simulation: {
      games_played: 57,
      games_remaining: 3,
      current_wins: wins,
      strength: 0.5,
      projected_wins_mean: wins,
      projected_wins_p10: wins,
      projected_wins_p50: wins,
      projected_wins_p90: wins,
      first_place_probability: firstPlace,
      additional_wins_histogram: [],
    },
  };
}

const league = (teams: TeamRow[]) => ({ teams, simulations: 10000 }) as unknown as LeagueData;

describe("league headline", () => {
  it("reads leader, runner-up, luck extremes and shut-out teams from the data", () => {
    const h = leagueHeadline(league([team("A", 0.2, 1.5), team("B", 0.8, -2), team("C", 0, 0.3)]))!;
    expect(h.leader.team).toBe("B");
    expect(h.runnerUp?.team).toBe("A");
    expect(h.luckiest?.team).toBe("A");
    expect(h.unluckiest?.team).toBe("B");
    expect(h.shutOut.map((t) => t.team)).toEqual(["C"]);
    expect(h.simulations).toBe(10000);
  });

  it("omits claims that the data does not support", () => {
    const h = leagueHeadline(league([team("A", 1, 0), team("B", 0, 0)]))!;
    expect(h.runnerUp).toBeUndefined();
    expect(h.luckiest).toBeUndefined();
    expect(h.unluckiest).toBeUndefined();
    expect(leagueHeadline(league([]))).toBeNull();
  });

  it("breaks probability ties by current wins", () => {
    expect(rankByFirstPlace([team("A", 0, 0, 20), team("B", 0, 0, 25)]).map((t) => t.team)).toEqual(["B", "A"]);
  });
});
