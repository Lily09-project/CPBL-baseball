import { useContext, useEffect, useState } from "react";
import { LoaderContext, useDataset, useDocumentTitle } from "../app/hooks";
import { ChartFrame, Histogram } from "../components/charts";
import { ScrollRegion } from "../components/ScrollRegion";
import { Gate } from "../components/States";
import { formatDate } from "../lib/format";
import type { DataFiles, LeagueData, Manifest, Provenance, SimInputs } from "../lib/types";
import "./DataTrust.css";

const FILES: (keyof DataFiles)[] = ["league.json", "players.json", "player-details.json", "sim.json", "provenance.json"];

type Check = { file: string; status: "pending" | "ok" | "failed"; hash?: string };

function useIntegrityChecks(): { manifest: Manifest | null; checks: Check[] } {
  const loader = useContext(LoaderContext);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [checks, setChecks] = useState<Check[]>(FILES.map((file) => ({ file, status: "pending" })));
  useEffect(() => {
    if (!loader) return;
    let alive = true;
    loader.manifest().then((m) => alive && setManifest(m));
    FILES.forEach((file, i) => {
      loader.load(file).then(
        () => alive && setChecks((prev) => prev.map((c, j) => (j === i ? { ...c, status: "ok" } : c))),
        () => alive && setChecks((prev) => prev.map((c, j) => (j === i ? { ...c, status: "failed" } : c))),
      );
    });
    return () => {
      alive = false;
    };
  }, [loader]);
  return { manifest, checks: checks.map((c) => ({ ...c, hash: manifest?.files[c.file] })) };
}

function Trust({ provenance, league, sim }: { provenance: Provenance; league: LeagueData; sim: SimInputs }) {
  const { manifest, checks } = useIntegrityChecks();
  const passed = checks.filter((c) => c.status === "ok").length;
  const snapshots = provenance.snapshots;
  return (
    <div className="stack">
      <header>
        <span className="eyebrow">資料工程</span>
        <h1>資料可信度</h1>
        <p className="lede">這個網站的每一個數字都能追溯到 CPBL 官方頁面的某一份快照，並在你的瀏覽器裡重新驗證。</p>
      </header>

      <section className="grid grid-3">
        <div className="card">
          <span className="stat-label">發布版本</span>
          <p className="mono" data-testid="release-id">
            {provenance.release_id}
          </p>
          <span className="muted small">快照 {provenance.snapshot_id}</span>
        </div>
        <div className="card">
          <span className="stat-label">資料品質檢查</span>
          <p className="stat-value quality" data-status={provenance.quality_status}>
            {provenance.quality_status === "pass" ? "通過" : provenance.quality_status}
          </p>
          <span className="muted small">產生於 {formatDate(provenance.generated_at)}</span>
        </div>
        <div className="card">
          <span className="stat-label">瀏覽器端完整性驗證</span>
          <p className="stat-value" data-testid="integrity-summary">
            {passed}/{checks.length}
          </p>
          <span className="muted small">以 Web Crypto 重新計算 SHA-256 並與 manifest 比對</span>
        </div>
      </section>

      <section className="card">
        <h2>完整性檢查</h2>
        <ScrollRegion label="完整性檢查結果">
          <table data-testid="integrity-table">
            <thead>
              <tr>
                <th scope="col">檔案</th>
                <th scope="col">狀態</th>
                <th scope="col">SHA-256（manifest {manifest?.schema_version ?? "—"}）</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((c) => (
                <tr key={c.file}>
                  <th scope="row" className="mono">
                    {c.file}
                  </th>
                  <td>
                    <span className={`badge check-${c.status}`}>{c.status === "ok" ? "✓ 相符" : c.status === "failed" ? "✕ 不符" : "驗證中"}</span>
                  </td>
                  <td className="mono hash">{c.hash ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollRegion>
      </section>

      <section className="grid grid-2">
        <div className="card">
          <ChartFrame
            title={`${snapshots.length} 份官方快照的資料異動列數`}
            summary={`從 ${formatDate(snapshots[0]?.captured_at ?? provenance.generated_at)} 到 ${formatDate(snapshots.at(-1)?.captured_at ?? provenance.generated_at)}`}
            table={
              <table data-testid="snapshot-table">
                <thead>
                  <tr>
                    <th scope="col">擷取時間</th>
                    <th scope="col">品質</th>
                    <th scope="col" className="num">總列數</th>
                    <th scope="col" className="num">新增</th>
                    <th scope="col" className="num">移除</th>
                    <th scope="col" className="num">異動</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshots.map((s) => (
                    <tr key={s.snapshot_id}>
                      <th scope="row">{s.captured_at.replace("T", " ").slice(0, 16)}</th>
                      <td>{s.quality_status}</td>
                      <td className="num">{s.total_rows}</td>
                      <td className="num">{s.added_rows}</td>
                      <td className="num">{s.removed_rows}</td>
                      <td className="num">{s.changed_rows}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          >
            <Histogram counts={snapshots.map((s) => s.changed_rows)} labels={snapshots.map((s) => s.captured_at.slice(5, 10))} height={200} labelEvery={4} />
          </ChartFrame>
        </div>
        <div className="card">
          <h2>官方來源</h2>
          <ul className="sources">
            {provenance.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noopener noreferrer">
                  {s.label}
                  <span className="visually-hidden">（在新分頁開啟）</span>
                </a>
              </li>
            ))}
          </ul>
          <h3>上游檔案指紋</h3>
          <ul className="artifacts">
            {provenance.artifacts.map((a) => (
              <li key={a.path}>
                <span className="mono">{a.path}</span>
                <span className="muted small mono">{a.sha256.slice(0, 16)}…</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="card method" id="methods">
        <h2>方法與限制</h2>
        <h3>真實實力（Empirical Bayes）</h3>
        <p>
          每個比率視為二項分布結果，以達門檻球員的分布用動差法估計 Beta 先驗，並扣除二項抽樣雜訊；後驗平均與 80% 等尾可信區間由自行實作的不完全 Beta 函數計算。打者上壘率的分子由官方上壘率乘以打席推回，因此包含觸身球。
        </p>
        <h3>打線模擬</h3>
        <p>
          事件機率先加 {sim.stabilizers.batter_pa} 個聯盟平均打席（投手 {sim.stabilizers.pitcher_bf} 名打者）收縮，再以廣義 log5 結合投手；跑壘推進使用固定機率。不模擬守備、盜壘、換投、延長賽與球場因素。
        </p>
        <h3>季末模擬</h3>
        <p>
          以畢氏期望勝率（指數 {league.pythagorean_exponent}）作為真實強度，log5 計算單場勝率，剩餘賽程依剩餘場數配對，模擬 {league.simulations.toLocaleString()} 次（種子 {league.seed}）。
        </p>
        <h3>不應該怎麼用</h3>
        <ul>
          <li>不是官方數據服務，也不是即時戰績；資料停在快照時間。</li>
          <li>收縮後的估計是描述性的「目前最可信的值」，不是下個月表現的預測。</li>
          <li>模擬結果適合比較不同選擇的相對差異，不適合拿來下注或做商業決策。</li>
        </ul>
      </section>
    </div>
  );
}

export default function DataTrust() {
  useDocumentTitle("資料可信度");
  const provenance = useDataset("provenance.json");
  const league = useDataset("league.json");
  const sim = useDataset("sim.json");
  return (
    <div className="page">
      <Gate<[Provenance, LeagueData, SimInputs]> states={[provenance, league, sim]}>{(p, l, s) => <Trust provenance={p} league={l} sim={s} />}</Gate>
    </div>
  );
}
