import { useState } from "react";
import { useDataset, useDocumentTitle, useRoute } from "../app/hooks";
import { ChartFrame, IntervalPlot } from "../components/charts";
import { ScrollRegion } from "../components/ScrollRegion";
import { Gate } from "../components/States";
import { formatMetric } from "../lib/format";
import { routeToHash } from "../lib/router";
import type { LeagueData, PlayerSummary, PlayerType } from "../lib/types";
import "./Talent.css";

export interface TalentMetric {
  key: string;
  label: string;
  higherIsBetter: boolean;
  fmt: "rate3" | "pct1";
}

export const TALENT_METRICS: Record<PlayerType, TalentMetric[]> = {
  batter: [
    { key: "obp", label: "上壘率", higherIsBetter: true, fmt: "rate3" },
    { key: "k_rate", label: "三振率", higherIsBetter: false, fmt: "pct1" },
    { key: "bb_rate", label: "保送率", higherIsBetter: true, fmt: "pct1" },
    { key: "hr_rate", label: "全壘打率", higherIsBetter: true, fmt: "pct1" },
  ],
  pitcher: [
    { key: "k_rate", label: "三振率", higherIsBetter: true, fmt: "pct1" },
    { key: "bb_rate", label: "保送率", higherIsBetter: false, fmt: "pct1" },
    { key: "hr_rate", label: "被全壘打率", higherIsBetter: false, fmt: "pct1" },
  ],
};

const PAGE = 20;

