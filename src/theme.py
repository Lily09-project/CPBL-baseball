from __future__ import annotations


STREAMLIT_CSS = """
<style>
:root {
  --bg-deep: #061217;
  --bg: #091c22;
  --surface: #0e272d;
  --surface-raised: #13343b;
  --surface-soft: #0a2026;
  --ink: #f5f1e8;
  --ink-soft: #d8e1dd;
  --muted: #9cadb0;
  --muted-strong: #bac9c8;
  --accent: #d85a52;
  --accent-soft: #f08a78;
  --mint: #65b995;
  --gold: #d3a354;
  --blue: #79b6bc;
  --line: rgba(195, 213, 209, .18);
  --line-strong: rgba(211, 163, 84, .45);
  --focus: #f0cf7a;
  --radius: 5px;
  --space-1: .5rem;
  --space-2: .75rem;
  --space-3: 1rem;
  --space-4: 1.5rem;
  --space-5: 2rem;
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
  font-family: "Noto Sans TC", "Microsoft JhengHei", "PingFang TC", system-ui, sans-serif;
  font-size: 20px;
  line-height: 1.6;
  overflow-x: hidden;
  touch-action: manipulation;
  -webkit-tap-highlight-color: rgba(216, 90, 82, .24);
}

.block-container {
  box-sizing: border-box;
  max-width: 1440px;
  width: 100%;
  padding-top: 2rem;
  padding-right: max(2rem, env(safe-area-inset-right));
  padding-bottom: max(3.5rem, env(safe-area-inset-bottom));
  padding-left: max(2rem, env(safe-area-inset-left));
}

#cpbl-main {
  scroll-margin-top: 1rem;
}

.skip-link {
  position: fixed;
  top: max(.75rem, env(safe-area-inset-top));
  left: max(.75rem, env(safe-area-inset-left));
  z-index: 100;
  transform: translateY(-180%);
  padding: .65rem .9rem;
  border: 2px solid var(--focus);
  border-radius: var(--radius);
  background: var(--bg-deep);
  color: var(--ink) !important;
  font-weight: 750;
  text-decoration: none;
  transition: transform 160ms ease;
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
  max-width: 20ch;
  margin: 0 0 .55rem !important;
  font-size: 2.75rem !important;
  font-weight: 760 !important;
  line-height: 1.16 !important;
}

h2 {
  margin-top: 2.25rem !important;
  margin-bottom: .75rem !important;
  padding-left: .75rem;
  border-left: 3px solid var(--accent);
  font-size: 1.82rem !important;
  font-weight: 730 !important;
  line-height: 1.25 !important;
}

h3 {
  margin: 0 0 .5rem !important;
  font-size: 1.22rem !important;
  font-weight: 720 !important;
  line-height: 1.34 !important;
}

p,
span,
label,
div {
  color: inherit;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
  font-size: 1.05rem;
  line-height: 1.65;
  overflow-wrap: anywhere;
  text-wrap: pretty;
}

[data-testid="stWidgetLabel"] p,
[data-testid="stRadio"] label,
[data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label,
[data-testid="stMultiSelect"] label {
  font-size: 1.02rem !important;
}

[data-testid="stHorizontalBlock"] {
  gap: 24px;
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
  background: #06151a;
  border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] > div:first-child {
  padding: 1rem .9rem 1.5rem;
}

.sidebar-brand {
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: .75rem;
  align-items: center;
  padding: .4rem .2rem 1.05rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--line);
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  color: var(--gold);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: .78rem;
  font-weight: 800;
  letter-spacing: .08em;
}

.sidebar-brand-title {
  color: var(--ink);
  font-size: 1.14rem;
  font-weight: 780;
  line-height: 1.2;
}

.sidebar-brand-subtitle,
.sidebar-nav-label,
.sidebar-status {
  color: var(--muted);
  font-size: .86rem;
  line-height: 1.5;
}

.sidebar-nav-label {
  color: var(--muted-strong);
  margin: 0 0 .45rem .25rem;
  font-size: .76rem;
  font-weight: 800;
  letter-spacing: .1em;
}

.sidebar-status {
  margin-top: 1.1rem;
  padding: .95rem .25rem 0;
  border-top: 1px solid var(--line);
}

.sidebar-status strong {
  color: var(--mint);
  font-weight: 750;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
  gap: .3rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
  min-height: 46px;
  padding: .58rem .65rem;
  border: 1px solid transparent;
  border-radius: var(--radius);
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  border-color: rgba(121, 182, 188, .36);
  background: rgba(121, 182, 188, .08);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  border-color: rgba(216, 90, 82, .66);
  background: rgba(216, 90, 82, .15);
  color: var(--ink);
}

.mobile-product-brand {
  display: none;
}

.page-masthead {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: end;
  margin: 0 0 1.3rem;
  padding-bottom: 1.2rem;
  border-bottom: 1px solid var(--line);
}

.page-kicker {
  display: inline-flex;
  align-items: center;
  gap: .55rem;
  margin: 0 0 .7rem;
  color: var(--muted);
  font-size: .88rem;
  font-weight: 700;
  line-height: 1.4;
}

.page-kicker strong {
  color: var(--mint);
  font-size: .8rem;
  letter-spacing: .08em;
}

.page-kicker .page-date {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.page-lead {
  max-width: 68ch;
  margin: 0 !important;
  color: var(--muted-strong) !important;
  font-size: 1.08rem !important;
  line-height: 1.65 !important;
}

.data-status-line {
  display: inline-flex;
  max-width: 100%;
  align-items: center;
  gap: .45rem;
  align-self: start;
  padding: .48rem .68rem;
  border: 1px solid rgba(101, 185, 149, .4);
  border-radius: var(--radius);
  background: rgba(101, 185, 149, .07);
  color: var(--mint);
  font-size: .86rem;
  font-variant-numeric: tabular-nums;
  white-space: normal;
}

.data-status-line::before {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--mint);
  content: "";
}

.metric-grid,
.cpbl-card-grid,
.workflow-grid,
.route-grid,
.evidence-grid {
  display: grid;
  grid-auto-rows: 1fr;
  gap: 24px;
  align-items: stretch;
}

.metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  margin: 1.2rem 0 2rem;
}

.metric-card {
  display: flex;
  min-height: 132px;
  height: 100%;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  padding: 1rem 1.1rem 1.05rem;
  border: 1px solid var(--line);
  border-top: 3px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

.metric-card:nth-child(3n + 2) {
  border-top-color: var(--gold);
}

.metric-card:nth-child(3n) {
  border-top-color: var(--blue);
}

.metric-label {
  color: var(--muted);
  font-size: .92rem;
  font-weight: 680;
  line-height: 1.4;
}

.metric-value {
  margin-top: .8rem;
  color: var(--ink);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 2.05rem;
  font-variant-numeric: tabular-nums;
  font-weight: 740;
  line-height: 1.12;
  overflow-wrap: anywhere;
}

.metric-card-detail {
  min-height: 1.25rem;
  margin-top: .45rem;
  color: var(--muted);
  font-size: .82rem;
  line-height: 1.45;
}

.cpbl-card {
  box-sizing: border-box;
  min-height: 0;
  margin: 0 0 1.5rem;
  padding: 1.2rem 1.25rem;
  overflow-wrap: anywhere;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
}

.cpbl-card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 1.25rem 0 2rem;
}

.cpbl-card-grid .cpbl-card {
  height: 100%;
  margin: 0;
}

.cpbl-card .card-heading {
  margin: 0 0 .7rem !important;
  padding: 0 !important;
  border: 0 !important;
  font-size: 1.2rem !important;
  line-height: 1.34 !important;
}

.cpbl-card p {
  margin: 0 0 .55rem;
  font-size: 1rem;
  line-height: 1.6;
}

.source-ribbon {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 0 0 .75rem;
  padding: .62rem .8rem;
  border: 1px solid rgba(101, 185, 149, .36);
  border-left: 3px solid var(--mint);
  border-radius: var(--radius);
  background: var(--surface-soft);
  color: var(--muted-strong);
  font-size: .9rem;
  line-height: 1.45;
}

.source-ribbon strong {
  color: var(--mint);
}

.source-card {
  border-left: 3px solid var(--mint);
}

.source-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: 1rem 0 .85rem;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--line);
}

.source-facts > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: .24rem;
  padding: .75rem .8rem;
  background: var(--surface-soft);
}

.source-facts strong {
  color: var(--muted);
  font-size: .78rem;
  font-weight: 720;
}

.source-facts span {
  color: var(--ink-soft);
  font-size: .96rem;
  line-height: 1.42;
  overflow-wrap: anywhere;
}

.source-footnote {
  margin-bottom: 0 !important;
  color: var(--muted) !important;
  font-size: .9rem !important;
}

.trust-strip {
  display: flex;
  flex-wrap: wrap;
  gap: .45rem .8rem;
  margin: .8rem 0 1.35rem;
  padding: .72rem .82rem;
  border: 1px solid rgba(101, 185, 149, .36);
  border-left: 3px solid var(--mint);
  border-radius: var(--radius);
  background: var(--surface-soft);
  color: var(--muted-strong);
  font-size: .88rem;
  line-height: 1.5;
}

.trust-item {
  display: inline-flex;
  align-items: center;
  gap: .45rem;
}

.trust-item + .trust-item::before {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--mint);
  content: "";
}

.workflow-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 1rem 0 1.7rem;
}

.workflow-row,
.route-card {
  box-sizing: border-box;
  min-height: 124px;
  height: 100%;
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

.workflow-row {
  display: grid;
  grid-template-columns: minmax(112px, .7fr) minmax(0, 1.4fr);
  gap: 1rem;
  align-items: start;
}

.workflow-row:hover,
.route-card:hover {
  border-color: rgba(216, 90, 82, .6);
  background: var(--surface-raised);
}

.workflow-label,
.route-label {
  color: var(--ink);
  font-size: 1.03rem;
  font-weight: 750;
  line-height: 1.4;
}

.workflow-description,
.route-description {
  color: var(--muted);
  font-size: .96rem;
  line-height: 1.55;
}

.route-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: .85rem 0 0;
}

.route-card {
  display: flex;
  min-height: 142px;
  height: 142px;
  flex-direction: column;
  justify-content: space-between;
  gap: .8rem;
}

.route-card:nth-child(2) {
  border-left-color: var(--gold);
}

.route-card:nth-child(3) {
  border-left-color: var(--blue);
}

.route-eyebrow,
.control-caption {
  color: var(--muted);
  font-size: .79rem;
  font-weight: 730;
  letter-spacing: .07em;
  line-height: 1.4;
}

.route-card .stButton {
  margin-top: auto;
}

.player-identity {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: end;
  margin: 1rem 0 1.25rem;
  padding: 1.15rem 1.2rem;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

.player-identity h2 {
  margin: .15rem 0 .42rem !important;
  padding: 0 !important;
  border: 0 !important;
  font-size: 2rem !important;
}

.player-identity p {
  margin: 0 !important;
  color: var(--muted-strong);
  font-size: .98rem !important;
}

.player-identity .identity-label {
  color: var(--gold);
  font-size: .8rem;
  font-weight: 780;
  letter-spacing: .08em;
}

.player-identity .identity-status {
  align-self: start;
  padding: .42rem .6rem;
  border: 1px solid rgba(101, 185, 149, .42);
  border-radius: var(--radius);
  color: var(--mint);
  font-size: .82rem;
  white-space: nowrap;
}

.evidence-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: .8rem 0 1.7rem;
}

.evidence-panel {
  height: 100%;
  box-sizing: border-box;
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-top: 3px solid var(--blue);
  border-radius: var(--radius);
  background: var(--surface);
}

.evidence-panel.risk {
  border-top-color: var(--accent);
}

.evidence-panel.note {
  border-top-color: var(--gold);
}

.evidence-panel h3 {
  margin-bottom: .65rem !important;
}

.evidence-panel ul {
  margin: 0;
  padding-left: 1.15rem;
}

.evidence-panel li,
.evidence-empty {
  color: var(--muted-strong);
  font-size: .95rem;
  line-height: 1.58;
}

.control-caption {
  display: block;
  margin: .2rem 0 .85rem;
  color: var(--muted-strong);
  letter-spacing: 0;
}

.model-label {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  margin: .15rem 0 .7rem;
  padding: .25rem .55rem;
  border: 1px solid rgba(216, 90, 82, .58);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface-soft);
  color: var(--muted-strong);
  font-size: .82rem;
  font-weight: 760;
  letter-spacing: .05em;
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: .55rem;
  margin: .45rem 0 .25rem;
  color: var(--muted);
  font-size: .82rem;
}

.table-toolbar-label {
  color: var(--muted-strong);
  font-weight: 740;
}

.table-toolbar-hint {
  color: var(--blue);
  font-variant-numeric: tabular-nums;
}

[data-testid="stDataFrame"] {
  max-width: 100%;
  margin: .4rem 0 .65rem;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface-soft);
  font-size: .99rem;
  font-variant-numeric: tabular-nums;
}

[data-testid="stMetric"] {
  box-sizing: border-box;
  min-height: 128px;
  margin-bottom: 18px;
  padding: 17px 19px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: none;
}

[data-testid="stMetricLabel"] p {
  color: var(--muted);
  font-size: 1rem;
  line-height: 1.35;
}

[data-testid="stMetricValue"] {
  color: var(--gold);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 2rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

.stButton button,
.stDownloadButton button {
  min-height: 48px;
  border-radius: var(--radius);
  font-size: .98rem !important;
  transition: border-color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
  touch-action: manipulation;
  cursor: pointer;
}

.stButton button {
  border: 1px solid rgba(216, 90, 82, .6);
  background: rgba(216, 90, 82, .13);
  color: var(--ink);
}

.stButton button:hover,
.stDownloadButton button:hover {
  border-color: var(--accent-soft);
  background: rgba(216, 90, 82, .22);
  box-shadow: 0 0 0 2px rgba(240, 138, 120, .18);
}

.stButton button:active,
.stDownloadButton button:active {
  box-shadow: inset 0 0 0 2px rgba(240, 138, 120, .28);
}

.stDownloadButton {
  display: flex;
  justify-content: flex-end;
  margin: 0 0 1.15rem;
}

.stDownloadButton button {
  min-width: 132px;
  border: 1px solid var(--line);
  background: var(--surface-soft);
  color: var(--ink-soft);
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  min-height: 48px;
  border-color: var(--line);
  border-radius: var(--radius);
  background: var(--surface-soft);
  font-size: 1rem;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
[data-testid="stNumberInput"] input:hover,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:hover {
  border-color: rgba(121, 182, 188, .7);
}

[data-testid="stRadio"] label,
[data-testid="stTabs"] button {
  min-height: 44px;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: .25rem;
  border-bottom: 1px solid var(--line);
}

[data-testid="stTabs"] [data-baseweb="tab"] {
  padding: .55rem .85rem;
  color: var(--muted);
}

[data-testid="stTabs"] [aria-selected="true"] {
  border-bottom-color: var(--accent);
  color: var(--ink);
}

[data-testid="stPlotlyChart"] {
  box-sizing: border-box;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface-soft);
  padding: 4px;
}

[data-testid="stAlert"] {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--muted-strong);
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
a:focus-visible,
[role="button"]:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  outline: 3px solid var(--focus) !important;
  outline-offset: 3px !important;
}

/* UI Pro Max: data-dense layouts must reflow without clipping or hidden focus. */
html {
  scroll-behavior: smooth;
  scroll-padding-top: 1rem;
}

[data-testid="stDataFrame"],
[data-testid="stPlotlyChart"] {
  max-width: 100%;
  min-width: 0;
}

[data-testid="stDataFrame"] {
  scrollbar-color: var(--line-strong) var(--surface-soft);
}

[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
  overflow-wrap: anywhere;
  text-wrap: pretty;
}

@media (max-width: 720px) {
  html { scroll-padding-top: 4.5rem; }

  [data-testid="stPlotlyChart"] {
    padding: 0;
  }

  .table-toolbar {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
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

[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] {
  display: none;
}

.snapshot-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  grid-auto-rows: 1fr;
  gap: 24px;
  margin: 1rem 0 1.6rem;
}

.snapshot-node {
  display: flex;
  min-height: 132px;
  height: 100%;
  box-sizing: border-box;
  flex-direction: column;
  justify-content: space-between;
  gap: .48rem;
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-top: 3px solid var(--blue);
  border-radius: var(--radius);
  background: var(--surface);
}

.snapshot-node strong {
  color: var(--ink);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.snapshot-node span {
  color: var(--muted);
  font-size: .86rem;
  line-height: 1.45;
}

.snapshot-node .snapshot-date {
  color: var(--muted-strong);
  font-variant-numeric: tabular-nums;
}

.snapshot-node-current {
  border-top-color: var(--mint);
  background: var(--surface-raised);
}

.snapshot-node-current::after {
  color: var(--mint);
  font-size: .78rem;
  font-weight: 760;
  content: "目前版本";
}
@media (max-width: 1100px) and (min-width: 721px) {
  .cpbl-card-grid,
  .route-grid,
  .evidence-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .mobile-product-brand {
    display: block;
    margin: 0 0 .85rem;
    color: var(--gold);
    font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .12em;
  }

  .stApp {
    font-size: 18.5px;
  }

  .block-container {
    padding-top: 1.25rem;
    padding-right: max(1rem, env(safe-area-inset-right));
    padding-bottom: max(2.2rem, env(safe-area-inset-bottom));
    padding-left: max(1rem, env(safe-area-inset-left));
  }

  [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: 16px !important;
  }

  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 auto !important;
    width: 100% !important;
  }

  h1 {
    font-size: 2.16rem !important;
  }

  h2 {
    font-size: 1.58rem !important;
  }

  .page-masthead,
  .player-identity {
    grid-template-columns: 1fr;
    gap: .8rem;
  }

  .data-status-line {
    justify-self: start;
  }

  .metric-grid,
  .cpbl-card-grid,
  .workflow-grid,
  .route-grid,
  .evidence-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .metric-card {
    min-height: 116px;
  }

  .route-card {
    min-height: 0;
    height: auto;
  }

  .workflow-row {
    grid-template-columns: 1fr;
    gap: .42rem;
    min-height: 0;
  }

  .source-ribbon {
    align-items: flex-start;
    flex-direction: column;
    gap: .3rem;
  }

  .source-facts {
    grid-template-columns: 1fr 1fr;
  }

  .trust-strip {
    align-items: flex-start;
    flex-direction: column;
    gap: .25rem;
  }

  .trust-item + .trust-item::before {
    display: none;
  }

  .stDownloadButton {
    justify-content: stretch;
  }

  .stDownloadButton button {
    width: 100%;
  }
}

[data-testid="stMarkdownContainer"] .metric-grid,
[data-testid="stMarkdownContainer"] .cpbl-card-grid,
[data-testid="stMarkdownContainer"] .workflow-grid,
[data-testid="stMarkdownContainer"] .route-grid,
[data-testid="stMarkdownContainer"] .evidence-grid {
  display: grid !important;
}

[data-testid="stMarkdownContainer"] .metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .cpbl-card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .workflow-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .route-grid,
[data-testid="stMarkdownContainer"] .evidence-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .evidence-panel,
[data-testid="stMarkdownContainer"] .route-card {
  min-width: 0;
  height: 100%;
}

@media (max-width: 1100px) and (min-width: 721px) {
  [data-testid="stMarkdownContainer"] .metric-grid,
  [data-testid="stMarkdownContainer"] .cpbl-card-grid,
  [data-testid="stMarkdownContainer"] .route-grid,
  [data-testid="stMarkdownContainer"] .evidence-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}

@media (max-width: 720px) {
  [data-testid="stMarkdownContainer"] .metric-grid,
  [data-testid="stMarkdownContainer"] .cpbl-card-grid,
  [data-testid="stMarkdownContainer"] .workflow-grid,
  [data-testid="stMarkdownContainer"] .route-grid,
  [data-testid="stMarkdownContainer"] .evidence-grid {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 720px) {
  .snapshot-timeline {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .snapshot-node {
    min-height: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
  }
}
</style>
"""

