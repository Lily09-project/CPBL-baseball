import { useState } from "react";
import { useDataset, useDocumentTitle } from "../app/hooks";
import { ChartFrame, Histogram, RangeBars } from "../components/charts";
import { ScrollRegion } from "../components/ScrollRegion";
import { SnapshotNotice } from "../components/SnapshotNotice";
import { Gate } from "../components/States";
import { formatPercent } from "../lib/format";
import { leagueHeadline, rankByFirstPlace } from "../lib/insights";
import type { LeagueData, Provenance } from "../lib/types";
import "./Season.css";

function SeasonView({ league, provenance }: { league: LeagueData; provenance: Provenance }) {
  const teams = rankByFirstPlace(league.teams);
  const headline = leagueHeadline(league);
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
          以每隊的畢氏期望勝率作為真實強度，用 log5 計算每場對戰勝率，從快照當時的戰績出發，把剩下的比賽模擬 {league.simulations.toLocaleString()} 次，看看誰最可能拿下這個半季。
        </p>
        <SnapshotNotice provenance={provenance} />
        <p className="notice">
          假設：每個半季每隊共 {league.segment_games} 場（中職半季制）；官方剩餘賽程不在公開快照中，因此依剩餘場數平均配對對手，配不到的場次以聯盟平均對手計算。結果是情境分析，不是官方預測。
        </p>
      </header>

      <section className="card">
        <h2>拿下半季第一的機率</h2>
        {headline && (
          <p className="takeaway" data-testid="season-takeaway">
            <strong>{headline.leader.team}</strong>在快照當時 {headline.leader.simulation.current_wins} 勝、剩 {headline.leader.simulation.games_remaining} 場，在 {headline.simulations.toLocaleString()} 次模擬中有{" "}
            <strong>{formatPercent(headline.leader.simulation.first_place_probability, 1)}</strong> 拿下半季第一
            {headline.runnerUp ? `；最大威脅是${headline.runnerUp.team}（${formatPercent(headline.runnerUp.simulation.first_place_probability, 1)}）` : ""}
            {headline.shutOut.length > 0 ? `。${headline.shutOut.length} 隊在所有模擬中都沒拿到第一。` : "。"}
          </p>
        )}
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
            title="最終勝場預估（｜快照時勝場 ● 中位數 ▬ 80% 區間）"
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
          <p className="muted small chart-guide">怎麼讀：直線是快照當時的勝場，圓點是模擬的中位數，綠色長條涵蓋 80% 的模擬結果；長條越短，代表剩餘場次越少、結局越確定。</p>
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
              title={`${team.team}：快照時剩餘 ${team.simulation.games_remaining} 場的額外勝場分布`}
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
                <p className="muted">快照當時這支球隊已打完這個半季。</p>
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
          <th scope="col" className="num">快照時勝場</th>
          <th scope="col" className="num">剩餘</th>
          <th scope="col" className="num">真實強度</th>
          <th scope="col" className="num">預估勝場</th>
          <th scope="col" className="num">80% 區間</th>
          <th scope="col" className="num">半季第一機率</th>
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
  const provenance = useDataset("provenance.json");
  return (
    <div className="page">
      <Gate<[LeagueData, Provenance]> states={[league, provenance]}>{(l, p) => <SeasonView league={l} provenance={p} />}</Gate>
    </div>
  );
}
