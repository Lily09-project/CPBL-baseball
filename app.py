from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.app_helpers import load_csv
from src.data_quality import load_data_quality_report
from src.fetch_cpbl_data import absolute_url
from src.log5_matchup import calculate_log5_probability, summarize_matchup_probability
from src.rankings import get_bottom_players, get_team_rankings, get_top_players
from src.similarity import find_similar_players
from src.theme import STREAMLIT_CSS


APP_TITLE = "CPBL 中職資料分析平台"
QUALITY_REPORT = load_data_quality_report()


def data_verified_date(report: dict | None = None) -> str:
    generated_at = str((report or QUALITY_REPORT).get("generated_at", ""))
    return generated_at[:10] if len(generated_at) >= 10 else "未記錄"


def source_note(report: dict | None = None) -> str:
    return (
        "球隊戰績、現役球員名單、打擊成績與投手成績取自 CPBL 官方網站 "
        f"/player、/standings/season、/stats/recordallaction；資料抓取日期：{data_verified_date(report)}。"
    )


def data_generated_time(report: dict | None = None) -> str:
    raw = str((report or QUALITY_REPORT).get("generated_at", ""))
    if not raw:
        return "未記錄"
    try:
        return datetime.fromisoformat(raw).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


DATA_VERIFIED_DATE = data_verified_date()
SOURCE_NOTE = source_note()

PAGES = [
    "首頁 / 專案介紹",
    "聯盟總覽",
    "球員排行榜",
    "球員個人頁",
    "投打對決",
    "分項排行",
]

LOWER_IS_BETTER = {"era", "whip", "bb_rate", "hr_allowed_rate"}
RATE_AS_PERCENT = {"bb_rate", "k_rate", "hr_rate", "hr_allowed_rate"}
THREE_DECIMAL_METRICS = {"batting_average", "obp", "slg", "ops", "iso", "bb_k_ratio", "win_pct", "avg"}
TWO_DECIMAL_METRICS = {"era", "whip", "k_bb_ratio", "innings_pitched", "similarity"}
SCORE_METRICS = {
    "contact_score",
    "power_score",
    "discipline_score",
    "hitter_value_score",
    "run_prevention_score",
    "strikeout_score",
    "command_score",
    "pitcher_value_score",
    "player_value_score",
    "momentum_score",
}

METRIC_LABELS = {
    "ops": "整體攻擊指標 (OPS)",
    "iso": "純長打率 (ISO)",
    "batting_average": "打擊率 (AVG)",
    "obp": "上壘率 (OBP)",
    "slg": "長打率 (SLG)",
    "bb_k_ratio": "保送三振比 (BB/K)",
    "era": "防禦率 (ERA)",
    "whip": "每局被上壘率 (WHIP)",
    "k_bb_ratio": "三振保送比 (K/BB)",
    "k_rate": "三振率 (K%)",
    "bb_rate": "保送率 (BB%)",
    "hr_rate": "全壘打率 (HR%)",
    "hr_allowed_rate": "被全壘打率 (HR%)",
    "hitter_value_score": "打者綜合分數",
    "pitcher_value_score": "投手綜合分數",
    "player_value_score": "球員綜合分數",
    "win_pct": "勝率",
    "home_win_pct": "主場勝率",
    "away_win_pct": "客場勝率",
    "run_diff": "得失分差",
    "momentum_score": "近期戰力分數",
    "games_behind": "勝差",
    "streak": "近況",
}

COLUMN_LABELS = {
    "season": "年度",
    "team": "球隊",
    "games": "出賽",
    "wins": "勝",
    "losses": "敗",
    "ties": "和",
    "win_pct": "勝率",
    "games_behind": "勝差",
    "streak": "近況",
    "source_note": "資料來源",
    "runs_scored": "得分",
    "runs_allowed": "失分",
    "run_diff": "得失分差",
    "home_wins": "主場勝",
    "home_losses": "主場敗",
    "away_wins": "客場勝",
    "away_losses": "客場敗",
    "recent_wins": "近況勝",
    "recent_losses": "近況敗",
    "momentum_score": "近期戰力",
    "player_id": "球員 ID",
    "player_name": "球員",
    "position": "守備位置",
    "role": "投手角色",
    "role_or_position": "位置 / 角色",
    "player_type": "球員類型",
    "pa": "打席 (PA)",
    "ab": "打數 (AB)",
    "hits": "安打",
    "doubles": "二壘安打",
    "triples": "三壘安打",
    "home_runs": "全壘打 (HR)",
    "walks": "保送 (BB)",
    "strikeouts": "三振 (K)",
    "stolen_bases": "盜壘 (SB)",
    "batting_average": "打擊率 (AVG)",
    "obp": "上壘率 (OBP)",
    "slg": "長打率 (SLG)",
    "ops": "OPS",
    "iso": "ISO",
    "bb_rate": "BB%",
    "k_rate": "K%",
    "hr_rate": "HR%",
    "bb_k_ratio": "BB/K",
    "innings_pitched": "投球局數 (IP)",
    "earned_runs": "自責分",
    "hits_allowed": "被安打",
    "home_runs_allowed": "被全壘打",
    "era": "ERA",
    "whip": "WHIP",
    "k_bb_ratio": "K/BB",
    "hr_allowed_rate": "被 HR%",
    "contact_score": "擊球接觸",
    "power_score": "長打能力",
    "discipline_score": "選球紀律",
    "hitter_value_score": "打者綜合",
    "run_prevention_score": "失分壓制",
    "strikeout_score": "三振能力",
    "command_score": "控球能力",
    "pitcher_value_score": "投手綜合",
    "player_value_score": "綜合分數",
    "metric_value": "指標數值",
    "similarity": "相似度",
}

