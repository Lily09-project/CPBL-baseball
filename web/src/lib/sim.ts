/**
 * Base-out Markov simulation of a nine-inning offence.
 *
 * Each plate appearance draws one of seven outcomes. Runner advancement on
 * hits and outs uses fixed, documented probabilities, so the engine stays
 * transparent: every rule below is covered by a unit test.
 */
import { gameSeed, mulberry32, type Rng } from "./rng";

export const EVENTS = ["single", "double", "triple", "home_run", "walk", "strikeout", "out"] as const;
export type GameEvent = (typeof EVENTS)[number];
export type EventProbabilities = Record<GameEvent, number>;

export const ADVANCEMENT = {
  scoreFromSecondOnSingle: 0.6,
  firstToThirdOnSingle: 0.28,
  scoreFromFirstOnDouble: 0.42,
  sacrificeFlyFromThird: 0.45,
  secondToThirdOnOut: 0.35,
  firstToSecondOnOut: 0.25,
  doublePlay: 0.12,
  reachOnError: 0.025,
} as const;

/** Safety valve: an all-home-run lineup would otherwise never make an out. */
export const MAX_PA_PER_INNING = 25;

const FIRST = 1;
const SECOND = 2;
const THIRD = 4;

export interface BaseOutState {
  outs: number;
  bases: number;
}

export interface EventResult extends BaseOutState {
  runs: number;
}

const has = (bases: number, base: number) => (bases & base) !== 0;

export function applyEvent(state: BaseOutState, event: GameEvent, rng: Rng): EventResult {
  const { outs, bases } = state;
  const b1 = has(bases, FIRST);
  const b2 = has(bases, SECOND);
  const b3 = has(bases, THIRD);
  switch (event) {
    case "strikeout":
      return { outs: outs + 1, bases, runs: 0 };
    case "out": {
      if (rng() < ADVANCEMENT.reachOnError) {
        // Batter reaches on an error: every runner moves up one base.
        return { outs, bases: ((bases << 1) & 0b111) | FIRST, runs: b3 ? 1 : 0 };
      }
      if (outs >= 2) return { outs: 3, bases, runs: 0 };
      if (b1 && rng() < ADVANCEMENT.doublePlay) {
        return { outs: outs + 2, bases: bases & ~FIRST, runs: 0 };
      }
      let next = bases;
      let runs = 0;
      if (b3 && rng() < ADVANCEMENT.sacrificeFlyFromThird) {
        runs = 1;
        next &= ~THIRD;
      }
      if (b2 && !has(next, THIRD) && rng() < ADVANCEMENT.secondToThirdOnOut) {
        next = (next & ~SECOND) | THIRD;
      }
      if (b1 && !has(next, SECOND) && rng() < ADVANCEMENT.firstToSecondOnOut) {
        next = (next & ~FIRST) | SECOND;
      }
      return { outs: outs + 1, bases: next, runs };
    }
    case "walk": {
      if (!b1) return { outs, bases: bases | FIRST, runs: 0 };
      if (!b2) return { outs, bases: bases | SECOND, runs: 0 };
      if (!b3) return { outs, bases: bases | THIRD, runs: 0 };
      return { outs, bases, runs: 1 };
    }
    case "single": {
      let runs = b3 ? 1 : 0;
      let toThird = false;
      let toSecond = false;
      if (b2) {
        if (rng() < ADVANCEMENT.scoreFromSecondOnSingle) runs += 1;
        else toThird = true;
      }
      if (b1) {
        if (!toThird && rng() < ADVANCEMENT.firstToThirdOnSingle) toThird = true;
        else toSecond = true;
      }
      return { outs, bases: FIRST | (toSecond ? SECOND : 0) | (toThird ? THIRD : 0), runs };
    }
    case "double": {
      let runs = (b3 ? 1 : 0) + (b2 ? 1 : 0);
      let toThird = false;
      if (b1) {
        if (rng() < ADVANCEMENT.scoreFromFirstOnDouble) runs += 1;
        else toThird = true;
      }
      return { outs, bases: SECOND | (toThird ? THIRD : 0), runs };
    }
    case "triple":
      return { outs, bases: THIRD, runs: (b1 ? 1 : 0) + (b2 ? 1 : 0) + (b3 ? 1 : 0) };
    case "home_run":
      return { outs, bases: 0, runs: 1 + (b1 ? 1 : 0) + (b2 ? 1 : 0) + (b3 ? 1 : 0) };
  }
}

