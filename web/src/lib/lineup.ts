import { combineLog5, cumulative, type EventProbabilities } from "./sim";
import type { PlayerSummary, SimInputs } from "./types";

export const LINEUP_SIZE = 9;

/** The team's nine batters with the most plate appearances, in that order. */
export function defaultLineup(players: readonly PlayerSummary[], sim: SimInputs, team: string): string[] {
  return players
    .filter((p) => p.type === "batter" && p.team === team && sim.batters[p.player_id])
    .sort((a, b) => b.trials - a.trials || a.player_id.localeCompare(b.player_id))
    .slice(0, LINEUP_SIZE)
    .map((p) => p.player_id);
}

/** Fill missing slots with the league's busiest remaining batters. */
export function completeLineup(ids: readonly string[], players: readonly PlayerSummary[], sim: SimInputs): string[] {
  const chosen = ids.filter((id, i) => sim.batters[id] && ids.indexOf(id) === i).slice(0, LINEUP_SIZE);
  if (chosen.length === LINEUP_SIZE) return chosen;
  const extras = players
    .filter((p) => p.type === "batter" && sim.batters[p.player_id] && !chosen.includes(p.player_id))
    .sort((a, b) => b.trials - a.trials || a.player_id.localeCompare(b.player_id));
  return [...chosen, ...extras.slice(0, LINEUP_SIZE - chosen.length).map((p) => p.player_id)];
}

export function matchupProbabilities(sim: SimInputs, batterId: string, pitcherId?: string): EventProbabilities {
  const batter = sim.batters[batterId];
  if (!batter) throw new Error(`沒有打者 ${batterId} 的模擬資料`);
  const pitcher = pitcherId ? sim.pitchers[pitcherId] : undefined;
  return combineLog5(batter, pitcher ?? sim.league, sim.league);
}

export function lineupCdfs(sim: SimInputs, ids: readonly string[], pitcherId?: string): number[][] {
  return ids.map((id) => cumulative(matchupProbabilities(sim, id, pitcherId)));
}

export function onBaseProbability(p: EventProbabilities): number {
  return p.single + p.double + p.triple + p.home_run + p.walk;
}

export function extraBaseProbability(p: EventProbabilities): number {
  return p.double + p.triple + p.home_run;
}

export function moveSlot<T>(items: readonly T[], from: number, to: number): T[] {
  if (to < 0 || to >= items.length || from === to) return [...items];
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item as T);
  return next;
}
