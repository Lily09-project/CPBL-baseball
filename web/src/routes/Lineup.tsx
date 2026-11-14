import { useEffect, useMemo, useRef, useState } from "react";
import { useDataset, useDocumentTitle, useRoute } from "../app/hooks";
import { ChartFrame, Histogram } from "../components/charts";
import { downloadText, toCsv } from "../lib/csv";
import { summarizePairedRuns } from "../lib/pairedLineup";
import { Gate } from "../components/States";
import { formatPercent, formatSigned } from "../lib/format";
import {
  completeLineup,
  defaultLineup,
  extraBaseProbability,
  hasBatter,
  hasPitcher,
  lineupCdfs,
  matchupProbabilities,
  moveSlot,
  onBaseProbability,
} from "../lib/lineup";
import { routeToHash, type SavedLineup } from "../lib/router";
import type { OrderSearchResult } from "../lib/sim";
import { integerHistogram, mean, quantile, shareAtLeast } from "../lib/stats";
import type { LeagueData, PlayerSummary, Provenance, SimInputs } from "../lib/types";
import { useSimWorker } from "../workers/useSimWorker";
import "./Lineup.css";

const GAME_OPTIONS = [1000, 5000, 20000];
const DEFAULT_SEED = 2026;
const HIST_CAP = 12;
const SEARCH_GAMES = 1500;
const SEARCH_ROUNDS = 3;

interface SimResult {
  inputKey: string;
  runs: number[];
  ids: string[];
  pitcher?: string;
  games: number;
}

