import type { MetricDefinition } from "./types";

export function formatMetric(value: number | null | undefined, fmt: MetricDefinition["fmt"]): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  switch (fmt) {
    case "rate3":
      return value.toFixed(3).replace(/^0(?=\.)/, "");
    case "pct1":
      return `${(value * 100).toFixed(1)}%`;
    case "num2":
      return value.toFixed(2);
  }
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSigned(value: number, digits = 1): string {
  const fixed = value.toFixed(digits);
  // A value that rounds to zero carries no sign: neither "+0.00" nor "-0.00".
  if (Number(fixed) === 0) return (0).toFixed(digits);
  return value > 0 ? `+${fixed}` : fixed;
}

export function ordinalPercentile(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `PR ${Math.round(value)}`;
}

export type FreshnessLevel = "current" | "recent" | "stale";

/** Data age relative to "now"; the export never pretends to be live. */
export function freshness(capturedAt: string, now: Date): { level: FreshnessLevel; days: number } {
  const days = Math.max(0, (now.getTime() - new Date(capturedAt).getTime()) / 86_400_000);
  const level: FreshnessLevel = days <= 2 ? "current" : days <= 7 ? "recent" : "stale";
  return { level, days: Math.floor(days) };
}

// CPBL plays in Taiwan, so dates are shown in Taipei time. Taiwan has used a
// fixed UTC+8 offset without daylight saving since 1979, so a constant offset
// keeps the output identical in every browser and test runner.
const TAIPEI_OFFSET_MS = 8 * 3_600_000;
const pad = (n: number) => String(n).padStart(2, "0");

/** Calendar date in Taipei time, e.g. 2026-09-30. */
export function formatDate(iso: string): string {
  const date = new Date(new Date(iso).getTime() + TAIPEI_OFFSET_MS);
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
}

/** Date and minute in Taipei time, e.g. 2026-09-30 04:48. */
export function formatDateTime(iso: string): string {
  const date = new Date(new Date(iso).getTime() + TAIPEI_OFFSET_MS);
  return `${formatDate(iso)} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
}

/** Innings in baseball notation: 49.333 → "49.1" (49⅓), 51.667 → "51.2". */
export function formatInnings(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const outs = Math.round(value * 3);
  return `${Math.floor(outs / 3)}.${outs % 3}`;
}
