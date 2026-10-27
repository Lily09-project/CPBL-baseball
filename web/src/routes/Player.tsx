import { useState } from "react";
import { useDataset, useDocumentTitle } from "../app/hooks";
import { ChartFrame, ContributionBars, IntervalPlot, PercentileBar, TrendLine } from "../components/charts";
import { ScrollRegion } from "../components/ScrollRegion";
import { EmptyState, Gate } from "../components/States";
import { formatMetric, formatSigned } from "../lib/format";
import { routeToHash } from "../lib/router";
import type { LeagueData, PlayerDetail, PlayerType } from "../lib/types";
import { TALENT_METRICS } from "./Talent";
import "./Player.css";

const TREND_LABEL = { improving: "上升", declining: "下滑", steady: "持平", insufficient: "資料不足" } as const;

const BATTER_STATS: [string, string, "int" | "rate3"][] = [
  ["pa", "打席", "int"],
  ["hits", "安打", "int"],
  ["doubles", "二安", "int"],
  ["triples", "三安", "int"],
  ["home_runs", "全壘打", "int"],
  ["walks", "保送", "int"],
  ["strikeouts", "三振", "int"],
  ["stolen_bases", "盜壘", "int"],
  ["batting_average", "打擊率", "rate3"],
  ["obp", "上壘率", "rate3"],
  ["slg", "長打率", "rate3"],
  ["ops", "OPS", "rate3"],
];

const PITCHER_STATS: [string, string, "int" | "num2"][] = [
  ["innings_pitched", "局數", "num2"],
  ["batters_faced", "面對打者（估計）", "int"],
  ["strikeouts", "三振", "int"],
  ["walks", "保送", "int"],
  ["home_runs_allowed", "被全壘打", "int"],
  ["era", "ERA", "num2"],
  ["fip", "FIP", "num2"],
  ["whip", "WHIP", "num2"],
];

function formatStat(value: number | null | undefined, kind: "int" | "rate3" | "num2") {
  if (value === null || value === undefined) return "—";
  if (kind === "int") return String(Math.round(value));
  return kind === "rate3" ? formatMetric(value, "rate3") : value.toFixed(2);
}

