import { useCallback, useEffect, useRef, useState } from "react";
import type { OrderSearchResult } from "../lib/sim";
import type { WorkerRequest, WorkerResponse } from "./protocol";

type Job = { kind: "simulate" | "optimise" } | null;

/** Every run owns its worker, listeners and one settled promise. */
export function useSimWorker() {
  const pending = useRef<(() => void) | null>(null);
  const nextId = useRef(1);
  const [job, setJob] = useState<Job>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const cancel = useCallback(() => {
    pending.current?.();
    setJob(null);
    setProgress(0);
  }, []);
  useEffect(() => () => pending.current?.(), []);

  const run = useCallback(<T extends WorkerRequest["kind"]>(request: Omit<Extract<WorkerRequest, { kind: T }>, "id">) => {
    pending.current?.();
    const id = nextId.current++;
    setJob({ kind: request.kind });
    setProgress(0);
    setError(null);
    return new Promise<T extends "simulate" ? number[] : OrderSearchResult>((resolve, reject) => {
      let target: Worker | null = null;
      const owns = () => pending.current === abort;
      const dispose = () => {
        target?.removeEventListener("message", onMessage);
        target?.removeEventListener("error", onFailure);
        target?.removeEventListener("messageerror", onFailure);
        target?.terminate();
        if (owns()) pending.current = null;
      };
      const abort = () => {
        if (!owns()) return;
        dispose();
        reject(new DOMException("Cancelled", "AbortError"));
      };
      const fail = (cause: unknown) => {
        if (!owns()) return;
        const failure = cause instanceof Error ? cause : new Error("計算工作無法執行，請重新開始。");
        dispose();
        setJob(null);
        setProgress(0);
        setError(failure.message);
        reject(failure);
      };
      const onFailure = (event: Event) => {
        event.preventDefault();
        fail(new Error("計算工作無法執行，請重新開始。"));
      };
      const onMessage = (event: MessageEvent<WorkerResponse>) => {
        if (!owns()) return;
        const message = event.data;
        if (message.id !== id) return;
        if (message.type === "progress") {
          setProgress(message.fraction);
          return;
        }
        if (message.type === "error") {
          fail(new Error(message.message));
          return;
        }
        dispose();
        setJob(null);
        setProgress(1);
        if (message.type === "simulated") resolve(message.runs as never);
        else resolve(message.search as never);
      };
      pending.current = abort;
      try {
        target = new Worker(new URL("./lineup.worker.ts", import.meta.url), { type: "module" });
        target.addEventListener("message", onMessage);
        target.addEventListener("error", onFailure);
        target.addEventListener("messageerror", onFailure);
        target.postMessage({ ...request, id } as WorkerRequest);
      } catch (cause) {
        fail(cause);
      }
    });
  }, []);

  return { run, cancel, job, progress, error };
}
