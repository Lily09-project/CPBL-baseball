import type { OrderSearchResult } from "../lib/sim";

export type WorkerRequest =
  | { id: number; kind: "simulate"; cdfs: number[][]; games: number; seed: number }
  | { id: number; kind: "optimise"; cdfs: number[][]; games: number; seed: number; rounds: number };

export type WorkerResponse =
  | { id: number; type: "progress"; fraction: number }
  | { id: number; type: "simulated"; runs: number[] }
  | { id: number; type: "optimised"; search: OrderSearchResult }
  | { id: number; type: "error"; message: string };