METRIC_HELP = {
    "ops": "OPS 是上壘率加長打率，用來快速衡量打者整體攻擊產出。",
    "iso": "ISO 是長打率扣掉打擊率，用來觀察純長打能力。",
    "bb_k_ratio": "BB/K 是保送除以三振，適合觀察選球紀律與揮棒控制。",
    "era": "ERA 是防禦率，越低代表每九局自責失分越少。",
    "whip": "WHIP 是每局被上壘率，越低代表壓制上壘越好。",
    "k_bb_ratio": "K/BB 是三振除以保送，越高通常代表壓制力與控球更穩。",
    "player_value_score": "球員綜合分數由打擊或投球核心指標轉成 0 到 100 分。",
    "win_pct": "勝率為勝場除以勝敗場，不含和局。",
    "run_diff": "得失分差是總得分減總失分。",
    "momentum_score": "近期戰力分數由近況勝敗與得失分差組合而成。",
}


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.markdown(STREAMLIT_CSS, unsafe_allow_html=True)
st.markdown(
    '<a class="skip-link" href="#cpbl-main">跳至主要內容</a><div id="cpbl-main" tabindex="-1"></div>',
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data() -> dict[str, pd.DataFrame]:
    return {
        "teams": load_csv("teams.csv"),
        "roster": load_csv("roster.csv"),
        "batters": load_csv("batters_scored.csv"),
        "pitchers": load_csv("pitchers_scored.csv"),
        "players": load_csv("players_scored.csv"),
    }


DATA = load_data()
TEAMS = DATA["teams"]
ROSTER = DATA["roster"]
BATTERS = DATA["batters"]
PITCHERS = DATA["pitchers"]
PLAYERS = DATA["players"]
TABLE_DOWNLOAD_INDEX = 0

CHART_TEXT = "#e7efed"
CHART_MUTED = "#9db0b5"
CHART_GRID = "rgba(157,176,181,.22)"
CHART_ACCENT = "#d85a52"
CHART_SECONDARY = "#79b6bc"
CHART_HIGHLIGHT = "#d3a354"


def metric_name(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.upper() if metric.islower() else metric)


def as_number(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def format_metric_value(metric: str, value: object) -> str:
    if pd.isna(value):
        return "N/A"
    if metric in RATE_AS_PERCENT:
        return f"{as_number(value):.1%}"
    if metric in THREE_DECIMAL_METRICS:
        return f"{as_number(value):.3f}"
    if metric in TWO_DECIMAL_METRICS:
        return f"{as_number(value):.2f}"
    if metric in SCORE_METRICS:
        return f"{as_number(value):.1f}"
    if metric in {"games_behind"}:
        number = as_number(value)
        return "-" if number == 0 else f"{number:g}"
    if isinstance(value, float):
        return f"{value:.1f}" if not value.is_integer() else f"{int(value)}"
    return str(value)


def to_display_table(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    if columns is not None:
        out = out[[col for col in columns if col in out.columns]]
    for col in out.columns:
        if col in RATE_AS_PERCENT or col in THREE_DECIMAL_METRICS or col in TWO_DECIMAL_METRICS or col in SCORE_METRICS:
            out[col] = out[col].map(lambda value, metric=col: format_metric_value(metric, value))
        elif col == "games_behind":
            out[col] = out[col].map(lambda value: format_metric_value("games_behind", value))
    return out.rename(columns={col: COLUMN_LABELS.get(col, col) for col in out.columns})


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    safe = df.copy()
    safe.columns = [neutralize_spreadsheet_formula(column) for column in safe.columns]
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        safe[column] = safe[column].map(neutralize_spreadsheet_formula)
    return safe.to_csv(index=False).encode("utf-8-sig")


def neutralize_spreadsheet_formula(value: object) -> object:
    if not isinstance(value, str) or not value:
        return value
    candidate = value.lstrip(" \t\r\n\v\f")
    if candidate.startswith(("=", "+", "-", "@")) and candidate != "-":
        return f"'{value}"
    return value


def show_table(container, df: pd.DataFrame, columns: list[str] | None = None) -> None:
    if df.empty:
        container.info("目前沒有可顯示的資料，請調整篩選條件或重新產生資料。")
        return
    global TABLE_DOWNLOAD_INDEX
    TABLE_DOWNLOAD_INDEX += 1
    display = to_display_table(df, columns)
    container.dataframe(display, width="stretch", hide_index=True)
    container.markdown(
        "<div class='table-toolbar'><span class='table-toolbar-label'>資料表</span><span class='table-toolbar-hint'>UTF-8 CSV</span></div>",
        unsafe_allow_html=True,
    )
    container.download_button(
        "下載 CSV",
        data=dataframe_to_csv_bytes(display),
        file_name=f"cpbl_table_{TABLE_DOWNLOAD_INDEX:02d}.csv",
        mime="text/csv",
        key=f"download_table_{TABLE_DOWNLOAD_INDEX}",
        icon=":material/download:",
    )


def apply_chart_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CHART_TEXT, size=18, family="Noto Sans TC, Microsoft JhengHei, sans-serif"),
        title_font=dict(color=CHART_TEXT, size=22),
        legend=dict(font=dict(size=16), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=26, r=26, t=58, b=34),
        coloraxis_colorbar=dict(title_font=dict(size=15), tickfont=dict(size=14)),
    )
    fig.update_xaxes(
        gridcolor=CHART_GRID,
        zerolinecolor="rgba(157,176,181,.38)",
        title_font=dict(size=17),
        tickfont=dict(size=15, color=CHART_MUTED),
    )
    fig.update_yaxes(
        gridcolor=CHART_GRID,
        zerolinecolor="rgba(157,176,181,.38)",
        title_font=dict(size=17),
        tickfont=dict(size=15, color=CHART_MUTED),
    )
    fig.update_polars(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(gridcolor="rgba(157,176,181,.32)", tickfont=dict(size=14, color=CHART_MUTED)),
        angularaxis=dict(gridcolor="rgba(157,176,181,.36)", tickfont=dict(size=16, color=CHART_TEXT)),
    )
    return fig


def compact_chart_value(value: object) -> str:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return str(value)
    numeric = float(number)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.3f}" if abs(numeric) < 1 else f"{numeric:.1f}"


