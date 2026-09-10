from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"



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

REMOVED_PAGES = ["相關新聞", "新聞 × 數據洞察", "資料品質與測試"]

REQUIRED_FRONTEND_TERMS = {
    "資料訊號總覽": ["資料訊號總覽", "球探工作台", "資料品質", "資料新鮮度", "發布健康", "發布 ID", "資料可回答", "資料限制", "LOG5 為情境計算，非校準預測模型", "資格門檻", "固定評估分數", "符合門檻母體百分位", "評估分數變化焦點", "累計資料差異"],
    "聯盟總覽": ["聯盟總覽", "戰績表", "勝差", "近況"],
    "版本趨勢": ["版本趨勢", "資料版本血緣", "球員指標走勢", "版本差異比較", "SHA-256", "OPS"],
    "分析驗證": ["分析驗證", "排名穩定性", "資料分布變化", "權重敏感度", "Top-K", "Spearman ρ", "描述性驗證"],
    "球探工作台": ["球探工作台", "最低打席 (PA)", "評估重點", "符合門檻母體", "最多選擇 4 位球員"],
    "球探報告": ["球探報告", "觀察名單", "建立可分享連結", "資格門檻", "評估重點", "最多選擇 4 位球員"],
    "球員排行榜": ["球員排行榜", "打者", "投手", "OPS"],
    "球員個人頁": ["球員個人頁", "全體球員", "官方現役名單", "本季成績", "前次快照變化", "累計資料差異", "評估依據", "進階指標", "聯盟平均比較", "排行摘要", "聯盟百分位", "能力雷達圖", "相似球員推薦"],
    "投打對決": ["投打對決", "LOG5", "OBP", "SLG", "OPS", "ERA", "WHIP", "K/BB"],
    "分項排行": ["分項排行", "指標", "Top 10"],
}

MOJIBAKE_MARKERS = ["嚙", "�", "銝剛", "鞈", "撟", "蝮", "瘥", "璅"]
LOWERCASE_BASEBALL_TERMS = ["log5", "ops", "iso", "avg", "obp", "slg", "era", "whip"]


def visible_text(app: AppTest) -> str:
    parts: list[str] = []
    for attr in ["title", "header", "subheader", "caption", "markdown", "info", "warning", "text", "code"]:
        for element in getattr(app, attr):
            value = getattr(element, "value", "")
            if value:
                text_value = str(value)
                if text_value.lstrip().startswith("<style>"):
                    continue
                parts.append(text_value)
    for metric in app.metric:
        for attr in ["label", "value", "delta"]:
            value = getattr(metric, attr, "")
            if value:
                parts.append(str(value))
    for selectbox in app.selectbox:
        parts.append(str(selectbox.label))
    for number_input in app.number_input:
        parts.append(str(number_input.label))
    for multiselect in app.multiselect:
        parts.append(str(multiselect.label))
        parts.extend(str(option) for option in multiselect.options)
    for button in app.button:
        parts.append(str(button.label))
    for button in app.download_button:
        parts.append(str(button.label))
    for radio in app.radio:
        parts.append(str(radio.label))
        parts.extend(str(option) for option in radio.options)
    return "\n".join(parts)


def test_all_streamlit_pages_render_without_exceptions():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    assert len(app.exception) == 0

    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=20)
        assert len(app.exception) == 0, page


def test_removed_pages_are_not_in_sidebar():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    sidebar_options = list(app.sidebar.radio[0].options)
    assert sidebar_options == PAGES
    for page in REMOVED_PAGES:
        assert page not in sidebar_options


def test_sidebar_has_complete_player_quick_search() -> None:
    import app as dashboard

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    search = next(box for box in app.sidebar.selectbox if box.label == "快速尋找球員")
    assert search.options[0] == "選擇球員"
    assert len(search.options) == dashboard.PLAYERS["player_id"].nunique() + 1
    assert any(button.label == "開啟球員頁" for button in app.sidebar.button)


def test_player_search_options_handles_roster_only_fallback() -> None:
    import pandas as pd
    import app as dashboard

    roster_only = pd.DataFrame(
        [{"player_id": "0000000001", "player_name": "測試球員", "team": "測試隊"}]
    )

    options = dashboard.player_search_options(roster_only)

    assert options == {"測試球員 · 測試隊 · 官方現役名單 · 0000000001": "0000000001"}


