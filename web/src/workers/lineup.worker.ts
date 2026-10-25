/// <reference lib="webworker" />
import { optimiseOrder, simulateMany } from "../lib/sim";
import type { WorkerRequest, WorkerResponse } from "./protocol";

const post = (message: WorkerResponse) => (self as DedicatedWorkerGlobalScope).postMessage(message);

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const request = event.data;
  try {
    if (request.kind === "simulate") {
      const runs = simulateMany(request.cdfs, request.games, request.seed, (done) =>
        post({ id: request.id, type: "progress", fraction: done / request.games }),
      );
      post({ id: request.id, type: "simulated", runs });
    } else {
      const search = optimiseOrder(request.cdfs, request.games, request.seed, request.rounds, (round) =>
        post({ id: request.id, type: "progress", fraction: round / request.rounds }),
      );
      post({ id: request.id, type: "optimised", search });
    }
  } catch (error) {
    post({ id: request.id, type: "error", message: error instanceof Error ? error.message : String(error) });
  }
};