def chart_sequence(value: object) -> list[object]:
    return [] if value is None else list(value)


def chart_accessibility_summary(fig: go.Figure) -> str:
    title = str(fig.layout.title.text or "資料圖表")
    segments: list[str] = []

    for trace in fig.data:
        trace_type = str(getattr(trace, "type", ""))
        trace_name = str(getattr(trace, "name", "") or "")
        if trace_type == "scatterpolar":
            labels = chart_sequence(getattr(trace, "theta", None))
            values = chart_sequence(getattr(trace, "r", None))
            if len(labels) > 1 and labels[0] == labels[-1]:
                labels = labels[:-1]
                values = values[:-1]
            pairs = [f"{label} {compact_chart_value(value)}" for label, value in zip(labels, values)]
        elif trace_type == "bar":
            orientation = str(getattr(trace, "orientation", "") or "v")
            categories = chart_sequence(getattr(trace, "y", None)) if orientation == "h" else chart_sequence(getattr(trace, "x", None))
            values = chart_sequence(getattr(trace, "x", None)) if orientation == "h" else chart_sequence(getattr(trace, "y", None))
            pairs = [f"{category} {compact_chart_value(value)}" for category, value in zip(categories, values)]
        else:
            pairs = []

        if pairs:
            prefix = f"{trace_name}：" if trace_name and trace_name != "能力輪廓" else ""
            segments.append(prefix + "、".join(pairs[:12]))

    details = "；".join(segments[:4])
    return f"圖表摘要：{title}。" + (details if details else "可使用相鄰資料表取得完整數值。")


def show_chart(container, fig: go.Figure) -> None:
    container.markdown(
        f"<p class='chart-summary sr-only' role='note'>{escape(chart_accessibility_summary(fig))}</p>",
        unsafe_allow_html=True,
    )
    container.plotly_chart(
        apply_chart_theme(fig),
        width="stretch",
        config={"displayModeBar": False, "displaylogo": False, "responsive": True, "scrollZoom": False},
    )


def metric_cards(items: list[tuple[str, object]]) -> None:
    if not items:
        return
    cards = "".join(
        f"<div class='metric-card'><div class='metric-label'>{escape(str(label))}</div><div class='metric-value'>{escape(str(value))}</div></div>"
        for label, value in items
    )
    st.markdown(f"<div class='metric-grid' role='group' aria-label='重點數據'>{cards}</div>", unsafe_allow_html=True)


def page_kicker(section: str) -> None:
    st.markdown(
        f"<div class='page-kicker'><strong>CPBL 官方資料</strong><span class='page-date'>{escape(section)} · 資料驗證 {escape(data_verified_date())}</span></div>",
        unsafe_allow_html=True,
    )


def radar_chart(labels: list[str], values: list[float], title: str = "能力雷達圖") -> go.Figure:
    closed_labels = labels + labels[:1]
    closed_values = [as_number(value) for value in values] + [as_number(values[0]) if values else 0.0]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=closed_values,
            theta=closed_labels,
            fill="toself",
            name="能力分布",
            showlegend=False,
            mode="lines+markers",
            line=dict(color=CHART_ACCENT, width=3),
            marker=dict(size=7, color=CHART_HIGHLIGHT),
            fillcolor="rgba(216,90,82,.22)",
            hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        showlegend=False,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(157,176,181,.32)"),
            angularaxis=dict(gridcolor="rgba(157,176,181,.36)"),
        ),
        height=420,
    )
    return apply_chart_theme(fig)


def pitcher_allowed_rate(row: pd.Series) -> float:
    estimated_batters_faced = max(as_number(row.get("innings_pitched")) * 4.25, 1.0)
    return min(max((as_number(row.get("hits_allowed")) + as_number(row.get("walks"))) / estimated_batters_faced, 0.0), 1.0)