def test_player_quick_search_opens_selected_player_page() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    search = next(box for box in app.sidebar.selectbox if box.label == "快速尋找球員")
    selected_label = search.options[1]

    search.set_value(selected_label)
    app.run(timeout=20)
    next(button for button in app.sidebar.button if button.label == "開啟球員頁").click()
    app.run(timeout=20)

    assert app.sidebar.radio[0].value == "球員個人頁"
    assert selected_label.split(" · ", 1)[0] in visible_text(app)


def test_player_quick_search_reopens_player_after_manual_selection_change() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    search = next(box for box in app.sidebar.selectbox if box.label == "快速尋找球員")
    selected_label = next(
        label
        for label in search.options[1:]
        if sum(f" · {label.split(' · ')[1]} · " in option for option in search.options) > 1
    )

    search.set_value(selected_label)
    app.run(timeout=20)
    next(button for button in app.sidebar.button if button.label == "開啟球員頁").click()
    app.run(timeout=20)

    player_select = next(box for box in app.selectbox if box.label == "球員選擇")
    alternate = next(option for option in player_select.options if option != player_select.value)
    player_select.set_value(alternate)
    app.run(timeout=20)
    assert str(alternate).split(" · ", 1)[0] in visible_text(app)

    next(button for button in app.sidebar.button if button.label == "開啟球員頁").click()
    app.run(timeout=20)

    assert selected_label.split(" · ", 1)[0] in visible_text(app)


def test_player_deep_link_restores_page_and_player() -> None:
    import app as dashboard

    target = dashboard.PLAYERS.iloc[0]
    app = AppTest.from_file(APP_PATH)
    app.query_params["page"] = "球員個人頁"
    app.query_params["player"] = str(target["player_id"])
    app.run(timeout=20)

    assert app.sidebar.radio[0].value == "球員個人頁"
    assert str(target["player_name"]) in visible_text(app)
    assert app.query_params["page"] == ["球員個人頁"]
    assert app.query_params["player"] == [str(target["player_id"])]


def test_rendered_frontend_text_is_readable_traditional_chinese():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=20)
        text = visible_text(app)
        assert "非 CPBL 官方服務" in text, f"{page} missing independent-product disclosure"
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"{page} contains mojibake marker {marker!r}"
        assert "undefined" not in text.lower(), f"{page} contains undefined"
        for term in LOWERCASE_BASEBALL_TERMS:
            assert term not in text, f"{page} contains lowercase baseball term {term!r}"
        for term in REQUIRED_FRONTEND_TERMS[page]:
            assert term in text, f"{page} missing frontend term {term!r}"


def test_league_table_uses_chinese_baseball_columns():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("聯盟總覽")
    app.run(timeout=20)

    assert len(app.dataframe) >= 1
    columns = set(app.dataframe[0].value.columns)
    assert {"球隊", "出賽", "勝", "敗", "勝率", "勝差", "近況", "得失分差", "主場勝", "主場敗", "客場勝", "客場敗", "近期戰力"}.issubset(columns)
    assert "觀眾數" not in columns


def test_table_exports_use_displayed_chinese_columns():
    import app as dashboard

    raw = dashboard.TEAMS.head(1)
    display = dashboard.to_display_table(raw, ["team", "games", "win_pct", "source_note"])
    csv_bytes = dashboard.dataframe_to_csv_bytes(display)
    text = csv_bytes.decode("utf-8-sig")

    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    assert "球隊,出賽,勝率,資料來源" in text
    assert "team" not in text.splitlines()[0]


def test_player_ids_keep_official_leading_zeroes_when_loaded():
    import app as dashboard

    assert dashboard.ROSTER["player_id"].dtype.name == "string"
    assert dashboard.ROSTER["player_id"].str.fullmatch(r"\d{10}").all()


def test_verified_date_comes_from_quality_report():
    import app as dashboard

    report = dashboard.load_data_quality_report()
    expected_date = report["generated_at"][:10]

    assert dashboard.data_verified_date(report) == expected_date
    assert dashboard.DATA_VERIFIED_DATE == expected_date
    assert "2026-07-05" not in APP_PATH.read_text(encoding="utf-8-sig")



