from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.app_helpers import (
    ProcessedDataError,
    load_csv,
    missing_processed_files,
    player_choice_options,
    processed_data_version,
    win_rate_series,
)
from src.data_quality import load_data_quality_report
from src.fetch_cpbl_data import absolute_url
from src.source_contract import SOURCE_DISPLAY_NAME, build_source_note
from src.freshness import data_freshness
from src.analysis_validation import DRIFT_METRICS, STABILITY_METRICS, priority_sensitivity, rank_stability, summarize_data_drift
from src.history import compare_metric_versions, later_snapshot_ids
from src.log5_matchup import calculate_log5_probability, summarize_matchup_probability
from src.rankings import get_bottom_players, get_team_rankings, get_top_players
from src.scouting import (
    DEFAULT_QUALIFICATION,
    build_evidence_signals,
    comparison_frame,
    percentile_rank,
    priority_options,
    qualification_label,
    qualification_upper_bound,
    qualified_population,
    rank_scouting_candidates,
)
from src.scouting_report import (
    build_report_manifest,
    build_watchlist_report,
    manifest_filename,
    report_filename,
    report_manifest_json,
    report_markdown,
)
from src.similarity import find_similar_players
from src.theme import STREAMLIT_CSS, STREAMLIT_LAYOUT_CSS


APP_TITLE = "CPBL 中職資料分析平台"
QUALITY_REPORT = load_data_quality_report()


def data_verified_date(report: dict | None = None) -> str:
    generated_at = str((report or QUALITY_REPORT).get("generated_at", ""))
    return generated_at[:10] if len(generated_at) >= 10 else "未記錄"


def source_note(report: dict | None = None) -> str:
    return build_source_note(data_verified_date(report))

def data_generated_time(report: dict | None = None) -> str:
    raw = str((report or QUALITY_REPORT).get("generated_at", ""))
    if not raw:
        return "未記錄"
    try:
        return datetime.fromisoformat(raw).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


def quality_status_label(value: object) -> str:
    status = str(value)
    if status == "pass":
        return "通過"
    if status == "warning":
        return "需注意"
    if status == "failed":
        return "失敗"
    return "未知"


def release_health_label(value: object) -> str:
    status = str(value)
    if status == "passed":
        return "通過"
    if status == "warning":
        return "需注意"
    if status == "failed":
        return "失敗"
    return "未知"


DATA_VERIFIED_DATE = data_verified_date()
SOURCE_NOTE = source_note()