function TalentBoard({ players, league }: { players: PlayerSummary[]; league: LeagueData }) {
  const [route, navigate] = useRoute();
  const params = route.name === "talent" ? route : { name: "talent" as const, type: "batter" as const };
  const type = params.type;
  const metrics = TALENT_METRICS[type];
  const metric = metrics.find((m) => m.key === params.metric) ?? (metrics[0] as TalentMetric);
  const sort = params.sort ?? "posterior";
  const team = params.team ?? "";
  const query = params.q ?? "";
  const [shown, setShown] = useState(PAGE);
  const [onlyQualified, setOnlyQualified] = useState(true);
  const update = (patch: Partial<typeof params>) => {
    setShown(PAGE);
    navigate({ ...params, ...patch, name: "talent" }, { replace: true });
  };

  const teams = [...new Set(players.map((p) => p.team))].sort((a, b) => a.localeCompare(b, "zh-Hant"));
  const prior = league.priors[type][metric.key];
  const fmt = (v: number) => formatMetric(v, metric.fmt);

  // ~350 players: recomputing on every render is cheap and keeps the code simple.
  const pool = players.filter(
    (p) =>
      p.type === type &&
      p.talent[metric.key]?.mean !== null &&
      (!team || p.team === team) &&
      (!query || p.name.includes(query.trim())) &&
      (!onlyQualified || p.qualified),
  );
  const value = (p: PlayerSummary) => {
    const t = p.talent[metric.key];
    return (sort === "raw" ? t?.raw : t?.mean) ?? Number.NaN;
  };
  const ranked = pool
    .filter((p) => !Number.isNaN(value(p)))
    .sort((a, b) => (metric.higherIsBetter ? value(b) - value(a) : value(a) - value(b)) || b.trials - a.trials);
  const traps = players
    .filter((p) => p.type === type && p.trials >= 10 && p.talent[metric.key]?.raw !== null)
    .map((p) => ({ p, gap: (p.talent[metric.key]?.raw ?? 0) - (p.talent[metric.key]?.mean ?? 0) }))
    .sort((a, b) => Math.abs(b.gap) - Math.abs(a.gap))
    .slice(0, 5);

  const visible = ranked.slice(0, shown);
  const plotRows = visible.slice(0, 12).map((p) => {
    const t = p.talent[metric.key];
    return { key: p.player_id, label: p.name, raw: t?.raw ?? null, mean: t?.mean ?? 0, low: t?.low ?? 0, high: t?.high ?? 0 };
  });

  return (
    <div className="stack">
      <header>
        <span className="eyebrow">實驗 01・Empirical Bayes</span>
        <h1>真實實力估計</h1>
        <p className="lede">
          40 個打席打出 .450 的上壘率，是實力還是運氣？我們用全聯盟的分布估計先驗，把每位球員的原始數據收縮成更可信的「真實實力」，並附上 80% 可信區間。
        </p>
      </header>

      <section className="card controls" aria-label="篩選條件">
        <fieldset className="segmented">
          <legend className="label">球員類型</legend>
          {(["batter", "pitcher"] as const).map((t) => (
            <label key={t}>
              <input type="radio" name="ptype" value={t} checked={type === t} onChange={() => update({ type: t, metric: undefined })} />
              <span>{t === "batter" ? "打者" : "投手"}</span>
            </label>
          ))}
        </fieldset>
        <div className="field">
          <label htmlFor="metric">指標</label>
          <select id="metric" className="input" value={metric.key} onChange={(e) => update({ metric: e.target.value })}>
            {metrics.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}（{m.higherIsBetter ? "越高越好" : "越低越好"}）
              </option>
            ))}
          </select>
        </div>
        <fieldset className="segmented">
          <legend className="label">排序依據</legend>
          {(["posterior", "raw"] as const).map((s) => (
            <label key={s}>
              <input type="radio" name="sort" value={s} checked={sort === s} onChange={() => update({ sort: s })} />
              <span>{s === "posterior" ? "收縮後估計" : "原始數據"}</span>
            </label>
          ))}
        </fieldset>
        <div className="field">
          <label htmlFor="team">球隊</label>
          <select id="team" className="input" value={team} onChange={(e) => update({ team: e.target.value || undefined })}>
            <option value="">全部球隊</option>
            {teams.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="q">球員名稱</label>
          <input id="q" className="input" type="search" value={query} placeholder="輸入名字篩選" onChange={(e) => update({ q: e.target.value || undefined })} />
        </div>
        <label className="check">
          <input type="checkbox" checked={onlyQualified} onChange={(e) => { setOnlyQualified(e.target.checked); setShown(PAGE); }} />
          只看達比較門檻的球員（{type === "batter" ? "50 打席" : "15 局"}）
        </label>
      </section>

      <section className="grid grid-2">
        <div className="card">
          <ChartFrame
            title={`前 ${plotRows.length} 名的${metric.label}（◆ 原始值 ● 收縮後）`}
            summary={plotRows.map((r) => `${r.label} 原始 ${r.raw === null ? "無" : fmt(r.raw)}、收縮後 ${fmt(r.mean)}`).join("；")}
            table={<TalentTable rows={visible.slice(0, 12)} metric={metric} />}
          >
            {plotRows.length > 0 ? <IntervalPlot data={plotRows} reference={prior?.mean ?? 0} format={fmt} /> : <p className="muted">沒有符合條件的球員。</p>}
          </ChartFrame>
          <p className="muted small">
            先驗：Beta(α={prior?.alpha.toFixed(1)}, β={prior?.beta.toFixed(1)})，相當於先看過約 {prior ? Math.round(prior.alpha + prior.beta) : "—"} 次聯盟平均的{type === "batter" ? "打席" : "對戰打者"}。
          </p>
        </div>
        <div className="card" data-testid="traps">
          <h2>小樣本陷阱</h2>
          <p className="muted">原始數據與收縮後估計差距最大的球員：他們的數字最容易誤導人。</p>
          <ol className="traps">
            {traps.map(({ p, gap }) => (
              <li key={p.player_id}>
                <a href={routeToHash({ name: "player", type, id: p.player_id })}>{p.name}</a>
                <span className="muted">
                  {p.team}・{p.trials} {type === "batter" ? "打席" : "對戰打者"}
                </span>
                <span className={gap > 0 ? "trap-up" : "trap-down"}>
                  原始 {formatMetric(p.talent[metric.key]?.raw, metric.fmt)} → 估計 {formatMetric(p.talent[metric.key]?.mean, metric.fmt)}
                  <span className="visually-hidden">{gap > 0 ? "（原始值偏高）" : "（原始值偏低）"}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="card">
        <div className="row spread">
          <h2>完整排行（{ranked.length} 人）</h2>
          <a className="btn" href={routeToHash({ name: "compare", type, ids: visible.slice(0, 3).map((p) => p.player_id) })}>
            比較前 3 名
          </a>
        </div>
        <ScrollRegion label="完整排行">
          <TalentTable rows={visible} metric={metric} withRank />
        </ScrollRegion>
        {shown < ranked.length && (
          <button type="button" className="btn show-more" onClick={() => setShown((s) => s + PAGE)}>
            顯示更多（剩 {ranked.length - shown} 人）
          </button>
        )}
      </section>
    </div>
  );
}

function TalentTable({ rows, metric, withRank = false }: { rows: PlayerSummary[]; metric: TalentMetric; withRank?: boolean }) {
  return (
    <table data-testid={withRank ? "talent-table" : undefined}>
      <thead>
        <tr>
          {withRank && <th scope="col" className="num">#</th>}
          <th scope="col">球員</th>
          <th scope="col">球隊</th>
          <th scope="col" className="num">樣本</th>
          <th scope="col" className="num">原始</th>
          <th scope="col" className="num">收縮後</th>
          <th scope="col" className="num">80% 區間</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p, i) => {
          const t = p.talent[metric.key];
          return (
            <tr key={p.player_id}>
              {withRank && <td className="num">{i + 1}</td>}
              <th scope="row">
                <a href={routeToHash({ name: "player", type: p.type, id: p.player_id })}>{p.name}</a>
                {!p.qualified && <span className="badge">小樣本</span>}
              </th>
              <td>{p.team}</td>
              <td className="num">{p.trials}</td>
              <td className="num">{formatMetric(t?.raw, metric.fmt)}</td>
              <td className="num strong">{formatMetric(t?.mean, metric.fmt)}</td>
              <td className="num muted">
                {formatMetric(t?.low, metric.fmt)}–{formatMetric(t?.high, metric.fmt)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function Talent() {
  useDocumentTitle("真實實力估計");
  const players = useDataset("players.json");
  const league = useDataset("league.json");
  return (
    <div className="page">
      <Gate<[PlayerSummary[], LeagueData]> states={[players, league]}>{(p, l) => <TalentBoard players={p} league={l} />}</Gate>
    </div>
  );
}