def test_data_signal_overview_exposes_lineage_quality_and_log5_limit() -> None:
    import app as dashboard

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("資料訊號總覽")
    app.run(timeout=20)
    text = visible_text(app)

    source = APP_PATH.read_text(encoding="utf-8-sig")
    assert '"來源網域：cpbl.com.tw"' in source
    assert "www.cpbl.com.tw" not in source
    assert dashboard.data_generated_time() in text
    assert "品質狀態" in text
    assert "LOG5 為情境計算，非校準預測模型" in text
    assert "球探工作台" in text
    assert "資格門檻" in text
    assert "固定評估分數" in text
    assert "符合門檻母體百分位" in text
    assert "def render_analysis_routes(" in source
    assert source.index('(\"球探工作台\"') < source.index('(\"球員排行榜\"')


def test_snapshot_movement_sections_are_visible_and_explicitly_limited() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    home_text = visible_text(app)

    assert "評估分數變化焦點" in home_text
    assert "累計資料差異" in home_text
    assert "不是逐場表現或未來預測" in home_text

    app.sidebar.radio[0].set_value("球員個人頁")
    app.run(timeout=20)
    player_type = next(radio for radio in app.radio if radio.label == "球員類型")
    player_type.set_value("打者")
    app.run(timeout=20)
    player_text = visible_text(app)

    assert "前次快照變化" in player_text
    assert "快照期間" in player_text
    assert "累計資料差異" in player_text


def test_player_page_renders_explainable_evidence_with_percentile_basis() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("球員個人頁")
    app.run(timeout=20)
    player_type = next(radio for radio in app.radio if radio.label == "球員類型")
    player_type.set_value("打者")
    app.run(timeout=20)
    text = visible_text(app)

    assert "評估依據" in text
    assert "符合門檻母體" in text
    assert "PA ≥ 30" in text
    assert "百分位依據：" in text
    assert "OBP 有利百分位" in text
    assert "ISO 有利百分位" in text
    assert "K% 有利百分位" in text


def test_player_page_has_complete_sections_and_no_raw_url_table():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("球員個人頁")
    app.run(timeout=20)

    text = visible_text(app)
    player_type = next(radio for radio in app.radio if radio.label == "球員類型")
    assert list(player_type.options) == ["全體球員", "打者", "投手"]
    assert "官方現役名單" in text
    assert "本季成績" in text
    assert "進階指標" in text
    assert "聯盟平均比較" in text
    assert "聯盟百分位" in text
    assert "能力雷達圖" in text
    assert "相似球員推薦" in text
    assert "投手 · 投手" not in text
    table_columns = [set(df.value.columns) for df in app.dataframe]
    assert all("url" not in cols and "原文連結" not in cols for cols in table_columns)


def test_source_contains_correct_page_and_baseball_terms():
    text = APP_PATH.read_text(encoding="utf-8-sig")
    required_terms = [
        "CPBL 中職資料分析平台",
        "打擊率 (AVG)",
        "上壘率 (OBP)",
        "長打率 (SLG)",
        "防禦率 (ERA)",
        "每局被上壘率 (WHIP)",
        "三振保送比 (K/BB)",
        "LOG5 官方成績衍生模型",
        "聯盟百分位",
    ]
    for term in required_terms:
        assert term in text
    for page in REMOVED_PAGES:
        assert page not in text
    assert 'name="能力分布"' in text
    assert "showlegend=False" in text
    assert "download_button" in text
    assert "下載 CSV" in text
    for forbidden in ["news.csv", "matchups.csv", "近期動態摘要", "觀眾數樣本", "news_heat_score", "under_the_radar_score"]:
        assert forbidden not in text


def test_league_filter_and_player_type_controls_update_without_errors():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    app.sidebar.radio[0].set_value("聯盟總覽")
    app.run(timeout=20)
    team_filter = next(box for box in app.selectbox if box.label == "選擇球隊")
    selected_team = next(option for option in team_filter.options if option != "全部")
    team_filter.set_value(selected_team)
    app.run(timeout=20)
    assert len(app.exception) == 0
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]["球隊"] == selected_team

    app.sidebar.radio[0].set_value("球員個人頁")
    app.run(timeout=20)
    player_type = next(radio for radio in app.radio if radio.label == "球員類型")
    for option in ["打者", "投手"]:
        player_type.set_value(option)
        app.run(timeout=20)
        assert len(app.exception) == 0
        text = visible_text(app)
        assert "聯盟百分位" in text
        assert "相似球員推薦" in text


