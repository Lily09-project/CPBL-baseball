import { useEffect, useMemo, useRef, useState } from "react";
import { useDataset, useDocumentTitle, useRoute } from "../app/hooks";
import { ChartFrame, Histogram } from "../components/charts";
import { Gate } from "../components/States";
import { formatPercent, formatSigned } from "../lib/format";
import {
  completeLineup,
  defaultLineup,
  extraBaseProbability,
  lineupCdfs,
  matchupProbabilities,
  moveSlot,
  onBaseProbability,
} from "../lib/lineup";
import { routeToHash } from "../lib/router";
import type { OrderSearchResult } from "../lib/sim";
import { integerHistogram, mean, quantile, shareAtLeast } from "../lib/stats";
import type { LeagueData, PlayerSummary, SimInputs } from "../lib/types";
import { useSimWorker } from "../workers/useSimWorker";
import "./Lineup.css";

const GAME_OPTIONS = [1000, 5000, 20000];
const DEFAULT_SEED = 2026;
const HIST_CAP = 12;

interface SimResult {
  inputKey: string;
  runs: number[];
  ids: string[];
  pitcher?: string;
  games: number;
}

function LineupLab({ players, sim, league }: { players: PlayerSummary[]; sim: SimInputs; league: LeagueData }) {
  const [route, navigate] = useRoute();
  const params = route.name === "lineup" ? route : { name: "lineup" as const };
  const teams = league.teams.map((t) => t.team);
  const team = params.team && teams.includes(params.team) ? params.team : (teams[0] as string);
  const ids = completeLineup(params.ids?.length ? params.ids : defaultLineup(players, sim, team), players, sim);
  const pitcher = params.pitcher && sim.pitchers[params.pitcher] ? params.pitcher : undefined;
  const seed = params.seed ?? DEFAULT_SEED;
  const [games, setGames] = useState(GAME_OPTIONS[1] as number);
  const [result, setResult] = useState<SimResult | null>(null);
  const [search, setSearch] = useState<(OrderSearchResult & { inputKey: string; ids: string[] }) | null>(null);
  const { run, cancel, job, progress, error } = useSimWorker();

  const byId = useMemo(() => new Map(players.map((p) => [`${p.type}:${p.player_id}`, p])), [players]);
  const batters = useMemo(() => players.filter((p) => p.type === "batter" && sim.batters[p.player_id]), [players, sim]);
  const pitchers = useMemo(() => players.filter((p) => p.type === "pitcher" && sim.pitchers[p.player_id]), [players, sim]);
  const groupByTeam = (list: PlayerSummary[]) =>
    teams.map((t) => ({ team: t, items: list.filter((p) => p.team === t).sort((a, b) => b.trials - a.trials) })).filter((g) => g.items.length > 0);

  const inputKey = JSON.stringify([ids, pitcher, seed, games]);
  const currentKey = useRef(inputKey);
  const generation = useRef(0);
  useEffect(() => {
    currentKey.current = inputKey;
    generation.current += 1;
    queueMicrotask(cancel);
  }, [inputKey, cancel]);

  const invalidate = () => { generation.current += 1; cancel(); };
  const update = (patch: Partial<typeof params>) => {
    invalidate();
    setResult(null);
    setSearch(null);
    navigate({ ...params, team, ids, pitcher, seed: params.seed, ...patch, name: "lineup" }, { replace: true });
  };

  const simulate = async () => {
    const version = ++generation.current;
    try {
      const runs = await run<"simulate">({ kind: "simulate", cdfs: lineupCdfs(sim, ids, pitcher), games, seed });
      if (version !== generation.current || currentKey.current !== inputKey) return;
      setResult({ runs, ids, pitcher, games, inputKey });
      setSearch(null);
    } catch { /* The worker owns error feedback; cancelled work has no result. */ }
  };

  const optimise = async () => {
    const version = ++generation.current;
    try {
      const found = await run<"optimise">({ kind: "optimise", cdfs: lineupCdfs(sim, ids, pitcher), games: 1500, seed, rounds: 3 });
      if (version !== generation.current || currentKey.current !== inputKey) return;
      setSearch({ ...found, inputKey, ids: [...ids] });
    } catch { /* The worker owns error feedback; cancelled work has no result. */ }
  };

  const fresh = result && result.inputKey === inputKey;
  const runsPerGame = result ? mean(result.runs) : null;
  const name = (type: "batter" | "pitcher", id: string) => byId.get(`${type}:${id}`)?.name ?? id;

  return (
    <div className="stack">
      <header>
        <span className="eyebrow">實驗 02・Monte Carlo</span>
        <h1>打線實驗室</h1>
        <p className="lede">
          排出你的 9 棒、指定對手投手，瀏覽器會在背景執行緒用壘包－出局數馬可夫鏈模擬整場比賽，告訴你這套打線平均能得幾分，以及換棒次值不值得。
        </p>
      </header>

      <section className="lineup-layout">
        <div className="card">
          <h2>排出打線</h2>
          <div className="lineup-controls">
            <div className="field">
              <label htmlFor="team-fill">以球隊預設打線填入</label>
              <select id="team-fill" className="input" value={team} onChange={(e) => update({ team: e.target.value, ids: defaultLineup(players, sim, e.target.value) })}>
                {teams.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="pitcher">對手投手</label>
              <select id="pitcher" className="input" value={pitcher ?? ""} onChange={(e) => update({ pitcher: e.target.value || undefined })}>
                <option value="">聯盟平均投手</option>
                {groupByTeam(pitchers).map((g) => (
                  <optgroup key={g.team} label={g.team}>
                    {g.items.map((p) => (
                      <option key={p.player_id} value={p.player_id}>
                        {p.name}（{p.trials} 打者）
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>
          </div>
          <ol className="slots" data-testid="lineup-slots">
            {ids.map((id, slot) => {
              const probs = matchupProbabilities(sim, id, pitcher);
              return (
                <li key={`${slot}-${id}`} className="slot">
                  <span className="slot-no" aria-hidden="true">
                    {slot + 1}
                  </span>
                  <div className="field slot-select">
                    <label htmlFor={`slot-${slot}`} className="visually-hidden">
                      第 {slot + 1} 棒
                    </label>
                    <select
                      id={`slot-${slot}`}
                      className="input"
                      value={id}
                      onChange={(e) => update({ ids: ids.map((x, i) => (i === slot ? e.target.value : x)) })}
                    >
                      {groupByTeam(batters).map((g) => (
                        <optgroup key={g.team} label={g.team}>
                          {g.items.map((p) => (
                            <option key={p.player_id} value={p.player_id} disabled={p.player_id !== id && ids.includes(p.player_id)}>
                              {p.name}（{p.trials} 打席）
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>
                  <span className="slot-stat" title="對上指定投手的上壘機率／長打機率">
                    上壘 {formatPercent(onBaseProbability(probs), 0)}・長打 {formatPercent(extraBaseProbability(probs), 1)}
                  </span>
                  <span className="slot-move">
                    <button type="button" className="btn icon" aria-label={`${name("batter", id)} 往前一棒`} disabled={slot === 0} onClick={() => update({ ids: moveSlot(ids, slot, slot - 1) })}>
                      ↑
                    </button>
                    <button type="button" className="btn icon" aria-label={`${name("batter", id)} 往後一棒`} disabled={slot === ids.length - 1} onClick={() => update({ ids: moveSlot(ids, slot, slot + 1) })}>
                      ↓
                    </button>
                  </span>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="card run-panel">
          <h2>執行模擬</h2>
          <fieldset className="segmented">
            <legend className="label">模擬場數</legend>
            {GAME_OPTIONS.map((g) => (
              <label key={g}>
                <input type="radio" name="games" value={g} checked={games === g} onChange={() => setGames(g)} />
                <span>{g.toLocaleString()}</span>
              </label>
            ))}
          </fieldset>
          <p className="muted small">亂數種子 {seed}：相同打線與種子永遠得到相同結果。</p>
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={simulate} disabled={job !== null}>
              模擬 {games.toLocaleString()} 場
            </button>
            <button type="button" className="btn" onClick={optimise} disabled={job !== null}>
              搜尋更好的棒次
            </button>
            {job && (
              <button type="button" className="btn" onClick={invalidate}>
                取消
              </button>
            )}
          </div>
          {job && (
            <div className="progress" role="progressbar" aria-label={job.kind === "simulate" ? "模擬進度" : "棒次搜尋進度"} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
              <span style={{ width: `${progress * 100}%` }} />
            </div>
          )}
          {error && (
            <p role="alert" className="error-text">
              模擬失敗：{error}
            </p>
          )}

          <div aria-live="polite">
            {result && runsPerGame !== null && (
              <div className="results" data-testid="sim-results">
                {!fresh && <p className="notice">打線已變更，以下是上一次的結果，請重新模擬。</p>}
                <div className="result-kpis">
                  <div>
                    <span className="stat-label">平均每場得分</span>
                    <span className="stat-value" data-testid="runs-per-game">
                      {runsPerGame.toFixed(2)}
                    </span>
                    <span className="muted small">聯盟 {league.runs_per_game.toFixed(2)}（{formatSigned(runsPerGame - league.runs_per_game, 2)}）</span>
                  </div>
                  <div>
                    <span className="stat-label">得 5 分以上</span>
                    <span className="stat-value">{formatPercent(shareAtLeast(result.runs, 5))}</span>
                  </div>
                  <div>
                    <span className="stat-label">被完封</span>
                    <span className="stat-value">{formatPercent(1 - shareAtLeast(result.runs, 1))}</span>
                  </div>
                </div>
                <ChartFrame
                  title={`每場得分分布（${result.games.toLocaleString()} 場）`}
                  summary={`中位數 ${quantile(result.runs, 0.5)} 分，80% 的比賽介於 ${quantile(result.runs, 0.1)} 到 ${quantile(result.runs, 0.9)} 分`}
                  table={
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">得分</th>
                          <th scope="col" className="num">場數</th>
                        </tr>
                      </thead>
                      <tbody>
                        {integerHistogram(result.runs, HIST_CAP).map((c, i) => (
                          <tr key={i}>
                            <th scope="row">{i === HIST_CAP ? `${HIST_CAP}+` : i}</th>
                            <td className="num">{c}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  }
                >
                  <Histogram counts={integerHistogram(result.runs, HIST_CAP)} labels={Array.from({ length: HIST_CAP + 1 }, (_, i) => (i === HIST_CAP ? `${i}+` : String(i)))} highlightFrom={5} />
                </ChartFrame>
              </div>
            )}

            {search && search.inputKey === inputKey && (
              <div className="search-result" data-testid="order-search">
                <h3>建議棒次</h3>
                {search.order.some((index, slot) => index !== slot) ? (
                  <>
                    <p>
                      調整後平均每場 {search.bestMean.toFixed(2)} 分，獨立評估的配對差值 <strong>{formatSigned(search.delta, 2)}</strong> 分（95% 區間 {formatSigned(search.deltaLow, 2)} 到 {formatSigned(search.deltaHigh, 2)}）。
                      {search.deltaLow <= 0 && " 區間包含 0，差異可能只是模擬雜訊。"}
                    </p>
                    <ol className="suggested">
                      {search.order.map((index, slot) => (
                        <li key={slot} className={index !== slot ? "moved" : undefined}>
                          {name("batter", search.ids[index] as string)}
                          {index !== slot && <span className="badge badge-accent">原第 {index + 1} 棒</span>}
                        </li>
                      ))}
                    </ol>
                    <button type="button" className="btn btn-primary" onClick={() => update({ ids: search.order.map((i) => search.ids[i] as string) })}>
                      套用建議棒次
                    </button>
                  </>
                ) : (
                  <p>目前的棒次已是局部最佳：任何兩棒對調都沒有讓平均得分提高。</p>
                )}
                <p className="muted small">共評估 {search.evaluations} 種棒次，每種搜尋 1,500 場；建議固定後另用 1,500 場未參與搜尋的亂數序列做配對評估。</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="card method">
        <h2>模型怎麼運作</h2>
        <ul>
          <li>每位打者的事件機率（一壘安打、二壘安打、三壘安打、全壘打、保送／觸身、三振、其他出局）先加上 {sim.stabilizers.batter_pa} 個聯盟平均打席做收縮，避免小樣本暴衝。</li>
          <li>對上指定投手時，用廣義 log5：P(事件) ∝ 打者機率 × 投手機率 ÷ 聯盟機率。</li>
          <li>跑壘推進（例如二壘跑者遇一壘安打回本壘）使用固定、公開的機率；聯盟平均打線的模擬得分與實際每場得分的差距在 ±20% 以內（單元測試把關）。</li>
          <li>不考慮守備、盜壘、換投與球場因素，因此適合比較打線之間的「相對」差異，而不是預測單場比分。</li>
        </ul>
        <p className="muted small">
          想看單一球員的完整數據？前往 <a href={routeToHash({ name: "talent", type: "batter" })}>真實實力排行</a>。
        </p>
      </section>
    </div>
  );
}

export default function Lineup() {
  useDocumentTitle("打線實驗室");
  const players = useDataset("players.json");
  const sim = useDataset("sim.json");
  const league = useDataset("league.json");
  return (
    <div className="page">
      <Gate<[PlayerSummary[], SimInputs, LeagueData]> states={[players, sim, league]}>{(p, s, l) => <LineupLab players={p} sim={s} league={l} />}</Gate>
    </div>
  );
}