function LineupLab({ players, sim, league, snapshot }: { players: PlayerSummary[]; sim: SimInputs; league: LeagueData; snapshot: string }) {
  const [route, navigate] = useRoute();
  const params = route.name === "lineup" ? route : { name: "lineup" as const };
  const teams = league.teams.map((t) => t.team);
  const team = params.team && teams.includes(params.team) ? params.team : (teams[0] as string);
  const ids = completeLineup(params.ids?.length ? params.ids : defaultLineup(players, sim, team), players, sim);
  const pitcher = params.pitcher && hasPitcher(sim, params.pitcher) ? params.pitcher : undefined;
  const seed = params.seed ?? DEFAULT_SEED;
  const games = params.games ?? GAME_OPTIONS[1]!;
  const [result, setResult] = useState<SimResult | null>(null);
  const [search, setSearch] = useState<(OrderSearchResult & { inputKey: string; ids: string[] }) | null>(null);
  const { run, cancel, job, progress, error } = useSimWorker();

  const byId = useMemo(() => new Map(players.map((p) => [`${p.type}:${p.player_id}`, p])), [players]);
  const batters = useMemo(() => players.filter((p) => p.type === "batter" && hasBatter(sim, p.player_id)), [players, sim]);
  const pitchers = useMemo(() => players.filter((p) => p.type === "pitcher" && hasPitcher(sim, p.player_id)), [players, sim]);
  const groupByTeam = (list: PlayerSummary[]) =>
    teams.map((t) => ({ team: t, items: list.filter((p) => p.team === t).sort((a, b) => b.trials - a.trials) })).filter((g) => g.items.length > 0);

  const a = params.a;
  const b = params.b;
  const valid = (value: SavedLineup | undefined) => Boolean(value && value.ids.length === 9 &&
    new Set(value.ids).size === 9 && value.ids.every((id) => hasBatter(sim, id)) &&
    (!value.pitcher || hasPitcher(sim, value.pitcher)));
  const canCompare = params.snapshot === snapshot && valid(a) && valid(b);
  const comparisonKey = JSON.stringify([snapshot, a, b, seed, games]);
  const [paired, setPaired] = useState<{ key: string; a: number[]; b: number[] } | null>(null);
  const [comparing, setComparing] = useState(false);
  const pairedResult = canCompare && paired?.key === comparisonKey ? paired : null;
  const stats = pairedResult ? summarizePairedRuns(pairedResult.a, pairedResult.b) : null;
  const distributions = pairedResult ? [pairedResult.a, pairedResult.b].map((runs) => integerHistogram(runs, HIST_CAP)) : [];
  const bins = Array.from({ length: HIST_CAP + 1 }, (_, i) => i === HIST_CAP ? `${i}+` : String(i));

  const inputKey = JSON.stringify([ids, pitcher, seed, games, comparisonKey]);
  const currentKey = useRef(inputKey);
  const generation = useRef(0);
  useEffect(() => {
    currentKey.current = inputKey;
    generation.current += 1;
    queueMicrotask(cancel);
  }, [inputKey, cancel]);

  const invalidate = () => { generation.current += 1; cancel(); };

  // Keyboard focus follows the action: a moved batter keeps focus on its move
  // button, and controls that disappear (cancel, apply) hand focus to the run button.
  const focusNext = useRef<string | null>(null);
  useEffect(() => {
    const id = focusNext.current;
    if (!id) return;
    const wanted = document.getElementById(id) as HTMLButtonElement | null;
    if (!wanted) return;
    // First/last slots have one disabled arrow; use the other arrow of that slot.
    const target = wanted.disabled && id.startsWith("slot-") ? wanted.parentElement?.querySelector<HTMLButtonElement>("button:not(:disabled)") : wanted;
    if (!target || target.disabled) return;
    focusNext.current = null;
    target.focus();
  });
  const move = (from: number, to: number) => {
    focusNext.current = `slot-${to}-${to < from ? "up" : "down"}`;
    update({ ids: moveSlot(ids, from, to) });
  };
  const update = (patch: Partial<typeof params>) => {
    invalidate();
    setResult(null);
    setSearch(null);
    navigate({ ...params, team, ids, pitcher, seed: params.seed, ...patch, name: "lineup" }, { replace: true });
  };

  const savePair = (patch: Partial<typeof params>) => update({ snapshot, ...patch });

  const compare = async () => {
    if (!canCompare || !a || !b) return;
    const version = ++generation.current;
    setPaired(null);
    setComparing(true);
    try {
      const first = await run<"simulate">({ kind: "simulate", cdfs: lineupCdfs(sim, a.ids, a.pitcher), games, seed });
      if (version !== generation.current) return;
      const second = await run<"simulate">({ kind: "simulate", cdfs: lineupCdfs(sim, b.ids, b.pitcher), games, seed });
      if (version !== generation.current) return;
      setPaired({ key: comparisonKey, a: first, b: second });
    } catch {
      // Worker errors are displayed next to the comparison controls.
    } finally {
      setComparing(false);
    }
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
      const found = await run<"optimise">({ kind: "optimise", cdfs: lineupCdfs(sim, ids, pitcher), games: SEARCH_GAMES, seed, rounds: SEARCH_ROUNDS });
      if (version !== generation.current || currentKey.current !== inputKey) return;
      setSearch({ ...found, inputKey, ids: [...ids] });
    } catch { /* The worker owns error feedback; cancelled work has no result. */ }
  };

  const fresh = result && result.inputKey === inputKey;
  const runsPerGame = result ? mean(result.runs) : null;
  const name = (type: "batter" | "pitcher", id: string) => byId.get(`${type}:${id}`)?.name ?? id;
  const changedSlots = a && b ? a.ids.flatMap((id, index) => id === b.ids[index] ? [] : [{ slot: index + 1, left: id, right: b.ids[index]! }]) : [];
  const pitcherName = (id?: string) => id ? name("pitcher", id) : "聯盟平均投手";
  const runsAt = (runs: number[], q: number) => {
    const v = quantile(runs, q);
    return Number.isInteger(v) ? String(v) : v.toFixed(1);
  };

  return (
    <div className="stack">
      <section className="lineup-layout">
        <div className="card">
          <h2>排出打線</h2>
          <p className="muted small lineup-hint">
            {params.ids?.length ? "" : `預設 9 棒是${team}打席數最多的 9 位打者。`}可以直接執行模擬，或換人、調棒次後再比較。
          </p>
          <button type="button" className="btn jump-run" onClick={() => {
            const panel = document.getElementById("run-panel");
            panel?.scrollIntoView({ block: "start" });
            panel?.focus({ preventScroll: true });
          }}>
            跳到執行模擬
          </button>
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
          <div className="slots-head" aria-hidden="true">
            <span>棒次</span>
            <span>打者（打席）</span>
            <span>對戰上壘・長打</span>
            <span>調整</span>
          </div>
          <ol className="slots" data-testid="lineup-slots">
            {ids.map((id, slot) => {
              const probs = matchupProbabilities(sim, id, pitcher);
              return (
                <li key={slot} className="slot">
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
                    <button type="button" id={`slot-${slot}-up`} className="btn icon" aria-label={`${name("batter", id)} 往前一棒`} disabled={slot === 0} onClick={() => move(slot, slot - 1)}>
                      ↑
                    </button>
                    <button type="button" id={`slot-${slot}-down`} className="btn icon" aria-label={`${name("batter", id)} 往後一棒`} disabled={slot === ids.length - 1} onClick={() => move(slot, slot + 1)}>
                      ↓
                    </button>
                  </span>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="card run-panel" id="run-panel" tabIndex={-1} aria-labelledby="run-title">
          <h2 id="run-title">執行模擬</h2>
          <fieldset className="segmented">
            <legend className="label">模擬場數</legend>
            {GAME_OPTIONS.map((g) => (
              <label key={g}>
                <input type="radio" name="games" value={g} checked={games === g} onChange={() => update({ games: g })} />
                <span>{g.toLocaleString()}</span>
              </label>
            ))}
          </fieldset>
          <p className="muted small">亂數種子 {seed}：相同打線與種子永遠得到相同結果。</p>
          <div className="row">
            <button type="button" id="run-simulate" className="btn btn-primary" onClick={simulate} disabled={job !== null}>
              模擬 {games.toLocaleString()} 場
            </button>
            <button type="button" className="btn" onClick={optimise} disabled={job !== null}>
              搜尋更好的棒次
            </button>
            {job && (
              <button type="button" className="btn" onClick={() => { focusNext.current = "run-simulate"; invalidate(); }}>
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
            {!result && !job && (
              <p className="run-empty muted">
                按下「模擬 {games.toLocaleString()} 場」後，這裡會顯示平均每場得分、得 5 分以上與被完封的機率，以及每場得分的分布；「搜尋更好的棒次」會嘗試兩兩對調棒次並檢查改善是否只是雜訊。
              </p>
            )}
            {result && runsPerGame !== null && (
              <div className="results" data-testid="sim-results">
                {!fresh && <p className="notice">打線或模擬設定已變更，以下是上一次的結果，請重新模擬。</p>}
                <div className="result-kpis">
                  <div>
                    <span className="stat-label">平均每場得分</span>
                    <span className="stat-value" data-testid="runs-per-game">
                      {runsPerGame.toFixed(2)}
                    </span>
                    <span className="muted small">聯盟 {league.runs_per_game.toFixed(2)}（{formatSigned(Number(runsPerGame.toFixed(2)) - Number(league.runs_per_game.toFixed(2)), 2)}）</span>
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
                <p className="muted small chart-guide">
                  怎麼讀：橫軸是單場得分，長條高度是場數；黑色長條是得 5 分以上的比賽。中位數 {runsAt(result.runs, 0.5)} 分，80% 的比賽介於 {runsAt(result.runs, 0.1)} 到 {runsAt(result.runs, 0.9)} 分。
                </p>
              </div>
            )}

            {search && search.inputKey === inputKey && (
              <div className="search-result" data-testid="order-search">
                <h3>建議棒次</h3>
                {search.order.some((index, slot) => index !== slot) ? (
                  <>
                    <p>
                      以另一組 {SEARCH_GAMES.toLocaleString()} 場未參與搜尋的亂數序列配對評估：原棒次平均每場 {search.baselineMean.toFixed(2)} 分、調整後 {search.bestMean.toFixed(2)} 分，配對差值 <strong>{formatSigned(search.delta, 2)}</strong> 分（95% 區間 {formatSigned(search.deltaLow, 2)} 到 {formatSigned(search.deltaHigh, 2)}）。
                      {search.deltaLow <= 0 && search.deltaHigh >= 0 && " 區間包含 0，差異可能只是模擬雜訊。"}
                      {search.deltaHigh < 0 && " 獨立評估顯示調整後得分較低，不建議依此結果調整。"}
                    </p>
                    <ol className="suggested">
                      {search.order.map((index, slot) => (
                        <li key={slot} className={index !== slot ? "moved" : undefined}>
                          {name("batter", search.ids[index] as string)}
                          {index !== slot && <span className="badge badge-accent">原第 {index + 1} 棒</span>}
                        </li>
                      ))}
                    </ol>
                    <button type="button" className="btn btn-primary" onClick={() => { focusNext.current = "run-simulate"; update({ ids: search.order.map((i) => search.ids[i] as string) }); }}>
                      套用建議棒次
                    </button>
                  </>
                ) : (
                  <p>目前的棒次已是局部最佳：任何兩棒對調都沒有讓平均得分提高。</p>
                )}
                <p className="muted small">共評估 {search.evaluations} 種棒次，每種搜尋 {SEARCH_GAMES.toLocaleString()} 場；這裡的平均得分來自獨立評估，因此和上方「模擬」按鈕的結果不會完全相同。</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="lineup-scenarios">
        <h2 id="lineup-scenarios">打線方案 A／B</h2>
        <p className="muted">把上方打線存成方案，再用相同場數與種子比較。網址會保留兩組設定與快照。</p>
        {(a || b) && params.snapshot !== snapshot ? (
          <div role="status">
            <p>這組方案使用不同資料快照。請重新確認球員，再儲存兩組方案。</p>
            <button type="button" className="btn" onClick={() => savePair({ a: undefined, b: undefined })}>清除舊方案</button>
          </div>
        ) : <>
          <div className="row">
            <button className="btn" type="button" onClick={() => savePair({ a: { ids, pitcher } })}>儲存為 A</button>
            <button className="btn" type="button" onClick={() => savePair({ b: { ids, pitcher } })}>儲存為 B</button>
            <button className="btn" type="button" disabled={!a} onClick={() => savePair({ b: a })}>複製 A 到 B</button>
            <button className="btn" type="button" disabled={!a || !b} onClick={() => savePair({ a: b, b: a })}>交換 A／B</button>
          </div>
          {([a, b] as const).map((value, index) => value && <details key={index}>
            <summary>{index === 0 ? "方案 A" : "方案 B"} · {value.pitcher ? name("pitcher", value.pitcher) : "聯盟平均投手"}</summary>
            <ol>{value.ids.map((id, slot) => <li key={slot}>{name("batter", id)}</li>)}</ol>
            <button className="btn" type="button" disabled={!valid(value)} onClick={() => update({ ids: value.ids, pitcher: value.pitcher })}>載入到編輯區</button>
          </details>)}
          {((a && !valid(a)) || (b && !valid(b))) && <p role="status">方案含有無法使用的球員，請重新儲存。</p>}
          {canCompare && a && b && <div className="notice" data-testid="lineup-differences">
            <strong>方案差異</strong>
            <p>{changedSlots.length === 0 ? "棒次與打者相同" : `第 ${changedSlots.map(({ slot }) => slot).join("、")} 棒不同`}
              {a.pitcher === b.pitcher ? " · 對手投手相同" : ` · 對手投手 A ${pitcherName(a.pitcher)}／B ${pitcherName(b.pitcher)}`}</p>
            {changedSlots.length > 0 && <details>
              <summary>查看打者差異</summary>
              <ul>{changedSlots.map(({ slot, left, right }) => <li key={slot}>
                第 {slot} 棒 · A {name("batter", left)}／B {name("batter", right)}
              </li>)}</ul>
            </details>}
          </div>}
          <div className="row">
            <button className="btn" type="button" disabled={!canCompare || comparing || Boolean(job)} onClick={() => void compare()}>比較兩組打線</button>
            {comparing && <button className="btn" type="button" onClick={invalidate}>取消比較</button>}
            {a && b && <a className="btn" href={routeToHash(params)}>比較分享網址</a>}
          </div>
          {comparing && <p role="status">正在模擬兩組打線</p>}
          {error && !comparing && <p role="status">{error}</p>}
          {stats && pairedResult && <div data-testid="paired-lineup-result">
            <h3>每場得分差（B − A）</h3>
            <p><strong className="stat-value">{formatSigned(stats.delta, 2)} 分</strong></p>
            <p>95% 配對模擬區間 {stats.low.toFixed(2)} 至 {stats.high.toFixed(2)} 分。
              {stats.low <= 0 && stats.high >= 0 ? "區間包含 0，模擬中尚未看出明確差異。" : stats.low > 0 ? "方案 B 的模擬平均得分較高。" : "方案 A 的模擬平均得分較高。"}</p>
            <p className="muted">A 平均 {stats.a.toFixed(2)} 分 · B 平均 {stats.b.toFixed(2)} 分</p>
            <ChartFrame title="兩組方案的得分分布" summary="比較每場得分的模擬次數" table={<table>
              <thead><tr><th scope="col">得分</th><th scope="col">A</th><th scope="col">B</th></tr></thead>
              <tbody>{bins.map((bin, i) => <tr key={bin}><th scope="row">{bin}</th><td>{distributions[0]?.[i]}</td><td>{distributions[1]?.[i]}</td></tr>)}</tbody>
            </table>}>
              <p>方案 A</p><Histogram counts={distributions[0]!} labels={bins} />
              <p>方案 B</p><Histogram counts={distributions[1]!} labels={bins} />
            </ChartFrame>
            <button className="btn" type="button" onClick={() => downloadText("cpbl-lineup-comparison.csv",
              toCsv(["snapshot", "seed", "game", "a", "b", "delta"], pairedResult.a.map((value, i) => ({
                snapshot, seed, game: i + 1, a: value, b: pairedResult.b[i]!, delta: pairedResult.b[i]! - value,
              }))), "text/csv;charset=utf-8")}>下載比較 CSV</button>
          </div>}
        </>}
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
  const provenance = useDataset("provenance.json");
  return (
    <div className="page stack">
      <header className="spread-head">
        <span className="eyebrow">實驗 02・Monte Carlo</span>
        <h1>打線實驗室</h1>
        <p className="lede">
          排出你的 9 棒、指定對手投手，瀏覽器會在背景執行緒用壘包－出局數馬可夫鏈模擬整場比賽，告訴你這套打線平均能得幾分，以及換棒次值不值得。
        </p>
      </header>

      <Gate<[PlayerSummary[], SimInputs, LeagueData, Provenance]> states={[players, sim, league, provenance]}>{(p, s, l, source) => <LineupLab players={p} sim={s} league={l} snapshot={source.snapshot_id} />}</Gate>
    </div>
  );
}