def test_scouting_workbench_filters_and_compares_without_errors() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("球探工作台")
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert "符合門檻母體" in visible_text(app)
    hitter_type = next(radio for radio in app.radio if radio.label == "球員類型")
    hitter_type.set_value("投手")
    app.run(timeout=20)
    assert len(app.exception) == 0
    assert any(box.label == "最低投球局數 (IP)" for box in app.number_input)
    assert any(box.label == "評估重點" for box in app.selectbox)
    assert any(box.label == "比較球員" for box in app.multiselect)


def test_scouting_report_page_builds_downloadable_watchlist() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("球探報告")
    app.run(timeout=20)

    assert len(app.exception) == 0
    text = visible_text(app)
    assert "觀察名單" in text
    assert "最多選擇 4 位球員" in text
    assert any(button.label == "建立可分享連結" for button in app.button)

    watchlist = next(box for box in app.multiselect if box.label == "觀察名單")
    watchlist.set_value(list(watchlist.options[:2]))
    app.run(timeout=20)
    assert len(app.exception) == 0
    assert "評估報告" in visible_text(app)
    assert len(app.dataframe) >= 1
    assert any(button.label == "下載球探報告 Markdown" for button in app.download_button)
    assert any(button.label == "下載球探報告 CSV" for button in app.download_button)
    assert any(button.label == "下載稽核 Manifest JSON" for button in app.download_button)

def test_scouting_report_deep_link_restores_watchlist_conditions() -> None:
    import app as dashboard

    candidates = dashboard.rank_scouting_candidates(
        dashboard.BATTERS,
        "打者",
        dashboard.DEFAULT_QUALIFICATION["打者"],
        "綜合價值",
    )
    selected_ids = candidates["player_id"].astype(str).head(2).tolist()
    assert len(selected_ids) == 2

    app = AppTest.from_file(APP_PATH)
    app.query_params["page"] = "球探報告"
    app.query_params["report_type"] = "打者"
    app.query_params["report_threshold"] = "30"
    app.query_params["report_focus"] = "綜合價值"
    app.query_params["watchlist"] = ",".join(selected_ids)
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert app.sidebar.radio[0].value == "球探報告"
    watchlist = next(box for box in app.multiselect if box.label == "觀察名單")
    assert len(watchlist.value) == 2
    assert all(str(player_id) in " ".join(watchlist.value) for player_id in selected_ids)

    next(button for button in app.button if button.label == "建立可分享連結").click()
    app.run(timeout=20)
    assert app.query_params["page"] == ["球探報告"]
    assert app.query_params["watchlist"] == [",".join(selected_ids)]


def test_external_page_query_change_updates_navigation_after_session_started() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    league_page = "\u806f\u76df\u7e3d\u89bd"
    rankings_page = "\u7403\u54e1\u6392\u884c\u699c"

    app.sidebar.radio[0].set_value(league_page)
    app.run(timeout=20)
    assert app.query_params["page"] == [league_page]

    app.query_params["page"] = rankings_page
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert app.sidebar.radio[0].value == rankings_page

def test_metric_ranking_team_view_renders_balanced_top_and_bottom_sections():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("分項排行")
    app.run(timeout=20)

    category = next(box for box in app.selectbox if box.label == "類型")
    category.set_value("球隊")
    app.run(timeout=20)

    assert len(app.exception) == 0
    text = visible_text(app)
    assert "Top 3" in text
    assert "Bottom 3" in text
    assert len(app.dataframe) == 2
    assert all(len(table.value) == 3 for table in app.dataframe)


def test_theme_enforces_equal_cards_spacing_touch_targets_and_mobile_layout():
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    for required_rule in [
        "gap: 24px",
        "grid-auto-rows: 1fr",
        "height: 100%",
        "min-height: 48px",
        "@media (max-width: 720px)",
        "grid-template-columns: 1fr",
        "color-scheme: dark",
        "font-variant-numeric: tabular-nums",
        ":focus-visible",
        "touch-action: manipulation",
        "text-wrap: balance",
    ]:
        assert required_rule in css
    assert "height: 224px" not in css
    assert "button:focus," not in css
    assert "transition: all" not in css