function Profile({ player, league, details }: { player: PlayerDetail; league: LeagueData; details: Record<string, PlayerDetail> }) {
  const [focused, setFocused] = useState<string | null>(null);
  const definitions = league.metric_definitions[player.type];
  const labels = Object.fromEntries(definitions.map((d) => [d.key, d.label]));
  const unit = player.type === "batter" ? "打席" : "對戰打者";
  const stats = player.type === "batter" ? BATTER_STATS : PITCHER_STATS;
  const trajectory = player.trajectory;
  const trajectoryFmt = (v: number) => (trajectory.metric === "ops" ? formatMetric(v, "rate3") : v.toFixed(2));

  return (
    <div className="stack">
      <nav aria-label="麵包屑" className="crumbs">
        <a href={routeToHash({ name: "talent", type: player.type })}>真實實力</a> / <span aria-current="page">{player.name}</span>
      </nav>
      <header className="profile-head">
        <div>
          <span className="eyebrow">
            {player.team}・{player.position}・{player.type === "batter" ? "打者" : "投手"}
          </span>
          <h1>{player.name}</h1>
          <div className="row">
            <span className={player.qualified ? "badge badge-teal" : "badge"}>{player.qualified ? "達比較門檻" : "小樣本"}</span>
            <span className="badge">
              {player.trials} {unit}
            </span>
            <span className="badge">軌跡：{TREND_LABEL[trajectory.trend]}</span>
          </div>
        </div>
        <div className="row">
          <a className="btn" href={routeToHash({ name: "compare", type: player.type, ids: [player.player_id, ...player.similar.slice(0, 2).map((s) => s.player_id)] })}>
            與相似球員比較
          </a>
          {player.type === "batter" && (
            <a className="btn btn-primary" href={routeToHash({ name: "lineup", team: player.team })}>
              在打線實驗室模擬
            </a>
          )}
        </div>
      </header>

      <section className="grid grid-2">
        <div className="card notes" data-testid="scouting-notes">
          <h2>球探摘要</h2>
          <p className="muted small">由規則自動產生，每一句都標示它依據的數據；沒有使用任何外部語言模型。</p>
          <ul>
            {player.notes.map((note, i) => (
              <li key={i}>
                <span>{note.text}</span>
                <span className="evidence">
                  {note.evidence.map((key) => (
                    <button
                      key={key}
                      type="button"
                      className="chip"
                      aria-pressed={focused === key}
                      onMouseEnter={() => setFocused(key)}
                      onMouseLeave={() => setFocused(null)}
                      onFocus={() => setFocused(key)}
                      onBlur={() => setFocused(null)}
                    >
                      依據：{labels[key] ?? (key === "similar" ? "相似球員" : key === "trials" ? "樣本數" : key.toUpperCase())}
                    </button>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2>聯盟百分位</h2>
          <p className="muted small">與達比較門檻的同類型球員相比（PR 50 = 聯盟中位數）。</p>
          <div className="pbars">
            {definitions.map((d) => (
              <div key={d.key} className={focused === d.key ? "pbar-focus" : undefined} data-metric={d.key}>
                <PercentileBar label={`${d.label}：${formatMetric(player.metrics[d.key], d.fmt)}`} value={player.percentiles[d.key] ?? null} />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-2">
        <div className="card">
          <h2>真實實力區間</h2>
          <p className="muted small">◆ 原始值・● 收縮後估計・▬ 80% 可信區間・虛線為聯盟平均</p>
          <div className="talent-list">
            {TALENT_METRICS[player.type].map((m) => {
              const t = player.talent[m.key];
              if (!t || t.mean === null || t.low === null || t.high === null) return null;
              const fmt = (v: number) => formatMetric(v, m.fmt);
              return (
                <ChartFrame
                  key={m.key}
                  title={m.label}
                  summary={`原始 ${t.raw === null ? "無" : fmt(t.raw)}，收縮後 ${fmt(t.mean)}，區間 ${fmt(t.low)} 到 ${fmt(t.high)}`}
                  table={
                    <table>
                      <tbody>
                        <tr>
                          <th scope="row">原始</th>
                          <td className="num">{t.raw === null ? "—" : fmt(t.raw)}</td>
                        </tr>
                        <tr>
                          <th scope="row">收縮後</th>
                          <td className="num">{fmt(t.mean)}</td>
                        </tr>
                        <tr>
                          <th scope="row">80% 區間</th>
                          <td className="num">
                            {fmt(t.low)}–{fmt(t.high)}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  }
                >
                  <IntervalPlot data={[{ key: m.key, label: fmt(t.mean), raw: t.raw, mean: t.mean, low: t.low, high: t.high }]} reference={league.priors[player.type][m.key]?.mean ?? t.mean} format={fmt} height={34} />
                </ChartFrame>
              );
            })}
          </div>
        </div>
        <div className="card">
          <h2>{trajectory.metric === "ops" ? "OPS" : "ERA"} 快照軌跡</h2>
          {trajectory.series.length >= 2 ? (
            <ChartFrame
              title={`跨 ${trajectory.series.length} 份官方快照的${trajectory.metric === "ops" ? "OPS" : "ERA"}`}
              summary={`從 ${trajectoryFmt(trajectory.series[0]?.v ?? 0)} 到 ${trajectoryFmt(trajectory.series.at(-1)?.v ?? 0)}，判讀為${TREND_LABEL[trajectory.trend]}`}
              table={
                <table>
                  <thead>
                    <tr>
                      <th scope="col">日期</th>
                      <th scope="col" className="num">{trajectory.metric.toUpperCase()}</th>
                      <th scope="col" className="num">{player.type === "batter" ? "打席" : "局數"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trajectory.series.map((p, i) => (
                      <tr key={`${p.t}-${i}`}>
                        <th scope="row">{p.t}</th>
                        <td className="num">{trajectoryFmt(p.v)}</td>
                        <td className="num">{p.w ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <TrendLine points={trajectory.series} format={trajectoryFmt} invert={trajectory.metric === "era"} />
            </ChartFrame>
          ) : (
            <EmptyState title="快照不足">這位球員出現在少於兩份快照中，無法判讀趨勢。</EmptyState>
          )}
          {trajectory.change !== null && (
            <p className="muted small">
              期間變化 {formatSigned(trajectory.change, trajectory.metric === "ops" ? 3 : 2)}；變化需超過 {trajectory.metric === "ops" ? "0.030" : "0.50"} 才判讀為上升或下滑。
            </p>
          )}
        </div>
      </section>

      <section className="card" data-testid="similar-players">
        <h2>數據輪廓最接近的球員</h2>
        {player.similar.length === 0 ? (
          <EmptyState title="尚無相似球員">只有達比較門檻的球員會計算相似度。</EmptyState>
        ) : (
          <>
            <p className="muted small">以標準化指標的餘弦相似度計算；長條顯示每項指標對相似度的貢獻（加總即相似度）。</p>
            <ol className="similar">
              {player.similar.map((s) => {
                const other = details[`${s.player_id}:${player.type}`];
                return (
                  <li key={s.player_id}>
                    <div className="similar-head">
                      <a href={routeToHash({ name: "player", type: player.type, id: s.player_id })}>{other?.name ?? s.player_id}</a>
                      <span className="muted">{other?.team}</span>
                      <strong>相似度 {s.similarity.toFixed(2)}</strong>
                    </div>
                    <ContributionBars items={s.contributions} labels={labels} />
                  </li>
                );
              })}
            </ol>
          </>
        )}
      </section>

      <section className="card">
        <h2>成績與衍生指標</h2>
        <ScrollRegion label="成績與衍生指標">
          <table data-testid="raw-stats">
            <thead>
              <tr>
                {stats.map(([key, label]) => (
                  <th key={key} scope="col" className="num">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                {stats.map(([key, , kind]) => (
                  <td key={key} className="num">
                    {formatStat(player.stats[key], kind)}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </ScrollRegion>
      </section>
    </div>
  );
}

export default function Player({ type, id }: { type: PlayerType; id: string }) {
  const details = useDataset("player-details.json");
  const league = useDataset("league.json");
  const player = details.status === "ready" ? details.data[`${id}:${type}`] : undefined;
  useDocumentTitle(player ? player.name : "球員檔案");
  return (
    <div className="page">
      <Gate<[Record<string, PlayerDetail>, LeagueData]> states={[details, league]}>
        {(d, l) =>
          player ? (
            <Profile player={player} league={l} details={d} />
          ) : (
            <EmptyState title="找不到這位球員">
              <p>
                網址中的球員編號不存在於目前的資料快照。<a href={routeToHash({ name: "talent", type })}>回到排行</a>
              </p>
            </EmptyState>
          )
        }
      </Gate>
    </div>
  );
}
