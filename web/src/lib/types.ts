import type { EventProbabilities } from "./sim";

export type PlayerType = "batter" | "pitcher";
export type Trend = "improving" | "declining" | "steady" | "insufficient";

export interface Interval {
  raw: number | null;
  mean: number | null;
  low: number | null;
  high: number | null;
}

export interface MetricDefinition {
  key: string;
  label: string;
  higher_is_better: boolean;
  fmt: "rate3" | "pct1" | "num2";
  short: string;
}

export interface PlayerSummary {
  player_id: string;
  name: string;
  team: string;
  type: PlayerType;
  position: string;
  trials: number;
  qualified: boolean;
  metrics: Record<string, number | null>;
  percentiles: Record<string, number | null>;
  talent: Record<string, Interval>;
  trend: Trend;
}

export interface Note {
  text: string;
  evidence: string[];
}

export interface SimilarPlayer {
  player_id: string;
  similarity: number;
  contributions: Record<string, number>;
}

export interface PlayerDetail extends Omit<PlayerSummary, "trend"> {
  stats: Record<string, number | null>;
  similar: SimilarPlayer[];
  notes: Note[];
  trajectory: {
    metric: "ops" | "era";
    series: { t: string; v: number; w: number | null }[];
    trend: Trend;
    change: number | null;
  };
}

export interface TeamSimulation {
  games_played: number;
  games_remaining: number;
  current_wins: number;
  strength: number;
  projected_wins_mean: number;
  projected_wins_p10: number;
  projected_wins_p50: number;
  projected_wins_p90: number;
  first_place_probability: number;
  additional_wins_histogram: number[];
}

export interface TeamRow {
  team: string;
  games: number;
  wins: number;
  losses: number;
  ties: number;
  win_pct: number;
  runs_scored: number;
  runs_allowed: number;
  run_diff: number;
  games_behind: number | null;
  streak: string;
  recent: string;
  pythag_win_pct: number;
  luck_wins: number;
  simulation: TeamSimulation;
}

export interface LeagueData {
  teams: TeamRow[];
  runs_per_game: number;
  segment_games: number;
  simulations: number;
  seed: number;
  pythagorean_exponent: number;
  pitching: { era: number; fip_constant: number; bf_per_ip: number };
  priors: Record<PlayerType, Record<string, { alpha: number; beta: number; mean: number }>>;
  metric_definitions: Record<PlayerType, MetricDefinition[]>;
}

export interface SimInputs {
  events: string[];
  league: EventProbabilities;
  batters: Record<string, EventProbabilities>;
  pitchers: Record<string, EventProbabilities>;
  stabilizers: { batter_pa: number; pitcher_bf: number };
}

export interface Provenance {
  release_id: string;
  snapshot_id: string;
  generated_at: string;
  quality_status: string;
  warnings: string[];
  artifacts: { path: string; rows: number | null; sha256: string }[];
  snapshots: {
    snapshot_id: string;
    captured_at: string;
    quality_status: string;
    total_rows: number;
    added_rows: number;
    removed_rows: number;
    changed_rows: number;
  }[];
  sources: { label: string; url: string }[];
}

export interface Manifest {
  schema_version: string;
  files: Record<string, string>;
}

export interface DataFiles {
  "league.json": LeagueData;
  "players.json": PlayerSummary[];
  "player-details.json": Record<string, PlayerDetail>;
  "sim.json": SimInputs;
  "provenance.json": Provenance;
}