def sorted_standings(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if {"games_behind", "win_pct", "run_diff"}.issubset(df.columns):
        return df.sort_values(["games_behind", "win_pct", "run_diff"], ascending=[True, False, False])
    return df.sort_values("win_pct", ascending=False) if "win_pct" in df.columns else df


def source_status_panel(compact: bool = False) -> None:
    report = load_data_quality_report()
    text = source_note(report)
    verified_date = data_verified_date(report)
    generated_at = data_generated_time(report)
    hitter_count = int(report.get("available_hitter_count", 0) or 0)
    pitcher_count = int(report.get("available_pitcher_count", 0) or 0)
    quality_label = {"pass": "通過", "warning": "需注意", "failed": "失敗"}.get(str(report.get("quality_status")), "未知")
    if compact:
        st.caption(f"{text} 產生時間：{generated_at}。")
        return
    st.markdown(
        f"<div class='source-ribbon'><strong>CPBL 官方資料</strong><span>品質 {escape(quality_label)} · 更新 {escape(generated_at)}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <section class="cpbl-card source-card" aria-labelledby="source-status-heading">
          <h2 id="source-status-heading" class="card-heading">資料來源狀態</h2>
          <p>{text}</p>
          <div class="source-facts" role="list" aria-label="資料來源摘要">
            <div role="listitem"><strong>資料模式</strong><span>CPBL 官方 API</span></div>
            <div role="listitem"><strong>品質狀態</strong><span>{quality_label}</span></div>
            <div role="listitem"><strong>資料量</strong><span>球隊 {report.get("available_team_count", 0)} 隊 · 球員 {report.get("player_summary_count", report.get("available_player_count", 0))} 人</span></div>
            <div role="listitem"><strong>最後更新</strong><span>{generated_at}</span></div>
          </div>
          <p class="source-footnote">官方現役名單 {report.get("official_roster_count", 0)} 人；打者 {hitter_count} 人；投手 {pitcher_count} 人。核對日期：{verified_date}。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def rank_value(df: pd.DataFrame, player_id: str, metric: str, ascending: bool = False) -> tuple[int | None, int]:
    if df.empty or metric not in df.columns:
        return None, 0
    work = df[["player_id", metric]].copy()
    work["player_id"] = work["player_id"].astype(str)
    work[metric] = pd.to_numeric(work[metric], errors="coerce")
    work = work.dropna(subset=[metric]).sort_values(metric, ascending=ascending).reset_index(drop=True)
    total = len(work)
    matches = work.index[work["player_id"] == player_id].tolist()
    if not matches:
        return None, total
    return matches[0] + 1, total


def player_rank_summary(df: pd.DataFrame, row: pd.Series, metrics: list[tuple[str, bool]]) -> pd.DataFrame:
    rows = []
    for metric, ascending in metrics:
        rank, total = rank_value(df, str(row["player_id"]), metric, ascending=ascending)
        rows.append(
            {
                "指標": metric_name(metric),
                "數值": format_metric_value(metric, row.get(metric)),
                "聯盟排名": "N/A" if rank is None else f"{rank} / {total}",
                "排序方向": "越低越好" if ascending else "越高越好",
            }
        )
    return pd.DataFrame(rows)


def league_comparison(row: pd.Series, df: pd.DataFrame, metrics: list[tuple[str, bool]]) -> pd.DataFrame:
    rows = []
    for metric, lower_better in metrics:
        if metric not in df.columns:
            continue
        player_value = as_number(row.get(metric))
        league_avg = as_number(pd.to_numeric(df[metric], errors="coerce").mean())
        diff = player_value - league_avg
        better = diff < 0 if lower_better else diff > 0
        rows.append(
            {
                "指標": metric_name(metric),
                "球員": format_metric_value(metric, player_value),
                "聯盟平均": format_metric_value(metric, league_avg),
                "差距": format_metric_value(metric, abs(diff)),
                "判讀": "優於平均" if better else "低於平均",
            }
        )
    return pd.DataFrame(rows)


def percentile_rank(df: pd.DataFrame, row: pd.Series, metric: str, lower_is_better: bool = False) -> float:
    if metric not in df.columns:
        return 0.0
    values = pd.to_numeric(df[metric], errors="coerce").dropna()
    player_value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
    if values.empty or pd.isna(player_value):
        return 0.0
    ahead = values >= player_value if lower_is_better else values <= player_value
    return round(float(ahead.mean() * 100), 1)


def league_percentile_chart(row: pd.Series, df: pd.DataFrame, metrics: list[tuple[str, bool]]) -> go.Figure:
    labels = [metric_name(metric) for metric, _ in metrics]
    values = [percentile_rank(df, row, metric, lower_better) for metric, lower_better in metrics]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[CHART_ACCENT, CHART_HIGHLIGHT, CHART_SECONDARY, "#65b995", "#e87d72"][: len(values)],
            text=[f"{value:.0f}" for value in values],
            textposition="auto",
            hovertemplate="%{y}: 第 %{x:.1f} 百分位<extra></extra>",
        )
    )
    fig.update_layout(title="聯盟百分位（越高代表相對表現越前）", height=330, xaxis_title="百分位", yaxis_title="")
    fig.update_xaxes(range=[0, 100])
    return apply_chart_theme(fig)


def player_directory_row(row: pd.Series) -> pd.Series | None:
    player_id = str(row.get("player_id", ""))
    for directory in [PLAYERS, ROSTER]:
        if directory.empty or "player_id" not in directory.columns:
            continue
        match = directory[directory["player_id"].astype(str) == player_id]
        if not match.empty:
            return match.iloc[0]
    return None


def ranking_bar_chart(df: pd.DataFrame, title: str) -> go.Figure:
    name_column = next((column for column in ["player_name", "team"] if column in df.columns), df.columns[0])
    work = df.sort_values("metric_value", ascending=True)
    fig = px.bar(
        work,
        x="metric_value",
        y=name_column,
        orientation="h",
        title=title,
        labels={"metric_value": "指標數值", name_column: COLUMN_LABELS.get(name_column, name_column)},
        color_discrete_sequence=[CHART_ACCENT],
    )
    fig.update_layout(height=360)
    return fig


def find_stat_row_for_roster(roster_row: pd.Series, stat_df: pd.DataFrame) -> pd.Series | None:
    if stat_df.empty:
        return None
    player_id = str(roster_row.get("player_id", ""))
    if "player_id" in stat_df.columns and player_id:
        id_matches = stat_df[stat_df["player_id"].astype(str) == player_id]
        if not id_matches.empty:
            return id_matches.iloc[0]
    name = str(roster_row.get("player_name", ""))
    team = str(roster_row.get("team", ""))
    if {"player_name", "team"}.issubset(stat_df.columns):
        name_matches = stat_df[(stat_df["player_name"].astype(str) == name) & (stat_df["team"].astype(str) == team)]
        if not name_matches.empty:
            return name_matches.iloc[0]
    return None


