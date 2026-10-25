import { useDataset, useDocumentTitle } from "../app/hooks";
import { ChartFrame, DivergingBars } from "../components/charts";
import { ScrollRegion } from "../components/ScrollRegion";
import { Gate } from "../components/States";
import { formatDate, formatPercent, formatSigned } from "../lib/format";
import { routeToHash } from "../lib/router";
import type { LeagueData, Provenance } from "../lib/types";
import "./Home.css";

const FEATURES = [
  {
    href: routeToHash({ name: "talent", type: "batter" }),
    title: "真實實力估計",
    body: "用 Empirical Bayes 把小樣本的運氣成分收縮回聯盟平均，附 80% 可信區間，揪出被數字騙到的「小樣本陷阱」。",
    tag: "統計推論",
  },
  {
    href: routeToHash({ name: "lineup" }),
    title: "打線實驗室",
    body: "挑 9 名打者對上任一投手，在瀏覽器裡用壘包－出局數馬可夫鏈模擬上千場比賽，並自動搜尋更好的棒次。",
    tag: "Monte Carlo",
  },
  {
    href: routeToHash({ name: "season" }),
    title: "季末戰績模擬",
    body: "以畢氏期望勝率與 log5 對戰機率模擬剩餘賽程 10,000 次，量化每隊的最終勝場區間與奪冠機率。",
    tag: "情境模擬",
  },
  {
    href: routeToHash({ name: "data" }),
    title: "可驗證的資料",
    body: "每個資料檔都以 SHA-256 在瀏覽器端驗證，17 份官方快照的時間軸與品質檢查全部公開。",
    tag: "資料工程",
  },
];

function Dashboard({ league, provenance }: { league: LeagueData; provenance: Provenance }) {
  const leader = [...league.teams].sort((a, b) => b.simulation.first_place_probability - a.simulation.first_place_probability)[0];
  const luckiest = [...league.teams].sort((a, b) => b.luck_wins - a.luck_wins)[0];
  const unluckiest = [...league.teams].sort((a, b) => a.luck_wins - b.luck_wins)[0];
  return (
    <>
      <section className="hero">
        <span className="eyebrow">2026 球季・資料快照 {formatDate(provenance.generated_at)}</span>
        <h1>看穿數字背後的真實實力</h1>
        <p className="lede">
          中職公開數據的分析實驗室：把運氣和實力分開、讓棒次與戰績用模擬說話。所有計算都在這個靜態網站或可重現的 Python 管線裡完成，不需要伺服器、也不呼叫任何外部服務。
        </p>
        <div className="row">
          <a className="btn btn-primary" href={routeToHash({ name: "lineup" })}>
            開始模擬打線
          </a>
          <a className="btn" href={routeToHash({ name: "talent", type: "batter" })}>
            查看真實實力排行
          </a>
        </div>
      </section>

      <section aria-label="聯盟重點" className="kpis">
        <div className="card kpi">
          <span className="stat-label">聯盟平均每場得分</span>
          <span className="stat-value">{league.runs_per_game.toFixed(2)}</span>
          <span className="muted">本段賽季戰績表</span>
        </div>
        {leader && (
          <div className="card kpi">
            <span className="stat-label">奪冠機率最高</span>
            <span className="stat-value">{formatPercent(leader.simulation.first_place_probability)}</span>
            <span className="muted">{leader.team}</span>
          </div>
        )}
        {luckiest && (
          <div className="card kpi">
            <span className="stat-label">運氣最好（比期望多贏）</span>
            <span className="stat-value">{formatSigned(luckiest.luck_wins)}</span>
            <span className="muted">{luckiest.team}</span>
          </div>
        )}
        {unluckiest && (
          <div className="card kpi">
            <span className="stat-label">運氣最差（比期望少贏）</span>
            <span className="stat-value">{formatSigned(unluckiest.luck_wins)}</span>
            <span className="muted">{unluckiest.team}</span>
          </div>
        )}
      </section>

      <section className="grid grid-2">
        <div className="card">
          <h2>戰績與畢氏期望</h2>
          <p className="muted">畢氏期望勝率只看得失分，比勝敗紀錄更能反映球隊真實強度。</p>
          <ScrollRegion label="戰績與畢氏期望">
            <table data-testid="standings">
              <caption className="visually-hidden">各隊戰績、畢氏期望勝率與運氣差</caption>
              <thead>
                <tr>
                  <th scope="col">球隊</th>
                  <th scope="col" className="num">勝-敗</th>
                  <th scope="col" className="num">勝率</th>
                  <th scope="col" className="num">得失分差</th>
                  <th scope="col" className="num">畢氏勝率</th>
                  <th scope="col" className="num">運氣差</th>
                </tr>
              </thead>
              <tbody>
                {league.teams.map((t) => (
                  <tr key={t.team}>
                    <th scope="row">{t.team}</th>
                    <td className="num">
                      {t.wins}-{t.losses}
                      {t.ties ? `-${t.ties}` : ""}
                    </td>
                    <td className="num">{t.win_pct.toFixed(3)}</td>
                    <td className="num">{formatSigned(t.run_diff, 0)}</td>
                    <td className="num">{t.pythag_win_pct.toFixed(3)}</td>
                    <td className="num">{formatSigned(t.luck_wins)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollRegion>
        </div>
        <div className="card">
          <ChartFrame
            title="運氣差：實際勝場 − 期望勝場"
            summary={league.teams.map((t) => `${t.team} ${formatSigned(t.luck_wins)}`).join("，")}
            table={
              <table>
                <thead>
                  <tr>
                    <th scope="col">球隊</th>
                    <th scope="col" className="num">運氣差（勝場）</th>
                  </tr>
                </thead>
                <tbody>
                  {league.teams.map((t) => (
                    <tr key={t.team}>
                      <th scope="row">{t.team}</th>
                      <td className="num">{formatSigned(t.luck_wins)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          >
            <DivergingBars rows={league.teams.map((t) => ({ key: t.team, label: t.team, value: t.luck_wins }))} format={(v) => formatSigned(v)} />
          </ChartFrame>
          <p className="muted small">正值代表比得失分應有的戰績多贏；通常會隨賽季進行回歸。</p>
        </div>
      </section>

      <section aria-labelledby="features-title">
        <h2 id="features-title">四個實驗</h2>
        <div className="grid grid-2 features">
          {FEATURES.map((f) => (
            <a key={f.title} className="card feature" href={f.href}>
              <span className="badge badge-teal">{f.tag}</span>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
              <span className="feature-cta" aria-hidden="true">
                進入 →
              </span>
            </a>
          ))}
        </div>
      </section>
    </>
  );
}

export default function Home() {
  useDocumentTitle("");
  const league = useDataset("league.json");
  const provenance = useDataset("provenance.json");
  return (
    <div className="page stack">
      <Gate<[LeagueData, Provenance]> states={[league, provenance]}>{(l, p) => <Dashboard league={l} provenance={p} />}</Gate>
    </div>
  );
}
