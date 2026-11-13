import { useDataset, useDocumentTitle } from "../app/hooks";
import { ChartFrame, DivergingBars } from "../components/chartFrame";
import { ScrollRegion } from "../components/ScrollRegion";
import { ErrorState, Loading } from "../components/States";
import { formatDate, formatDateTime, formatPercent, formatSigned } from "../lib/format";
import { leagueHeadline } from "../lib/insights";
import { MODEL_CARD_URL } from "../lib/links";
import { routeToHash } from "../lib/router";
import type { LeagueData, Provenance } from "../lib/types";
import "./Home.css";

/** The inside pages, told as the front page's secondary stories. */
function stories(league: LeagueData, provenance: Provenance) {
  return [
    {
      href: routeToHash({ name: "talent", type: "batter" }),
      step: "01",
      section: "真實實力",
      title: "真實實力估計",
      body: "用 Empirical Bayes 把小樣本的運氣成分收縮回聯盟平均，附 80% 可信區間，揪出被數字騙到的「小樣本陷阱」。",
      tag: "統計推論",
    },
    {
      href: routeToHash({ name: "lineup" }),
      step: "02",
      section: "打線實驗室",
      title: "打線實驗室",
      body: "挑 9 名打者對上任一投手，在瀏覽器裡用壘包－出局數馬可夫鏈模擬上千場比賽，並自動搜尋更好的棒次。",
      tag: "Monte Carlo",
    },
    {
      href: routeToHash({ name: "season" }),
      step: "03",
      section: "季末模擬",
      title: "季末戰績模擬",
      body: `從快照當時的戰績出發，以畢氏期望勝率與 log5 對戰機率模擬剩餘賽程 ${league.simulations.toLocaleString()} 次，量化每隊的最終勝場區間與拿下半季第一的機率。`,
      tag: "情境模擬",
    },
    {
      href: routeToHash({ name: "data" }),
      step: "04",
      section: "資料可信度",
      title: "可驗證的資料",
      body: `每個資料檔都以 SHA-256 在瀏覽器端驗證，${provenance.snapshots.length} 份官方快照的時間軸與品質檢查全部公開。`,
      tag: "資料工程",
    },
  ];
}

/** The lead story: one sentence a judge can repeat, computed from the snapshot. */
function LeadStory({ league, provenance }: { league: LeagueData; provenance: Provenance }) {
  const headline = leagueHeadline(league);
  const passed = provenance.snapshots.filter((s) => s.quality_status === "pass").length;
  return (
    <article className="lead" aria-labelledby="lead-title" data-testid="headline-insight">
      <p className="lead-kicker">
        <span className="lead-kicker-tag">快照焦點</span>
        以 {formatDate(provenance.generated_at)} 快照戰績推演
      </p>
      {headline ? (
        <>
          <h2 id="lead-title" className="lead-headline">
            <span className="phrase">{headline.leader.team}</span>{" "}
            <span className="phrase">
              <span className="lead-figure">{formatPercent(headline.leader.simulation.first_place_probability)}</span> 機率
            </span>
            <span className="phrase">拿下半季第一</span>
          </h2>
          <p className="lead-deck">
            {headline.leader.team}在快照當時 {headline.leader.simulation.current_wins} 勝、剩 {headline.leader.simulation.games_remaining} 場。以畢氏期望勝率作為各隊真實強度、把剩餘賽程模擬{" "}
            {headline.simulations.toLocaleString()} 次，其中 <strong>{formatPercent(headline.leader.simulation.first_place_probability)}</strong> 的模擬由{headline.leader.team}拿下半季第一。
          </p>
          <ul className="lead-facts">
            {headline.runnerUp && (
              <li>
                <span className="lead-fact-label">最接近的對手</span>
                {headline.runnerUp.team}（{formatPercent(headline.runnerUp.simulation.first_place_probability)}）
              </li>
            )}
            {headline.shutOut.length > 0 && (
              <li>
                <span className="lead-fact-label">與第一無緣</span>
                另有 {headline.shutOut.length} 隊在所有模擬中都沒拿到第一
              </li>
            )}
            {headline.unluckiest && (
              <li>
                <span className="lead-fact-label">運氣最差</span>
                {headline.unluckiest.team}比得失分推算的戰績少贏 {Math.abs(headline.unluckiest.luck_wins).toFixed(1)} 場
              </li>
            )}
          </ul>
        </>
      ) : (
        <h2 id="lead-title" className="lead-headline">
          快照焦點
        </h2>
      )}
      <p className="lead-source">
        資料：CPBL 官方公開頁面快照（擷取於 {formatDateTime(provenance.generated_at)} 台北時間，{passed}/{provenance.snapshots.length} 份快照通過品質檢查）。快照之後的比賽沒有納入。非 CPBL 官方服務。
        <br />
        <a href={routeToHash({ name: "data" })}>方法與資料驗證</a>
        <span aria-hidden="true">・</span>
        <a href={MODEL_CARD_URL} target="_blank" rel="noopener noreferrer">
          模型卡<span className="visually-hidden">（在新分頁開啟 GitHub）</span>
        </a>
      </p>
    </article>
  );
}