def test_theme_stacks_masthead_when_sidebar_constrains_tablet_width():
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")
    tablet_rules = css.split(
        "@media (max-width: 1100px) and (min-width: 721px)", 1
    )[1]

    assert '.page-masthead,' in tablet_rules
    assert '.player-identity {' in tablet_rules
    assert 'display: flex !important;' in tablet_rules
    assert 'flex-direction: column;' in tablet_rules
    assert 'align-items: flex-start;' in tablet_rules
    assert '.page-kicker {' in tablet_rules
    assert 'flex-wrap: wrap;' in tablet_rules
    assert '.data-status-line {' in tablet_rules
    assert 'justify-self: start;' in tablet_rules


def test_theme_uses_flat_editorial_data_tool_direction():
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    assert "linear-gradient" not in css
    assert "metric-index" not in css
    assert ".workflow-grid" in css
    assert ".source-facts" in css
    assert "--accent: #d85a52" in css
    assert "box-shadow: none" in css


def test_every_page_has_one_level_one_title():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=20)
        assert len(app.title) == 1, f"{page} must render exactly one H1 title"


def test_accessibility_shell_and_chart_summaries_are_present():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("聯盟總覽")
    app.run(timeout=20)

    markdown_values = [str(element.value) for element in app.markdown]
    assert any("skip-link" in value and "cpbl-main" in value for value in markdown_values)
    chart_summaries = [value for value in markdown_values if "chart-summary" in value]
    assert len(chart_summaries) == 4
    assert all("圖表摘要" in summary and "sr-only" in summary for summary in chart_summaries)


def test_radar_chart_reserves_space_for_mobile_axis_labels() -> None:
    import app as dashboard

    figure = dashboard.radar_chart(
        ["擊球接觸", "長打能力", "選球紀律", "綜合價值"],
        [20.0, 40.0, 60.0, 80.0],
    )

    assert figure.layout.height >= 440
    assert figure.layout.margin.l >= 72
    assert figure.layout.margin.r >= 72
    assert tuple(figure.layout.polar.domain.x) == (0.16, 0.84)


def test_theme_styles_freshness_states_and_sidebar_search() -> None:
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    for required_rule in [
        ".status-recent",
        ".status-stale",
        ".status-unknown",
        ".sidebar-search-label",
    ]:
        assert required_rule in css


def test_theme_covers_safe_areas_native_controls_and_interaction_states():
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    for required_rule in [
        ".skip-link",
        ".sr-only",
        "env(safe-area-inset-left)",
        "env(safe-area-inset-right)",
        "env(safe-area-inset-bottom)",
        "cursor: pointer",
        ":disabled",
        ":active",
        "select,",
        "textarea",
        '[data-testid="stAppDeployButton"]',
        '[data-testid="stMainMenu"]',
        '[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]',
        "flex-direction: column !important",
    ]:
        assert required_rule in css


def test_scouting_workbench_hides_unverified_position_role_filter_and_shows_snapshot_lineage() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("球探工作台")
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert all(box.label != "位置 / 角色" for box in app.selectbox)
    source = APP_PATH.read_text(encoding="utf-8-sig")
    assert "資料快照" in source
    assert "snapshot_id" in source


def test_scouting_desk_visual_system_is_available_to_every_page() -> None:
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")
    source = APP_PATH.read_text(encoding="utf-8-sig")

    for required_rule in [
        ".page-masthead",
        ".data-status-line",
        ".metric-card-detail",
        ".evidence-grid",
        ".route-card",
        ".player-identity",
        ".control-caption",
        "--space-4",
        "--radius",
    ]:
        assert required_rule in css

    assert "def page_intro(" in source
    assert "def render_analysis_routes(" in source
    assert "def switch_page(" in source
    assert 'key="main_navigation"' in source

