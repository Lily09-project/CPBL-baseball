import { useCallback, useEffect, useRef, useState } from "react";
import type { OrderSearchResult } from "../lib/sim";
import type { WorkerRequest, WorkerResponse } from "./protocol";

type Job = { kind: "simulate" | "optimise" } | null;

/**
 * Owns one dedicated worker. Cancelling terminates it outright (a busy
 * worker cannot be interrupted any other way) and a fresh one is created
 * for the next job.
 */
export function useSimWorker() {
  const worker = useRef<Worker | null>(null);
  const nextId = useRef(1);
  const [job, setJob] = useState<Job>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const ensure = () => {
    worker.current ??= new Worker(new URL("./lineup.worker.ts", import.meta.url), { type: "module" });
    return worker.current;
  };

  const cancel = useCallback(() => {
    worker.current?.terminate();
    worker.current = null;
    setJob(null);
    setProgress(0);
  }, []);

  useEffect(() => () => worker.current?.terminate(), []);

  const run = useCallback(<T extends WorkerRequest["kind"]>(request: Omit<Extract<WorkerRequest, { kind: T }>, "id">) => {
    const id = nextId.current++;
    const target = ensure();
    setJob({ kind: request.kind });
    setProgress(0);
    setError(null);
    return new Promise<T extends "simulate" ? number[] : OrderSearchResult>((resolve, reject) => {
      const onMessage = (event: MessageEvent<WorkerResponse>) => {
        const message = event.data;
        if (message.id !== id) return;
        if (message.type === "progress") {
          setProgress(message.fraction);
          return;
        }
        target.removeEventListener("message", onMessage);
        setJob(null);
        setProgress(1);
        if (message.type === "error") {
          setError(message.message);
          reject(new Error(message.message));
        } else if (message.type === "simulated") {
          resolve(message.runs as never);
        } else {
          resolve(message.search as never);
        }
      };
      target.addEventListener("message", onMessage);
      target.postMessage({ ...request, id } as WorkerRequest);
    });
  }, []);

  return { run, cancel, job, progress, error };
}
