import { useEffect, useState, type ReactNode } from "react";
import { useDataset, useRoute } from "../app/hooks";
import { formatDate, freshness } from "../lib/format";
import { routeToHash, type Route } from "../lib/router";
import { CommandPalette } from "./CommandPalette";
import "./Shell.css";

const NAV: { route: Route; label: string; match: Route["name"][] }[] = [
  { route: { name: "home" }, label: "聯盟脈動", match: ["home"] },
  { route: { name: "talent", type: "batter" }, label: "真實實力", match: ["talent", "player", "compare"] },
  { route: { name: "lineup" }, label: "打線實驗室", match: ["lineup"] },
  { route: { name: "season" }, label: "季末模擬", match: ["season"] },
  { route: { name: "data" }, label: "資料可信度", match: ["data"] },
];

export function Shell({ children }: { children: ReactNode }) {
  const [route] = useRoute();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const provenance = useDataset("provenance.json");

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "SELECT" || target.tagName === "TEXTAREA");
      if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const age = provenance.status === "ready" ? freshness(provenance.data.generated_at, new Date()) : null;

  return (
    <>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>
        跳到主要內容
      </a>
      <header className="site-header">
        <div className="site-header-inner">
          <a className="brand" href={routeToHash({ name: "home" })}>
            <span className="brand-mark" aria-hidden="true">CPBL</span>
            <span className="brand-text">
              <strong>Scouting Lab</strong>
              <span>中職數據實驗室</span>
            </span>
          </a>
          <nav aria-label="主要頁面" className="site-nav">
            <ul>
              {NAV.map((item) => (
                <li key={item.label}>
                  <a href={routeToHash(item.route)} aria-current={item.match.includes(route.name) ? "page" : undefined}>
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
          <div className="site-tools">
            <button type="button" className="btn tool-search" onClick={() => setPaletteOpen(true)} aria-keyshortcuts="Control+K Meta+K /">
              <span aria-hidden="true">⌕</span> <span className="tool-search-text">搜尋球員</span> <kbd aria-hidden="true">⌘K</kbd>
            </button>
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <footer className="site-footer">
        <div className="site-footer-inner">
          <p>
            資料來自 CPBL 官方公開頁面的已驗證快照
            {provenance.status === "ready" && (
              <>
                （{formatDate(provenance.data.generated_at)}，
                <span data-testid="data-age" data-level={age?.level}>
                  {age?.level === "stale" ? `已 ${age.days} 天未更新` : "近期更新"}
                </span>
                ）
              </>
            )}
            。非 CPBL 官方服務、不是即時戰績；所有估計與模擬皆為分析示範，不構成任何預測保證。
          </p>
          <p className="muted">
            <a href={routeToHash({ name: "data" })}>方法、限制與資料完整性</a>
          </p>
        </div>
      </footer>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
