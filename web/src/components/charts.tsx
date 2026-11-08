import { scaleBand, scaleLinear } from "d3-scale";
import { line } from "d3-shape";
import { W } from "./chartFrame";

export { ChartFrame, DivergingBars } from "./chartFrame";

export function PercentileBar({ value, label }: { value: number | null; label: string }) {
  const v = value ?? 0;
  const tone = value === null ? "none" : v >= 80 ? "high" : v <= 20 ? "low" : "mid";
  return (
    <div className="pbar" data-tone={tone}>
      <div className="pbar-head">
        <span>{label}</span>
        <strong>{value === null ? "—" : Math.round(v)}</strong>
      </div>
      <div className="pbar-track" aria-hidden="true">
        <span className="pbar-fill" style={{ width: `${v}%` }} />
        <span className="pbar-mid" />
      </div>
    </div>
  );
}

export interface IntervalDatum {
  key: string;
  label: string;
  raw: number | null;
  mean: number;
  low: number;
  high: number;
  emphasis?: boolean;
}

/** Forest plot: posterior interval (bar), posterior mean (dot), raw value (diamond). */
export function IntervalPlot({
  data,
  reference,
  format,
  height = 30,
}: {
  data: IntervalDatum[];
  reference: number;
  format: (v: number) => string;
  height?: number;
}) {
  const width = W;
  const labelWidth = 104;
  const values = data.flatMap((d) => [d.low, d.high, d.raw ?? d.mean, reference]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.08 || 0.01;
  const x = scaleLinear().domain([min - pad, max + pad]).range([labelWidth, width - 16]);
  const total = data.length * height + 28;
  return (
    <svg className="chart interval-plot" viewBox={`0 0 ${width} ${total}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <line className="ref-line" x1={x(reference)} x2={x(reference)} y1={0} y2={total - 20} />
      <text x={x(reference)} y={total - 6} textAnchor="middle">
        聯盟 {format(reference)}
      </text>
      {data.map((d, i) => {
        const y = i * height + height / 2;
        return (
          <g key={d.key} className={d.emphasis ? "row-emphasis" : undefined}>
            <text x={0} y={y + 4} className="row-label">
              {d.label}
            </text>
            <line className="ci" x1={x(d.low)} x2={x(d.high)} y1={y} y2={y} />
            {d.raw !== null && (
              <path className="raw" d={`M${x(d.raw)},${y - 6} l6,6 l-6,6 l-6,-6 z`}>
                <title>原始值 {format(d.raw)}</title>
              </path>
            )}
            <circle className="post" cx={x(d.mean)} cy={y} r={5}>
              <title>收縮後 {format(d.mean)}（80% 區間 {format(d.low)}–{format(d.high)}）</title>
            </circle>
          </g>
        );
      })}
    </svg>
  );
}

export function Histogram({
  counts,
  labels,
  highlightFrom,
  height = 180,
  labelEvery = 1,
}: {
  counts: number[];
  labels: string[];
  highlightFrom?: number;
  height?: number;
  labelEvery?: number;
}) {
  const width = W;
  const x = scaleBand<number>().domain(counts.map((_, i) => i)).range([32, width - 8]).padding(0.15);
  const y = scaleLinear().domain([0, Math.max(...counts, 1)]).range([height - 24, 8]);
  return (
    <svg className="chart histogram" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      {y.ticks(4).map((t) => (
        <g key={t}>
          <line className="grid-line" x1={32} x2={width - 8} y1={y(t)} y2={y(t)} />
        </g>
      ))}
      {counts.map((c, i) => (
        <rect
          key={i}
          x={x(i)}
          y={y(c)}
          width={x.bandwidth()}
          height={Math.max(height - 24 - y(c), 0)}
          rx={3}
          className={highlightFrom !== undefined && i >= highlightFrom ? "bar bar-hi" : "bar"}
        >
          <title>
            {labels[i]}：{c}
          </title>
        </rect>
      ))}
      {counts.map((_, i) =>
        i % labelEvery === 0 || i === counts.length - 1 ? (
          <text key={i} x={(x(i) ?? 0) + x.bandwidth() / 2} y={height - 6} textAnchor="middle">
            {labels[i]}
          </text>
        ) : null,
      )}
    </svg>
  );
}

export function TrendLine({
  points,
  format,
  invert = false,
  height = 200,
}: {
  points: { t: string; v: number }[];
  format: (v: number) => string;
  invert?: boolean;
  height?: number;
}) {
  const width = W;
  if (points.length === 0) return null;
  const values = points.map((p) => p.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.15 || 0.05;
  const x = scaleLinear().domain([0, Math.max(points.length - 1, 1)]).range([48, width - 16]);
  const y = scaleLinear()
    .domain(invert ? [max + pad, min - pad] : [min - pad, max + pad])
    .range([height - 28, 12]);
  const path = line<{ v: number }>()
    .x((_, i) => x(i))
    .y((p) => y(p.v))(points);
  return (
    <svg className="chart trend" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      {y.ticks(4).map((t) => (
        <g key={t}>
          <line className="grid-line" x1={48} x2={width - 16} y1={y(t)} y2={y(t)} />
          <text x={42} y={y(t) + 4} textAnchor="end">
            {format(t)}
          </text>
        </g>
      ))}
      <path className="trend-line" d={path ?? ""} />
      {points.map((p, i) => (
        <circle key={`${p.t}-${i}`} cx={x(i)} cy={y(p.v)} r={3.5} className="trend-dot">
          <title>
            {p.t}：{format(p.v)}
          </title>
        </circle>
      ))}
      <text x={48} y={height - 8}>
        {points[0]?.t}
      </text>
      <text x={width - 16} y={height - 8} textAnchor="end">
        {points.at(-1)?.t}
      </text>
    </svg>
  );
}

export function RangeBars({
  rows,
  domain,
  height = 34,
}: {
  rows: { key: string; label: string; low: number; high: number; mid: number; current: number }[];
  domain: [number, number];
  height?: number;
}) {
  const width = W;
  const labelWidth = 130;
  const x = scaleLinear().domain(domain).range([labelWidth, width - 16]);
  const total = rows.length * height + 24;
  return (
    <svg className="chart range-bars" viewBox={`0 0 ${width} ${total}`} aria-hidden="true">
      {x.ticks(6).map((t) => (
        <g key={t}>
          <line className="grid-line" x1={x(t)} x2={x(t)} y1={0} y2={total - 20} />
          <text x={x(t)} y={total - 6} textAnchor="middle">
            {t}
          </text>
        </g>
      ))}
      {rows.map((r, i) => {
        const y = i * height + height / 2;
        return (
          <g key={r.key}>
            <text x={0} y={y + 4} className="row-label">
              {r.label}
            </text>
            <rect className="range" x={x(r.low)} y={y - 7} width={Math.max(x(r.high) - x(r.low), 2)} height={14} rx={7} />
            <line className="current" x1={x(r.current)} x2={x(r.current)} y1={y - 11} y2={y + 11} />
            <circle className="mid" cx={x(r.mid)} cy={y} r={5}>
              <title>
                {r.label}：預估 {r.mid} 勝（80% 區間 {r.low}–{r.high}）
              </title>
            </circle>
          </g>
        );
      })}
    </svg>
  );
}

export function ContributionBars({ items, labels }: { items: Record<string, number>; labels: Record<string, string> }) {
  const entries = Object.entries(items).sort((a, b) => b[1] - a[1]);
  const extent = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.01);
  return (
    <ul className="contrib">
      {entries.map(([key, value]) => (
        <li key={key}>
          <span className="contrib-label">{labels[key] ?? key}</span>
          <span className="contrib-track" aria-hidden="true">
            <span className={value >= 0 ? "contrib-pos" : "contrib-neg"} style={{ width: `${(Math.abs(value) / extent) * 50}%`, [value >= 0 ? "left" : "right"]: "50%" }} />
          </span>
          <span className="contrib-value">{value >= 0 ? "+" : ""}{value.toFixed(2)}</span>
        </li>
      ))}
    </ul>
  );
}