def test_snapshot_trend_page_renders_lineage_trend_and_version_comparison() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("版本趨勢")
    app.run(timeout=20)

    assert len(app.exception) == 0
    text = visible_text(app)
    for expected in ["版本趨勢", "資料版本血緣", "球員指標走勢", "版本差異比較", "SHA-256"]:
        assert expected in text
    labels = {box.label for box in app.selectbox}
    assert {"球員類型", "球員", "指標", "基準版本", "比較版本"}.issubset(labels)
    assert len(app.get("plotly_chart")) >= 2
    assert len(app.dataframe) >= 2


def test_snapshot_trend_controls_switch_to_pitcher_era_without_errors() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("版本趨勢")
    app.run(timeout=20)

    player_type = next(box for box in app.selectbox if box.label == "球員類型")
    player_type.set_value("投手")
    app.run(timeout=20)
    metric = next(box for box in app.selectbox if box.label == "指標")
    metric.set_value("era")
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert "防禦率 (ERA)" in visible_text(app)
    assert any("chart-summary" in str(element.value) and "ERA" in str(element.value) for element in app.markdown)


def test_snapshot_trend_theme_has_timeline_and_mobile_rules() -> None:
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    for required_rule in [
        ".snapshot-timeline",
        ".snapshot-node",
        ".snapshot-node-current",
        "grid-auto-rows: 1fr",
        "@media (max-width: 720px)",
    ]:
        assert required_rule in css

def test_player_page_uses_unambiguous_cpbl_id_options() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)
    app.sidebar.radio[0].set_value("球員個人頁")
    app.run(timeout=30)

    player_select = next(box for box in app.selectbox if box.label == "球員選擇")

    assert player_select.options
    assert all(len(str(option).rsplit(" · ", 1)[-1]) == 10 for option in player_select.options)
    assert len(player_select.options) == len(set(player_select.options))


def test_snapshot_comparison_controls_only_offer_forward_versions() -> None:
    import app as dashboard

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("版本趨勢")
    app.run(timeout=20)

    baseline = next(box for box in app.selectbox if box.label == "基準版本")
    current = next(box for box in app.selectbox if box.label == "比較版本")
    version_ids = dashboard.SNAPSHOT_HISTORY.sort_values("captured_at")["snapshot_id"].astype(str).tolist()

    expected_baselines = [dashboard.snapshot_option_label(value) for value in version_ids[:-1]]
    assert list(baseline.options) == expected_baselines
    baseline_id = str(baseline.value)
    baseline_index = version_ids.index(baseline_id)
    expected_current = [dashboard.snapshot_option_label(value) for value in version_ids[baseline_index + 1 :]]
    assert list(current.options) == expected_current

    if len(version_ids) > 2:
        baseline.set_value(version_ids[1])
        app.run(timeout=20)
        current = next(box for box in app.selectbox if box.label == "比較版本")
        assert list(current.options) == [
            dashboard.snapshot_option_label(value) for value in version_ids[2:]
        ]

def test_matchup_uses_unique_player_ids_and_recalculates() -> None:
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)
    app.sidebar.radio[0].set_value("投打對決")
    app.run(timeout=30)

    hitter = next(box for box in app.selectbox if box.label == "打者")
    pitcher = next(box for box in app.selectbox if box.label == "投手")
    assert all(len(str(option).rsplit(" · ", 1)[-1]) == 10 for option in hitter.options)
    assert all(len(str(option).rsplit(" · ", 1)[-1]) == 10 for option in pitcher.options)

    hitter.set_value(hitter.options[-1])
    pitcher.set_value(pitcher.options[-1])
    app.run(timeout=30)

    assert len(app.exception) == 0
    assert "LOG5 上壘機率" in visible_text(app)
    assert len(app.get("plotly_chart")) == 2

def test_freshness_display_explains_noncurrent_snapshot_age() -> None:
    from datetime import datetime, timedelta, timezone

    import app as dashboard

    generated_at = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    label = dashboard.freshness_display_label({"generated_at": generated_at})

    assert "資料近期更新" in label
    assert "天前" in label


def test_analysis_entry_cards_use_real_streamlit_actions() -> None:
    source = APP_PATH.read_text(encoding="utf-8-sig")
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    assert "route_columns = st.columns(3, gap=\"medium\")" in source
    assert "f\"開啟 {target}\"" in source
    assert "key=f\"route_card_{target}\"" in source
    assert "on_click=switch_page" in source
    assert "a:focus-visible" in css
