import { mean, standardDeviation } from "./stats";

export function summarizePairedRuns(a: readonly number[], b: readonly number[]) {
  if (!a.length || a.length !== b.length) throw new Error("兩組方案的模擬場數不一致");
  const differences = b.map((runs, i) => runs - a[i]!);
  const delta = mean(differences);
  const margin = 1.96 * standardDeviation(differences) / Math.sqrt(differences.length);
  return { a: mean(a), b: mean(b), delta, low: delta - margin, high: delta + margin };
}
