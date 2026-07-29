from pathlib import Path

from streamlit.testing.v1 import AppTest


PAGES = [
    "首頁 / 專案介紹",
    "聯盟總覽",
    "球員排行榜",
    "球員個人頁",
    "投打對決",
    "分項排行",
]

REMOVED_PAGES = ["相關新聞", "新聞 × 數據洞察", "資料品質與測試"]

REQUIRED_FRONTEND_TERMS = {
    "首頁 / 專案介紹": ["CPBL 中職資料分析平台", "資料來源狀態", "球員個人頁", "LOG5"],
    "聯盟總覽": ["聯盟總覽", "戰績表", "勝差", "近況"],
    "球員排行榜": ["球員排行榜", "打者", "投手", "OPS"],
    "球員個人頁": ["球員個人頁", "全體球員", "官方現役名單", "本季成績", "進階指標", "聯盟平均比較", "排行摘要", "聯盟百分位", "能力雷達圖", "相似球員推薦"],
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
    for radio in app.radio:
        parts.append(str(radio.label))
        parts.extend(str(option) for option in radio.options)
    return "\n".join(parts)


def test_all_streamlit_pages_render_without_exceptions():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    assert len(app.exception) == 0

    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=20)
        assert len(app.exception) == 0, page


def test_removed_pages_are_not_in_sidebar():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    sidebar_options = list(app.sidebar.radio[0].options)
    assert sidebar_options == PAGES
    for page in REMOVED_PAGES:
        assert page not in sidebar_options


def test_rendered_frontend_text_is_readable_traditional_chinese():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=20)
        text = visible_text(app)
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"{page} contains mojibake marker {marker!r}"
        assert "undefined" not in text.lower(), f"{page} contains undefined"
        for term in LOWERCASE_BASEBALL_TERMS:
            assert term not in text, f"{page} contains lowercase baseball term {term!r}"
        for term in REQUIRED_FRONTEND_TERMS[page]:
            assert term in text, f"{page} missing frontend term {term!r}"


def test_league_table_uses_chinese_baseball_columns():
    app = AppTest.from_file("app.py")
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
    assert "2026-07-05" not in Path("app.py").read_text(encoding="utf-8-sig")


def test_player_page_has_complete_sections_and_no_raw_url_table():
    app = AppTest.from_file("app.py")
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
    text = Path("app.py").read_text(encoding="utf-8-sig")
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
    app = AppTest.from_file("app.py")
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


def test_metric_ranking_team_view_renders_balanced_top_and_bottom_sections():
    app = AppTest.from_file("app.py")
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


def test_theme_uses_flat_editorial_data_tool_direction():
    css = Path("src/theme.py").read_text(encoding="utf-8-sig")

    assert "linear-gradient" not in css
    assert "metric-index" not in css
    assert ".workflow-grid" in css
    assert ".source-facts" in css
    assert "--accent: #d85a52" in css
    assert "box-shadow: none" in css


def test_every_page_has_one_level_one_title():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=20)
        assert len(app.title) == 1, f"{page} must render exactly one H1 title"


def test_accessibility_shell_and_chart_summaries_are_present():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.sidebar.radio[0].set_value("聯盟總覽")
    app.run(timeout=20)

    markdown_values = [str(element.value) for element in app.markdown]
    assert any("skip-link" in value and "cpbl-main" in value for value in markdown_values)
    chart_summaries = [value for value in markdown_values if "chart-summary" in value]
    assert len(chart_summaries) == 4
    assert all("圖表摘要" in summary and "sr-only" in summary for summary in chart_summaries)


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
    ]:
        assert required_rule in css
