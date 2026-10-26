import { describe, expect, it } from "vitest";
import { mulberry32 } from "./rng";
import {
  ADVANCEMENT,
  applyEvent,
  combineLog5,
  cumulative,
  drawEvent,
  EVENTS,
  MAX_PA_PER_INNING,
  optimiseOrder,
  simulateGame,
  simulateMany,
  type EventProbabilities,
} from "./sim";

/** Deterministic RNG that returns the given values in order (then 0.99). */
const seq = (...values: number[]) => {
  let i = 0;
  return () => values[i++] ?? 0.99;
};
const NO_LUCK = () => 0.99; // never triggers any probabilistic advance
const ALWAYS = () => 0; // always triggers every probabilistic advance

const only = (event: (typeof EVENTS)[number]): EventProbabilities =>
  Object.fromEntries(EVENTS.map((e) => [e, e === event ? 1 : 0])) as EventProbabilities;

// League rates from the 2026 CPBL export (fixed fixture for calibration).
const LEAGUE: EventProbabilities = {
  single: 0.176022,
  double: 0.033308,
  triple: 0.004472,
  home_run: 0.010524,
  walk: 0.094179,
  strikeout: 0.160216,
  out: 0.52128,
};
const LEAGUE_RUNS_PER_GAME = 3.786;

describe("applyEvent advancement rules", () => {
  it("strikeouts add an out and move nobody", () => {
    expect(applyEvent({ outs: 1, bases: 0b111 }, "strikeout", NO_LUCK)).toEqual({ outs: 2, bases: 0b111, runs: 0 });
  });

  it("walks force runners only when needed", () => {
    expect(applyEvent({ outs: 0, bases: 0b000 }, "walk", NO_LUCK)).toEqual({ outs: 0, bases: 0b001, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b100 }, "walk", NO_LUCK)).toEqual({ outs: 0, bases: 0b101, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b001 }, "walk", NO_LUCK)).toEqual({ outs: 0, bases: 0b011, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b011 }, "walk", NO_LUCK)).toEqual({ outs: 0, bases: 0b111, runs: 0 });
    expect(applyEvent({ outs: 2, bases: 0b111 }, "walk", NO_LUCK)).toEqual({ outs: 2, bases: 0b111, runs: 1 });
  });

  it("singles score third, may score second and may send first to third", () => {
    expect(applyEvent({ outs: 0, bases: 0b100 }, "single", NO_LUCK)).toEqual({ outs: 0, bases: 0b001, runs: 1 });
    expect(applyEvent({ outs: 0, bases: 0b010 }, "single", NO_LUCK)).toEqual({ outs: 0, bases: 0b101, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b010 }, "single", ALWAYS)).toEqual({ outs: 0, bases: 0b001, runs: 1 });
    expect(applyEvent({ outs: 0, bases: 0b001 }, "single", NO_LUCK)).toEqual({ outs: 0, bases: 0b011, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b001 }, "single", ALWAYS)).toEqual({ outs: 0, bases: 0b101, runs: 0 });
    // Runner from second stops at third, so the runner from first cannot also take third.
    expect(applyEvent({ outs: 0, bases: 0b011 }, "single", seq(0.99, 0))).toEqual({ outs: 0, bases: 0b111, runs: 0 });
  });

  it("doubles score second and third and may score first", () => {
    expect(applyEvent({ outs: 1, bases: 0b110 }, "double", NO_LUCK)).toEqual({ outs: 1, bases: 0b010, runs: 2 });
    expect(applyEvent({ outs: 1, bases: 0b001 }, "double", NO_LUCK)).toEqual({ outs: 1, bases: 0b110, runs: 0 });
    expect(applyEvent({ outs: 1, bases: 0b001 }, "double", ALWAYS)).toEqual({ outs: 1, bases: 0b010, runs: 1 });
  });

  it("triples and home runs clear the bases", () => {
    expect(applyEvent({ outs: 2, bases: 0b111 }, "triple", NO_LUCK)).toEqual({ outs: 2, bases: 0b100, runs: 3 });
    expect(applyEvent({ outs: 2, bases: 0b111 }, "home_run", NO_LUCK)).toEqual({ outs: 2, bases: 0, runs: 4 });
    expect(applyEvent({ outs: 0, bases: 0 }, "home_run", NO_LUCK)).toEqual({ outs: 0, bases: 0, runs: 1 });
  });

  it("in-play outs: third out, double plays, sacrifice flies and productive outs", () => {
    expect(applyEvent({ outs: 2, bases: 0b100 }, "out", NO_LUCK)).toEqual({ outs: 3, bases: 0b100, runs: 0 });
    // First draw skips the error, second triggers the double play.
    expect(applyEvent({ outs: 0, bases: 0b001 }, "out", seq(0.99, 0))).toEqual({ outs: 2, bases: 0, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b100 }, "out", seq(0.99, 0))).toEqual({ outs: 1, bases: 0, runs: 1 });
    expect(applyEvent({ outs: 1, bases: 0b010 }, "out", seq(0.99, 0))).toEqual({ outs: 2, bases: 0b100, runs: 0 });
    expect(applyEvent({ outs: 1, bases: 0b001 }, "out", seq(0.99, 0.99, 0))).toEqual({ outs: 2, bases: 0b010, runs: 0 });
    expect(applyEvent({ outs: 0, bases: 0b111 }, "out", NO_LUCK)).toEqual({ outs: 1, bases: 0b111, runs: 0 });
  });

  it("reaching on an error moves every runner up one base", () => {
    expect(applyEvent({ outs: 1, bases: 0b101 }, "out", ALWAYS)).toEqual({ outs: 1, bases: 0b011, runs: 1 });
    expect(applyEvent({ outs: 2, bases: 0 }, "out", ALWAYS)).toEqual({ outs: 2, bases: 0b001, runs: 0 });
  });

  it("documents plausible advancement probabilities", () => {
    for (const value of Object.values(ADVANCEMENT)) {
      expect(value).toBeGreaterThan(0);
      expect(value).toBeLessThan(1);
    }
  });
});

