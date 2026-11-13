import { useEffect, useState, type ReactNode } from "react";
import { useDataset, useRoute } from "../app/hooks";
import { DATA_FROZEN } from "../lib/dataPolicy";
import { formatDate, formatDateTime, freshness } from "../lib/format";
import { MODEL_CARD_URL, REPO_URL } from "../lib/links";
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

// Both Ctrl+K and ⌘K open search; show the one this platform's keyboard has.
const SHORTCUT_HINT = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘K" : "Ctrl K";

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
      <header className={route.name === "home" ? "site-header site-header-front" : "site-header"}>
        <div className="site-header-inner">
          <p className="dateline">
            <span className="dateline-ear">非官方分析示範・不是即時戰績</span>
            {/* The edition date is the snapshot date; the slot keeps its height while provenance loads. */}
            <span className="dateline-edition" data-testid="edition-date">
              {provenance.status === "ready" ? (
                <>
                  <time dateTime={provenance.data.generated_at}>{formatDate(provenance.data.generated_at)}</time> 快照版
                  {DATA_FROZEN && <span className="dateline-frozen">・資料已凍結</span>}
                </>
              ) : (
                <span aria-hidden="true">&nbsp;</span>
              )}
            </span>
          </p>
          <a className="brand" href={routeToHash({ name: "home" })}>
            <span className="brand-mark" aria-hidden="true">CPBL</span>
            <span className="brand-text">
              <strong>Scouting Lab</strong>
              <span>中職數據實驗室</span>
            </span>
          </a>
          <div className="site-tools">
            <button type="button" className="btn tool-search" onClick={() => setPaletteOpen(true)} aria-keyshortcuts="Control+K Meta+K /">
              <span aria-hidden="true">⌕</span> <span className="tool-search-text">搜尋球員</span> <kbd aria-hidden="true">{SHORTCUT_HINT}</kbd>
            </button>
          </div>
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
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <footer className="site-footer">
        <div className="site-footer-inner">
          <p className="footer-flag" aria-hidden="true">
            <span className="footer-mark">CPBL</span>
            <span className="footer-name">Scouting Lab</span>
            <span className="footer-sub">中職數據實驗室</span>
          </p>
          <p className="footer-note">
            資料來自 CPBL 官方公開頁面的已驗證快照
            {provenance.status === "ready" && (
              <>
                （擷取於 {formatDateTime(provenance.data.generated_at)} 台北時間，
                <span data-testid="data-age" data-level={DATA_FROZEN ? "frozen" : age?.level}>
                  {DATA_FROZEN
                    ? "資料已凍結，不再更新"
                    : age?.level === "stale"
                      ? `距今 ${age.days} 天；之後的比賽尚未納入`
                      : "近期更新"}
                </span>
                ）
              </>
            )}
            。非 CPBL 官方服務、不是即時戰績；所有估計與模擬皆為分析示範，不構成任何預測保證。
          </p>
          <p className="muted footer-links">
            <span className="footer-links-label">延伸閱讀</span>
            <a href={routeToHash({ name: "data" })}>方法、限制與資料完整性</a>
            <a href={MODEL_CARD_URL} target="_blank" rel="noopener noreferrer">
              模型卡<span className="visually-hidden">（在新分頁開啟 GitHub）</span>
            </a>
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
              原始碼<span className="visually-hidden">（在新分頁開啟 GitHub）</span>
            </a>
          </p>
        </div>
      </footer>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
