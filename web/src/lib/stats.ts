export function mean(values: readonly number[]): number {
  if (values.length === 0) return Number.NaN;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function standardDeviation(values: readonly number[]): number {
  if (values.length < 2) return 0;
  const m = mean(values);
  return Math.sqrt(values.reduce((acc, v) => acc + (v - m) ** 2, 0) / (values.length - 1));
}

/** Linear-interpolated quantile, q in [0, 1]. */
export function quantile(values: readonly number[], q: number): number {
  if (values.length === 0) return Number.NaN;
  const sorted = [...values].sort((a, b) => a - b);
  const position = (sorted.length - 1) * Math.min(Math.max(q, 0), 1);
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  const lo = sorted[lower] as number;
  const hi = sorted[upper] as number;
  return lo + (hi - lo) * (position - lower);
}

/** Integer histogram with a final "cap or more" bucket. */
export function integerHistogram(values: readonly number[], cap: number): number[] {
  const counts = new Array<number>(cap + 1).fill(0);
  for (const value of values) {
    const bucket = Math.min(Math.max(Math.round(value), 0), cap);
    counts[bucket] = (counts[bucket] ?? 0) + 1;
  }
  return counts;
}

export function shareAtLeast(values: readonly number[], threshold: number): number {
  if (values.length === 0) return Number.NaN;
  return values.filter((v) => v >= threshold).length / values.length;
}
