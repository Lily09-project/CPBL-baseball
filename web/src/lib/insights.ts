import type { LeagueData, TeamRow } from "./types";

/**
 * Plain-language takeaways derived only from the exported league data.
 * Every field is read from the snapshot; when a fact does not hold (no team
 * out-performed its run differential, say) the field is left undefined so the
 * page shows nothing instead of a made-up claim.
 */
export interface LeagueHeadline {
  leader: TeamRow;
  runnerUp?: TeamRow;
  luckiest?: TeamRow;
  unluckiest?: TeamRow;
  /** Teams that finished first in none of the simulated seasons. */
  shutOut: TeamRow[];
  simulations: number;
}

export function rankByFirstPlace(teams: TeamRow[]): TeamRow[] {
  return [...teams].sort(
    (a, b) => b.simulation.first_place_probability - a.simulation.first_place_probability || b.wins - a.wins,
  );
}

export function leagueHeadline(league: LeagueData): LeagueHeadline | null {
  const ranked = rankByFirstPlace(league.teams);
  const leader = ranked[0];
  if (!leader) return null;
  const second = ranked[1];
  const byLuck = [...league.teams].sort((a, b) => b.luck_wins - a.luck_wins);
  const top = byLuck[0];
  const bottom = byLuck.at(-1);
  return {
    leader,
    runnerUp: second && second.simulation.first_place_probability > 0 ? second : undefined,
    luckiest: top && top.luck_wins > 0 ? top : undefined,
    unluckiest: bottom && bottom.luck_wins < 0 ? bottom : undefined,
    shutOut: ranked.filter((t) => t.simulation.first_place_probability === 0),
    simulations: league.simulations,
  };
}
