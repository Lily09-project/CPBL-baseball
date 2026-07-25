from __future__ import annotations


STREAMLIT_CSS = """
<style>
:root {
  --bg: #071820;
  --bg-deep: #041117;
  --panel: #0e2731;
  --panel-2: #153641;
  --panel-3: #1a4350;
  --ink: #f7f2df;
  --muted: #b4c8cc;
  --muted-strong: #d6e4e4;
  --gold: #e2b65a;
  --gold-soft: #f4d88e;
  --mint: #42d2ae;
  --blue: #78c8ff;
  --red: #ef7773;
  --line: rgba(214, 168, 79, .28);
  --line-soft: rgba(167, 192, 196, .22);
  --focus: #f4d88e;
  color-scheme: dark;
}
html,
body {
  background-color: var(--bg-deep);
  color: var(--ink);
  color-scheme: dark;
}
.stApp {
  background: linear-gradient(180deg, var(--bg-deep) 0%, var(--bg) 52%, #09212a 100%);
  color: var(--ink);
  font-size: 20px;
  font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", system-ui, sans-serif;
  overflow-x: hidden;
  touch-action: manipulation;
  -webkit-tap-highlight-color: rgba(214,168,79,.22);
}
.block-container {
  padding-top: 2.25rem;
  padding-bottom: max(3rem, env(safe-area-inset-bottom));
  padding-left: max(2.25rem, env(safe-area-inset-left));
  padding-right: max(2.25rem, env(safe-area-inset-right));
  max-width: 1480px;
  width: 100%;
  box-sizing: border-box;
}
#cpbl-main {
  scroll-margin-top: 1rem;
}
.skip-link {
  position: fixed;
  top: max(.75rem, env(safe-area-inset-top));
  left: max(.75rem, env(safe-area-inset-left));
  z-index: 100;
  padding: .65rem .9rem;
  border: 2px solid var(--focus);
  border-radius: 8px;
  background: var(--bg-deep);
  color: var(--ink) !important;
  font-weight: 700;
  text-decoration: none;
  transform: translateY(-180%);
  transition: transform 180ms ease;
}
.skip-link:focus-visible {
  transform: translateY(0);
}
.sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}
h1, h2, h3 {
  color: var(--ink);
  letter-spacing: 0 !important;
  text-wrap: balance;
}
h1 { font-size: 2.85rem !important; line-height: 1.18 !important; margin-bottom: .8rem !important; }
h2 {
  font-size: 2.2rem !important;
  line-height: 1.24 !important;
  margin-top: 2rem !important;
  margin-bottom: .9rem !important;
  padding-left: 14px;
  border-left: 4px solid var(--gold);
}
h3 { font-size: 1.55rem !important; line-height: 1.32 !important; }
p, span, label, div { color: inherit; }
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
  font-size: 1.16rem;
  line-height: 1.68;
  overflow-wrap: anywhere;
  text-wrap: pretty;
}
[data-testid="stWidgetLabel"] p,
[data-testid="stRadio"] label,
[data-testid="stSelectbox"] label {
  font-size: 1.14rem !important;
}
[data-testid="stDataFrame"] {
  font-size: 1.08rem;
  margin: .4rem 0 .75rem 0;
  max-width: 100%;
  overflow-x: auto;
  font-variant-numeric: tabular-nums;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: rgba(4, 17, 23, .34);
}
[data-testid="stHorizontalBlock"] {
  gap: 1.75rem;
  align-items: stretch;
  margin-bottom: 1.4rem;
}
[data-testid="column"],
[data-testid="stColumn"] {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
[data-testid="stSidebar"] {
  background: #05141a;
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] > div:first-child {
  padding: 1.15rem .9rem 1.5rem .9rem;
}
.sidebar-brand {
  padding: 8px 4px 18px 4px;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--line-soft);
}
.sidebar-brand-title {
  color: var(--gold-soft);
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.25;
}
.sidebar-brand-subtitle,
.sidebar-nav-label,
.sidebar-status {
  color: var(--muted);
  font-size: .92rem;
  line-height: 1.45;
}
.sidebar-nav-label {
  color: var(--muted-strong);
  font-weight: 700;
  margin: 0 0 .45rem .2rem;
}
.sidebar-status {
  border-top: 1px solid var(--line-soft);
  margin-top: 1rem;
  padding: .9rem .2rem 0 .2rem;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > div {
  gap: .4rem;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  min-height: 48px;
  padding: .65rem .75rem;
  border: 1px solid transparent;
  border-radius: 8px;
  transition: background-color 180ms ease, border-color 180ms ease, color 180ms ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: rgba(120, 200, 255, .08);
  border-color: rgba(120, 200, 255, .22);
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: rgba(226, 182, 90, .14);
  border-color: rgba(226, 182, 90, .48);
  color: var(--gold-soft);
}
[data-testid="stMetric"] {
  background: linear-gradient(180deg, rgba(21, 54, 65, .98), rgba(9, 29, 37, .98));
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px 20px;
  margin-bottom: 18px;
  min-height: 132px;
  box-sizing: border-box;
  box-shadow: 0 10px 22px rgba(0, 0, 0, .18);
}
[data-testid="stMetricLabel"] p { color: var(--muted); font-size: 1.12rem; line-height: 1.35; }
[data-testid="stMetricValue"] {
  color: var(--gold);
  font-size: 2.24rem;
  line-height: 1.15;
  white-space: normal;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] {
  display: none;
}
.metric-grid,
.cpbl-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
  margin: 20px 0 28px 0;
  align-items: stretch;
  grid-auto-rows: 1fr;
}
.metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}
.metric-card {
  position: relative;
  background: linear-gradient(180deg, rgba(21, 54, 65, .98), rgba(9, 29, 37, .98));
  border: 1px solid var(--line);
  border-radius: 8px;
  min-height: 136px;
  padding: 16px 18px 18px 18px;
  box-sizing: border-box;
  box-shadow: 0 10px 22px rgba(0, 0, 0, .18);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.metric-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--gold);
  border-radius: 8px 0 0 8px;
}
.metric-index {
  color: var(--blue);
  font-size: .82rem;
  font-weight: 700;
  letter-spacing: 0;
  font-variant-numeric: tabular-nums;
}
.metric-card .metric-label {
  color: var(--muted);
  font-size: 1.06rem;
  line-height: 1.35;
}
.metric-card .metric-value {
  color: var(--gold-soft);
  font-size: 2.18rem;
  line-height: 1.15;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}
.cpbl-card {
  background: linear-gradient(180deg, rgba(16, 42, 51, .95), rgba(9, 28, 36, .95));
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 22px 24px;
  min-height: 176px;
  margin: 0 0 24px 0;
  box-sizing: border-box;
  box-shadow: 0 12px 26px rgba(0, 0, 0, .20);
  overflow-wrap: anywhere;
}
.cpbl-card-grid .cpbl-card {
  margin: 0;
  height: 100%;
}
.cpbl-card h3 { margin: 0 0 12px 0; }
.cpbl-card .card-heading {
  margin: 0 0 12px 0 !important;
  padding: 0 !important;
  border: 0 !important;
  font-size: 1.55rem !important;
  line-height: 1.32 !important;
}
.cpbl-card p { font-size: 1.1rem; line-height: 1.6; }
.equal-card {
  min-height: 204px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}
.source-card,
.player-hero {
  min-height: 0;
}
.source-ribbon,
.page-kicker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  color: var(--muted-strong);
  font-size: .98rem;
  line-height: 1.45;
  margin: 0 0 .85rem 0;
}
.source-ribbon {
  background: rgba(66, 210, 174, .08);
  border: 1px solid rgba(66, 210, 174, .28);
  border-radius: 8px;
  padding: .75rem .9rem;
}
.source-ribbon strong,
.page-kicker strong {
  color: var(--mint);
}
.page-kicker {
  border-bottom: 1px solid var(--line-soft);
  padding-bottom: .85rem;
  margin-bottom: 1.1rem;
}
.page-kicker .page-date {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.source-card p,
.player-hero p {
  margin: 0 0 10px 0;
}
.player-hero h2 {
  margin: 0 0 8px 0;
}
.cpbl-badge {
  display: inline-block;
  background: rgba(62,199,164,.16);
  border: 1px solid rgba(62,199,164,.48);
  color: #dffcf4;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 1.05rem;
}
.table-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: .75rem;
  color: var(--muted);
  font-size: .92rem;
  margin: .4rem 0 .2rem 0;
}
.table-toolbar-label {
  color: var(--muted-strong);
  font-weight: 700;
}
.table-toolbar-hint {
  color: var(--blue);
  font-variant-numeric: tabular-nums;
}
.warning-note {
  background: rgba(239,111,108,.14);
  border-left: 4px solid var(--red);
  padding: 14px 16px;
  border-radius: 6px;
  font-size: 1.1rem;
  line-height: 1.65;
}
a { color: #f1c86c !important; }
a:hover { color: #ffe19a !important; text-decoration: underline; }
[data-testid="stMarkdownContainer"] a:not(.skip-link) {
  text-decoration: underline;
  text-underline-offset: .18em;
}
button:focus-visible, [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible {
  outline: 2px solid var(--focus) !important;
  outline-offset: 2px !important;
}
.stButton button, .stDownloadButton button {
  min-height: 48px;
  border-radius: 8px;
  font-size: 1.08rem !important;
  transition: border-color 180ms ease, background-color 180ms ease, transform 180ms ease;
  touch-action: manipulation;
  cursor: pointer;
}
.stDownloadButton {
  display: flex;
  justify-content: flex-end;
  margin: 0 0 1.15rem 0;
}
.stDownloadButton button {
  background: rgba(120, 200, 255, .08);
  border: 1px solid rgba(120, 200, 255, .35);
  color: var(--muted-strong);
  min-width: 132px;
}
.stDownloadButton button:hover {
  background: rgba(120, 200, 255, .16);
  border-color: var(--blue);
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
  min-height: 48px;
  font-size: 1.05rem;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
  background: rgba(4, 17, 23, .48);
  border-color: var(--line-soft);
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
[data-testid="stNumberInput"] input:hover {
  border-color: rgba(120, 200, 255, .55);
}
select,
input,
textarea {
  background-color: var(--bg-deep);
  color: var(--ink);
  caret-color: var(--gold-soft);
}
select:disabled,
input:disabled,
textarea:disabled,
button:disabled,
[aria-disabled="true"] {
  cursor: not-allowed !important;
  opacity: .48 !important;
  transform: none !important;
}
[data-testid="stSelectbox"]:focus-within,
[data-testid="stNumberInput"]:focus-within {
  border-radius: 8px;
  box-shadow: 0 0 0 2px rgba(244, 216, 142, .26);
}
[data-testid="stAlert"] {
  border-radius: 8px;
  border: 1px solid var(--line-soft);
  background: rgba(16, 42, 51, .78);
  color: var(--muted-strong);
}
[data-testid="stPlotlyChart"] {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: rgba(4, 17, 23, .28);
  padding: 4px;
  box-sizing: border-box;
  min-width: 0;
  overflow: hidden;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: .35rem;
  border-bottom: 1px solid var(--line-soft);
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  min-height: 48px;
  padding: .55rem .95rem;
  color: var(--muted);
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--gold-soft);
  border-bottom-color: var(--gold);
}
[data-testid="stRadio"] label,
[data-testid="stTabs"] button {
  min-height: 44px;
}
[data-testid="stTabs"] button {
  cursor: pointer;
  touch-action: manipulation;
}
.stButton button:hover, .stDownloadButton button:hover {
  border-color: var(--gold);
  transform: translateY(-1px);
}
.stButton button:active, .stDownloadButton button:active {
  background: rgba(226, 182, 90, .18);
  transform: translateY(0);
}
@media (max-width: 1100px) and (min-width: 721px) {
  .cpbl-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
@media (max-width: 720px) {
  .stApp { font-size: 18.5px; }
  .block-container {
    padding-top: 1.25rem;
    padding-bottom: max(2rem, env(safe-area-inset-bottom));
    padding-left: max(1rem, env(safe-area-inset-left));
    padding-right: max(1rem, env(safe-area-inset-right));
  }
  .page-kicker,
  .source-ribbon {
    align-items: flex-start;
    flex-direction: column;
    gap: .3rem;
  }
  h1 { font-size: 2.15rem !important; }
  h2 { font-size: 1.75rem !important; }
  .metric-grid,
  .cpbl-card-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .metric-card {
    min-height: 116px;
  }
  .equal-card { height: auto; min-height: 168px; }
  [data-testid="stMetric"] { min-height: 116px; }
  [data-testid="stHorizontalBlock"] { gap: 1rem; }
  .stDownloadButton { justify-content: stretch; }
  .stDownloadButton button { width: 100%; }
}
</style>
"""