PAGES = [
    "資料訊號總覽",
    "聯盟總覽",
    "版本趨勢",
    "分析驗證",
    "球探工作台",
    "球探報告",
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
    "priority_score",
    "qualified_percentile",
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
    "priority_score": "評估分數",
    "qualified_percentile": "符合門檻母體百分位",
    "usage_label": "資格量單位",
    "usage_value": "資格量",
    "evidence_strengths": "強項依據",
    "evidence_risks": "風險依據",
    "evidence_notes": "資料註記",
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
st.markdown(STREAMLIT_LAYOUT_CSS, unsafe_allow_html=True)
st.markdown(
    '<a class="skip-link" href="#cpbl-main">跳至主要內容</a><div id="cpbl-main" tabindex="-1"></div>',
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data(_data_version: tuple[tuple[str, int | None, int | None], ...]) -> dict[str, pd.DataFrame]:
    return {
        "teams": load_csv("teams.csv"),
        "roster": load_csv("roster.csv"),
        "batters": load_csv("batters_scored.csv"),
        "pitchers": load_csv("pitchers_scored.csv"),
        "players": load_csv("players_scored.csv"),
        "movements": load_csv("player_movements.csv"),
        "snapshot_history": load_csv("snapshot_history.csv"),
        "player_metric_history": load_csv("player_metric_history.csv"),
    }


MISSING_PROCESSED_FILES = missing_processed_files()
if MISSING_PROCESSED_FILES:
    st.error(
        "官方處理後資料不完整，已停止載入。請先在專案根目錄執行 run_project.bat --check。"
    )
    st.stop()
if QUALITY_REPORT.get("quality_status") == "failed":
    st.error("資料品質報告未通過或無法讀取，已停止顯示目前資料。請先重新執行 run_project.bat --check。")
    st.stop()
try:
    DATA = load_data(processed_data_version())
except ProcessedDataError as error:
    st.error(
        f"官方處理後資料無法讀取（{error}），已停止載入。請重新執行 run_project.bat --check。"
    )
    st.stop()
TEAMS = DATA["teams"]
ROSTER = DATA["roster"]
BATTERS = DATA["batters"]
PITCHERS = DATA["pitchers"]
PLAYERS = DATA["players"]
MOVEMENTS = DATA["movements"]
SNAPSHOT_HISTORY = DATA["snapshot_history"]
PLAYER_METRIC_HISTORY = DATA["player_metric_history"]
TABLE_DOWNLOAD_INDEX = 0

CHART_TEXT = "#e7efed"
CHART_MUTED = "#9db0b5"
CHART_GRID = "rgba(157,176,181,.22)"
CHART_ACCENT = "#d85a52"
CHART_SECONDARY = "#79b6bc"
CHART_HIGHLIGHT = "#d3a354"
HISTORY_METRICS = {
    "打者": ["ops", "batting_average", "obp", "slg", "iso", "bb_rate", "k_rate", "player_value_score"],
    "投手": ["era", "whip", "k_bb_ratio", "k_rate", "bb_rate", "player_value_score"],
}
VERSION_STATUS_LABELS = {
    "changed": "有變動",
    "new": "新增",
    "removed": "移除",
    "unchanged": "未變動",
}


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


def format_snapshot_time(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "未記錄"
    try:
        return datetime.fromisoformat(raw).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


def movement_period_label(frame: pd.DataFrame | None = None) -> str:
    details = QUALITY_REPORT.get("movement", {})
    baseline = details.get("baseline_captured_at", "")
    current = details.get("current_captured_at", "")
    if frame is not None and not frame.empty:
        baseline = frame.iloc[0].get("baseline_captured_at", baseline)
        current = frame.iloc[0].get("current_captured_at", current)
    if not baseline:
        return "尚待第二份已驗證快照"
    return f"{format_snapshot_time(baseline)} → {format_snapshot_time(current)}"


def movement_metric_label(metric: str) -> str:
    return COLUMN_LABELS.get(metric, METRIC_LABELS.get(metric, metric.upper()))


def format_movement_delta(metric: str, value: object) -> str:
    if pd.isna(value):
        return "N/A"
    number = as_number(value)
    formatted = format_metric_value(metric, abs(number))
    return f"{'+' if number > 0 else '-' if number < 0 else ''}{formatted}"


def movement_direction(row: pd.Series) -> str:
    if row.get("movement_status") == "new":
        return "新收錄"
    favorable = row.get("favorable_delta")
    if pd.isna(favorable) or as_number(favorable) == 0:
        return "持平"
    return "改善" if as_number(favorable) > 0 else "轉弱"


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


def metric_cards(items: list[tuple[object, ...]]) -> None:
    if not items:
        return
    cards: list[str] = []
    for item in items:
        label, value = item[0], item[1]
        detail = item[2] if len(item) > 2 else ""
        cards.append(
            "<div class='metric-card'><div class='metric-label'>"
            + escape(str(label))
            + "</div><div class='metric-value'>"
            + escape(str(value))
            + "</div><div class='metric-card-detail'>"
            + escape(str(detail))
            + "</div></div>"
        )
    st.markdown(f"<div class='metric-grid' role='group' aria-label='重點數據'>{''.join(cards)}</div>", unsafe_allow_html=True)


def page_kicker(section: str) -> str:
    return (
        "<div class='page-kicker'><strong>CPBL 官方資料</strong>"
        f"<span class='page-date'>{escape(section)} · 資料驗證 {escape(data_verified_date())}</span></div>"
    )


def page_intro(section: str, title: str, description: str) -> None:
    freshness = data_freshness(QUALITY_REPORT.get("generated_at", ""))
    st.markdown(
        "<div class='mobile-product-brand'>CPBL / SCOUTING DESK</div><section class='page-masthead' aria-label='頁面資料狀態'><div>"
        + page_kicker(section)
        + f"</div><div class='data-status-line status-{escape(str(freshness['status']))}'>"
        + f"官方資料已核對 · {escape(str(freshness['label']))}</div></section>",
        unsafe_allow_html=True,
    )
    st.title(title)
    st.caption(description)


def switch_page(page: str) -> None:
    st.session_state["main_navigation"] = page


def query_param_value(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value)


def query_param_values(name: str) -> list[str]:
    raw = query_param_value(name)
    return [value.strip() for value in raw.split(",") if value.strip()]


def set_report_query(player_type: str, team: str, threshold: float, priority: str, player_ids: list[str]) -> None:
    st.query_params["page"] = "球探報告"
    st.query_params["report_type"] = player_type
    st.query_params["report_team"] = team
    st.query_params["report_threshold"] = f"{threshold:g}"
    st.query_params["report_focus"] = priority
    if player_ids:
        st.query_params["watchlist"] = ",".join(player_ids[:4])
    elif "watchlist" in st.query_params:
        del st.query_params["watchlist"]


def clear_report_query() -> None:
    for name in ("watchlist", "report_type", "report_team", "report_threshold", "report_focus"):
        if name in st.query_params:
            del st.query_params[name]


def sync_page_query(page: str) -> None:
    if query_param_value("page") != page:
        st.query_params["page"] = page
    if page != "球員個人頁" and "player" in st.query_params:
        del st.query_params["player"]


def sync_player_query(player_id: object) -> None:
    player_id_text = str(player_id)
    if query_param_value("player") != player_id_text:
        st.query_params["player"] = player_id_text


def open_player_from_search(player_id: str) -> None:
    if not player_id:
        return
    st.session_state["main_navigation"] = "球員個人頁"
    st.session_state["player_type"] = "全體球員"
    st.session_state.pop("applied_player_request", None)
    st.session_state["requested_player_id"] = player_id


def player_search_options(frame: pd.DataFrame) -> dict[str, str]:
    required = {"player_id", "player_name", "team"}
    if frame.empty or not required.issubset(frame.columns):
        return {}
    directory = frame.copy()
    if "player_type" not in directory.columns:
        directory["player_type"] = "官方現役名單"
    directory["player_type"] = (
        directory["player_type"]
        .fillna("官方現役名單")
        .replace({"": "官方現役名單", "名單": "官方現役名單"})
    )
    directory = directory.drop_duplicates("player_id").sort_values(
        ["player_name", "team", "player_id"], kind="stable"
    )
    return {
        f"{row.player_name} · {row.team} · {row.player_type} · {row.player_id}": str(row.player_id)
        for row in directory[["player_id", "player_name", "team", "player_type"]].itertuples(index=False)
    }


def render_analysis_routes() -> None:
    routes = [
        ("球探工作台", "從資格門檻開始，建立可說明的觀察名單。"),
        ("球員排行榜", "依單一指標快速縮小本季候選範圍。"),
        ("投打對決", "用明確限制的 LOG5 情境理解投打差異。"),
    ]
    route_cards = "".join(
        "<section class='route-card'><div class='route-eyebrow'>分析入口</div>"
        f"<div class='route-label'>{escape(target)}</div>"
        f"<div class='route-description'>{escape(description)}</div></section>"
        for target, description in routes
    )
    st.markdown(f"<div class='route-grid' aria-label='主要分析入口'>{route_cards}</div>", unsafe_allow_html=True)
    target = st.selectbox("開啟分析頁", [route[0] for route in routes], key="analysis_route_target")
    st.button("前往分析頁", key="analysis_route_go", on_click=switch_page, args=(target,), width="content")


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
            domain=dict(x=[0.16, 0.84], y=[0.08, 0.92]),
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(157,176,181,.32)"),
            angularaxis=dict(gridcolor="rgba(157,176,181,.36)"),
        ),
        height=420,
    )
    fig = apply_chart_theme(fig)
    fig.update_layout(
        height=440,
        margin=dict(l=72, r=72, t=64, b=54),
    )
    return fig


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
    report = QUALITY_REPORT
    text = source_note(report)
    verified_date = data_verified_date(report)
    generated_at = data_generated_time(report)
    hitter_count = report.get("available_hitter_count", 0)
    pitcher_count = report.get("available_pitcher_count", 0)
    quality_label = quality_status_label(report.get("quality_status"))
    if compact:
        st.caption(f"{text} 產生時間：{generated_at}。")
        return
    safe_text = escape(str(text))
    safe_verified_date = escape(str(verified_date))
    safe_generated_at = escape(str(generated_at))
    safe_quality_label = escape(str(quality_label))
    safe_source_display_name = escape(str(SOURCE_DISPLAY_NAME))
    safe_team_count = escape(str(report.get("available_team_count", 0)))
    safe_player_count = escape(str(report.get("player_summary_count", report.get("available_player_count", 0))))
    safe_roster_count = escape(str(report.get("official_roster_count", 0)))
    safe_hitter_count = escape(str(hitter_count))
    safe_pitcher_count = escape(str(pitcher_count))
    st.markdown(
        f"<div class='source-ribbon'><strong>CPBL 官方資料</strong><span>品質 {safe_quality_label} · 更新 {safe_generated_at}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <section class="cpbl-card source-card" aria-labelledby="source-status-heading">
          <h2 id="source-status-heading" class="card-heading">資料來源狀態</h2>
          <p>{safe_text}</p>
          <div class="source-facts" role="list" aria-label="資料來源摘要">
            <div role="listitem"><strong>資料模式</strong><span>{safe_source_display_name}（HTML／表單分頁）</span></div>
            <div role="listitem"><strong>品質狀態</strong><span>{safe_quality_label}</span></div>
            <div role="listitem"><strong>資料量</strong><span>球隊 {safe_team_count} 隊 · 球員 {safe_player_count} 人</span></div>
            <div role="listitem"><strong>最後更新</strong><span>{safe_generated_at}</span></div>
          </div>
          <p class="source-footnote">官方現役名單 {safe_roster_count} 人；打者 {safe_hitter_count} 人；投手 {safe_pitcher_count} 人。核對日期：{safe_verified_date}。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

def render_data_trust_surface(
    report: dict,
    player_type: str | None = None,
    threshold: float | None = None,
    population_count: int | None = None,
) -> None:
    quality_status = str(report.get("quality_status", "unknown"))
    quality_label = quality_status_label(quality_status)
    details = [
        "來源網域：cpbl.com.tw",
        f"最後驗證：{data_generated_time(report)}",
        f"資料品質：{quality_label}",
        f"資料新鮮度：{data_freshness(report.get('generated_at', ''))['label']}",
    ]
    snapshot = report.get("snapshot", {})
    if isinstance(snapshot, dict) and snapshot.get("snapshot_id"):
        details.append(f"資料快照：{snapshot['snapshot_id']}")
        diff = snapshot.get("diff")
        if isinstance(diff, dict):
            details.append(
                f"本次異動：新增 {diff.get('added_rows', 0)}、移除 {diff.get('removed_rows', 0)}、變更 {diff.get('changed_rows', 0)}"
            )
    release_health = report.get("release_health")
    health_issues: list[str] = []
    if isinstance(release_health, dict):
        health_status = str(release_health.get("status", "unknown"))
        details.append(f"發布健康：{release_health_label(health_status)}")
        for check in release_health.get("checks", []):
            if isinstance(check, dict) and check.get("status") in {"warning", "failed"}:
                health_issues.append(str(check.get("summary", check.get("name", "未知檢查"))))
    if player_type is not None and threshold is not None and population_count is not None:
        details.append(f"符合門檻母體：{population_count} 人（{qualification_label(player_type)} ≥ {threshold:g}）")
    trust_items = "".join(f"<span class='trust-item'>{escape(item)}</span>" for item in details)
    st.markdown(f"<div class='trust-strip' role='note'>{trust_items}</div>", unsafe_allow_html=True)
    warnings = [str(item) for item in report.get("warnings", []) if str(item)]
    if quality_status != "pass" and warnings:
        st.warning("資料品質警示：" + "；".join(warnings))
    if isinstance(release_health, dict) and health_issues:
        health_status = str(release_health.get("status", "unknown"))
        message = "；".join(health_issues)
        if health_status == "failed":
            st.error("發布健康檢查失敗：" + message)
        else:
            st.warning("發布健康提醒：" + message)
    st.caption("LOG5 為情境計算，非校準預測模型；不可視為未來表現、勝負或名單決策預測。")


def render_player_evidence(row: pd.Series, population: pd.DataFrame, player_type: str, threshold: float) -> None:
    evidence = build_evidence_signals(row, population, player_type, threshold)
    st.header("評估依據")
    st.markdown(
        f"<span class='control-caption'>符合門檻母體 {len(population)} 人 · {qualification_label(player_type)} ≥ {threshold:g} · 百分位越高代表相對表現越前</span>",
        unsafe_allow_html=True,
    )
    sections = [
        ("強項", evidence["strengths"], "strength"),
        ("風險", evidence["risks"], "risk"),
        ("資料註記", evidence["notes"], "note"),
    ]
    cards: list[str] = []
    for heading, items, tone in sections:
        if items:
            content = "<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in items) + "</ul>"
        else:
            content = "<div class='evidence-empty'>未觸發既定門檻。</div>"
        cards.append(f"<section class='evidence-panel {tone}'><h3>{heading}</h3>{content}</section>")
    st.markdown(f"<div class='evidence-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


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


def league_percentile_chart(row: pd.Series, df: pd.DataFrame, metrics: list[tuple[str, bool]]) -> go.Figure:
    labels = [metric_name(metric) for metric, _ in metrics]
    values = [percentile_rank(df, row, metric, lower_better) or 0.0 for metric, lower_better in metrics]
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
    st.header("評估依據")
    st.info("尚無一軍成績，無法計算符合門檻母體百分位或評估訊號。")

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
        f"<section class='player-identity' aria-label='球員基本資料'><div>"
        f"<div class='identity-label'>PLAYER DOSSIER</div><h2>{escape(str(row['player_name']))}</h2>"
        f"<p>{escape(identity_line)} · 資料核對 {escape(data_verified_date())}</p></div>"
        f"<div class='identity-status'>{escape(str(status))}</div></section>",
        unsafe_allow_html=True,
    )
    profile_url = absolute_url(str(directory_row.get("profile_url", "") or "") if directory_row is not None else "")
    if profile_url.startswith("https://cpbl.com.tw/"):
        st.link_button("開啟 CPBL 官方球員頁", profile_url, width="content")


def render_version_trend_cta() -> None:
    st.button(
        "查看版本趨勢",
        icon=":material/timeline:",
        key="movement_trends_go",
        on_click=switch_page,
        args=("版本趨勢",),
        width="content",
    )


def render_movement_focus() -> None:
    st.header("評估分數變化焦點")
    st.caption(
        f"快照期間：{movement_period_label(MOVEMENTS)}。比較最近兩份已驗證快照的累計資料差異；"
        "不是逐場表現或未來預測。"
    )
    required = {"metric", "movement_status", "delta"}
    if MOVEMENTS.empty or not required.issubset(MOVEMENTS.columns):
        st.info("目前尚未形成兩份可比較快照；再次完成官方資料刷新後會建立差異基準。")
        render_version_trend_cta()
        return
    focus = MOVEMENTS[
        (MOVEMENTS["metric"] == "player_value_score")
        & (MOVEMENTS["movement_status"] == "changed")
    ].copy()
    focus["_magnitude"] = pd.to_numeric(focus["delta"], errors="coerce").abs()
    focus = focus.dropna(subset=["_magnitude"]).sort_values(
        ["_magnitude", "player_id"],
        ascending=[False, True],
        kind="stable",
    ).head(8)
    if focus.empty:
        st.info("最近兩份快照沒有球員綜合分數變化；可在「版本趨勢」查看其他指標差異。")
        render_version_trend_cta()
        return
    display = pd.DataFrame(
        {
            "球員": focus["player_name"],
            "球隊": focus["team"],
            "類型": focus["player_type"],
            "前次分數": focus["previous_value"].map(lambda value: format_metric_value("player_value_score", value)),
            "最新分數": focus["current_value"].map(lambda value: format_metric_value("player_value_score", value)),
            "分數差": focus["delta"].map(lambda value: format_movement_delta("player_value_score", value)),
            "有利方向": focus.apply(movement_direction, axis=1),
        }
    )
    show_table(st, display)
    render_version_trend_cta()

def render_player_movements(row: pd.Series, player_type: str) -> None:
    st.header("前次快照變化")
    player_id = str(row.get("player_id", ""))
    subset = MOVEMENTS.copy()
    if not subset.empty and {"player_id", "player_type"}.issubset(subset.columns):
        subset = subset[
            (subset["player_id"].astype("string") == player_id)
            & (subset["player_type"] == player_type)
        ].copy()
    st.caption(
        f"快照期間：{movement_period_label(subset)}。此表比較官方球季累計資料差異，"
        "不是逐場表現或未來預測。"
    )
    if subset.empty:
        st.info("這名球員目前沒有可比較的前次快照資料。")
        return
    display_rows = []
    for _, movement in subset.iterrows():
        metric = str(movement["metric"])
        previous = movement.get("previous_value")
        display_rows.append(
            {
                "指標": movement_metric_label(metric),
                "前次快照": "未收錄" if pd.isna(previous) else format_metric_value(metric, previous),
                "最新快照": format_metric_value(metric, movement.get("current_value")),
                "差值": format_movement_delta(metric, movement.get("delta")),
                "有利方向": movement_direction(movement),
            }
        )
    show_table(st, pd.DataFrame(display_rows))


def page_home() -> None:
    page_intro("資料訊號總覽", "資料訊號總覽", "以 CPBL 官方資料建立本季觀察框架：先確認資料，再進入可重現的比較。")
    render_data_trust_surface(QUALITY_REPORT)
    metric_cards(
        [
            ("球隊數", TEAMS["team"].nunique(), "官方戰績資料"),
            ("官方球員總表", PLAYERS["player_id"].nunique() if not PLAYERS.empty else ROSTER["player_id"].nunique(), "名單與成績聯集"),
            ("打者樣本", len(BATTERS), "官方全記錄表"),
            ("投手樣本", len(PITCHERS), "官方全記錄表"),
        ]
    )
    render_movement_focus()
    st.header("分析入口")
    st.caption("從一項清楚的工作開始，避免在沒有資格門檻與母體基準的情況下直接比較數字。")
    render_analysis_routes()

    st.header("資料可回答")
    st.markdown(
        "- 球員是否達到打席或投球局數資格門檻。\n"
        "- 評估分數由哪些官方成績訊號推動。\n"
        "- 球員在符合門檻母體中的相對百分位。\n"
        "- 官方資料目前可支撐與不可支撐的判讀範圍。"
    )
    st.header("資料限制")
    st.markdown(
        "- 目前使用本季官方彙總成績，不投射未來表現。\n"
        "- LOG5 為情境計算，非校準預測模型；不可視為未來表現、勝負或名單決策預測。\n"
        "- 未列入官方本季全記錄表的現役球員只呈現名單資訊，不計算百分位或評估訊號。"
    )
    workflows = [
        ("球探工作台", "查看打席與投球局數資格門檻、以官方成績產生固定評估分數，並比較符合門檻母體百分位。"),
        ("聯盟總覽", "戰績、勝差、近況、得失分差與主客場勝率。"),
        ("球員排行榜", "以 OPS、ISO、ERA、WHIP、K/BB 等指標篩選投打表現。"),
        ("球員個人頁", "查看本季成績、評估依據、聯盟比較、百分位與相似球員。"),
        ("投打對決", "以官方成績與聯盟平均 OBP 計算 LOG5 情境結果。"),
        ("分項排行", "比較打者、投手與球隊的 Top / Bottom 結果。"),
    ]
    workflow_html = "\n".join(
        f"<div class='workflow-row' role='listitem'><span class='workflow-label'>{escape(title)}</span><span class='workflow-description'>{escape(body)}</span></div>"
        for title, body in workflows
    )
    st.markdown(f"<div class='workflow-grid' role='list' aria-label='完整分析流程'>{workflow_html}</div>", unsafe_allow_html=True)
    source_status_panel()


def snapshot_option_label(snapshot_id: str) -> str:
    if SNAPSHOT_HISTORY.empty or "snapshot_id" not in SNAPSHOT_HISTORY:
        return snapshot_id
    matched = SNAPSHOT_HISTORY.loc[SNAPSHOT_HISTORY["snapshot_id"] == snapshot_id]
    if matched.empty:
        return snapshot_id
    return f"{format_snapshot_time(matched.iloc[0].get('captured_at'))} · {snapshot_id[-12:]}"


def snapshot_activity_chart(history: pd.DataFrame) -> go.Figure:
    frame = history.copy()
    frame["版本時間"] = frame["captured_at"].map(format_snapshot_time)
    fig = px.bar(
        frame,
        x="版本時間",
        y="changed_rows",
        title="各版本資料異動列數",
        labels={"changed_rows": "異動列數", "版本時間": "版本時間"},
        color="changed_rows",
        color_continuous_scale=[CHART_SECONDARY, CHART_ACCENT],
    )
    fig.update_layout(height=350, coloraxis_showscale=False)
    return fig


def player_history_chart(frame: pd.DataFrame, metric: str, player_name: str) -> go.Figure:
    values = frame.sort_values("captured_at", kind="stable").copy()
    values["版本時間"] = values["captured_at"].map(format_snapshot_time)
    fig = go.Figure(
        go.Scatter(
            x=values["版本時間"],
            y=pd.to_numeric(values[metric], errors="coerce"),
            mode="lines+markers",
            name=metric_name(metric),
            line=dict(color=CHART_ACCENT, width=3),
            marker=dict(color=CHART_HIGHLIGHT, size=9, line=dict(color=CHART_TEXT, width=1)),
            hovertemplate="%{x}<br>%{y}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"{player_name} · {metric_name(metric)} 版本走勢",
        xaxis_title="版本時間",
        yaxis_title=metric_name(metric),
        height=390,
        showlegend=False,
    )
    return fig


def version_change_chart(frame: pd.DataFrame, metric: str) -> go.Figure:
    changed = frame.loc[frame["movement_status"] == "changed"].copy()
    changed = changed.sort_values("favorable_delta", ascending=True, kind="stable").tail(12)
    colors = [CHART_SECONDARY if value >= 0 else CHART_ACCENT for value in changed["favorable_delta"]]
    fig = go.Figure(
        go.Bar(
            x=changed["favorable_delta"],
            y=changed["player_name"],
            orientation="h",
            marker_color=colors,
            name="有利變化",
            hovertemplate="%{y}<br>%{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"{metric_name(metric)} 有利變化幅度",
        xaxis_title="有利變化量",
        yaxis_title="球員",
        height=max(360, 46 * len(changed)),
        showlegend=False,
    )
    return fig


def page_snapshot_trends() -> None:
    page_intro(
        "版本趨勢",
        "版本趨勢",
        "以可稽核的 CPBL 官方資料快照檢視資料血緣、球員指標走勢與任意兩版差異。",
    )
    if SNAPSHOT_HISTORY.empty or PLAYER_METRIC_HISTORY.empty:
        st.info("目前尚未建立足夠的公開歷史資料。請先執行 python run_all.py --mode api。")
        return

    history = SNAPSHOT_HISTORY.sort_values("captured_at", kind="stable").reset_index(drop=True)
    players = PLAYER_METRIC_HISTORY.copy()
    version_ids = history["snapshot_id"].astype(str).tolist()
    oldest = format_snapshot_time(history.iloc[0]["captured_at"])
    latest = format_snapshot_time(history.iloc[-1]["captured_at"])
    schema_drift_count = int(history["schema_changed_files"].fillna("").astype(str).ne("").sum())
    metric_cards(
        [
            ("資料版本", len(history), "通過品質檢查的官方快照"),
            ("歷史球員", players["player_id"].nunique(), "依 CPBL 官方球員 ID 去重"),
            ("涵蓋期間", f"{oldest[:10]} → {latest[:10]}", "時間採快照 captured_at"),
            ("Schema 漂移", schema_drift_count, "欄位新增或移除的版本數"),
        ]
    )

    st.header("資料版本血緣")
    st.caption("每個版本由處理後資料的 SHA-256 指紋識別；內部原始 HTML 與本機路徑不會出現在公開輸出。")
    nodes = []
    for index, row in history.iterrows():
        current_class = " snapshot-node-current" if index == len(history) - 1 else ""
        nodes.append(
            f"<div class='snapshot-node{current_class}' role='listitem'>"
            f"<span class='snapshot-date'>{escape(format_snapshot_time(row['captured_at']))}</span>"
            f"<strong>{escape(str(row['snapshot_id'])[-12:])}</strong>"
            f"<span>異動 {int(row['changed_rows'])} 列 · 新增 {int(row['added_rows'])} · 移除 {int(row['removed_rows'])}</span>"
            "</div>"
        )
    st.markdown(
        f"<div class='snapshot-timeline' role='list' aria-label='資料版本時間軸'>{''.join(nodes)}</div>",
        unsafe_allow_html=True,
    )
    show_chart(st, snapshot_activity_chart(history))
    lineage_table = pd.DataFrame(
        {
            "版本時間": history["captured_at"].map(format_snapshot_time),
            "版本 ID": history["snapshot_id"],
            "前一版本": history["previous_snapshot_id"].fillna("—"),
            "總列數": history["total_rows"],
            "異動列數": history["changed_rows"],
            "品質狀態": history["quality_status"].map(
                lambda value: "通過" if value == "pass" else "警示" if value == "warning" else "未知"
            ),
        }
    )
    show_table(st, lineage_table)

    st.header("球員指標走勢")
    control_type, control_player, control_metric = st.columns(3, gap="medium")
    player_type = control_type.selectbox("球員類型", ["打者", "投手"], key="history_player_type")
    type_history = players.loc[players["player_type"] == player_type].copy()
    directory = (
        type_history[["player_id", "player_name", "team"]]
        .drop_duplicates("player_id")
        .sort_values(["player_name", "team", "player_id"], kind="stable")
    )
    player_labels = {
        str(row.player_id): f"{row.player_name} · {row.team} · {row.player_id}"
        for row in directory.itertuples(index=False)
    }
    player_ids = list(player_labels)
    if not player_ids:
        st.info(f"目前沒有可比較的{player_type}歷史資料。")
        return
    player_id = control_player.selectbox(
        "球員",
        player_ids,
        format_func=lambda value: player_labels.get(value, value),
        key=f"history_player_{player_type}",
    )
    metric_options = [
        metric
        for metric in HISTORY_METRICS[player_type]
        if metric in type_history.columns and type_history[metric].notna().any()
    ]
    metric = control_metric.selectbox(
        "指標",
        metric_options,
        format_func=metric_name,
        key=f"history_metric_{player_type}",
    )
    selected_history = type_history.loc[type_history["player_id"].astype(str) == str(player_id)].copy()
    player_name = str(selected_history.iloc[-1]["player_name"])
    st.caption(f"{metric_name(metric)} 僅反映各次官方彙總資料快照，不代表單場或逐打席表現。")
    show_chart(st, player_history_chart(selected_history, metric, player_name))
    trend_table = pd.DataFrame(
        {
            "版本時間": selected_history["captured_at"].map(format_snapshot_time),
            "球員": selected_history["player_name"],
            "球隊": selected_history["team"],
            metric_name(metric): selected_history[metric].map(lambda value: format_metric_value(metric, value)),
            "版本 ID": selected_history["snapshot_id"],
        }
    )
    show_table(st, trend_table)

    st.header("版本差異比較")
    if len(version_ids) < 2:
        st.info("至少需要兩個通過品質檢查的版本才能進行差異比較。")
        return
    baseline_control, current_control = st.columns(2, gap="medium")
    baseline_id = baseline_control.selectbox(
        "基準版本",
        version_ids[:-1],
        index=0,
        format_func=snapshot_option_label,
        key="history_baseline_version",
        help="基準版本必須早於比較版本。",
    )
    current_options = later_snapshot_ids(version_ids, baseline_id)
    current_id = current_control.selectbox(
        "比較版本",
        current_options,
        index=len(current_options) - 1,
        format_func=snapshot_option_label,
        key=f"history_current_version_{baseline_id}",
        help="只顯示晚於目前基準的資料版本。",
    )
    st.caption("已限制為時間順序有效的版本組合，避免反向或同版本比較。")
    comparison = compare_metric_versions(players, baseline_id, current_id, player_type, metric)
    if comparison.empty:
        st.info("所選版本沒有可比較的球員指標。")
        return
    counts = comparison["movement_status"].value_counts()
    metric_cards(
        [
            ("有變動", int(counts.get("changed", 0)), metric_name(metric)),
            ("新增", int(counts.get("new", 0)), "只存在比較版本"),
            ("移除", int(counts.get("removed", 0)), "只存在基準版本"),
            ("未變動", int(counts.get("unchanged", 0)), "兩版數值相同"),
        ]
    )
    changed = comparison.loc[comparison["movement_status"] == "changed"]
    if not changed.empty:
        show_chart(st, version_change_chart(comparison, metric))
    else:
        st.info("兩個版本之間沒有球員指標數值變動。")
    comparison_table = pd.DataFrame(
        {
            "球員": comparison["player_name"],
            "球隊": comparison["team"],
            "狀態": comparison["movement_status"].map(VERSION_STATUS_LABELS),
            "基準值": comparison["previous_value"].map(lambda value: format_metric_value(metric, value)),
            "比較值": comparison["current_value"].map(lambda value: format_metric_value(metric, value)),
            "差值": comparison["delta"].map(lambda value: format_movement_delta(metric, value)),
            "有利變化": comparison["favorable_delta"].map(lambda value: format_movement_delta(metric, value)),
            "CPBL 球員 ID": comparison["player_id"],
        }
    )
    show_table(st, comparison_table)
def _format_validation_ratio(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{as_number(value):.0%}"


def _format_validation_correlation(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{as_number(value):.2f}"


def stability_validation_chart(frame: pd.DataFrame, metric: str) -> go.Figure:
    chart = go.Figure()
    x = frame["current_captured_at"].map(format_snapshot_time)
    chart.add_trace(
        go.Scatter(
            x=x,
            y=frame["top_k_overlap"],
            mode="lines+markers",
            name="Top-K 重疊率",
            line=dict(color=CHART_ACCENT, width=3),
        )
    )
    chart.add_trace(
        go.Scatter(
            x=x,
            y=frame["spearman_rank_correlation"],
            mode="lines+markers",
            name="Spearman ρ",
            yaxis="y2",
            line=dict(color=CHART_SECONDARY, width=3),
        )
    )
    chart.update_layout(
        title=f"{metric_name(metric)} · 相鄰版本排名一致性",
        height=390,
        yaxis=dict(title="Top-K 重疊率", range=[0, 1], tickformat=".0%"),
        yaxis2=dict(title="Spearman ρ", overlaying="y", side="right", range=[-1, 1]),
        legend=dict(orientation="h", y=1.12),
    )
    return apply_chart_theme(chart)


def drift_validation_chart(frame: pd.DataFrame, metric: str) -> go.Figure:
    chart = go.Figure()
    x = frame["current_captured_at"].map(format_snapshot_time)
    chart.add_trace(
        go.Scatter(
            x=x,
            y=frame["baseline_median"],
            mode="lines+markers",
            name="基準版本中位數",
            line=dict(color=CHART_MUTED, width=2, dash="dot"),
        )
    )
    chart.add_trace(
        go.Scatter(
            x=x,
            y=frame["current_median"],
            mode="lines+markers",
            name="比較版本中位數",
            line=dict(color=CHART_HIGHLIGHT, width=3),
        )
    )
    chart.update_layout(
        title=f"{metric_name(metric)} · 相鄰版本中位數變化",
        height=370,
        xaxis_title="比較版本時間",
        yaxis_title=metric_name(metric),
    )
    return apply_chart_theme(chart)


def page_analysis_validation() -> None:
    page_intro(
        "分析驗證",
        "分析驗證",
        "以跨快照穩定性、資料分布變化與權重敏感度，檢查分析結果的可解釋範圍；這些是描述性驗證，不是未來表現預測。",
    )
    if SNAPSHOT_HISTORY.empty or PLAYER_METRIC_HISTORY.empty:
        st.info("目前尚未建立足夠的公開歷史資料。請先執行 python run_all.py --mode api。")
        return

    history = PLAYER_METRIC_HISTORY.sort_values("captured_at", kind="stable").reset_index(drop=True)
    player_type = st.radio(
        "球員類型",
        ["打者", "投手"],
        horizontal=True,
        key="validation_player_type",
    )
    available_history = history.loc[history["player_type"] == player_type]
    available_metrics = [
        metric
        for metric in STABILITY_METRICS[player_type]
        if metric in available_history.columns and available_history[metric].notna().any()
    ]
    if not available_metrics:
        st.info(f"目前沒有足夠的{player_type}歷史指標可驗證。")
        return

    metric_cards(
        [
            ("資料版本", history["snapshot_id"].nunique(), "官方快照數"),
            ("分析球員", available_history["player_id"].nunique(), f"{player_type}歷史球員"),
            ("可比較版本", max(0, history["snapshot_id"].nunique() - 1), "相鄰版本組合"),
            ("驗證定位", "描述性", "不代表預測準確率"),
        ]
    )

    stability_tab, drift_tab, sensitivity_tab = st.tabs(
        ["排名穩定性", "資料分布變化", "權重敏感度"]
    )
    with stability_tab:
        st.subheader("排名穩定性")
        control_metric, control_top_k = st.columns(2, gap="medium")
        metric = control_metric.selectbox(
            "穩定性指標",
            available_metrics,
            format_func=metric_name,
            key="validation_stability_metric",
        )
        top_k = control_top_k.selectbox(
            "Top-K",
            [5, 10, 20],
            index=1,
            key="validation_stability_top_k",
        )
        stability = rank_stability(history, player_type, metric, top_k=top_k)
        st.caption("Top-K 重疊率越高，代表相鄰版本的前段名單越一致；Spearman ρ 越接近 1，代表整體排名順序越穩定。")
        if stability.empty:
            st.info("目前只有一個可用版本，尚無法計算相鄰版本排名穩定性。")
        else:
            latest = stability.iloc[-1]
            metric_cards(
                [
                    ("最新 Top-K 重疊", _format_validation_ratio(latest["top_k_overlap"]), "相鄰兩版"),
                    ("最新 Spearman ρ", _format_validation_correlation(latest["spearman_rank_correlation"]), "共同球員排名"),
                    ("共同球員", int(latest["common_population"]), "可比較母體"),
                ]
            )
            show_chart(st, stability_validation_chart(stability, metric))
            stability_table = pd.DataFrame(
                {
                    "比較版本": stability["current_captured_at"].map(format_snapshot_time),
                    "基準版本": stability["baseline_snapshot_id"],
                    "比較版本 ID": stability["current_snapshot_id"],
                    "基準母體": stability["baseline_population"],
                    "比較母體": stability["current_population"],
                    "Top-K 重疊率": stability["top_k_overlap"].map(_format_validation_ratio),
                    "Spearman ρ": stability["spearman_rank_correlation"].map(_format_validation_correlation),
                    "平均排名變化": stability["mean_abs_rank_delta"].map(lambda value: "N/A" if pd.isna(value) else f"{as_number(value):.1f}"),
                }
            )
            show_table(st, stability_table)

    with drift_tab:
        st.subheader("資料分布變化")
        drift_options = [
            metric
            for metric in DRIFT_METRICS[player_type]
            if metric in available_history.columns and available_history[metric].notna().any()
        ]
        drift_metric = st.selectbox(
            "分布指標",
            drift_options,
            format_func=metric_name,
            key="validation_drift_metric",
        )
        drift = summarize_data_drift(history, player_type, [drift_metric])
        st.caption("中位數、平均數與涵蓋人數呈現官方彙總資料的版本差異；分布變化本身不等於資料品質錯誤。")
        if drift.empty:
            st.info("目前沒有可比較的分布資料。")
        else:
            latest = drift.iloc[-1]
            metric_cards(
                [
                    ("本版涵蓋", int(latest["current_count"]), f"{metric_name(drift_metric)} 有效值"),
                    ("涵蓋變化", _format_validation_ratio(as_number(latest["coverage_change_pct"]) / 100 if not pd.isna(latest["coverage_change_pct"]) else None), "相對前版"),
                    ("中位數差", format_movement_delta(drift_metric, latest["median_delta"]), "描述性變化"),
                ]
            )
            recent_drift = drift.tail(8).reset_index(drop=True)
            show_chart(st, drift_validation_chart(recent_drift, drift_metric))
            drift_table = pd.DataFrame(
                {
                    "比較版本": recent_drift["current_captured_at"].map(format_snapshot_time),
                    "基準版本": recent_drift["baseline_snapshot_id"],
                    "前版涵蓋": recent_drift["baseline_count"],
                    "本版涵蓋": recent_drift["current_count"],
                    "涵蓋變化": recent_drift["coverage_change_pct"].map(lambda value: "N/A" if pd.isna(value) else f"{as_number(value):+.1f}%"),
                    "前版中位數": recent_drift["baseline_median"].map(lambda value: format_metric_value(drift_metric, value)),
                    "本版中位數": recent_drift["current_median"].map(lambda value: format_metric_value(drift_metric, value)),
                    "中位數變化": recent_drift["median_delta"].map(lambda value: format_movement_delta(drift_metric, value)),
                }
            )
            show_table(st, drift_table)

    with sensitivity_tab:
        st.subheader("權重敏感度")
        source = BATTERS if player_type == "打者" else PITCHERS
        default_threshold = float(DEFAULT_QUALIFICATION[player_type])
        threshold_max = qualification_upper_bound(source, player_type)
        threshold = st.number_input(
            f"最低{qualification_label(player_type)}",
            min_value=0.0,
            max_value=max(default_threshold, threshold_max),
            value=min(default_threshold, max(default_threshold, threshold_max)),
            step=1.0,
            key="validation_sensitivity_threshold",
        )
        focus = st.selectbox(
            "評估重點",
            priority_options(player_type),
            format_func=lambda value: value,
            key="validation_sensitivity_focus",
        )
        teams = ["全部"] + sorted(str(team) for team in source["team"].dropna().unique())
        team = st.selectbox("球隊篩選", teams, key="validation_sensitivity_team")
        perturbation = st.selectbox(
            "權重擾動幅度",
            [0.05, 0.10, 0.15],
            index=1,
            format_func=lambda value: f"±{value:.0%}",
            key="validation_sensitivity_perturbation",
        )
        sensitivity = priority_sensitivity(
            source,
            player_type,
            threshold,
            focus,
            team=team,
            perturbation=perturbation,
            top_k=10,
        )
        st.caption("每個情境把一項權重上下調整指定幅度，並按比例重分配其他權重；結果用來檢查排序是否過度依賴單一假設。")
        if sensitivity.empty:
            st.info("目前沒有符合條件的候選球員。")
        else:
            sensitivity_table = pd.DataFrame(
                {
                    "情境": sensitivity["scenario"].map({"baseline": "基準", "increase": "提高指標權重", "decrease": "降低指標權重"}),
                    "變動指標": sensitivity["changed_metric"],
                    "權重變化": sensitivity["weight_delta"].map(lambda value: f"{as_number(value):+.0%}"),
                    "候選人數": sensitivity["candidate_count"],
                    "Top-K 重疊率": sensitivity["top_k_overlap"].map(_format_validation_ratio),
                    "排名相關": sensitivity["rank_correlation"].map(_format_validation_correlation),
                    "基準領先者": sensitivity["baseline_leader"],
                    "情境領先者": sensitivity["scenario_leader"],
                }
            )
            show_table(st, sensitivity_table)

def page_league() -> None:
    page_intro("聯盟總覽", "聯盟總覽", "以球隊戰績、得失分與主客場差異，建立本季聯盟的可比較基準。")
    if TEAMS.empty:
        st.info("目前沒有可顯示的官方球隊戰績，請重新執行官方資料刷新。")
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
    venue["主場勝率"] = win_rate_series(venue["home_wins"], venue["home_losses"])
    venue["客場勝率"] = win_rate_series(venue["away_wins"], venue["away_losses"])
    venue_long = venue.melt(id_vars="team", value_vars=["主場勝率", "客場勝率"], var_name="場地", value_name="勝率")
    show_chart(c4, px.bar(venue_long, x="勝率", y="team", color="場地", orientation="h", barmode="group", title="主客場勝率", labels={"team": "球隊"}))


def page_scouting_workbench() -> None:
    page_intro("球探工作台", "球探工作台", "以可重現的資格門檻、既有衍生分數與聯盟百分位建立本季觀察名單；不預測未來表現。")
    player_type = st.radio("球員類型", ["打者", "投手"], horizontal=True, key="scouting_player_type")
    source = BATTERS if player_type == "打者" else PITCHERS
    if source.empty:
        st.info(f"目前缺少官方{player_type}成績，無法建立球探工作台。")
        return

    usage_label = qualification_label(player_type)
    default_threshold = DEFAULT_QUALIFICATION[player_type]
    maximum = qualification_upper_bound(source, player_type)
    st.markdown("<span class='control-caption'>設定資料母體：球隊、資格門檻與評估重點會共同決定候選範圍。</span>", unsafe_allow_html=True)
    control_team, control_threshold, control_priority = st.columns(3, gap="medium")
    team = control_team.selectbox("球隊", ["全部", *sorted(source["team"].dropna().unique())], key=f"scouting_team_{player_type}")
    if player_type == "打者":
        threshold = control_threshold.number_input("最低打席 (PA)", min_value=int(default_threshold), max_value=max(int(maximum), int(default_threshold)), value=int(default_threshold), step=5, key="scouting_min_pa")
    else:
        threshold = control_threshold.number_input("最低投球局數 (IP)", min_value=float(default_threshold), max_value=maximum, value=float(default_threshold), step=1.0, key="scouting_min_ip")
    priority = control_priority.selectbox("評估重點", priority_options(player_type), key=f"scouting_priority_{player_type}")

    qualified = qualified_population(source, player_type, float(threshold))
    render_data_trust_surface(QUALITY_REPORT, player_type, float(threshold), len(qualified))
    candidates = rank_scouting_candidates(source, player_type, float(threshold), priority, team)
    if candidates.empty:
        st.info(f"目前沒有符合條件的球員。資格門檻維持 {usage_label} ≥ {float(threshold):g}，請調整球隊。")
        return

    st.header("候選名單")
    st.caption(f"評估重點：{priority}；排名依評估分數降冪，同分時依 CPBL 球員 ID 排序。")
    display_columns = (
        ["player_id", "player_name", "team", "pa", "priority_score", "qualified_percentile", "contact_score", "power_score", "discipline_score", "hitter_value_score", "evidence_strengths", "evidence_risks", "evidence_notes"]
        if player_type == "打者"
        else ["player_id", "player_name", "team", "innings_pitched", "priority_score", "qualified_percentile", "run_prevention_score", "strikeout_score", "command_score", "pitcher_value_score", "evidence_strengths", "evidence_risks", "evidence_notes"]
    )
    show_table(st, candidates, display_columns)

    options = {
        f"{row.player_name} · {row.team} · {row.player_id}": str(row.player_id)
        for row in candidates[["player_id", "player_name", "team"]].itertuples(index=False)
    }
    selected_labels = st.multiselect(
        "比較球員",
        list(options),
        max_selections=4,
        help="最多選擇 4 位球員；比較表會保留此選擇順序。",
        key=f"scouting_compare_{player_type}",
    )
    st.caption("最多選擇 4 位球員。")
    comparison = comparison_frame(candidates, [options[label] for label in selected_labels], player_type)
    st.header("並列比較")
    if comparison.empty:
        st.info("選擇候選名單中的球員後，這裡會顯示相同資格母體下的並列數據。")
    else:
        show_table(st, comparison)


def page_scouting_report() -> None:
    page_intro(
        "球探報告",
        "球探報告",
        "把目前的球探候選人固定成一份具備資料版本、資格門檻與判讀依據的可下載觀察名單。",
    )
    report_type_param = query_param_value("report_type")
    type_index = 1 if report_type_param == "投手" else 0
    player_type = st.radio("球員類型", ["打者", "投手"], index=type_index, horizontal=True, key="scouting_report_type")
    source = BATTERS if player_type == "打者" else PITCHERS
    if source.empty:
        st.info(f"目前缺少官方{player_type}成績，無法建立球探報告。")
        return

    usage_label = qualification_label(player_type)
    default_threshold = float(DEFAULT_QUALIFICATION[player_type])
    maximum = qualification_upper_bound(source, player_type)
    try:
        requested_threshold = float(query_param_value("report_threshold"))
    except ValueError:
        requested_threshold = default_threshold
    threshold_value = min(max(requested_threshold, default_threshold), maximum)

    team_options = ["全部", *sorted(source["team"].dropna().astype(str).unique())]
    requested_team = query_param_value("report_team")
    team_index = team_options.index(requested_team) if requested_team in team_options else 0
    control_team, control_threshold, control_priority = st.columns(3, gap="medium")
    team = control_team.selectbox("球隊", team_options, index=team_index, key=f"report_team_{player_type}")
    if player_type == "打者":
        threshold = control_threshold.number_input(
            "最低打席 (PA)",
            min_value=int(default_threshold),
            max_value=max(int(maximum), int(default_threshold)),
            value=int(threshold_value),
            step=5,
            key="report_min_pa",
        )
    else:
        threshold = control_threshold.number_input(
            "最低投球局數 (IP)",
            min_value=default_threshold,
            max_value=maximum,
            value=float(threshold_value),
            step=1.0,
            key="report_min_ip",
        )
    priorities = priority_options(player_type)
    requested_priority = query_param_value("report_focus")
    priority_index = priorities.index(requested_priority) if requested_priority in priorities else 0
    priority = control_priority.selectbox("評估重點", priorities, index=priority_index, key=f"report_priority_{player_type}")

    qualified = qualified_population(source, player_type, float(threshold))
    render_data_trust_surface(QUALITY_REPORT, player_type, float(threshold), len(qualified))
    candidates = rank_scouting_candidates(source, player_type, float(threshold), priority, team)
    if candidates.empty:
        st.info(f"目前沒有符合條件的球員。資格門檻維持 {usage_label} ≥ {float(threshold):g}，請調整球隊或門檻。")
        return

    st.header("觀察名單")
    st.caption("最多選擇 4 位球員；報告會保留選取順序，並只使用同一資格母體的評估結果。")
    options = player_choice_options(candidates)
    requested_ids = query_param_values("watchlist")
    option_by_id = {player_id: label for label, player_id in options.items()}
    default_labels = [option_by_id[player_id] for player_id in requested_ids if player_id in option_by_id]
    selected_labels = st.multiselect(
        "觀察名單",
        list(options),
        default=default_labels[:4],
        max_selections=4,
        help="最多選擇 4 位球員；選取順序會保留在下載報告中。",
        key=f"report_watchlist_{player_type}",
    )
    selected_ids = [options[label] for label in selected_labels]

    action_share, action_clear = st.columns(2, gap="medium")
    if action_share.button("建立可分享連結", icon=":material/link:", width="stretch", key="report_share"):
        set_report_query(player_type, team, float(threshold), priority, selected_ids)
        st.success("已將球員、資格門檻與評估重點寫入目前網址參數。")
    if action_clear.button("清除觀察名單", icon=":material/clear_all:", width="stretch", key="report_clear"):
        clear_report_query()
        st.rerun()

    report = build_watchlist_report(candidates, selected_ids, player_type)
    st.header("評估報告")
    st.caption("資料版本與品質狀態會隨下載球探報告一併保留。")
    st.caption("下載稽核 Manifest JSON 會保留報告條件與資料血緣。")
    st.caption("建立可分享連結後，網址會保留目前的球員與評估條件。")
    st.caption("選取球員後會顯示報告 ID，方便核對同一份分析成果。")
    if report.empty:
        st.info("選擇候選球員後，這裡會產生可下載的球探報告。")
        return

    snapshot = QUALITY_REPORT.get("snapshot", {})
    snapshot_id = str(snapshot.get("snapshot_id", "latest")) if isinstance(snapshot, dict) else "latest"
    quality_status = quality_status_label(QUALITY_REPORT.get("quality_status"))
    metadata = {
        "player_type": player_type,
        "qualification": f"{usage_label} ≥ {float(threshold):g}",
        "priority": priority,
        "qualified_count": len(qualified),
        "snapshot_id": snapshot_id,
        "generated_at": data_generated_time(),
        "quality_status": quality_status,
    }
    manifest = build_report_manifest(report, {**metadata, "team": team})
    report_id = str(manifest["report_id"])
    st.caption(f"資料版本：{snapshot_id} · 產生時間：{metadata['generated_at']} · 品質狀態：{quality_status} · 報告 ID：{report_id}")
    chart = report.sort_values("priority_score", ascending=True)
    show_chart(
        st,
        px.bar(
            chart,
            x="priority_score",
            y="player_name",
            orientation="h",
            title="觀察名單評估分數",
            labels={"priority_score": "評估分數", "player_name": "球員"},
            color="priority_score",
            color_continuous_scale=["#79b6bc", CHART_HIGHLIGHT],
        ),
    )
    show_table(
        st,
        report,
        [
            "player_id",
            "player_name",
            "team",
            "role_or_position",
            "usage_value",
            "usage_label",
            "priority_score",
            "qualified_percentile",
            "evidence_strengths",
            "evidence_risks",
            "evidence_notes",
        ],
    )

    markdown = report_markdown(report, {**metadata, "team": team, "report_id": report_id})
    manifest_json = report_manifest_json(manifest)
    display_report = to_display_table(
        report,
        [
            "player_id",
            "player_name",
            "team",
            "role_or_position",
            "usage_value",
            "usage_label",
            "priority_score",
            "qualified_percentile",
            "evidence_strengths",
            "evidence_risks",
            "evidence_notes",
        ],
    )
    download_markdown, download_csv, download_manifest = st.columns(3, gap="medium")
    download_markdown.download_button(
        "下載球探報告 Markdown",
        data=markdown.encode("utf-8"),
        file_name=report_filename(player_type, snapshot_id),
        mime="text/markdown",
        icon=":material/description:",
        width="stretch",
        key="download_scouting_report_markdown",
    )
    download_manifest.download_button(
        "下載稽核 Manifest JSON",
        data=manifest_json.encode("utf-8"),
        file_name=manifest_filename(player_type, snapshot_id),
        mime="application/json",
        icon=":material/fact_check:",
        width="stretch",
        help="下載後可用 python -m src.verify_report_manifest 驗證報告完整性。",
        key="download_scouting_report_manifest",
    )

    download_csv.download_button(
        "下載球探報告 CSV",
        data=dataframe_to_csv_bytes(display_report),
        file_name=report_filename(player_type, snapshot_id).replace(".md", ".csv"),
        mime="text/csv",
        icon=":material/table_view:",
        width="stretch",
        key="download_scouting_report_csv",
    )


def page_rankings() -> None:
    page_intro("球員排行榜", "球員排行榜", "以清楚的門檻與單一指標縮小候選範圍，再回到球員檔案查看完整脈絡。")
    if BATTERS.empty or PITCHERS.empty:
        st.info("目前缺少官方打者或投手資料，請重新執行官方資料刷新。")
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
    page_intro("球員個人頁", "球員個人頁", "從官方名單或本季成績選擇球員，依序檢視事實、相對位置與可解釋的評估訊號。")
    source_status_panel(compact=True)
    st.caption("全體球員以 CPBL 官方現役名單與官方全記錄成績表的聯集為主；本季一軍成績表未列出的球員會顯示為「官方現役名單」。")
    player_type = st.radio("球員類型", ["全體球員", "打者", "投手"], horizontal=True, key="player_type")
    requested_player_id = str(
        st.session_state.pop("requested_player_id", "") or query_param_value("player")
    )

    if player_type == "全體球員":
        directory = PLAYERS if not PLAYERS.empty else ROSTER
        if directory.empty:
            st.info("目前沒有可顯示的官方球員名單，請重新執行官方資料刷新。")
            return
        requested = directory[directory["player_id"].astype("string") == requested_player_id]
        if not requested.empty and st.session_state.get("applied_player_request") != requested_player_id:
            requested_team = str(requested.iloc[0]["team"])
            st.session_state["player_directory_team"] = requested_team
        team = st.selectbox("球隊選擇", sorted(directory["team"].dropna().unique()), key="player_directory_team")
        subset = directory[directory["team"] == team]
        choices = player_choice_options(subset)
        if not choices:
            st.info("這支球隊目前沒有可選擇的官方球員資料。")
            return
        selector_key = f"player_directory_choice_{team}"
        if not requested.empty and st.session_state.get("applied_player_request") != requested_player_id:
            requested_label = next(
                (label for label, player_id in choices.items() if player_id == requested_player_id),
                None,
            )
            if requested_label is not None:
                st.session_state[selector_key] = requested_label
            st.session_state["applied_player_request"] = requested_player_id
        selected_label = st.selectbox("球員選擇", list(choices), key=selector_key)
        selected_player_id = choices[selected_label]
        roster_row = subset[subset["player_id"].astype("string") == selected_player_id].iloc[0]
        sync_player_query(selected_player_id)
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
            st.info(f"目前沒有可顯示的{player_type}成績資料，請重新執行官方資料刷新。")
            return
        team = st.selectbox("球隊選擇", sorted(df["team"].dropna().unique()), key=f"player_{player_type}_team")
        subset = df[df["team"] == team]
        choices = player_choice_options(subset)
        if not choices:
            st.info(f"這支球隊目前沒有可選擇的{player_type}成績。")
            return
        selected_label = st.selectbox(
            "球員選擇",
            list(choices),
            key=f"player_{player_type}_choice_{team}",
        )
        selected_player_id = choices[selected_label]
        row = subset[subset["player_id"].astype("string") == selected_player_id].iloc[0]
        sync_player_query(selected_player_id)

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

    render_player_movements(row, stat_type)
    st.header("本季成績")
    show_table(st, pd.DataFrame([row]), season_columns)
    evidence_threshold = DEFAULT_QUALIFICATION[stat_type]
    evidence_population = qualified_population(df, stat_type, evidence_threshold)
    render_data_trust_surface(QUALITY_REPORT, stat_type, evidence_threshold, len(evidence_population))
    render_player_evidence(row, evidence_population, stat_type, evidence_threshold)

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

    radar_column, similar_column = st.columns(2, gap="medium")
    radar_column.subheader("能力雷達圖")
    show_chart(radar_column, radar_chart(radar_labels, radar_values, "能力雷達圖"))
    similar_column.subheader("相似球員推薦")
    show_table(similar_column, find_similar_players(df, row["player_id"], player_type=stat_type, n=5))


def page_matchup() -> None:
    page_intro("投打對決", "投打對決", "以本季官方彙總成績建構受限的 LOG5 情境，協助閱讀投打差異，不作比賽預測。")
    if BATTERS.empty or PITCHERS.empty:
        st.info("目前缺少官方打者或投手資料，請重新執行官方資料刷新。")
        return
    selector_hitter, selector_pitcher = st.columns(2, gap="medium")
    hitter_team = selector_hitter.selectbox(
        "打者球隊", sorted(BATTERS["team"].unique()), key="matchup_hitter_team"
    )
    hitter_df = BATTERS[BATTERS["team"] == hitter_team]
    hitter_choices = player_choice_options(hitter_df)
    if not hitter_choices:
        st.info("所選球隊目前沒有可用的打者資料。")
        return
    hitter_label = selector_hitter.selectbox(
        "打者",
        list(hitter_choices),
        key=f"matchup_hitter_{hitter_team}",
    )
    hitter_id = hitter_choices[hitter_label]
    hitter = hitter_df[hitter_df["player_id"].astype("string") == hitter_id].iloc[0]

    pitcher_team = selector_pitcher.selectbox(
        "投手球隊", sorted(PITCHERS["team"].unique()), key="matchup_pitcher_team"
    )
    pitcher_df = PITCHERS[PITCHERS["team"] == pitcher_team]
    pitcher_choices = player_choice_options(pitcher_df)
    if not pitcher_choices:
        st.info("所選球隊目前沒有可用的投手資料。")
        return
    pitcher_label = selector_pitcher.selectbox(
        "投手",
        list(pitcher_choices),
        key=f"matchup_pitcher_{pitcher_team}",
    )
    pitcher_id = pitcher_choices[pitcher_label]
    pitcher = pitcher_df[pitcher_df["player_id"].astype("string") == pitcher_id].iloc[0]
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
    page_intro("分項排行", "分項排行", "將打者、投手與球隊放在一致的比較格式中，同時保留前段與後段觀察。")
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


def render_product_footer() -> None:
    st.markdown(
        "<footer class='product-footer'><strong>獨立資料分析作品 · 非 CPBL 官方服務</strong>"
        "<span>資料取自 CPBL 官方公開頁面；分析結果不構成投注、比賽結果或球員決策建議。</span></footer>",
        unsafe_allow_html=True,
    )


PAGE_HANDLERS = {
    "資料訊號總覽": page_home,
    "聯盟總覽": page_league,
    "版本趨勢": page_snapshot_trends,
    "分析驗證": page_analysis_validation,
    "球探工作台": page_scouting_workbench,
    "球探報告": page_scouting_report,
    "球員排行榜": page_rankings,
    "球員個人頁": page_player,
    "投打對決": page_matchup,
    "分項排行": page_metric_rankings,
}

st.sidebar.markdown(
    "<div class='sidebar-brand'><div class='brand-mark'>CPBL</div><div><div class='sidebar-brand-title'>Scouting Desk</div><div class='sidebar-brand-subtitle'>官方賽季資料工作台</div></div></div>",
    unsafe_allow_html=True,
)
requested_page = query_param_value("page")
if "main_navigation" not in st.session_state and requested_page in PAGE_HANDLERS:
    st.session_state["main_navigation"] = requested_page

st.sidebar.markdown("<div class='sidebar-nav-label'>頁面導覽</div>", unsafe_allow_html=True)
selected = st.sidebar.radio("頁面導覽", PAGES, label_visibility="collapsed", key="main_navigation")
sync_page_query(selected)

search_map = player_search_options(PLAYERS if not PLAYERS.empty else ROSTER)
search_labels = ["選擇球員", *search_map]
st.sidebar.markdown("<div class='sidebar-nav-label sidebar-search-label'>球員搜尋</div>", unsafe_allow_html=True)
quick_player = st.sidebar.selectbox("快速尋找球員", search_labels, key="player_quick_search")
st.sidebar.button(
    "開啟球員頁",
    key="open_quick_player",
    on_click=open_player_from_search,
    args=(search_map.get(quick_player, ""),),
    disabled=quick_player == "選擇球員",
    width="stretch",
)

freshness = data_freshness(QUALITY_REPORT.get("generated_at", ""))
st.sidebar.markdown(
    f"<div class='sidebar-status status-{escape(str(freshness['status']))}'><strong>官方資料已核對 · {escape(str(freshness['label']))}</strong><br>"
    f"更新日期：{escape(data_verified_date())}<br>術語：OPS · ISO · AVG · OBP · SLG · ERA · WHIP · K/BB · LOG5</div>",
    unsafe_allow_html=True,
)
PAGE_HANDLERS[selected]()
render_product_footer()
