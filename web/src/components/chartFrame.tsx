/**
 * Chart pieces the home page needs. They stay free of d3 so the first screen
 * does not download the scale library; the other charts live in charts.tsx.
 */
import { useId, type ReactNode } from "react";
import "./charts.css";
import { ScrollRegion } from "./ScrollRegion";

/** Narrower viewBox keeps chart text legible when cards are ~400–560px wide. */
export const W = 520;

/** Same mapping as d3 scaleLinear (normalise, then interpolate) without the dependency. */
function linear([d0, d1]: [number, number], [r0, r1]: [number, number]) {
  return (value: number) => {
    const t = d1 - d0 === 0 ? 0.5 : (value - d0) / (d1 - d0);
    return r0 * (1 - t) + r1 * t;
  };
}

/** Every chart pairs its SVG with an equivalent table for screen readers. */
export function ChartFrame({ title, summary, table, children }: { title: string; summary: string; table: ReactNode; children: ReactNode }) {
  const id = useId();
  return (
    <figure className="chart-frame" aria-labelledby={`${id}-title`}>
      <figcaption id={`${id}-title`} className="chart-title">
        {title}
      </figcaption>
      <div role="img" aria-label={`${title}：${summary}`}>
        {children}
      </div>
      <details className="data-table">
        <summary>以表格檢視資料</summary>
        <ScrollRegion label={`${title}（資料表）`}>{table}</ScrollRegion>
      </details>
    </figure>
  );
}

export function DivergingBars({
  rows,
  format,
  height = 30,
}: {
  rows: { key: string; label: string; value: number }[];
  format: (v: number) => string;
  height?: number;
}) {
  const width = W;
  const labelWidth = 140;
  const extent = Math.max(...rows.map((r) => Math.abs(r.value)), 1);
  const x = linear([-extent, extent], [labelWidth + 44, width - 48]);
  const total = rows.length * height + 8;
  return (
    <svg className="chart diverging" viewBox={`0 0 ${width} ${total}`} aria-hidden="true">
      <line className="zero" x1={x(0)} x2={x(0)} y1={0} y2={total} />
      {rows.map((r, i) => {
        const y = i * height + 4;
        const start = Math.min(x(0), x(r.value));
        return (
          <g key={r.key}>
            <text x={0} y={y + height / 2} className="row-label">
              {r.label}
            </text>
            <rect className={r.value >= 0 ? "pos" : "neg"} x={start} y={y + 4} width={Math.abs(x(r.value) - x(0))} height={height - 12} rx={3} />
            <text x={r.value >= 0 ? x(r.value) + 6 : x(r.value) - 6} y={y + height / 2} textAnchor={r.value >= 0 ? "start" : "end"} className="value-label">
              {format(r.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
