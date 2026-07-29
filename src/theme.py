from __future__ import annotations


STREAMLIT_CSS = """
<style>
:root {
  --bg: #08171c;
  --bg-deep: #051015;
  --surface: #0d2329;
  --surface-raised: #122d34;
  --surface-muted: #0a1d23;
  --ink: #f1f3ed;
  --muted: #9db0b5;
  --muted-strong: #d3dfdd;
  --accent: #d85a52;
  --accent-soft: #f08a78;
  --gold: #d3a354;
  --blue: #79b6bc;
  --mint: #65b995;
  --red: #e87d72;
  --line: rgba(211, 163, 84, .34);
  --line-soft: rgba(157, 176, 181, .24);
  --focus: #f0cf7a;
  color-scheme: dark;
}

html,
body {
  background: var(--bg-deep);
  color: var(--ink);
  color-scheme: dark;
}

.stApp {
  background: var(--bg-deep);
  color: var(--ink);
  font-size: 20px;
  font-family: "Noto Sans TC", "Microsoft JhengHei", "PingFang TC", system-ui, sans-serif;
  overflow-x: hidden;
  touch-action: manipulation;
  -webkit-tap-highlight-color: rgba(216, 90, 82, .2);
}

.block-container {
  padding-top: 2rem;
  padding-bottom: max(3rem, env(safe-area-inset-bottom));
  padding-left: max(2rem, env(safe-area-inset-left));
  padding-right: max(2rem, env(safe-area-inset-right));
  max-width: 1440px;
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
  border-radius: 5px;
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

h1,
h2,
h3 {
  color: var(--ink);
  letter-spacing: 0 !important;
  text-wrap: balance;
}

h1 {
  font-size: 2.7rem !important;
  line-height: 1.18 !important;
  margin-bottom: .8rem !important;
  font-weight: 750 !important;
}

h2 {
  font-size: 2rem !important;
  line-height: 1.24 !important;
  margin-top: 2rem !important;
  margin-bottom: .9rem !important;
  padding-left: 12px;
  border-left: 3px solid var(--accent);
  font-weight: 700 !important;
}

h3 {
  font-size: 1.45rem !important;
  line-height: 1.32 !important;
  font-weight: 700 !important;
}

p,
span,
label,
div {
  color: inherit;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
  font-size: 1.12rem;
  line-height: 1.65;
  overflow-wrap: anywhere;
  text-wrap: pretty;
}

[data-testid="stWidgetLabel"] p,
[data-testid="stRadio"] label,
[data-testid="stSelectbox"] label {
  font-size: 1.1rem !important;
}

[data-testid="stDataFrame"] {
  font-size: 1.06rem;
  margin: .5rem 0 .75rem 0;
  max-width: 100%;
  overflow-x: auto;
  font-variant-numeric: tabular-nums;
  border: 1px solid var(--line-soft);
  border-radius: 5px;
  background: var(--surface-muted);
}

[data-testid="stHorizontalBlock"] {
  gap: 1.5rem;
  align-items: stretch;
  margin-bottom: 1.35rem;
}

[data-testid="column"],
[data-testid="stColumn"] {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

[data-testid="stSidebar"] {
  background: #061318;
  border-right: 1px solid var(--line-soft);
}

[data-testid="stSidebar"] > div:first-child {
  padding: 1rem .85rem 1.5rem .85rem;
}

.sidebar-brand {
  padding: 7px 4px 16px 4px;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--line-soft);
}

.sidebar-brand-title {
  color: var(--ink);
  font-size: 1.28rem;
  font-weight: 750;
  line-height: 1.25;
}

.sidebar-brand-subtitle,
.sidebar-nav-label,
.sidebar-status {
  color: var(--muted);
  font-size: .9rem;
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
  gap: .35rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
  min-height: 48px;
  padding: .62rem .7rem;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: background-color 180ms ease, border-color 180ms ease, color 180ms ease;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: rgba(121, 182, 188, .08);
  border-color: rgba(121, 182, 188, .34);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: rgba(216, 90, 82, .16);
  border-color: rgba(216, 90, 82, .62);
  color: var(--ink);
}

[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 5px;
  padding: 17px 19px;
  margin-bottom: 18px;
  min-height: 128px;
  box-sizing: border-box;
  box-shadow: none;
}

[data-testid="stMetricLabel"] p {
  color: var(--muted);
  font-size: 1.08rem;
  line-height: 1.35;
}

[data-testid="stMetricValue"] {
  color: var(--gold);
  font-size: 2.2rem;
  line-height: 1.15;
  white-space: normal;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
}

[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] {
  display: none;
}

.metric-grid,
.cpbl-card-grid,
.workflow-grid {
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
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-top: 3px solid var(--accent);
  border-radius: 5px;
  min-height: 124px;
  padding: 15px 18px 17px 18px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-card .metric-label {
  color: var(--muted);
  font-size: 1.04rem;
  line-height: 1.35;
}

.metric-card .metric-value {
  color: var(--ink);
  font-size: 2.05rem;
  line-height: 1.15;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
}

.cpbl-card {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 5px;
  padding: 20px 22px;
  min-height: 166px;
  margin: 0 0 20px 0;
  box-sizing: border-box;
  overflow-wrap: anywhere;
}

.cpbl-card-grid .cpbl-card {
  margin: 0;
  height: 100%;
}

.cpbl-card h3 {
  margin: 0 0 12px 0;
}

.cpbl-card .card-heading {
  margin: 0 0 12px 0 !important;
  padding: 0 !important;
  border: 0 !important;
  font-size: 1.42rem !important;
  line-height: 1.32 !important;
}

.cpbl-card p {
  font-size: 1.08rem;
  line-height: 1.6;
}

.equal-card {
  min-height: 190px;
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
  font-size: .96rem;
  line-height: 1.45;
  margin: 0 0 .85rem 0;
}

.source-ribbon {
  background: var(--surface-muted);
  border: 1px solid rgba(101, 185, 149, .42);
  border-left: 3px solid var(--mint);
  border-radius: 4px;
  padding: .72rem .88rem;
}

.source-ribbon strong,
.page-kicker strong {
  color: var(--mint);
}

.page-kicker {
  border-bottom: 1px solid var(--line-soft);
  padding-bottom: .8rem;
  margin-bottom: 1rem;
}

.page-kicker .page-date {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.source-card {
  border-left: 3px solid var(--mint);
}

.source-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: 1.1rem 0 1rem 0;
  border: 1px solid var(--line-soft);
  background: var(--line-soft);
}

.source-facts > div {
  display: flex;
  flex-direction: column;
  gap: .28rem;
  min-width: 0;
  padding: .8rem .9rem;
  background: var(--surface-muted);
}

.source-facts strong {
  color: var(--muted);
  font-size: .9rem;
  font-weight: 600;
}

.source-facts span {
  color: var(--ink);
  font-size: 1.02rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.source-footnote {
  color: var(--muted) !important;
  font-size: .98rem !important;
}

.source-card p,
.player-hero p {
  margin: 0 0 9px 0;
}

.player-hero {
  border-left: 3px solid var(--accent);
}

.player-hero h2 {
  margin: 0 0 8px 0;
}

.workflow-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workflow-row {
  display: grid;
  grid-template-columns: minmax(130px, .7fr) minmax(0, 1.3fr);
  gap: 16px;
  align-items: start;
  min-height: 94px;
  padding: 16px 18px;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-left: 3px solid var(--accent);
  border-radius: 5px;
  box-sizing: border-box;
  transition: background-color 180ms ease, border-color 180ms ease;
}

.workflow-row:hover {
  background: var(--surface-raised);
  border-color: rgba(216, 90, 82, .6);
}

.workflow-label {
  color: var(--ink);
  font-weight: 700;
  line-height: 1.4;
}

.workflow-description {
  color: var(--muted);
  font-size: 1.03rem;
  line-height: 1.55;
}

.model-label {
  display: inline-block;
  background: var(--surface-muted);
  border: 1px solid rgba(216, 90, 82, .62);
  border-left: 3px solid var(--accent);
  color: var(--muted-strong);
  border-radius: 4px;
  padding: 6px 11px;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: .02em;
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: .75rem;
  color: var(--muted);
  font-size: .9rem;
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
  background: rgba(232, 125, 114, .12);
  border-left: 3px solid var(--red);
  padding: 13px 15px;
  border-radius: 4px;
  font-size: 1.08rem;
  line-height: 1.65;
}

a {
  color: var(--gold) !important;
}

a:hover {
  color: var(--accent-soft) !important;
  text-decoration: underline;
}

[data-testid="stMarkdownContainer"] a:not(.skip-link) {
  text-decoration: underline;
  text-underline-offset: .18em;
}

button:focus-visible,
[role="button"]:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  outline: 2px solid var(--focus) !important;
  outline-offset: 2px !important;
}

.stButton button,
.stDownloadButton button {
  min-height: 48px;
  border-radius: 4px;
  font-size: 1.06rem !important;
  transition: border-color 180ms ease, background-color 180ms ease, transform 180ms ease;
  touch-action: manipulation;
  cursor: pointer;
}

.stDownloadButton {
  display: flex;
  justify-content: flex-end;
  margin: 0 0 1.1rem 0;
}

.stDownloadButton button {
  background: var(--surface-muted);
  border: 1px solid var(--line-soft);
  color: var(--muted-strong);
  min-width: 132px;
}

.stDownloadButton button:hover {
  background: var(--surface-raised);
  border-color: var(--blue);
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
  min-height: 48px;
  font-size: 1.04rem;
  background: var(--surface-muted);
  border-color: var(--line-soft);
  border-radius: 4px;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
[data-testid="stNumberInput"] input:hover {
  border-color: rgba(121, 182, 188, .6);
}

select,
input,
textarea {
  background-color: var(--bg-deep);
  color: var(--ink);
  caret-color: var(--gold);
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
  border-radius: 4px;
  box-shadow: 0 0 0 2px rgba(240, 207, 122, .28);
}

[data-testid="stAlert"] {
  border-radius: 4px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
  color: var(--muted-strong);
}

[data-testid="stPlotlyChart"] {
  border: 1px solid var(--line-soft);
  border-radius: 5px;
  background: var(--surface-muted);
  padding: 4px;
  box-sizing: border-box;
  min-width: 0;
  overflow: hidden;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: .25rem;
  border-bottom: 1px solid var(--line-soft);
}

[data-testid="stTabs"] [data-baseweb="tab"] {
  min-height: 48px;
  padding: .55rem .95rem;
  color: var(--muted);
}

[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--ink);
  border-bottom-color: var(--accent);
}

[data-testid="stRadio"] label,
[data-testid="stTabs"] button {
  min-height: 44px;
}

[data-testid="stTabs"] button {
  cursor: pointer;
  touch-action: manipulation;
}

.stButton button:hover,
.stDownloadButton button:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}

.stButton button:active,
.stDownloadButton button:active {
  background: rgba(216, 90, 82, .18);
  transform: translateY(0);
}

@media (max-width: 1100px) and (min-width: 721px) {
  .cpbl-card-grid,
  .workflow-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
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
  .stApp {
    font-size: 18.5px;
  }

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

  h1 {
    font-size: 2.15rem !important;
  }

  h2 {
    font-size: 1.72rem !important;
  }

  .metric-grid,
  .cpbl-card-grid,
  .workflow-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .metric-card {
    min-height: 112px;
  }

  .equal-card {
    height: auto;
    min-height: 162px;
  }

  .workflow-row {
    grid-template-columns: 1fr;
    gap: 7px;
    min-height: 0;
  }

  .source-facts {
    grid-template-columns: 1fr 1fr;
  }

  [data-testid="stMetric"] {
    min-height: 116px;
  }

  [data-testid="stHorizontalBlock"] {
    gap: 1rem;
  }

  .stDownloadButton {
    justify-content: stretch;
  }

  .stDownloadButton button {
    width: 100%;
  }
}
</style>
"""
