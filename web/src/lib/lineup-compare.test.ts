import { describe, expect, it, vi } from "vitest";
import { addToComparison, comparisonCsv, comparisonJson, comparisonRows, MAX_COMPARE, removeFromComparison } from "./compare";
import { downloadText } from "./csv";
import {
  completeLineup,
  defaultLineup,
  extraBaseProbability,
  lineupCdfs,
  LINEUP_SIZE,
  matchupProbabilities,
  moveSlot,
  onBaseProbability,
} from "./lineup";
import type { EventProbabilities } from "./sim";
import type { MetricDefinition, PlayerDetail, PlayerSummary, SimInputs } from "./types";

const LEAGUE: EventProbabilities = { single: 0.17, double: 0.03, triple: 0.005, home_run: 0.01, walk: 0.09, strikeout: 0.16, out: 0.535 };
const STRONG: EventProbabilities = { ...LEAGUE, home_run: 0.05, out: 0.495 };

const summary = (id: string, team: string, trials: number, type: "batter" | "pitcher" = "batter"): PlayerSummary => ({
  player_id: id,
  name: `P${id}`,
  team,
  type,
  position: "",
  trials,
  qualified: trials >= 50,
  metrics: {},
  percentiles: {},
  talent: {},
  trend: "steady",
});

const players = [
  ...Array.from({ length: 11 }, (_, i) => summary(`a${i}`, "A", 500 - i * 10)),
  summary("b0", "B", 900),
  summary("b1", "B", 30),
  summary("p0", "A", 300, "pitcher"),
];
const sim: SimInputs = {
  events: [],
  league: LEAGUE,
  batters: Object.fromEntries(players.filter((p) => p.type === "batter").map((p) => [p.player_id, p.player_id === "b0" ? STRONG : LEAGUE])),
  pitchers: { p0: { ...LEAGUE, strikeout: 0.25, out: 0.445 } },
  stabilizers: { batter_pa: 120, pitcher_bf: 150 },
};

describe("lineup helpers", () => {
  it("builds a team's default lineup from its busiest batters", () => {
    const ids = defaultLineup(players, sim, "A");
    expect(ids).toHaveLength(LINEUP_SIZE);
    expect(ids[0]).toBe("a0");
    expect(ids).not.toContain("a9");
  });

  it("completes short or duplicated lineups with league regulars", () => {
    const ids = completeLineup(["b1", "b1", "missing"], players, sim);
    expect(ids).toHaveLength(LINEUP_SIZE);
    expect(ids[0]).toBe("b1");
    expect(new Set(ids).size).toBe(LINEUP_SIZE);
    expect(ids[1]).toBe("b0"); // busiest remaining batter
    const full = defaultLineup(players, sim, "A");
    expect(completeLineup(full, players, sim)).toEqual(full);
  });

  it("applies the opposing pitcher through log5", () => {
    const vsLeague = matchupProbabilities(sim, "a0");
    const vsAce = matchupProbabilities(sim, "a0", "p0");
    expect(vsLeague.strikeout).toBeCloseTo(LEAGUE.strikeout / 1.0, 6);
    expect(vsAce.strikeout).toBeGreaterThan(vsLeague.strikeout);
    expect(matchupProbabilities(sim, "a0", "unknown").strikeout).toBeCloseTo(vsLeague.strikeout, 9);
    expect(() => matchupProbabilities(sim, "nobody")).toThrow();
    const cdfs = lineupCdfs(sim, ["a0", "b0"], "p0");
    expect(cdfs).toHaveLength(2);
    expect(cdfs[0]?.at(-1)).toBeCloseTo(1, 9);
  });

  it("summarises on-base and extra-base chances", () => {
    expect(onBaseProbability(LEAGUE)).toBeCloseTo(0.305, 9);
    expect(extraBaseProbability(STRONG)).toBeCloseTo(0.085, 9);
  });

  it("moves slots without mutating the input", () => {
    const input = ["a", "b", "c"];
    expect(moveSlot(input, 0, 1)).toEqual(["b", "a", "c"]);
    expect(moveSlot(input, 2, 0)).toEqual(["c", "a", "b"]);
    expect(moveSlot(input, 0, -1)).toEqual(input);
    expect(moveSlot(input, 1, 1)).toEqual(input);
    expect(input).toEqual(["a", "b", "c"]);
  });
});

const definitions: MetricDefinition[] = [
  { key: "obp_post", label: "上壘能力", higher_is_better: true, fmt: "rate3", short: "上壘率" },
  { key: "iso", label: "長打力 ISO", higher_is_better: true, fmt: "rate3", short: "ISO" },
];

const detail = (id: string, name: string): PlayerDetail => ({
  ...summary(id, "A", 300),
  name,
  metrics: { obp_post: 0.35, iso: 0.15 },
  percentiles: { obp_post: 80, iso: 55 },
  talent: { obp: { raw: 0.36, mean: 0.35, low: 0.32, high: 0.38 } },
  stats: {},
  similar: [],
  notes: [],
  trajectory: { metric: "ops", series: [], trend: "steady", change: null },
});

describe("comparison helpers", () => {
  it("keeps at most three unique players, replacing the oldest", () => {
    expect(addToComparison(["a"], "a")).toEqual(["a"]);
    expect(addToComparison(["a", "b", "c"], "d")).toEqual(["b", "c", "d"]);
    expect(removeFromComparison(["a", "b"], "a")).toEqual(["b"]);
    expect(MAX_COMPARE).toBe(3);
  });

  it("exports one row per player and metric, with talent where available", () => {
    const rows = comparisonRows([detail("1", "甲"), detail("2", "=乙")], definitions);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toMatchObject({ metric: "obp_post", raw: 0.36, posterior: 0.35 });
    expect(rows[1]).toMatchObject({ metric: "iso", raw: "", posterior: "" });
    const csv = comparisonCsv([detail("2", "=乙")], definitions);
    expect(csv).toContain("'=乙");
    const json = JSON.parse(comparisonJson([detail("1", "甲")], "snap-1"));
    expect(json).toMatchObject({ snapshot_id: "snap-1", players: [{ name: "甲", talent: { obp: { mean: 0.35 } } }] });
    expect(json.players[0]).not.toHaveProperty("notes");
  });
});

describe("downloadText", () => {
  it("creates and revokes an object URL for the download", async () => {
    const create = vi.fn(() => "blob:test");
    const revoke = vi.fn();
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    downloadText("x.csv", "a,b", "text/csv");
    expect(create).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(document.querySelector("a[download]")).toBeNull();
    await new Promise((r) => setTimeout(r, 0));
    expect(revoke).toHaveBeenCalledWith("blob:test");
  });
});
