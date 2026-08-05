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


def qualification_upper_bound(df: pd.DataFrame, player_type: str) -> float:
    column = qualification_column(player_type)
    default = float(DEFAULT_QUALIFICATION[player_type])
    if df.empty or column not in df.columns:
        return default

    maximum = pd.to_numeric(df[column], errors="coerce").max()
    if pd.isna(maximum):
        return default
    return max(float(maximum), default)


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
    basis: list[str] = []

    def percentile(metric: str, lower_is_better: bool = False) -> float | None:
        value = percentile_rank(population, row, metric, lower_is_better)
        if value is None:
            missing.append(metric)
        return value

    def add_basis(label: str, value: float | None) -> None:
        if value is not None:
            basis.append(f"{label} 有利百分位 {value:.1f}")

    if player_type == "打者":
        obp = percentile("obp")
        iso = percentile("iso")
        k_rate = percentile("k_rate", lower_is_better=True)
        add_basis("OBP", obp)
        add_basis("ISO", iso)
        add_basis("K%", k_rate)
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
        add_basis("ERA", era)
        add_basis("WHIP", whip)
        add_basis("K/BB", k_bb_ratio)
        add_basis("被 HR%", hr_allowed_rate)
        if era is not None and whip is not None and era >= 75 and whip >= 75:
            strengths.append(f"失分壓制訊號：ERA 第 {era:.1f}、WHIP 第 {whip:.1f} 百分位（各門檻 ≥ 75；越低越好）。")
        if k_bb_ratio is not None and k_bb_ratio >= 75:
            strengths.append(f"控球訊號：K/BB 第 {k_bb_ratio:.1f} 百分位（門檻 ≥ 75）。")
        if hr_allowed_rate is not None and hr_allowed_rate <= 25:
            risks.append(f"被全壘打風險：被 HR% 有利百分位 {hr_allowed_rate:.1f}（門檻 ≤ 25；越低越好）。")

    usage = pd.to_numeric(pd.Series([row.get(usage_column)]), errors="coerce").iloc[0]
    if pd.notna(usage) and float(usage) < float(threshold):
        notes.append(f"樣本限制：{usage_label} {float(usage):g}，低於 {float(threshold):g} 門檻。")
    notes.append("百分位依據：" + "；".join(basis) + "。")
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
    score = pd.Series(0.0, index=df.index, dtype=float)
    for column, weight in weights.items():
        score = score + pd.to_numeric(df[column], errors="coerce") * weight
    return score.round(1)


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
        lambda row: percentile_rank(population, row, "priority_score") or 0.0,
        axis=1,
    )
    role_column = "position" if player_type == "打者" else "role"
    population["role_or_position"] = population[role_column].fillna("未記錄")
    evidence = population.apply(
        lambda row: build_evidence_signals(row, population, player_type, threshold),
        axis=1,
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
        "player_id",
        "player_name",
        "team",
        "role_or_position",
        usage_column,
        "priority_score",
        "qualified_percentile",
        *score_columns,
    ]
    if candidates.empty or not selected_player_ids:
        return pd.DataFrame(columns=columns)

    indexed = candidates.copy()
    indexed["player_id"] = indexed["player_id"].astype("string")
    indexed = indexed.drop_duplicates(subset=["player_id"]).set_index("player_id", drop=False)
    ordered_ids = [str(player_id) for player_id in selected_player_ids[:4] if str(player_id) in indexed.index]
    return indexed.reindex(ordered_ids)[columns].reset_index(drop=True)