/** Standings in a classic newspaper box: tight rows, figures right-aligned. */
function StandingsBox({ league, provenance }: { league: LeagueData; provenance: Provenance }) {
  return (
    <section className="box standings-box" aria-labelledby="standings-title">
      <h2 id="standings-title" className="box-title">
        戰績與畢氏期望
        <span className="box-title-note">截至 {formatDate(provenance.generated_at)}</span>
      </h2>
      <ScrollRegion label="戰績與畢氏期望">
        <table data-testid="standings" className="box-score">
          <caption className="visually-hidden">各隊戰績、畢氏期望勝率與實際減期望勝場</caption>
          <thead>
            <tr>
              <th scope="col">球隊</th>
              <th scope="col" className="num">勝-敗</th>
              <th scope="col" className="num">勝率</th>
              <th scope="col" className="num">得失分差</th>
              <th scope="col" className="num">畢氏勝率</th>
              <th scope="col" className="num">實際−期望</th>
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
      <p className="box-note">
        畢氏期望勝率只看得失分，比勝敗紀錄更能反映球隊真實強度；「實際−期望」是實際勝場減去期望勝場，正值代表比得失分應有的戰績多贏（運氣好）。
      </p>
    </section>
  );
}

function FrontPage({ league, provenance }: { league: LeagueData; provenance: Provenance }) {
  const headline = leagueHeadline(league);
  const leader = headline?.leader;
  const luckiest = [...league.teams].sort((a, b) => b.luck_wins - a.luck_wins)[0];
  const unluckiest = [...league.teams].sort((a, b) => a.luck_wins - b.luck_wins)[0];
  return (
    <>
      <div className="front-top">
        <LeadStory league={league} provenance={provenance} />
        <StandingsBox league={league} provenance={provenance} />
      </div>

      <section aria-label="聯盟重點" className="kpis">
        <div className="kpi">
          <span className="stat-label">聯盟平均每場得分</span>
          <span className="stat-value">{league.runs_per_game.toFixed(2)}</span>
          <span className="muted small">截至 {formatDate(provenance.generated_at)} 的半季戰績</span>
        </div>
        {leader && (
          <div className="kpi">
            <span className="stat-label">半季第一機率最高</span>
            <span className="stat-value">{formatPercent(leader.simulation.first_place_probability)}</span>
            <span className="muted small">{leader.team}</span>
          </div>
        )}
        {luckiest && (
          <div className="kpi">
            <span className="stat-label">運氣最好（比期望多贏）</span>
            <span className="stat-value">{formatSigned(luckiest.luck_wins)}</span>
            <span className="muted small">{luckiest.team}</span>
          </div>
        )}
        {unluckiest && (
          <div className="kpi">
            <span className="stat-label">運氣最差（比期望少贏）</span>
            <span className="stat-value">{formatSigned(unluckiest.luck_wins)}</span>
            <span className="muted small">{unluckiest.team}</span>
          </div>
        )}
      </section>

      <section aria-labelledby="features-title" className="stories">
        <div className="stories-head">
          <h2 id="features-title">從哪裡開始？</h2>
          <p className="muted">依序看 01 → 03 三個實驗，最後到 04 檢查資料怎麼來、怎麼驗證。</p>
        </div>
        <ol className="story-list">
          {stories(league, provenance).map((s) => (
            <li key={s.title}>
              <a className="story" href={s.href}>
                <span className="story-kicker">
                  <span className="story-step" aria-hidden="true">
                    {s.step}
                  </span>
                  {s.tag}
                </span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
                <span className="story-cta" aria-hidden="true">
                  見「{s.section}」版 →
                </span>
              </a>
            </li>
          ))}
        </ol>
      </section>

      <section className="front-chart" aria-labelledby="luck-title">
        <div className="front-chart-copy">
          <p className="eyebrow">數據圖解</p>
          <h2 id="luck-title">誰的戰績比得失分好看？</h2>
          <p className="muted">
            長條是每隊「實際勝場 − 畢氏期望勝場」。綠色向右代表比得失分應有的戰績多贏（運氣好），黑色向左代表少贏；這種差距通常會隨賽季進行回歸。
          </p>
        </div>
        <div className="front-chart-figure">
          <ChartFrame
            title="運氣：實際勝場 − 期望勝場（正值＝多贏）"
            summary={league.teams.map((t) => `${t.team} ${formatSigned(t.luck_wins)}`).join("，")}
            table={
              <table>
                <thead>
                  <tr>
                    <th scope="col">球隊</th>
                    <th scope="col" className="num">實際−期望（勝場）</th>
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
        </div>
      </section>
    </>
  );
}

export default function Home() {
  useDocumentTitle("");
  const league = useDataset("league.json");
  const provenance = useDataset("provenance.json");
  const failed = league.status === "error" ? league : provenance.status === "error" ? provenance : null;
  return (
    <div className="page front">
      {/* The banner is static, so the largest headline paints before any data arrives. */}
      <section className="banner" aria-labelledby="home-title">
        <div className="banner-head">
          <p className="eyebrow">中職公開數據・非官方分析實驗室</p>
          <h1 id="home-title">
            <span className="phrase">看穿數字背後</span>
            <span className="phrase">的真實實力</span>
          </h1>
        </div>
        <div className="banner-deck">
          <p className="lede">用中職公開數據回答三個問題：誰的好成績只是運氣？棒次怎麼排最會得分？從快照當時的戰績推演，誰最可能拿下半季第一？</p>
          <div className="row">
            <a className="btn btn-primary" href={routeToHash({ name: "lineup" })}>
              開始模擬打線
            </a>
            <a className="btn" href={routeToHash({ name: "talent", type: "batter" })}>
              查看真實實力排行
            </a>
          </div>
        </div>
      </section>
      {failed && failed.status === "error" ? (
        <ErrorState error={failed.error} />
      ) : league.status === "ready" && provenance.status === "ready" ? (
        <FrontPage league={league.data} provenance={provenance.data} />
      ) : (
        // Hold the lead story's space so nothing in the first screen moves when the data lands.
        <div className="front-pending">
          <Loading />
        </div>
      )}
    </div>
  );
}
