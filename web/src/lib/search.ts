import type { PlayerSummary } from "./types";

const normalise = (text: string) => text.normalize("NFKC").toLowerCase().replace(/\s+/g, "");

/**
 * Rank players for the quick search: exact name, prefix, substring, then
 * team matches. Ties keep qualified players and larger samples first.
 */
export function searchPlayers(players: readonly PlayerSummary[], query: string, limit = 8): PlayerSummary[] {
  const q = normalise(query);
  if (!q) return [];
  const scored: { player: PlayerSummary; score: number }[] = [];
  for (const player of players) {
    const name = normalise(player.name);
    const team = normalise(player.team);
    let score = 0;
    if (name === q) score = 100;
    else if (name.startsWith(q)) score = 80;
    else if (name.includes(q)) score = 60;
    else if (team.includes(q)) score = 20;
    if (score > 0) scored.push({ player, score: score + (player.qualified ? 5 : 0) });
  }
  scored.sort((a, b) => b.score - a.score || b.player.trials - a.player.trials || a.player.name.localeCompare(b.player.name, "zh-Hant"));
  return scored.slice(0, limit).map((s) => s.player);
}