describe("event drawing and log5", () => {
  it("draws events from the cumulative distribution", () => {
    const cdf = cumulative(LEAGUE);
    expect(cdf.at(-1)).toBeCloseTo(1, 12);
    expect(drawEvent(cdf, 0)).toBe("single");
    expect(drawEvent(cdf, 0.999999)).toBe("out");
    expect(drawEvent([0.5, 0.5], 0.9)).toBe("out");
  });

  it("log5 with a league-average pitcher returns the batter's own rates", () => {
    const batter = { ...LEAGUE, home_run: 0.03, out: 0.501804 };
    const total = EVENTS.reduce((sum, e) => sum + batter[e], 0);
    const combined = combineLog5(batter, LEAGUE, LEAGUE);
    for (const e of EVENTS) expect(combined[e]).toBeCloseTo(batter[e] / total, 12);
  });

  it("log5 matches the Python reference implementation", () => {
    // Same inputs as tests/test_analytics_events.py would produce.
    const batter = { ...LEAGUE, strikeout: 0.2, out: 0.481496 };
    const pitcher = { ...LEAGUE, strikeout: 0.25, out: 0.431496 };
    const combined = combineLog5(batter, pitcher, LEAGUE);
    const weights = EVENTS.map((e) => (batter[e] * pitcher[e]) / LEAGUE[e]);
    const total = weights.reduce((a, b) => a + b, 0);
    EVENTS.forEach((e, i) => expect(combined[e]).toBeCloseTo((weights[i] as number) / total, 12));
    expect(combined.strikeout).toBeGreaterThan(batter.strikeout);
  });
});

