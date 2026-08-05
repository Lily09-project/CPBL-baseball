# CPBL Scouting Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable CPBL scouting workbench that turns verified official statistics into reproducible, explainable player shortlists and comparisons.

**Architecture:** Keep deterministic evaluation logic in a new src/scouting.py module and keep app.py responsible only for Streamlit controls and rendering. The workbench ranks a qualified hitter or pitcher population using documented existing component scores, attaches traceable evidence strings, and exposes the same evidence on the player page. Existing retrieval, preprocessing, quality, similarity, and LOG5 modules retain their present boundaries.

**Tech Stack:** Python 3.12, pandas, Streamlit, Plotly, pytest, CPBL official public pages, GitHub Actions security workflow.

## Global Constraints

- Preserve CPBL player_id values as strings through filtering, ranking, comparison, CSV display, and tests so leading zeroes remain intact.
- Use only tracked data/processed/*.csv in the UI. Raw CPBL HTML stays ignored under data/raw/ and internal prompts stay ignored under notes/source_prompt.txt.
- Qualification defaults are 30 PA for hitters and 10 IP for pitchers. Workbench controls may raise, but not lower, those defaults.
- Calculate percentiles within the active player type and qualification population before team or position/role filtering. After metric direction is applied, higher percentile means better relative performance.
- Keep the existing dark editorial language: 24px desktop card gaps, 5px or lower card radii, no gradients, no nested cards, visible keyboard focus, and one H1 per page.
- Use Traditional Chinese UI copy and uppercase baseball abbreviations: AVG, OBP, SLG, OPS, ISO, ERA, WHIP, K/BB, PA, and IP.
- Do not add predictions, injury claims, betting, roster recommendations, generative claims, external models, private data, credentials, raw HTML, caches, or local-environment features.
- Before a public push, run the data refresh, quality report, full tests, Bandit, detect-secrets, pip-audit, Git object integrity check, tracked-file audit, and GitHub Security checks workflow.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| src/scouting.py | Qualification, percentile, priority score, evidence, shortlist ranking, and comparison-frame logic. It must not import Streamlit. |
| tests/test_scouting.py | Fast deterministic tests for every public scouting function and evidence threshold. |
| app.py | Imports the scouting boundary, renders the data-signal overview, player evidence, and workbench page. |
| src/theme.py | Adds compact trust/evidence layout rules consistent with existing spacing and responsive behavior. |
| tests/test_streamlit_pages.py | Extends page, control, text, evidence, and trust-surface rendering checks. |
| README.md | Explains source-to-signal pipeline, formulas, limitations, test workflow, and public repository policy for interview review. |
| tests/test_project_docs.py | Locks the README’s required interview-facing sections and limitations in place. |

### Task 1: Create Qualified-Population and Percentile Primitives

**Files:**
- Create: src/scouting.py
- Create: tests/test_scouting.py

**Interfaces:**
- Produces: DEFAULT_QUALIFICATION: dict[str, float], qualification_column(player_type: str) -> str, qualification_label(player_type: str) -> str, qualified_population(df: pd.DataFrame, player_type: str, threshold: float) -> pd.DataFrame, percentile_rank(population: pd.DataFrame, row: pd.Series, metric: str, lower_is_better: bool = False) -> float | None.
- Consumes: pa for hitters and innings_pitched for pitchers; no Streamlit state or app globals.
- Used by: build_evidence_signals, rank_scouting_candidates, the player page, and the workbench page.

- [ ] **Step 1: Write the failing tests**

Create tests/test_scouting.py:

    import pandas as pd
    import pytest

    from src.scouting import percentile_rank, qualified_population


    @pytest.fixture
    def hitter_population() -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"player_id": "0000000001", "player_name": "A", "pa": 20, "obp": 0.400, "era": 4.0},
                {"player_id": "0000000002", "player_name": "B", "pa": 30, "obp": 0.350, "era": 3.0},
                {"player_id": "0000000003", "player_name": "C", "pa": 45, "obp": 0.300, "era": 2.0},
            ]
        )


    def test_qualified_population_uses_hitter_pa_threshold(hitter_population: pd.DataFrame) -> None:
        qualified = qualified_population(hitter_population, "打者", 30)
        assert qualified["player_id"].tolist() == ["0000000002", "0000000003"]
        assert qualified["player_id"].dtype.name == "string"


    def test_qualified_population_uses_pitcher_ip_threshold() -> None:
        pitchers = pd.DataFrame(
            [
                {"player_id": "0000000011", "innings_pitched": 9.2},
                {"player_id": "0000000012", "innings_pitched": 10.0},
            ]
        )
        qualified = qualified_population(pitchers, "投手", 10)
        assert qualified["player_id"].tolist() == ["0000000012"]


    def test_percentile_rank_handles_direction_ties_missing_values_and_singleton(hitter_population: pd.DataFrame) -> None:
        middle = hitter_population.iloc[1]
        assert percentile_rank(hitter_population, middle, "obp") == 66.7
        assert percentile_rank(hitter_population, middle, "era", lower_is_better=True) == 66.7
        assert percentile_rank(hitter_population, middle, "missing_metric") is None
        assert percentile_rank(hitter_population.iloc[[0]], hitter_population.iloc[0], "obp") == 100.0


    def test_qualified_population_rejects_unknown_type_and_negative_threshold(hitter_population: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="球員類型"):
            qualified_population(hitter_population, "捕手", 30)
        with pytest.raises(ValueError, match="門檻"):
            qualified_population(hitter_population, "打者", -1)

- [ ] **Step 2: Run the focused test to verify it fails**

Run: python -m pytest tests/test_scouting.py -q

Expected: collection fails because src.scouting does not exist.

- [ ] **Step 3: Implement the primitives**

Create src/scouting.py:

    from __future__ import annotations

    import pandas as pd


    DEFAULT_QUALIFICATION = {"打者": 30.0, "投手": 10.0}
    QUALIFICATION_COLUMNS = {"打者": "pa", "投手": "innings_pitched"}
    QUALIFICATION_LABELS = {"打者": "PA", "投手": "IP"}


    def qualification_column(player_type: str) -> str:
        try:
            return QUALIFICATION_COLUMNS[player_type]
        except KeyError as exc:
            raise ValueError(f"不支援的球員類型：{player_type}") from exc


    def qualification_label(player_type: str) -> str:
        qualification_column(player_type)
        return QUALIFICATION_LABELS[player_type]


    def qualified_population(df: pd.DataFrame, player_type: str, threshold: float) -> pd.DataFrame:
        column = qualification_column(player_type)
        if threshold < 0:
            raise ValueError("資格門檻不得小於 0")
        if df.empty or column not in df.columns:
            return df.iloc[0:0].copy()
        out = df.copy()
        if "player_id" in out.columns:
            out["player_id"] = out["player_id"].astype("string")
        usage = pd.to_numeric(out[column], errors="coerce")
        return out.loc[usage >= float(threshold)].copy().reset_index(drop=True)


    def percentile_rank(
        population: pd.DataFrame,
        row: pd.Series,
        metric: str,
        lower_is_better: bool = False,
    ) -> float | None:
        if population.empty or metric not in population.columns:
            return None
        values = pd.to_numeric(population[metric], errors="coerce").dropna()
        player_value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
        if values.empty or pd.isna(player_value):
            return None
        comparison = values >= player_value if lower_is_better else values <= player_value
        return round(float(comparison.mean() * 100), 1)

- [ ] **Step 4: Run the focused test to verify it passes**

Run: python -m pytest tests/test_scouting.py -q

Expected: 4 passed.

- [ ] **Step 5: Commit**

    git add src/scouting.py tests/test_scouting.py
    git commit -m "feat: add scouting population primitives"

### Task 2: Add Explainable Evidence, Priorities, and Stable Comparisons

**Files:**
- Modify: src/scouting.py
- Modify: tests/test_scouting.py

**Interfaces:**
- Consumes: Task 1 qualified_population, qualification_column, qualification_label, and percentile_rank.
- Produces: priority_options(player_type: str) -> list[str], build_evidence_signals(row: pd.Series, population: pd.DataFrame, player_type: str, threshold: float) -> dict[str, list[str]], rank_scouting_candidates(df: pd.DataFrame, player_type: str, threshold: float, priority: str, team: str = "全部", role_or_position: str = "全部") -> pd.DataFrame, comparison_frame(candidates: pd.DataFrame, selected_player_ids: list[str], player_type: str) -> pd.DataFrame.
- Used by: page_player and page_scouting_workbench.

- [ ] **Step 1: Add failing evidence and comparison tests**

Append to tests/test_scouting.py:

    from src.scouting import build_evidence_signals, comparison_frame, rank_scouting_candidates


    @pytest.fixture
    def scored_hitters() -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"player_id": "0000000001", "player_name": "A", "team": "T1", "position": "外野手", "pa": 20, "obp": 0.400, "iso": 0.250, "k_rate": 0.400, "contact_score": 88.0, "power_score": 90.0, "discipline_score": 70.0, "hitter_value_score": 85.0, "player_value_score": 85.0},
                {"player_id": "0000000002", "player_name": "B", "team": "T1", "position": "外野手", "pa": 40, "obp": 0.350, "iso": 0.200, "k_rate": 0.300, "contact_score": 72.0, "power_score": 75.0, "discipline_score": 80.0, "hitter_value_score": 77.0, "player_value_score": 77.0},
                {"player_id": "0000000003", "player_name": "C", "team": "T2", "position": "內野手", "pa": 50, "obp": 0.300, "iso": 0.150, "k_rate": 0.200, "contact_score": 68.0, "power_score": 55.0, "discipline_score": 75.0, "hitter_value_score": 65.0, "player_value_score": 65.0},
                {"player_id": "0000000004", "player_name": "D", "team": "T2", "position": "內野手", "pa": 60, "obp": 0.250, "iso": 0.100, "k_rate": 0.100, "contact_score": 55.0, "power_score": 40.0, "discipline_score": 60.0, "hitter_value_score": 50.0, "player_value_score": 50.0},
            ]
        )


    def test_hitter_evidence_is_bounded_numeric_and_marks_limited_sample(scored_hitters: pd.DataFrame) -> None:
        qualified = qualified_population(scored_hitters, "打者", 30)
        evidence = build_evidence_signals(scored_hitters.iloc[0], qualified, "打者", 30)
        assert len(evidence["strengths"]) <= 3
        assert len(evidence["risks"]) <= 2
        assert any("OBP 第" in text and "75" in text for text in evidence["strengths"])
        assert any("ISO 第" in text and "75" in text for text in evidence["strengths"])
        assert any("K% 有利百分位" in text and "25" in text for text in evidence["risks"])
        assert any("PA 20" in text and "30" in text for text in evidence["notes"])


    def test_pitcher_evidence_uses_lower_is_better_percentiles() -> None:
        pitchers = pd.DataFrame(
            [
                {"player_id": "0000000101", "innings_pitched": 18.0, "era": 1.5, "whip": 0.90, "k_bb_ratio": 5.0, "hr_allowed_rate": 0.04},
                {"player_id": "0000000102", "innings_pitched": 18.0, "era": 2.2, "whip": 1.10, "k_bb_ratio": 3.0, "hr_allowed_rate": 0.03},
                {"player_id": "0000000103", "innings_pitched": 18.0, "era": 3.4, "whip": 1.30, "k_bb_ratio": 2.0, "hr_allowed_rate": 0.02},
                {"player_id": "0000000104", "innings_pitched": 18.0, "era": 4.6, "whip": 1.50, "k_bb_ratio": 1.0, "hr_allowed_rate": 0.01},
            ]
        )
        strength_evidence = build_evidence_signals(pitchers.iloc[0], pitchers, "投手", 10)
        risk_evidence = build_evidence_signals(pitchers.iloc[0], pitchers, "投手", 10)
        assert any("ERA 第" in text and "WHIP 第" in text for text in strength_evidence["strengths"])
        assert any("被 HR% 有利百分位" in text for text in risk_evidence["risks"])


    def test_ranking_and_comparison_preserve_documented_order(scored_hitters: pd.DataFrame) -> None:
        ranked = rank_scouting_candidates(scored_hitters, "打者", 30, "長打")
        assert ranked["player_id"].tolist() == ["0000000002", "0000000003", "0000000004"]
        assert ranked["qualified_percentile"].between(0, 100).all()
        compared = comparison_frame(ranked, ["0000000003", "0000000002"], "打者")
        assert compared["player_id"].tolist() == ["0000000003", "0000000002"]
        assert compared.columns.tolist() == [
            "player_id", "player_name", "team", "role_or_position", "pa",
            "priority_score", "qualified_percentile", "contact_score",
            "power_score", "discipline_score", "hitter_value_score",
        ]

- [ ] **Step 2: Run the tests to verify they fail**

Run: python -m pytest tests/test_scouting.py -q

Expected: import failure for build_evidence_signals, comparison_frame, and rank_scouting_candidates.

- [ ] **Step 3: Implement priority calculation and evidence generation**

Append to src/scouting.py:

    PRIORITY_WEIGHTS = {
        "打者": {
            "綜合價值": {"player_value_score": 1.00},
            "接觸與選球": {"contact_score": 0.55, "discipline_score": 0.45},
            "長打": {"power_score": 0.70, "hitter_value_score": 0.30},
        },
        "投手": {
            "綜合價值": {"player_value_score": 1.00},
            "失分壓制": {"run_prevention_score": 0.75, "pitcher_value_score": 0.25},
            "控球能力": {"command_score": 0.70, "strikeout_score": 0.30},
        },
    }


    def priority_options(player_type: str) -> list[str]:
        qualification_column(player_type)
        return list(PRIORITY_WEIGHTS[player_type])


    def build_evidence_signals(
        row: pd.Series,
        population: pd.DataFrame,
        player_type: str,
        threshold: float,
    ) -> dict[str, list[str]]:
        usage_column = qualification_column(player_type)
        usage_label = qualification_label(player_type)
        strengths: list[str] = []
        risks: list[str] = []
        notes: list[str] = []
        missing: list[str] = []

        def percentile(metric: str, lower_is_better: bool = False) -> float | None:
            value = percentile_rank(population, row, metric, lower_is_better)
            if value is None:
                missing.append(metric)
            return value

        if player_type == "打者":
            obp = percentile("obp")
            iso = percentile("iso")
            k_rate = percentile("k_rate", lower_is_better=True)
            if obp is not None and obp >= 75:
                strengths.append(f"上壘訊號：OBP 第 {obp:.1f} 百分位（門檻 ≥ 75）。")
            if iso is not None and iso >= 75:
                strengths.append(f"長打訊號：ISO 第 {iso:.1f} 百分位（門檻 ≥ 75）。")
            if k_rate is not None and k_rate <= 25:
                risks.append(f"選球風險：K% 有利百分位 {k_rate:.1f}（門檻 ≤ 25；K% 越低越好）。")
        else:
            era = percentile("era", lower_is_better=True)
            whip = percentile("whip", lower_is_better=True)
            k_bb_ratio = percentile("k_bb_ratio")
            hr_allowed_rate = percentile("hr_allowed_rate", lower_is_better=True)
            if era is not None and whip is not None and era >= 75 and whip >= 75:
                strengths.append(f"失分壓制訊號：ERA 第 {era:.1f}、WHIP 第 {whip:.1f} 百分位（各門檻 ≥ 75；越低越好）。")
            if k_bb_ratio is not None and k_bb_ratio >= 75:
                strengths.append(f"控球訊號：K/BB 第 {k_bb_ratio:.1f} 百分位（門檻 ≥ 75）。")
            if hr_allowed_rate is not None and hr_allowed_rate <= 25:
                risks.append(f"被全壘打風險：被 HR% 有利百分位 {hr_allowed_rate:.1f}（門檻 ≤ 25；越低越好）。")

        usage = pd.to_numeric(pd.Series([row.get(usage_column)]), errors="coerce").iloc[0]
        if pd.notna(usage) and float(usage) < float(threshold):
            notes.append(f"樣本限制：{usage_label} {float(usage):g}，低於 {float(threshold):g} 門檻。")
        if missing:
            notes.append("資料涵蓋不足：缺少 " + "、".join(sorted(set(missing))).upper() + "，未產生對應訊號。")
        if not strengths and not risks:
            notes.append("中性判讀：尚未達到既定強項或風險門檻，請搭配完整成績與聯盟比較。")
        return {"strengths": strengths[:3], "risks": risks[:2], "notes": notes}


    def _priority_score(df: pd.DataFrame, player_type: str, priority: str) -> pd.Series:
        try:
            weights = PRIORITY_WEIGHTS[player_type][priority]
        except KeyError as exc:
            raise ValueError(f"{player_type} 不支援評估重點：{priority}") from exc
        if any(column not in df.columns for column in weights):
            return pd.Series(index=df.index, dtype=float)
        return sum(pd.to_numeric(df[column], errors="coerce") * weight for column, weight in weights.items()).round(1)


    def rank_scouting_candidates(
        df: pd.DataFrame,
        player_type: str,
        threshold: float,
        priority: str,
        team: str = "全部",
        role_or_position: str = "全部",
    ) -> pd.DataFrame:
        population = qualified_population(df, player_type, threshold)
        if population.empty:
            return population
        population["priority_score"] = _priority_score(population, player_type, priority)
        population = population.dropna(subset=["priority_score"])
        population["qualified_percentile"] = population.apply(
            lambda row: percentile_rank(population, row, "priority_score") or 0.0, axis=1
        )
        role_column = "position" if player_type == "打者" else "role"
        population["role_or_position"] = population[role_column].fillna("未記錄")
        evidence = population.apply(
            lambda row: build_evidence_signals(row, population, player_type, threshold), axis=1
        )
        population["evidence_strengths"] = evidence.map(lambda item: "；".join(item["strengths"]) or "無")
        population["evidence_risks"] = evidence.map(lambda item: "；".join(item["risks"]) or "無")
        population["evidence_notes"] = evidence.map(lambda item: "；".join(item["notes"]))
        filtered = population
        if team != "全部":
            filtered = filtered[filtered["team"] == team]
        if role_or_position != "全部":
            filtered = filtered[filtered["role_or_position"] == role_or_position]
        return filtered.sort_values(["priority_score", "player_id"], ascending=[False, True]).reset_index(drop=True)


    def comparison_frame(candidates: pd.DataFrame, selected_player_ids: list[str], player_type: str) -> pd.DataFrame:
        usage_column = qualification_column(player_type)
        score_columns = (
            ["contact_score", "power_score", "discipline_score", "hitter_value_score"]
            if player_type == "打者"
            else ["run_prevention_score", "strikeout_score", "command_score", "pitcher_value_score"]
        )
        columns = [
            "player_id", "player_name", "team", "role_or_position", usage_column,
            "priority_score", "qualified_percentile", *score_columns,
        ]
        if candidates.empty or not selected_player_ids:
            return pd.DataFrame(columns=columns)
        indexed = candidates.copy()
        indexed["player_id"] = indexed["player_id"].astype("string")
        indexed = indexed.drop_duplicates(subset=["player_id"]).set_index("player_id", drop=False)
        ordered_ids = [str(player_id) for player_id in selected_player_ids[:4] if str(player_id) in indexed.index]
        return indexed.reindex(ordered_ids)[columns].reset_index(drop=True)

The qualified percentile and evidence are deliberately calculated before the team and role/position filters. A team subgroup must never be displayed as a league percentile.

- [ ] **Step 4: Run the scouting suite**

Run: python -m pytest tests/test_scouting.py -q

Expected: all scouting tests pass. The long-ball ranking starts with 0000000002 because 0000000001 is below the 30 PA qualification threshold.

- [ ] **Step 5: Commit**

    git add src/scouting.py tests/test_scouting.py
    git commit -m "feat: add explainable scouting rankings"

### Task 3: Render Data Trust and Player Evidence

**Files:**
- Modify: app.py imports, PAGES, display labels, source helpers, page_home, page_player, and PAGE_HANDLERS.
- Modify: src/theme.py trust strip and mobile rules.
- Modify: tests/test_streamlit_pages.py.

**Interfaces:**
- Consumes: DEFAULT_QUALIFICATION, qualified_population, qualification_label, percentile_rank, and build_evidence_signals.
- Produces: render_data_trust_surface(report: dict, player_type: str | None = None, threshold: float | None = None, population_count: int | None = None) -> None and render_player_evidence(row: pd.Series, population: pd.DataFrame, player_type: str, threshold: float) -> None.

- [ ] **Step 1: Add failing page assertions**

Update PAGES in tests/test_streamlit_pages.py so the first page is 資料訊號總覽 and a 球探工作台 entry follows 聯盟總覽. Add:

    def test_data_signal_overview_exposes_lineage_quality_and_log5_limit() -> None:
        import app as dashboard

        app = AppTest.from_file(APP_PATH)
        app.run(timeout=20)
        app.sidebar.radio[0].set_value("資料訊號總覽")
        app.run(timeout=20)
        text = visible_text(app)

        assert "www.cpbl.com.tw" in text
        assert dashboard.data_generated_time() in text
        assert "品質狀態" in text
        assert "LOG5 為情境計算，非校準預測模型" in text


    def test_player_page_renders_explainable_evidence_with_percentile_basis() -> None:
        app = AppTest.from_file(APP_PATH)
        app.run(timeout=20)
        app.sidebar.radio[0].set_value("球員個人頁")
        app.run(timeout=20)
        text = visible_text(app)

        assert "評估依據" in text
        assert "符合門檻母體" in text
        assert "百分位" in text
        assert "樣本限制" in text or "中性判讀" in text or "訊號" in text

In REQUIRED_FRONTEND_TERMS, replace the overview key with 資料訊號總覽 and require 資料品質, 資料可回答, 資料限制, and LOG5 為情境計算，非校準預測模型. Add 評估依據 to 球員個人頁 requirements.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: python -m pytest tests/test_streamlit_pages.py::test_data_signal_overview_exposes_lineage_quality_and_log5_limit tests/test_streamlit_pages.py::test_player_page_renders_explainable_evidence_with_percentile_basis -q

Expected: both tests fail because the overview and evidence section do not yet render the required terms.

- [ ] **Step 3: Import the analytics boundary and expose labels**

Add this app.py import:

    from src.scouting import (
        DEFAULT_QUALIFICATION,
        build_evidence_signals,
        percentile_rank,
        qualification_label,
        qualified_population,
    )

Add these COLUMN_LABELS entries:

    "priority_score": "評估分數",
    "qualified_percentile": "符合門檻母體百分位",
    "evidence_strengths": "強項依據",
    "evidence_risks": "風險依據",
    "evidence_notes": "資料註記",

Add priority_score and qualified_percentile to SCORE_METRICS. Delete the local app.py percentile_rank implementation and update league_percentile_chart to plot None as 0.0:

    values = [percentile_rank(df, row, metric, lower_better) or 0.0 for metric, lower_better in metrics]

- [ ] **Step 4: Implement trust and evidence rendering**

Insert after source_status_panel in app.py:

    def render_data_trust_surface(
        report: dict,
        player_type: str | None = None,
        threshold: float | None = None,
        population_count: int | None = None,
    ) -> None:
        quality_status = str(report.get("quality_status", "unknown"))
        quality_label = {"pass": "通過", "warning": "需注意", "failed": "失敗"}.get(quality_status, "未知")
        details = [
            "來源網域：www.cpbl.com.tw",
            f"最後驗證：{data_generated_time(report)}",
            f"資料品質：{quality_label}",
        ]
        if player_type is not None and threshold is not None and population_count is not None:
            details.append(f"符合門檻母體：{population_count} 人（{qualification_label(player_type)} ≥ {threshold:g}）")
        st.markdown(
            "<div class='trust-strip' role='note'><span>" + "</span><span>".join(escape(item) for item in details) + "</span></div>",
            unsafe_allow_html=True,
        )
        warnings = [str(item) for item in report.get("warnings", []) if str(item)]
        if quality_status != "pass" and warnings:
            st.warning("資料品質警示：" + "；".join(warnings))
        st.caption("LOG5 為情境計算，非校準預測模型；不可視為未來表現、勝負或名單決策預測。")


    def render_player_evidence(row: pd.Series, population: pd.DataFrame, player_type: str, threshold: float) -> None:
        evidence = build_evidence_signals(row, population, player_type, threshold)
        st.header("評估依據")
        st.caption(f"符合門檻母體 {len(population)} 人；{qualification_label(player_type)} ≥ {threshold:g}；百分位越高代表相對表現越前。")
        columns = st.columns(3, gap="medium")
        sections = [("強項", evidence["strengths"]), ("風險", evidence["risks"]), ("資料註記", evidence["notes"])]
        for container, (heading, items) in zip(columns, sections):
            container.subheader(heading)
            if items:
                for item in items:
                    container.markdown(f"- {item}")
            else:
                container.caption("未觸發既定門檻。")

Replace generic page_home copy with st.title("資料訊號總覽"), source_status_panel(), render_data_trust_surface(QUALITY_REPORT), current counts, and unframed 資料可回答 and 資料限制 sections. The answerable questions are qualification, score drivers, qualified-population comparison, and data limits. The limitation text says current-season official summaries do not project future performance. Retain the workflow grid and add 球探工作台 as the first workflow.

In page_player, after resolving stat_type, df, and row, render:

    evidence_threshold = DEFAULT_QUALIFICATION[stat_type]
    evidence_population = qualified_population(df, stat_type, evidence_threshold)
    render_data_trust_surface(QUALITY_REPORT, stat_type, evidence_threshold, len(evidence_population))
    render_player_evidence(row, evidence_population, stat_type, evidence_threshold)

Place it after 本季成績. For roster-only players, add 評估依據 and the exact sentence 尚無一軍成績，無法計算符合門檻母體百分位或評估訊號。 before advanced statistics.

- [ ] **Step 5: Add focused layout rules**

Append before the current mobile media query in src/theme.py:

    .trust-strip {
      display: flex;
      flex-wrap: wrap;
      gap: .45rem .9rem;
      margin: .75rem 0 1.25rem 0;
      padding: .78rem .92rem;
      border: 1px solid rgba(101, 185, 149, .42);
      border-left: 3px solid var(--mint);
      border-radius: 4px;
      background: var(--surface-muted);
      color: var(--muted-strong);
      font-size: 1rem;
      line-height: 1.5;
    }

    .trust-strip span + span::before {
      content: "•";
      color: var(--mint);
      margin-right: .9rem;
    }

Add this declaration inside the current 720px media block:

    .trust-strip {
      align-items: flex-start;
      flex-direction: column;
      gap: .25rem;
    }

Do not wrap the three evidence columns in a cpbl-card, avoiding nested cards.

- [ ] **Step 6: Run the page and complete regression suites**

Run:

    python -m pytest tests/test_streamlit_pages.py -q
    python -m pytest -q

Expected: every page still has exactly one H1; page rendering, Traditional Chinese, terminology, table export, accessibility, and new trust/evidence tests pass.

- [ ] **Step 7: Commit**

    git add app.py src/theme.py tests/test_streamlit_pages.py
    git commit -m "feat: show auditable player evidence"

### Task 4: Build the Scouting Workbench Page

**Files:**
- Modify: app.py PAGES, PAGE_HANDLERS, imports, and page functions.
- Modify: tests/test_streamlit_pages.py.

**Interfaces:**
- Consumes: DEFAULT_QUALIFICATION, qualified_population, qualification_label, priority_options, rank_scouting_candidates, comparison_frame, and render_data_trust_surface.
- Produces: page_scouting_workbench() -> None and a 球探工作台 entry in PAGES and PAGE_HANDLERS.
- Controls: 球員類型, 球隊, 位置 / 角色, 最低打席 (PA) or 最低投球局數 (IP), 評估重點, and 比較球員.

- [ ] **Step 1: Add a failing workbench page test**

Add 球探工作台 to REQUIRED_FRONTEND_TERMS with 球探工作台, 最低打席 (PA), 評估重點, 符合門檻母體, and 最多選擇 4 位球員.

Extend visible_text:

    for multiselect in app.multiselect:
        parts.append(str(multiselect.label))
        parts.extend(str(option) for option in multiselect.options)

Add this test:

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

- [ ] **Step 2: Run the focused test to verify it fails**

Run: python -m pytest tests/test_streamlit_pages.py::test_scouting_workbench_filters_and_compares_without_errors -q

Expected: sidebar selection fails because 球探工作台 has no handler.

- [ ] **Step 3: Wire the page into navigation**

Add comparison_frame, priority_options, and rank_scouting_candidates to the app.py scouting import group.

Replace PAGES with:

    PAGES = [
        "資料訊號總覽",
        "聯盟總覽",
        "球探工作台",
        "球員排行榜",
        "球員個人頁",
        "投打對決",
        "分項排行",
    ]

Rename page_home’s page-kicker to 資料訊號總覽. In PAGE_HANDLERS replace the old overview key with 資料訊號總覽, and add:

    "球探工作台": page_scouting_workbench,

- [ ] **Step 4: Implement the workbench**

Insert page_scouting_workbench between page_league and page_rankings in app.py:

    def page_scouting_workbench() -> None:
        page_kicker("球探工作台")
        st.title("球探工作台")
        st.caption("以可重現的資格門檻、既有衍生分數與聯盟百分位建立本季觀察名單；不預測未來表現。")
        player_type = st.radio("球員類型", ["打者", "投手"], horizontal=True, key="scouting_player_type")
        source = BATTERS if player_type == "打者" else PITCHERS
        if source.empty:
            st.info(f"目前缺少官方{player_type}成績，無法建立球探工作台。")
            return

        usage_column = "pa" if player_type == "打者" else "innings_pitched"
        usage_label = qualification_label(player_type)
        default_threshold = DEFAULT_QUALIFICATION[player_type]
        maximum = float(pd.to_numeric(source[usage_column], errors="coerce").max() or default_threshold)
        maximum = max(maximum, default_threshold)
        team = st.selectbox("球隊", ["全部", *sorted(source["team"].dropna().unique())], key=f"scouting_team_{player_type}")
        role_column = "position" if player_type == "打者" else "role"
        role_values = sorted(source[role_column].dropna().astype(str).unique())
        role_or_position = st.selectbox("位置 / 角色", ["全部", *role_values], key=f"scouting_role_{player_type}")
        if player_type == "打者":
            threshold = st.number_input("最低打席 (PA)", min_value=int(default_threshold), max_value=max(int(maximum), int(default_threshold)), value=int(default_threshold), step=5, key="scouting_min_pa")
        else:
            threshold = st.number_input("最低投球局數 (IP)", min_value=float(default_threshold), max_value=maximum, value=float(default_threshold), step=1.0, key="scouting_min_ip")
        priority = st.selectbox("評估重點", priority_options(player_type), key=f"scouting_priority_{player_type}")

        qualified = qualified_population(source, player_type, float(threshold))
        render_data_trust_surface(QUALITY_REPORT, player_type, float(threshold), len(qualified))
        candidates = rank_scouting_candidates(source, player_type, float(threshold), priority, team, role_or_position)
        if candidates.empty:
            st.info(f"目前沒有符合條件的球員。資格門檻維持 {usage_label} ≥ {float(threshold):g}，請調整球隊或位置 / 角色。")
            return

        st.header("候選名單")
        st.caption(f"評估重點：{priority}；排名依評估分數降冪，同分時依 CPBL 球員 ID 排序。")
        display_columns = (
            ["player_id", "player_name", "team", "role_or_position", "pa", "priority_score", "qualified_percentile", "contact_score", "power_score", "discipline_score", "hitter_value_score", "evidence_strengths", "evidence_risks", "evidence_notes"]
            if player_type == "打者"
            else ["player_id", "player_name", "team", "role_or_position", "innings_pitched", "priority_score", "qualified_percentile", "run_prevention_score", "strikeout_score", "command_score", "pitcher_value_score", "evidence_strengths", "evidence_risks", "evidence_notes"]
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

Pass float(threshold) to all analytical functions. Do not duplicate a score, percentile, or evidence calculation in app.py.

- [ ] **Step 5: Run focused and complete page tests**

Run:

    python -m pytest tests/test_streamlit_pages.py::test_scouting_workbench_filters_and_compares_without_errors -q
    python -m pytest tests/test_streamlit_pages.py -q

Expected: both player types render with the correct PA/IP input, evidence table, up-to-four comparison control, and existing pages unchanged.

- [ ] **Step 6: Commit**

    git add app.py tests/test_streamlit_pages.py
    git commit -m "feat: add CPBL scouting workbench"

### Task 5: Document the Interview Narrative and Public Repository Contract

**Files:**
- Modify: README.md
- Create: tests/test_project_docs.py

**Interfaces:**
- Consumes: pipeline module names and priority weights from Tasks 1–4.
- Produces: an interview-reviewable README and a docs regression test.
- Public repository rule: only source, tests, processed CSVs, reports, documentation, workflows, and configuration may be tracked.

- [ ] **Step 1: Write the failing README-contract test**

Create tests/test_project_docs.py:

    from pathlib import Path


    def test_readme_explains_auditable_data_product_and_limits() -> None:
        readme = Path("README.md").read_text(encoding="utf-8-sig")
        required = [
            "官方 CPBL 資料來源",
            "資料管線",
            "資料品質與可稽核性",
            "球探工作台",
            "評估公式",
            "資料限制",
            "重現與測試",
            "公開儲存庫政策",
            "LOG5 為情境計算，非校準預測模型",
            "data/raw/",
            "notes/source_prompt.txt",
        ]
        for heading in required:
            assert heading in readme

- [ ] **Step 2: Run the test to verify it fails**

Run: python -m pytest tests/test_project_docs.py -q

Expected: the current README fails the complete interview-facing contract.

- [ ] **Step 3: Replace README with concise, verifiable documentation**

Use these exact headings, prose requirements, and formulas:

    # CPBL 中職資料分析平台

    以 CPBL 官方公開資料建立的可稽核球員評估資料產品。它不預測比賽或產生名單建議；每個結論都可追溯到官方資料、資格門檻、衍生分數與百分位。

    ## 官方 CPBL 資料來源

    List /player, /standings/season, and /stats/recordallaction as full www.cpbl.com.tw URLs. State that reports/metrics/data_quality_report.json records fetch time, row counts, field completeness, duplicate IDs, and value-range checks.

    ## 資料管線

    CPBL 官方公開頁面 -> src/fetch_cpbl_data.py -> src/preprocess.py -> data/processed/*.csv -> src/data_quality.py -> src/scouting.py -> Streamlit 介面

    State that player_id remains a string to preserve leading zeroes.

    ## 資料品質與可稽核性

    State official-host restriction, full-pagination requirement, schema/duplicate/range checks, CSV formula neutralization, loopback binding, and exclusion of raw/private artifacts.

    ## 球探工作台

    State PA >= 30 and IP >= 10 defaults; analysts may raise thresholds and filter team/position/role. State percentiles are computed on the qualified type population before filters.

    ## 評估公式

    | 類型 | 評估重點 | 公式 |
    | --- | --- | --- |
    | 打者 | 綜合價值 | player_value_score |
    | 打者 | 接觸與選球 | 0.55 * contact_score + 0.45 * discipline_score |
    | 打者 | 長打 | 0.70 * power_score + 0.30 * hitter_value_score |
    | 投手 | 綜合價值 | player_value_score |
    | 投手 | 失分壓制 | 0.75 * run_prevention_score + 0.25 * pitcher_value_score |
    | 投手 | 控球能力 | 0.70 * command_score + 0.30 * strikeout_score |

    State that fixed thresholds create evidence and that a limited sample is separate from performance.

    ## 資料限制

    State that current-season official aggregates do not establish injuries, tactics, future performance, or roster decisions. Include exactly: LOG5 為情境計算，非校準預測模型；不可視為勝負、投注或未來表現預測。

    ## 重現與測試

        run_project.bat --runtime-check
        python run_all.py --mode api
        python -m pytest -q
        run_project.bat --check

    ## 公開儲存庫政策

    State that source, tests, data/processed CSVs, quality reports, docs, workflows, and config are public. State that data/raw/, notes/source_prompt.txt, .env, .streamlit/secrets.toml, credentials, local databases, logs, cache, and .venv/ are never tracked.

- [ ] **Step 4: Run README and complete application tests**

Run:

    python -m pytest tests/test_project_docs.py -q
    python -m pytest -q

Expected: all tests pass and the repository story can be understood without running the dashboard.

- [ ] **Step 5: Commit**

    git add README.md tests/test_project_docs.py
    git commit -m "docs: explain CPBL scouting data product"

### Task 6: Refresh, Verify, Audit, and Publish Only Public Material

**Files:**
- Modify only if official API output has changed: data/processed/*.csv and reports/metrics/data_quality_report.json.
- Never modify or stage: data/raw/, notes/source_prompt.txt, .env, .streamlit/secrets.toml, credential files, local environments, caches, or logs.

**Interfaces:**
- Consumes: all preceding tasks, existing run_all.py, run_project.bat, .github/workflows/security.yml, and .gitignore.
- Produces: a verified public main commit and a successful GitHub Security checks run.

- [ ] **Step 1: Refresh from official CPBL sources and inspect quality**

Run:

    python run_all.py --mode api
    python -c "import json; r=json.load(open('reports/metrics/data_quality_report.json', encoding='utf-8')); print({'quality_status': r['quality_status'], 'generated_at': r['generated_at'], 'teams': r['available_team_count'], 'roster': r['official_roster_count'], 'hitters': r['available_hitter_count'], 'pitchers': r['available_pitcher_count']})"

Expected: quality_status is pass; every count is nonzero and meets the existing quality-report minimums. If it is failed, diagnose official-source retrieval or schema before continuing.

- [ ] **Step 2: Run full functional regression checks**

Run:

    run_project.bat --check
    python -m pytest -q

Expected: refresh, quality checks, all tests, and smoke test complete successfully.

- [ ] **Step 3: Run security scans in the project environment**

Run:

    .\.venv\Scripts\python.exe -m pip install --upgrade pip-audit bandit detect-secrets
    .\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
    .\.venv\Scripts\python.exe -m bandit -r app.py src run_all.py -ll
    .\.venv\Scripts\detect-secrets.exe scan --all-files --exclude-files '(^|[\\/])\.(venv|git|pytest_cache|pytest_tmp)([\\/]|$)' | Set-Content -Encoding utf8 .\reports\metrics\secret-scan.json
    .\.venv\Scripts\python.exe -c "import json,sys; r=json.load(open('reports/metrics/secret-scan.json', encoding='utf-8')).get('results', {}); n=sum(len(v) for v in r.values()); print(f'secret findings={n}'); sys.exit(1 if n else 0)"

Expected: no known dependency vulnerability, no Bandit medium/high finding, and secret findings=0. Remove reports/metrics/secret-scan.json before staging because it is a transient audit artifact.

- [ ] **Step 4: Audit Git history and tracked files**

Run:

    git fsck --full
    git log --all -G "BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}" --oneline
    git ls-files | rg "(^|/)(data/raw|notes/source_prompt\.txt|\.env|\.venv|.*\.(pem|key|p12|pfx)|credentials\.json)$"
    git status --short

Expected: fsck succeeds; history and tracked-file searches return no matching private files; status contains only reviewed source, test, processed CSV, report, and documentation changes.

- [ ] **Step 5: Stage only reviewed public files and commit the release**

Run:

    git diff --check
    git diff -- app.py src/scouting.py src/theme.py tests/test_scouting.py tests/test_streamlit_pages.py tests/test_project_docs.py README.md data/processed reports/metrics/data_quality_report.json
    git add app.py src/scouting.py src/theme.py tests/test_scouting.py tests/test_streamlit_pages.py tests/test_project_docs.py README.md data/processed reports/metrics/data_quality_report.json
    git commit -m "feat: deliver auditable CPBL scouting workbench"

Expected: the commit has no raw data, secret, cache, environment, prompt, or transient audit-scan file.

- [ ] **Step 6: Push the reviewed public commit and verify CI**

Run:

    git push origin main

Open the run created by the push. Security checks must be green for the Gitleaks history scan, tracked-file secret scan, pip-audit, Bandit, and pytest. Record the run URL in the completion summary.

## Plan Self-Review

**Spec coverage:** Task 1 provides PA/IP qualification and direction-aware percentiles. Task 2 provides deterministic strengths, risks, neutral notes, documented priorities, stable sort order, and four-player comparison. Task 3 turns the home page into a data-signal overview and exposes lineage, quality status, warnings, LOG5 limitation, and player evidence. Task 4 implements every requested workbench filter, shortlist, evidence table, empty state, and comparison. Task 5 makes pipeline, formulas, limits, reproducibility, and public policy clear to an interviewer. Task 6 refreshes official data and verifies functionality, security, Git integrity, public-file scope, and CI.

**Placeholder scan:** Every task has paths, signatures, UI labels, formulas, test code, commands, expected results, and commits. No deferred work markers are present.

**Type consistency:** qualified_population returns the DataFrame used by percentile_rank, build_evidence_signals, and rank_scouting_candidates. rank_scouting_candidates returns the candidate DataFrame consumed by comparison_frame. comparison_frame returns the DataFrame consumed by show_table. The qualification boundary converts player_id to pandas string and comparison converts selected IDs to str before indexing.