/** Generalised log5: P(event) ∝ batter × pitcher / league. */
export function combineLog5(batter: EventProbabilities, pitcher: EventProbabilities, league: EventProbabilities): EventProbabilities {
  const weights = EVENTS.map((e) => (batter[e] * pitcher[e]) / league[e]);
  const total = weights.reduce((a, b) => a + b, 0);
  return Object.fromEntries(EVENTS.map((e, i) => [e, (weights[i] ?? 0) / total])) as EventProbabilities;
}

export function cumulative(probabilities: EventProbabilities): number[] {
  const total = EVENTS.reduce((sum, e) => sum + probabilities[e], 0);
  let running = 0;
  return EVENTS.map((e) => (running += probabilities[e] / total));
}

export function drawEvent(cdf: readonly number[], r: number): GameEvent {
  for (let i = 0; i < cdf.length; i += 1) {
    if (r < (cdf[i] ?? 1)) return EVENTS[i] as GameEvent;
  }
  return EVENTS[EVENTS.length - 1] as GameEvent;
}

export interface GameResult {
  runs: number;
  plateAppearances: number;
}

export function simulateGame(lineup: readonly (readonly number[])[], rng: Rng, innings = 9): GameResult {
  if (lineup.length === 0) throw new Error("lineup must contain at least one batter");
  let batter = 0;
  let runs = 0;
  let plateAppearances = 0;
  for (let inning = 0; inning < innings; inning += 1) {
    let state: BaseOutState = { outs: 0, bases: 0 };
    let inningPa = 0;
    while (state.outs < 3 && inningPa < MAX_PA_PER_INNING) {
      const cdf = lineup[batter % lineup.length] as readonly number[];
      const result = applyEvent(state, drawEvent(cdf, rng()), rng);
      runs += result.runs;
      state = result;
      batter += 1;
      inningPa += 1;
      plateAppearances += 1;
    }
  }
  return { runs, plateAppearances };
}

export function simulateMany(
  lineup: readonly (readonly number[])[],
  games: number,
  seed: number,
  onProgress?: (done: number) => void,
): number[] {
  const results: number[] = new Array(games);
  for (let g = 0; g < games; g += 1) {
    results[g] = simulateGame(lineup, mulberry32(gameSeed(seed, g))).runs;
    if (onProgress && (g + 1) % 250 === 0) onProgress(g + 1);
  }
  onProgress?.(games);
  return results;
}

export interface OrderSearchResult {
  order: number[];
  baselineMean: number;
  bestMean: number;
  delta: number;
  deltaLow: number;
  deltaHigh: number;
  evaluations: number;
}

/**
 * Steepest-ascent search over pairwise swaps of the batting order.
 *
 * Every candidate is evaluated with the same per-game seeds (common random
 * numbers), which makes paired comparisons far less noisy than independent
 * runs. The returned interval is a 95% CI on the per-game run difference.
 */
export function optimiseOrder(
  lineup: readonly (readonly number[])[],
  games: number,
  seed: number,
  maxRounds = 4,
  onProgress?: (round: number) => void,
): OrderSearchResult {
  const evaluate = (order: readonly number[]) => simulateMany(order.map((i) => lineup[i] as readonly number[]), games, seed);
  const mean = (xs: readonly number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
  let order = lineup.map((_, i) => i);
  const baseline = evaluate(order);
  let best = baseline;
  let evaluations = 1;
  for (let round = 0; round < maxRounds; round += 1) {
    let improved: { order: number[]; runs: number[] } | null = null;
    for (let i = 0; i < order.length; i += 1) {
      for (let j = i + 1; j < order.length; j += 1) {
        const candidate = [...order];
        [candidate[i], candidate[j]] = [candidate[j] as number, candidate[i] as number];
        const runs = evaluate(candidate);
        evaluations += 1;
        if (mean(runs) > mean(improved?.runs ?? best) + 1e-9) improved = { order: candidate, runs };
      }
    }
    onProgress?.(round + 1);
    if (!improved) break;
    order = improved.order;
    best = improved.runs;
  }
  const diffs = best.map((r, g) => r - (baseline[g] ?? 0));
  const delta = mean(diffs);
  const sd = Math.sqrt(diffs.reduce((acc, d) => acc + (d - delta) ** 2, 0) / Math.max(diffs.length - 1, 1));
  const half = (1.96 * sd) / Math.sqrt(diffs.length);
  return {
    order,
    baselineMean: mean(baseline),
    bestMean: mean(best),
    delta,
    deltaLow: delta - half,
    deltaHigh: delta + half,
    evaluations,
  };
}
