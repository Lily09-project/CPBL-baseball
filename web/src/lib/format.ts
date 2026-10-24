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
  return value > 0 ? `+${fixed}` : fixed === `-${(0).toFixed(digits)}` ? (0).toFixed(digits) : fixed;
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

export function formatDate(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
}