def render_roster_only_player(row: pd.Series) -> None:
    render_player_header(row, "官方現役名單")
    metric_cards(
        [
            ("球隊", row.get("team", "N/A")),
            ("狀態", row.get("roster_status", "現役")),
            ("資料來源", "CPBL 官方"),
            ("目前一軍成績", "未列入官方全記錄表"),
        ]
    )
    st.subheader("本季成績")
    show_table(st, pd.DataFrame([row]), ["season", "team", "player_name", "roster_status", "source_note"])
    st.info("此球員存在於 CPBL 官方現役名單，但目前官方本季打擊或投球全記錄表未列出一軍成績。")

    c1, c2 = st.columns(2, gap="medium")
    c1.subheader("進階指標")
    c1.info("尚無可計算的打擊或投球進階指標。")
    c2.subheader("聯盟平均比較")
    c2.info("尚無一軍成績，暫不納入聯盟平均比較。")

    c3, c4 = st.columns(2, gap="medium")
    c3.subheader("排行摘要")
    c3.info("尚無排行榜資料。")
    c4.subheader("聯盟百分位")
    c4.info("尚無一軍成績，暫不計算聯盟百分位。")

    c5, c6 = st.columns(2, gap="medium")
    c5.subheader("能力雷達圖")
    c5.info("尚無足夠官方成績可建立能力雷達圖。")
    c6.subheader("相似球員推薦")
    c6.info("尚無同類型成績，暫不產生相似球員推薦。")