STREAMLIT_LAYOUT_CSS = """
<style>
.page-masthead {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
  gap: 1.5rem;
  align-items: end;
  margin: 0 0 1.3rem;
  padding-bottom: 1.2rem;
  border-bottom: 1px solid var(--line);
}

[data-testid="stMarkdownContainer"] .page-kicker {
  display: inline-flex !important;
  align-items: center;
  gap: .55rem;
  margin: 0 !important;
  color: var(--muted);
  font-size: .88rem;
  font-weight: 700;
}

[data-testid="stMarkdownContainer"] .page-kicker strong {
  color: var(--mint);
  font-size: .8rem;
  letter-spacing: .08em;
}

[data-testid="stMarkdownContainer"] .data-status-line {
  display: inline-flex !important;
  align-items: center;
  gap: .45rem;
  padding: .48rem .68rem;
  border: 1px solid rgba(101, 185, 149, .4);
  border-radius: var(--radius);
  background: rgba(101, 185, 149, .07);
  color: var(--mint);
  font-size: .86rem;
  white-space: normal;
}

[data-testid="stMarkdownContainer"] .data-status-line::before {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--mint);
  content: "";
}

[data-testid="stMarkdownContainer"] .metric-grid,
[data-testid="stMarkdownContainer"] .cpbl-card-grid,
[data-testid="stMarkdownContainer"] .workflow-grid,
[data-testid="stMarkdownContainer"] .route-grid,
[data-testid="stMarkdownContainer"] .evidence-grid {
  display: grid !important;
  gap: 24px;
  align-items: stretch;
  grid-auto-rows: 1fr;
}

[data-testid="stMarkdownContainer"] .metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .cpbl-card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .workflow-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .route-grid,
[data-testid="stMarkdownContainer"] .evidence-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

[data-testid="stMarkdownContainer"] .route-card,
[data-testid="stMarkdownContainer"] .evidence-panel {
  min-width: 0;
  height: 100%;
  box-sizing: border-box;
}

[data-testid="stMarkdownContainer"] .route-card {
  display: flex !important;
  min-height: 142px;
  height: 142px;
  flex-direction: column;
  justify-content: space-between;
  gap: .8rem;
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

[data-testid="stMarkdownContainer"] .route-card:nth-child(2) { border-left-color: var(--gold); }
[data-testid="stMarkdownContainer"] .route-card:nth-child(3) { border-left-color: var(--blue); }
[data-testid="stMarkdownContainer"] .route-eyebrow,
[data-testid="stMarkdownContainer"] .control-caption {
  color: var(--muted);
  font-size: .79rem;
  font-weight: 730;
  letter-spacing: .07em;
}

[data-testid="stMarkdownContainer"] .route-label {
  color: var(--ink);
  font-size: 1.03rem;
  font-weight: 750;
}

[data-testid="stMarkdownContainer"] .route-description {
  color: var(--muted);
  font-size: .96rem;
  line-height: 1.55;
}

[data-testid="stMarkdownContainer"] .player-identity {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
  gap: 1rem;
  align-items: end;
  margin: 1rem 0 1.25rem;
  padding: 1.15rem 1.2rem;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

[data-testid="stMarkdownContainer"] .player-identity h2 {
  margin: .15rem 0 .42rem !important;
  padding: 0 !important;
  border: 0 !important;
  font-size: 2rem !important;
}

[data-testid="stMarkdownContainer"] .player-identity p {
  margin: 0 !important;
  color: var(--muted-strong);
  font-size: .98rem !important;
}

[data-testid="stMarkdownContainer"] .identity-label {
  color: var(--gold);
  font-size: .8rem;
  font-weight: 780;
  letter-spacing: .08em;
}

[data-testid="stMarkdownContainer"] .identity-status {
  align-self: start;
  padding: .42rem .6rem;
  border: 1px solid rgba(101, 185, 149, .42);
  border-radius: var(--radius);
  color: var(--mint);
  font-size: .82rem;
  white-space: nowrap;
}

[data-testid="stMarkdownContainer"] .evidence-panel {
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-top: 3px solid var(--blue);
  border-radius: var(--radius);
  background: var(--surface);
}

[data-testid="stMarkdownContainer"] .evidence-panel.risk { border-top-color: var(--accent); }
[data-testid="stMarkdownContainer"] .evidence-panel.note { border-top-color: var(--gold); }
[data-testid="stMarkdownContainer"] .evidence-panel h3 { margin-bottom: .65rem !important; }
[data-testid="stMarkdownContainer"] .evidence-panel ul { margin: 0; padding-left: 1.15rem; }
[data-testid="stMarkdownContainer"] .evidence-panel li,
[data-testid="stMarkdownContainer"] .evidence-empty {
  color: var(--muted-strong);
  font-size: .95rem;
  line-height: 1.58;
}

[data-testid="stMarkdownContainer"] .trust-strip {
  display: flex !important;
  flex-wrap: wrap;
  gap: .45rem .8rem;
  margin: .8rem 0 1.35rem;
  padding: .72rem .82rem;
  border: 1px solid rgba(101, 185, 149, .36);
  border-left: 3px solid var(--mint);
  border-radius: var(--radius);
  background: var(--surface-soft);
  color: var(--muted-strong);
  font-size: .88rem;
}

[data-testid="stMarkdownContainer"] .trust-item { display: inline-flex !important; align-items: center; gap: .45rem; }
[data-testid="stMarkdownContainer"] .trust-item + .trust-item::before {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--mint);
  content: "";
}

@media (max-width: 1100px) and (min-width: 721px) {
  [data-testid="stMarkdownContainer"] .page-masthead,
  [data-testid="stMarkdownContainer"] .player-identity {
    grid-template-columns: 1fr !important;
    gap: .8rem;
  }

  [data-testid="stMarkdownContainer"] .data-status-line {
    justify-self: start;
  }

  [data-testid="stMarkdownContainer"] .cpbl-card-grid,
  [data-testid="stMarkdownContainer"] .route-grid,
  [data-testid="stMarkdownContainer"] .evidence-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
}

@media (max-width: 1100px) and (min-width: 721px) {
  [data-testid="stMarkdownContainer"] .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}
@media (max-width: 720px) {
  [data-testid="stMarkdownContainer"] .page-masthead,
  [data-testid="stMarkdownContainer"] .player-identity { grid-template-columns: 1fr !important; gap: .8rem; }
  [data-testid="stMarkdownContainer"] .metric-grid,
  [data-testid="stMarkdownContainer"] .cpbl-card-grid,
  [data-testid="stMarkdownContainer"] .workflow-grid,
  [data-testid="stMarkdownContainer"] .route-grid,
  [data-testid="stMarkdownContainer"] .evidence-grid { grid-template-columns: 1fr !important; gap: 16px; }
  [data-testid="stMarkdownContainer"] .route-card { min-height: 0; height: auto; }
  [data-testid="stMarkdownContainer"] .trust-strip { align-items: flex-start; flex-direction: column; gap: .25rem; }
  [data-testid="stMarkdownContainer"] .trust-item + .trust-item::before { display: none; }
}
.sidebar-search-label {
  margin-top: 1.35rem;
}

[data-testid="stMarkdownContainer"] .data-status-line.status-recent {
  border-color: rgba(211, 163, 84, .55);
  background: rgba(211, 163, 84, .1);
  color: var(--gold);
}

[data-testid="stMarkdownContainer"] .data-status-line.status-recent::before {
  background: var(--gold);
}

[data-testid="stMarkdownContainer"] .data-status-line.status-stale {
  border-color: rgba(240, 138, 120, .6);
  background: rgba(216, 90, 82, .12);
  color: var(--accent-soft);
}

[data-testid="stMarkdownContainer"] .data-status-line.status-stale::before {
  background: var(--accent-soft);
}

[data-testid="stMarkdownContainer"] .data-status-line.status-unknown {
  border-color: rgba(156, 173, 176, .5);
  background: rgba(156, 173, 176, .08);
  color: var(--muted-strong);
}

[data-testid="stMarkdownContainer"] .data-status-line.status-unknown::before {
  background: var(--muted-strong);
}

[data-testid="stSidebar"] .sidebar-status.status-recent strong {
  color: var(--gold);
}

[data-testid="stSidebar"] .sidebar-status.status-stale strong {
  color: var(--accent-soft);
}

[data-testid="stSidebar"] .sidebar-status.status-unknown strong {
  color: var(--muted-strong);
}

.product-footer {
  display: grid;
  gap: .35rem;
  margin-top: 3.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: .86rem;
  line-height: 1.55;
}

.product-footer strong {
  color: var(--muted-strong);
  font-weight: 700;
}
</style>
"""
