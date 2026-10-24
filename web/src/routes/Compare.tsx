import { useDataset, useDocumentTitle, useRoute } from "../app/hooks";
import { PercentileBar } from "../components/charts";
import { EmptyState, Gate } from "../components/States";
import { addToComparison, comparisonCsv, comparisonJson, MAX_COMPARE, removeFromComparison } from "../lib/compare";
import { downloadText } from "../lib/csv";
import { formatMetric } from "../lib/format";
import { routeToHash } from "../lib/router";
import type { LeagueData, PlayerDetail, PlayerType, Provenance } from "../lib/types";
import "./Compare.css";

function CompareView({ details, league, provenance, type, ids }: { details: Record<string, PlayerDetail>; league: LeagueData; provenance: Provenance; type: PlayerType; ids: string[] }) {
  const [, navigate] = useRoute();
  const players = ids.map((id) => details[`${id}:${type}`]).filter((p): p is PlayerDetail => Boolean(p));
  const definitions = league.metric_definitions[type];
  const candidates = Object.values(details)
    .filter((p) => p.type === type && p.qualified && !ids.includes(p.player_id))
    .sort((a, b) => a.team.localeCompare(b.team, "zh-Hant") || b.trials - a.trials);
  const go = (next: string[], nextType: PlayerType = type) => navigate({ name: "compare", type: nextType, ids: next }, { replace: true });
  const stamp = provenance.snapshot_id.slice(0, 15);

  return (
    <div className="stack">
      <header>
        <span className="eyebrow">比較</span>
        <h1>球員並列比較</h1>
        <p className="lede">最多 {MAX_COMPARE} 名同類型球員並排檢視百分位與真實實力；網址會保存選擇，可以直接分享。</p>
      </header>

      <section className="card controls-row">
        <fieldset className="segmented">
          <legend className="label">球員類型</legend>
          {(["batter", "pitcher"] as const).map((t) => (
            <label key={t}>
              <input type="radio" name="ctype" checked={type === t} onChange={() => go([], t)} />
              <span>{t === "batter" ? "打者" : "投手"}</span>
            </label>
          ))}
        </fieldset>
        <div className="field">
          <label htmlFor="add-player">加入球員</label>
          <select id="add-player" className="input" value="" onChange={(e) => e.target.value && go(addToComparison(ids, e.target.value))} disabled={candidates.length === 0}>
            <option value="">{players.length >= MAX_COMPARE ? `已達 ${MAX_COMPARE} 人（加入會取代最早的）` : "選擇球員…"}</option>
            {candidates.map((p) => (
              <option key={p.player_id} value={p.player_id}>
                {p.team}・{p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="row export">
          <button type="button" className="btn" disabled={players.length === 0} onClick={() => downloadText(`cpbl-compare-${stamp}.csv`, comparisonCsv(players, definitions), "text/csv;charset=utf-8")}>
            匯出 CSV
          </button>
          <button type="button" className="btn" disabled={players.length === 0} onClick={() => downloadText(`cpbl-compare-${stamp}.json`, comparisonJson(players, provenance.snapshot_id), "application/json")}>
            匯出 JSON
          </button>
        </div>
      </section>

      {players.length === 0 ? (
        <EmptyState title="還沒有選擇球員">
          <p>從上方選單加入球員，或在球員檔案按「與相似球員比較」。</p>
        </EmptyState>
      ) : (
        <section className="compare-grid" style={{ ["--cols" as string]: players.length }} data-testid="compare-grid">
          {players.map((p) => (
            <article key={p.player_id} className="card compare-card">
              <header>
                <h2>
                  <a href={routeToHash({ name: "player", type, id: p.player_id })}>{p.name}</a>
                </h2>
                <p className="muted">
                  {p.team}・{p.trials} {type === "batter" ? "打席" : "對戰打者"}
                  {!p.qualified && "・小樣本"}
                </p>
                <button type="button" className="btn" onClick={() => go(removeFromComparison(ids, p.player_id))} aria-label={`從比較中移除 ${p.name}`}>
                  移除
                </button>
              </header>
              <div className="pbars">
                {definitions.map((d) => (
                  <PercentileBar key={d.key} label={`${d.label}：${formatMetric(p.metrics[d.key], d.fmt)}`} value={p.percentiles[d.key] ?? null} />
                ))}
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

export default function Compare({ type, ids }: { type: PlayerType; ids: string[] }) {
  useDocumentTitle("球員比較");
  const details = useDataset("player-details.json");
  const league = useDataset("league.json");
  const provenance = useDataset("provenance.json");
  return (
    <div className="page">
      <Gate<[Record<string, PlayerDetail>, LeagueData, Provenance]> states={[details, league, provenance]}>
        {(d, l, p) => <CompareView details={d} league={l} provenance={p} type={type} ids={ids} />}
      </Gate>
    </div>
  );
}
