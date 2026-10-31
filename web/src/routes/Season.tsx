import { useState } from "react";
import { useDataset, useDocumentTitle } from "../app/hooks";
import { ChartFrame, Histogram, RangeBars } from "../components/charts";
import { ScrollRegion } from "../components/ScrollRegion";
import { Gate } from "../components/States";
import { formatPercent } from "../lib/format";
import type { LeagueData } from "../lib/types";
import "./Season.css";

function SeasonView({ league }: { league: LeagueData }) {
  const teams = [...league.teams].sort((a, b) => b.simulation.first_place_probability - a.simulation.first_place_probability || b.wins - a.wins);
  const [selected, setSelected] = useState(teams[0]?.team ?? "");
  const team = teams.find((t) => t.team === selected) ?? teams[0];
  const lo = Math.min(...teams.map((t) => t.simulation.current_wins)) - 1;
  const hi = Math.max(...teams.map((t) => t.simulation.projected_wins_p90)) + 1;

  return (
    <div className="stack">
      <header>
        <span className="eyebrow">實驗 03・情境模擬</span>
        <h1>季末戰績模擬</h1>
        <p className="lede">
          以每隊的畢氏期望勝率作為真實強度，用 log5 計算每場對戰勝率，把剩下的比賽模擬 {league.simulations.toLocaleString()} 次，看看誰最可能拿下這個半季。
        </p>
        <p className="notice">
          假設：本段賽季每隊共 {league.segment_games} 場（中職半季制）；官方剩餘賽程不在公開快照中，因此依剩餘場數平均配對對手，配不到的場次以聯盟平均對手計算。結果是情境分析，不是官方預測。
        </p>
      </header>

      <section className="card">
        <h2>奪冠機率</h2>
        <ul className="prob-list" data-testid="title-odds">
          {teams.map((t) => (
            <li key={t.team}>
              <span className="prob-team">{t.team}</span>
              <span className="prob-track" aria-hidden="true">
                <span style={{ width: `${t.simulation.first_place_probability * 100}%` }} />
              </span>
              <strong className="prob-value">{formatPercent(t.simulation.first_place_probability, 1)}</strong>
            </li>
          ))}
        </ul>
        <p className="muted small">依勝率排名（和局不計），同勝率並列第一時平分機率，因此全部加總恰好為 100%。種子 {league.seed}，可完全重現。</p>
      </section>

      <section className="grid grid-2">
        <div className="card">
          <ChartFrame
            title="最終勝場預估（｜目前勝場 ● 中位數 ▬ 80% 區間）"
            summary={teams.map((t) => `${t.team} 預估 ${t.simulation.projected_wins_p50} 勝`).join("，")}
            table={<SeasonTable league={league} />}
          >
            <RangeBars
              domain={[lo, hi]}
              rows={teams.map((t) => ({
                key: t.team,
                label: t.team,
                low: t.simulation.projected_wins_p10,
                high: t.simulation.projected_wins_p90,
                mid: t.simulation.projected_wins_p50,
                current: t.simulation.current_wins,
              }))}
            />
          </ChartFrame>
        </div>
        <div className="card">
          <div className="field">
            <label htmlFor="season-team">檢視球隊</label>
            <select id="season-team" className="input" value={team?.team} onChange={(e) => setSelected(e.target.value)}>
              {teams.map((t) => (
                <option key={t.team} value={t.team}>
                  {t.team}
                </option>
              ))}
            </select>
          </div>
          {team && (
            <ChartFrame
              title={`${team.team}：剩餘 ${team.simulation.games_remaining} 場的額外勝場分布`}
              summary={`平均再贏 ${(team.simulation.projected_wins_mean - team.simulation.current_wins).toFixed(1)} 場`}
              table={
                <table>
                  <thead>
                    <tr>
                      <th scope="col">再贏場數</th>
                      <th scope="col" className="num">模擬次數</th>
                    </tr>
                  </thead>
                  <tbody>
                    {team.simulation.additional_wins_histogram.map((c, i) => (
                      <tr key={i}>
                        <th scope="row">{i}</th>
                        <td className="num">{c}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              {team.simulation.games_remaining > 0 ? (
                <Histogram counts={team.simulation.additional_wins_histogram} labels={team.simulation.additional_wins_histogram.map((_, i) => String(i))} />
              ) : (
                <p className="muted">這支球隊已打完本段賽季。</p>
              )}
            </ChartFrame>
          )}
        </div>
      </section>

      <section className="card">
        <h2>完整數據</h2>
        <ScrollRegion label="季末模擬完整數據">
          <SeasonTable league={league} />
        </ScrollRegion>
      </section>
    </div>
  );
}

function SeasonTable({ league }: { league: LeagueData }) {
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">球隊</th>
          <th scope="col" className="num">目前勝場</th>
          <th scope="col" className="num">剩餘</th>
          <th scope="col" className="num">真實強度</th>
          <th scope="col" className="num">預估勝場</th>
          <th scope="col" className="num">80% 區間</th>
          <th scope="col" className="num">奪冠機率</th>
        </tr>
      </thead>
      <tbody>
        {league.teams.map((t) => (
          <tr key={t.team}>
            <th scope="row">{t.team}</th>
            <td className="num">{t.simulation.current_wins}</td>
            <td className="num">{t.simulation.games_remaining}</td>
            <td className="num">{t.simulation.strength.toFixed(3)}</td>
            <td className="num">{t.simulation.projected_wins_mean.toFixed(1)}</td>
            <td className="num">
              {t.simulation.projected_wins_p10}–{t.simulation.projected_wins_p90}
            </td>
            <td className="num">{formatPercent(t.simulation.first_place_probability, 1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Season() {
  useDocumentTitle("季末戰績模擬");
  const league = useDataset("league.json");
  return (
    <div className="page">
      <Gate<[LeagueData]> states={[league]}>{(l) => <SeasonView league={l} />}</Gate>
    </div>
  );
}