def render_player_header(row: pd.Series, player_type: str) -> None:
    directory_row = player_directory_row(row)
    role = row.get("position", row.get("role", row.get("role_or_position", "官方現役名單")))
    status = directory_row.get("roster_status", "官方成績表") if directory_row is not None else "官方成績表"
    season = int(as_number(row.get("season"), DATA_VERIFIED_DATE[:4]))
    identity_parts = [str(row["team"]).strip(), player_type.strip()]
    role_text = str(role).strip()
    if role_text and role_text not in identity_parts:
        identity_parts.append(role_text)
    identity_parts.append(str(season))
    identity_line = " · ".join(identity_parts)
    st.markdown(
        f"""
        <div class="cpbl-card player-hero">
          <h2>{escape(str(row["player_name"]))}</h2>
          <p>{escape(identity_line)}</p>
          <p>名單狀態：{escape(str(status))}</p>
          <p>資料核對：{data_verified_date()}；名單與成績取自 CPBL 官方網站，進階分數由官方成績衍生。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    profile_url = absolute_url(
        str(directory_row.get("profile_url", "") or "") if directory_row is not None else ""
    )
    if profile_url.startswith("https://www.cpbl.com.tw/"):
        st.markdown(f"[開啟 CPBL 官方球員頁]({profile_url})")


def page_home() -> None:
    page_kicker("首頁 / 專案介紹")
    st.title(APP_TITLE)
    st.caption("官方戰績、球員成績與衍生比較；資料以 CPBL 公開頁面為來源。")
    source_status_panel()
    metric_cards(
        [
            ("球隊數", TEAMS["team"].nunique()),
            ("官方球員總表", PLAYERS["player_id"].nunique() if not PLAYERS.empty else ROSTER["player_id"].nunique()),
            ("核對日期", data_verified_date()),
            ("資料模式", "官方 API"),
        ]
    )
    st.header("分析入口")
    workflows = [
        ("聯盟總覽", "戰績、勝差、近況、得失分差與主客場勝率。"),
        ("球員排行榜", "以 OPS、ISO、ERA、WHIP、K/BB 等指標篩選投打表現。"),
        ("球員個人頁", "查看本季成績、進階指標、聯盟比較、百分位與相似球員。"),
        ("投打對決", "以官方成績與聯盟平均 OBP 計算 LOG5 衍生機率。"),
        ("分項排行", "比較打者、投手與球隊的 Top / Bottom 結果。"),
    ]
    workflow_html = "\n".join(
        f"<div class='workflow-row' role='listitem'><span class='workflow-label'>{escape(title)}</span><span class='workflow-description'>{escape(body)}</span></div>"
        for title, body in workflows
    )
    st.markdown(f"<div class='workflow-grid' role='list' aria-label='分析入口'>{workflow_html}</div>", unsafe_allow_html=True)


def page_league() -> None:
    page_kicker("聯盟總覽")
    st.title("聯盟總覽")
    if TEAMS.empty:
        st.info("目前沒有可顯示的官方球隊戰績，請重新執行 API 資料抓取。")
        return
    source_status_panel(compact=True)
    st.caption("戰績表包含勝差、近況、勝率、得失分差與資料來源欄位。")
    season = st.selectbox("選擇年度", sorted(TEAMS["season"].unique(), reverse=True), key="league_season")
    season_teams = sorted_standings(TEAMS[TEAMS["season"] == season].copy())
    team_options = ["全部"] + sorted(season_teams["team"].unique())
    team = st.selectbox("選擇球隊", team_options, key=f"league_team_{season}")
    teams = season_teams
    if team != "全部":
        teams = teams[teams["team"] == team]
    metric_cards(
        [
            ("球隊數", season_teams["team"].nunique()),
            ("球員數", PLAYERS["player_id"].nunique() if not PLAYERS.empty else ROSTER["player_id"].nunique()),
            ("聯盟已賽場次", int(season_teams["games"].sum() / 2)),
            ("資料核對", data_verified_date()),
        ]
    )
    st.header("戰績表")
    show_table(
        st,
        teams,
        ["team", "games", "wins", "losses", "ties", "win_pct", "games_behind", "streak", "run_diff", "home_wins", "home_losses", "away_wins", "away_losses", "momentum_score", "source_note"],
    )
    st.header("勝率與得失分差")
    c1, c2 = st.columns(2, gap="medium")
    show_chart(
        c1,
        px.bar(
            teams,
            x="win_pct",
            y="team",
            orientation="h",
            title="勝率排行",
            color="win_pct",
            color_continuous_scale=["#65b995", CHART_HIGHLIGHT],
            labels={"win_pct": "勝率", "team": "球隊"},
        ),
    )
    show_chart(
        c2,
        px.bar(
            teams.sort_values("run_diff"),
            x="run_diff",
            y="team",
            orientation="h",
            title="得失分差",
            color="run_diff",
            color_continuous_scale=["#e87d72", CHART_HIGHLIGHT],
            labels={"run_diff": "得失分差", "team": "球隊"},
        ),
    )
    st.header("近期戰力與主客場勝率")
    c3, c4 = st.columns(2, gap="medium")
    show_chart(
        c3,
        px.bar(
            teams.sort_values("momentum_score"),
            x="momentum_score",
            y="team",
            orientation="h",
            title="近期戰力分數",
            labels={"momentum_score": "近期戰力", "team": "球隊"},
        ),
    )
    venue = teams[["team", "home_wins", "home_losses", "away_wins", "away_losses"]].copy()
    venue["主場勝率"] = venue.apply(lambda row: as_number(row["home_wins"]) / max(as_number(row["home_wins"]) + as_number(row["home_losses"]), 1), axis=1)
    venue["客場勝率"] = venue.apply(lambda row: as_number(row["away_wins"]) / max(as_number(row["away_wins"]) + as_number(row["away_losses"]), 1), axis=1)
    venue_long = venue.melt(id_vars="team", value_vars=["主場勝率", "客場勝率"], var_name="場地", value_name="勝率")
    show_chart(c4, px.bar(venue_long, x="勝率", y="team", color="場地", orientation="h", barmode="group", title="主客場勝率", labels={"team": "球隊"}))


def page_rankings() -> None:
    page_kicker("球員排行榜")
    st.title("球員排行榜")
    if BATTERS.empty or PITCHERS.empty:
        st.info("目前缺少官方打者或投手資料，請重新執行 API 資料抓取。")
        return
    tab_b, tab_p = st.tabs(["打者", "投手"])
    with tab_b:
        min_pa = st.number_input("最低打席 (PA)", min_value=0, max_value=max(int(BATTERS["pa"].max()), 0), value=1, step=1, key="ranking_min_pa")
        qualified_batters = BATTERS[BATTERS["pa"] >= min_pa]
        metric = st.selectbox(
            "打者指標",
            ["ops", "iso", "batting_average", "obp", "slg", "bb_k_ratio", "hitter_value_score"],
            format_func=metric_name,
            key="ranking_hitter_metric",
        )
        st.info(METRIC_HELP.get(metric, "此指標可用於排序與篩選打者表現。"))
        st.caption(f"符合最低打席條件：{len(qualified_batters)} 人。")
        show_table(st, get_top_players(qualified_batters, metric, 10))
    with tab_p:
        min_ip = st.number_input("最低投球局數 (IP)", min_value=0.0, max_value=max(float(PITCHERS["innings_pitched"].max()), 0.0), value=1.0, step=1.0, key="ranking_min_ip")
        qualified_pitchers = PITCHERS[PITCHERS["innings_pitched"] >= min_ip]
        metric = st.selectbox(
            "投手指標",
            ["era", "whip", "k_bb_ratio", "k_rate", "bb_rate", "hr_allowed_rate", "pitcher_value_score"],
            format_func=metric_name,
            key="ranking_pitcher_metric",
        )
        st.info(METRIC_HELP.get(metric, "此指標可用於排序與篩選投手表現。ERA、WHIP、BB% 與被 HR% 越低越好。"))
        st.caption(f"符合最低投球局數條件：{len(qualified_pitchers)} 人。")
        table = get_bottom_players(qualified_pitchers, metric, 10) if metric in LOWER_IS_BETTER else get_top_players(qualified_pitchers, metric, 10)
        show_table(st, table)


def page_player() -> None:
    page_kicker("球員個人頁")
    st.title("球員個人頁")
    source_status_panel(compact=True)
    st.caption("全體球員以 CPBL 官方現役名單與官方全記錄成績表的聯集為主；本季一軍成績表未列出的球員會顯示為「官方現役名單」。")
    player_type = st.radio("球員類型", ["全體球員", "打者", "投手"], horizontal=True, key="player_type")

    if player_type == "全體球員":
        directory = PLAYERS if not PLAYERS.empty else ROSTER
        if directory.empty:
            st.info("目前沒有可顯示的官方球員名單，請重新執行 API 資料抓取。")
            return
        team = st.selectbox("球隊選擇", sorted(directory["team"].dropna().unique()), key="player_directory_team")
        subset = directory[directory["team"] == team]
        player_name = st.selectbox("球員選擇", sorted(subset["player_name"].dropna().unique()), key=f"player_directory_name_{team}")
        roster_row = subset[subset["player_name"] == player_name].iloc[0]
        batter_row = find_stat_row_for_roster(roster_row, BATTERS)
        pitcher_row = find_stat_row_for_roster(roster_row, PITCHERS)
        if pitcher_row is not None and str(roster_row.get("player_type", "")) == "投手":
            row = pitcher_row
            stat_type = "投手"
            df = PITCHERS
        elif batter_row is not None:
            row = batter_row
            stat_type = "打者"
            df = BATTERS
        elif pitcher_row is not None:
            row = pitcher_row
            stat_type = "投手"
            df = PITCHERS
        else:
            render_roster_only_player(roster_row)
            return
    else:
        stat_type = player_type
        df = BATTERS if player_type == "打者" else PITCHERS
        if df.empty:
            st.info(f"目前沒有可顯示的{player_type}成績資料，請重新執行 API 資料抓取。")
            return
        team = st.selectbox("球隊選擇", sorted(df["team"].dropna().unique()), key=f"player_{player_type}_team")
        subset = df[df["team"] == team]
        player_name = st.selectbox("球員選擇", sorted(subset["player_name"].dropna().unique()), key=f"player_{player_type}_name_{team}")
        row = subset[subset["player_name"] == player_name].iloc[0]

    render_player_header(row, stat_type)
    if stat_type == "打者":
        metric_cards(
            [
                ("AVG", format_metric_value("batting_average", row["batting_average"])),
                ("OBP", format_metric_value("obp", row["obp"])),
                ("SLG", format_metric_value("slg", row["slg"])),
                ("OPS", format_metric_value("ops", row["ops"])),
                ("HR", int(row["home_runs"])),
            ]
        )
        season_columns = [
            "season",
            "team",
            "position",
            "pa",
            "ab",
            "hits",
            "doubles",
            "triples",
            "home_runs",
            "walks",
            "strikeouts",
            "stolen_bases",
            "batting_average",
            "obp",
            "slg",
            "ops",
            "iso",
            "bb_k_ratio",
        ]
        advanced_columns = [
            "contact_score",
            "power_score",
            "discipline_score",
            "hitter_value_score",
        ]
        rank_metrics = [("ops", False), ("batting_average", False), ("home_runs", False), ("bb_k_ratio", False), ("hitter_value_score", False)]
        compare_metrics = [("batting_average", False), ("obp", False), ("slg", False), ("ops", False), ("bb_k_ratio", False)]
        radar_labels = ["擊球接觸", "長打能力", "選球紀律", "綜合價值"]
        radar_values = [row["contact_score"], row["power_score"], row["discipline_score"], row["hitter_value_score"]]
    else:
        metric_cards(
            [
                ("ERA", format_metric_value("era", row["era"])),
                ("WHIP", format_metric_value("whip", row["whip"])),
                ("K", int(row["strikeouts"])),
                ("K/BB", format_metric_value("k_bb_ratio", row["k_bb_ratio"])),
                ("IP", format_metric_value("innings_pitched", row["innings_pitched"])),
            ]
        )
        season_columns = [
            "season",
            "team",
            "role",
            "innings_pitched",
            "earned_runs",
            "hits_allowed",
            "walks",
            "strikeouts",
            "home_runs_allowed",
            "era",
            "whip",
            "k_bb_ratio",
            "k_rate",
            "bb_rate",
            "hr_allowed_rate",
        ]
        advanced_columns = [
            "run_prevention_score",
            "strikeout_score",
            "command_score",
            "pitcher_value_score",
        ]
        rank_metrics = [("era", True), ("whip", True), ("strikeouts", False), ("k_bb_ratio", False), ("pitcher_value_score", False)]
        compare_metrics = [("era", True), ("whip", True), ("k_bb_ratio", False), ("k_rate", False), ("bb_rate", True)]
        radar_labels = ["失分壓制", "三振能力", "控球能力", "綜合價值"]
        radar_values = [row["run_prevention_score"], row["strikeout_score"], row["command_score"], row["pitcher_value_score"]]

    st.header("本季成績")
    show_table(st, pd.DataFrame([row]), season_columns)

    c1, c2 = st.columns(2, gap="medium")
    c1.subheader("進階指標")
    show_table(c1, pd.DataFrame([row]), advanced_columns)
    c2.subheader("聯盟平均比較")
    show_table(c2, league_comparison(row, df, compare_metrics))

    c3, c4 = st.columns(2, gap="medium")
    c3.subheader("排行摘要")
    show_table(c3, player_rank_summary(df, row, rank_metrics))
    c4.subheader("聯盟百分位")
    show_chart(c4, league_percentile_chart(row, df, compare_metrics))

    st.header("能力雷達圖")
    show_chart(st, radar_chart(radar_labels, radar_values, "能力雷達圖"))

    st.header("相似球員推薦")
    show_table(st, find_similar_players(df, row["player_id"], player_type=stat_type, n=5))


def page_matchup() -> None:
    page_kicker("投打對決")
    st.title("投打對決")
    if BATTERS.empty or PITCHERS.empty:
        st.info("目前缺少官方打者或投手資料，請重新執行 API 資料抓取。")
        return
    hitter_team = st.selectbox("打者球隊", sorted(BATTERS["team"].unique()), key="matchup_hitter_team")
    hitter_df = BATTERS[BATTERS["team"] == hitter_team]
    hitter = hitter_df[hitter_df["player_name"] == st.selectbox("打者", sorted(hitter_df["player_name"].unique()), key=f"matchup_hitter_{hitter_team}")].iloc[0]
    pitcher_team = st.selectbox("投手球隊", sorted(PITCHERS["team"].unique()), key="matchup_pitcher_team")
    pitcher_df = PITCHERS[PITCHERS["team"] == pitcher_team]
    pitcher = pitcher_df[pitcher_df["player_name"] == st.selectbox("投手", sorted(pitcher_df["player_name"].unique()), key=f"matchup_pitcher_{pitcher_team}")].iloc[0]

    hitter_obp = as_number(hitter["obp"])
    pitcher_obp_allowed = pitcher_allowed_rate(pitcher)
    league_obp = as_number(BATTERS["obp"].mean())
    probability = calculate_log5_probability(hitter_obp, pitcher_obp_allowed, league_obp)
    st.markdown("<div class='model-label'>MODEL · LOG5 官方成績衍生模型</div>", unsafe_allow_html=True)
    metric_cards(
        [
            ("打者 OBP", f"{hitter_obp:.3f}"),
            ("投手估算被上壘率", f"{pitcher_obp_allowed:.3f}"),
            ("聯盟平均 OBP", f"{league_obp:.3f}"),
            ("LOG5 上壘機率", "資料不足" if probability is None else f"{probability:.1%}"),
        ]
    )
    st.write(summarize_matchup_probability(probability))
    st.caption("投手端被上壘率由官方被安打、保送與投球局數估算；LOG5 為分析模型，不是官方逐打席對戰紀錄。")

    st.header("能力對照")
    c1, c2 = st.columns(2, gap="medium")
    show_chart(
        c1,
        radar_chart(
            ["擊球接觸", "長打能力", "選球紀律", "綜合價值"],
            [hitter["contact_score"], hitter["power_score"], hitter["discipline_score"], hitter["hitter_value_score"]],
            f"{hitter['player_name']} 打擊能力",
        ),
    )
    show_chart(
        c2,
        radar_chart(
            ["失分壓制", "三振能力", "控球能力", "綜合價值"],
            [pitcher["run_prevention_score"], pitcher["strikeout_score"], pitcher["command_score"], pitcher["pitcher_value_score"]],
            f"{pitcher['player_name']} 投球能力",
        ),
    )
    st.write("打者端重點看 OBP、SLG、OPS 與選球紀律；投手端重點看 ERA、WHIP、K/BB 與三振能力。")
    st.warning("LOG5 只是簡化展示模型，不代表實際比賽預測；若有逐打席資料，應以真實對戰紀錄優先。")


def page_metric_rankings() -> None:
    page_kicker("分項排行")
    st.title("分項排行")
    category = st.selectbox("類型", ["打者", "投手", "球隊"], key="metric_ranking_category")
    if category == "打者":
        df = BATTERS
        limit = max(1, min(10, len(df) // 2))
        metric = st.selectbox("指標", ["ops", "iso", "bb_k_ratio", "player_value_score"], format_func=metric_name, key="metric_ranking_metric_batter")
        top = get_top_players(df, metric, limit)
        bottom = get_bottom_players(df, metric, limit)
    elif category == "投手":
        df = PITCHERS
        limit = max(1, min(10, len(df) // 2))
        metric = st.selectbox("指標", ["era", "whip", "k_bb_ratio", "player_value_score"], format_func=metric_name, key="metric_ranking_metric_pitcher")
        top = get_bottom_players(df, metric, limit) if metric in LOWER_IS_BETTER else get_top_players(df, metric, limit)
        bottom = get_top_players(df, metric, limit) if metric in LOWER_IS_BETTER else get_bottom_players(df, metric, limit)
    else:
        df = TEAMS
        limit = max(1, min(10, len(df) // 2))
        metric = st.selectbox("指標", ["win_pct", "run_diff", "momentum_score"], format_func=metric_name, key="metric_ranking_metric_team")
        top = get_team_rankings(df, metric, limit)
        bottom = get_team_rankings(df, metric, limit, ascending=True)

    st.info(METRIC_HELP.get(metric, "此指標可用於快速排序與比較。"))
    st.header("排行結果")
    c1, c2 = st.columns(2, gap="medium")
    top_label = f"Top {len(top)}"
    bottom_label = f"Bottom {len(bottom)}"
    c1.subheader(top_label)
    if not top.empty:
        show_chart(c1, ranking_bar_chart(top, f"{metric_name(metric)} {top_label}"))
        show_table(c1, top)
    else:
        c1.info("目前沒有符合條件的排行資料。")
    c2.subheader(bottom_label)
    if not bottom.empty:
        show_chart(c2, ranking_bar_chart(bottom, f"{metric_name(metric)} {bottom_label}"))
        show_table(c2, bottom)
    else:
        c2.info("目前沒有符合條件的排行資料。")


PAGE_HANDLERS = {
    "首頁 / 專案介紹": page_home,
    "聯盟總覽": page_league,
    "球員排行榜": page_rankings,
    "球員個人頁": page_player,
    "投打對決": page_matchup,
    "分項排行": page_metric_rankings,
}

st.sidebar.markdown(
    "<div class='sidebar-brand'><div class='sidebar-brand-title'>CPBL 賽季資料</div><div class='sidebar-brand-subtitle'>官方成績與球員資料</div></div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("<div class='sidebar-nav-label'>頁面導覽</div>", unsafe_allow_html=True)
selected = st.sidebar.radio("頁面導覽", PAGES, label_visibility="collapsed")
st.sidebar.markdown(
    f"<div class='sidebar-status'><strong>官方資料已核對</strong><br>更新日期：{escape(data_verified_date())}<br>術語：OPS · ISO · AVG · OBP · SLG · ERA · WHIP · K/BB · LOG5</div>",
    unsafe_allow_html=True,
)
PAGE_HANDLERS[selected]()
