import { toCsv } from "./csv";
import type { MetricDefinition, PlayerDetail } from "./types";

export const MAX_COMPARE = 3;

export function addToComparison(ids: readonly string[], id: string): string[] {
  if (ids.includes(id)) return [...ids];
  return [...ids, id].slice(-MAX_COMPARE);
}

export function removeFromComparison(ids: readonly string[], id: string): string[] {
  return ids.filter((x) => x !== id);
}

export const COMPARE_COLUMNS = ["player_id", "name", "team", "type", "trials", "qualified", "metric", "label", "value", "percentile", "raw", "posterior", "low", "high"];

/** One row per player × metric so the export opens cleanly in any spreadsheet. */
export function comparisonRows(players: readonly PlayerDetail[], definitions: readonly MetricDefinition[]) {
  const talentKey: Record<string, string> = { obp_post: "obp", k_rate_post: "k_rate", bb_rate_post: "bb_rate", hr_rate_post: "hr_rate" };
  return players.flatMap((p) =>
    definitions.map((d) => {
      const t = talentKey[d.key] ? p.talent[talentKey[d.key] as string] : undefined;
      return {
        player_id: p.player_id,
        name: p.name,
        team: p.team,
        type: p.type,
        trials: p.trials,
        qualified: p.qualified,
        metric: d.key,
        label: d.label,
        value: p.metrics[d.key],
        percentile: p.percentiles[d.key],
        raw: t?.raw ?? "",
        posterior: t?.mean ?? "",
        low: t?.low ?? "",
        high: t?.high ?? "",
      };
    }),
  );
}

export function comparisonCsv(players: readonly PlayerDetail[], definitions: readonly MetricDefinition[]): string {
  return toCsv(COMPARE_COLUMNS, comparisonRows(players, definitions));
}

export function comparisonJson(players: readonly PlayerDetail[], snapshotId: string): string {
  return JSON.stringify(
    {
      snapshot_id: snapshotId,
      players: players.map(({ player_id, name, team, type, trials, qualified, metrics, percentiles, talent }) => ({
        player_id,
        name,
        team,
        type,
        trials,
        qualified,
        metrics,
        percentiles,
        talent,
      })),
    },
    null,
    2,
  );
}