describe("game simulation", () => {
  it("an all-home-run lineup scores one run per plate appearance", () => {
    const lineup = Array(9).fill(cumulative(only("home_run")));
    const result = simulateGame(lineup, mulberry32(1));
    expect(result.runs).toBe(result.plateAppearances);
    expect(result.plateAppearances).toBe(9 * MAX_PA_PER_INNING);
  });

  it("an all-strikeout lineup never scores", () => {
    const lineup = Array(9).fill(cumulative(only("strikeout")));
    expect(simulateGame(lineup, mulberry32(1))).toEqual({ runs: 0, plateAppearances: 27 });
  });

  it("rejects an empty lineup", () => {
    expect(() => simulateGame([], mulberry32(1))).toThrow();
  });

  it("is reproducible with the same seed and differs across seeds", () => {
    const lineup = Array(9).fill(cumulative(LEAGUE));
    expect(simulateMany(lineup, 300, 42)).toEqual(simulateMany(lineup, 300, 42));
    expect(simulateMany(lineup, 300, 42)).not.toEqual(simulateMany(lineup, 300, 43));
  });

  it("reports progress", () => {
    const progress: number[] = [];
    simulateMany(Array(9).fill(cumulative(LEAGUE)), 600, 1, (d) => progress.push(d));
    expect(progress).toEqual([250, 500, 600]);
  });

  it("a league-average lineup scores within ±20% of the league's runs per game", () => {
    const runs = simulateMany(Array(9).fill(cumulative(LEAGUE)), 20_000, 2026);
    const perGame = runs.reduce((a, b) => a + b, 0) / runs.length;
    expect(Math.abs(perGame - LEAGUE_RUNS_PER_GAME) / LEAGUE_RUNS_PER_GAME).toBeLessThan(0.2);
  });
});

describe("batting order search", () => {
  it("moves the best hitters up and reports a non-negative gain", () => {
    const weak = cumulative({ ...LEAGUE, out: 0.62128, single: 0.076022 });
    const strong = cumulative({ ...LEAGUE, home_run: 0.06, single: 0.22, out: 0.427806 });
    const lineup = [weak, weak, weak, weak, weak, weak, strong, strong, strong];
    const rounds: number[] = [];
    const result = optimiseOrder(lineup, 400, 7, 3, (r) => rounds.push(r));
    expect(result.bestMean).toBeGreaterThanOrEqual(result.baselineMean);
    expect(result.delta).toBeCloseTo(result.bestMean - result.baselineMean, 9);
    expect(result.deltaLow).toBeLessThanOrEqual(result.delta);
    expect(result.deltaHigh).toBeGreaterThanOrEqual(result.delta);
    expect([...result.order].sort()).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8]);
    const strongSlots = result.order.map((p, slot) => (p >= 6 ? slot : -1)).filter((s) => s >= 0);
    expect(Math.min(...strongSlots)).toBeLessThan(6);
    expect(rounds.length).toBeGreaterThan(0);
    expect(result.evaluations).toBeGreaterThan(1);
  });

  it("stops immediately when no swap helps", () => {
    const identical = Array(9).fill(cumulative(LEAGUE));
    const result = optimiseOrder(identical, 50, 1, 2);
    expect(result.order).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8]);
    expect(result.delta).toBe(0);
  });
});

describe("held-out order evaluation", () => {
  it("reports metrics from disjoint game streams after selection", () => {
    const weak = cumulative({ ...LEAGUE, out: 0.62128, single: 0.076022 });
    const strong = cumulative({ ...LEAGUE, home_run: 0.06, single: 0.22, out: 0.427806 });
    const lineup = [weak, weak, weak, weak, weak, weak, strong, strong, strong];
    const games = 200;
    const result = optimiseOrder(lineup, games, 99, 2);
    const heldBaseline = simulateMany(lineup, games, 99, undefined, games);
    const heldBest = simulateMany(result.order.map((i) => lineup[i]!), games, 99, undefined, games);
    const avg = (x: number[]) => x.reduce((a, b) => a + b, 0) / x.length;
    expect(result.baselineMean).toBe(avg(heldBaseline));
    expect(result.bestMean).toBe(avg(heldBest));
    expect(result.delta).toBeCloseTo(avg(heldBest) - avg(heldBaseline), 10);
    expect(heldBaseline).not.toEqual(simulateMany(lineup, games, 99));
  });

  it("does not invent an improvement for exchangeable identical batters", () => {
    for (let seed = 0; seed < 12; seed += 1) {
      const result = optimiseOrder(Array(9).fill(cumulative(LEAGUE)), 40, seed, 1);
      expect(result.delta).toBe(0);
      expect(result.deltaLow).toBe(0);
      expect(result.deltaHigh).toBe(0);
    }
  });
});
