from __future__ import annotations

import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "outputs" / "tables"
FIGURE_DIR = ROOT / "outputs" / "figures"
REPORT_DIR = ROOT / "outputs" / "report"
ARTICLE_URL = "https://qiita.com/tikeda123/items/091519af64bd22367c2d"


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLE_DIR / name)


def one(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        raise ValueError("Expected one row, got no rows.")
    return df.iloc[0]


def fnum(value: object, digits: int = 3, suffix: str = "") -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(numeric):
        return "-"
    return f"{numeric:.{digits}f}{suffix}"


def markdown_table(df: pd.DataFrame, cols: list[str], digits: int = 3) -> str:
    if df.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df[cols].iterrows():
        cells = []
        for col in cols:
            value = row[col]
            cells.append(fnum(value, digits) if isinstance(value, (float, np.floating)) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        "btc_crash_baseline": read_csv("btc_crash_baseline.csv"),
        "btc_cost_stress": read_csv("btc_cost_stress.csv"),
        "btc_entry_execution_stress": read_csv("btc_entry_execution_stress.csv"),
        "btc_definition_robustness": read_csv("btc_definition_robustness.csv"),
        "btc_risk_env_robustness": read_csv("btc_risk_env_robustness.csv"),
        "btc_funding_definition_robustness": read_csv("btc_funding_definition_robustness.csv"),
        "btc_subperiod_results": read_csv("btc_subperiod_results.csv"),
        "btc_bootstrap_uncertainty": read_csv("btc_bootstrap_uncertainty.csv"),
        "btc_leverage_tolerance": read_csv("btc_leverage_tolerance.csv"),
    }


def build_article_fragility_matrix(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = tables["btc_crash_baseline"]
    boot = tables["btc_bootstrap_uncertainty"]
    definition = tables["btc_definition_robustness"]
    period = tables["btc_subperiod_results"]
    cost = tables["btc_cost_stress"]
    entry = tables["btc_entry_execution_stress"]
    leverage = tables["btc_leverage_tolerance"]
    risk = tables["btc_risk_env_robustness"]

    low48 = one(base[(base["horizon"].eq("48h")) & (base["group"].eq("funding_low_x_risk_on"))])
    boot48 = one(boot[(boot["horizon"].eq("48h")) & (boot["group"].eq("funding_low_x_risk_on"))])
    q025 = one(
        definition[
            (definition["horizon"].eq("48h"))
            & (definition["event_def"].eq("full_sample_q025"))
            & (definition["group"].eq("funding_low_x_risk_on"))
        ]
    )
    period2022 = one(
        period[
            (period["horizon"].eq("48h"))
            & (period["period"].eq("2022_stress"))
            & (period["group"].eq("funding_low_x_risk_on"))
        ]
    )
    cost5 = one(
        cost[
            (cost["horizon"].eq("48h"))
            & (cost["cost_case"].eq("cost_x5"))
            & (cost["group"].eq("funding_low_x_risk_on"))
        ]
    )
    delay4 = one(
        entry[
            (entry["horizon"].eq("48h"))
            & (entry["entry_case"].eq("delay_4h"))
            & (entry["group"].eq("funding_low_x_risk_on"))
        ]
    )
    lev3 = one(
        leverage[
            (leverage["horizon"].eq("48h"))
            & (leverage["leverage"].eq(3.0))
            & (leverage["group"].eq("funding_low_x_risk_on"))
        ]
    )
    sp500 = one(
        risk[
            (risk["horizon"].eq("48h"))
            & (risk["risk_env"].eq("sp500_5d_up"))
            & (risk["group"].eq("funding_low_x_risk_on"))
        ]
    )

    rows = [
        {
            "article_section": "12 Fragility Matrix",
            "breakable_assumption": "小標本でも平均が安定",
            "assumption_being_doubted": "条件付き平均は安定している",
            "stress_case": "48h bootstrap",
            "metric": "mean_ret_pct",
            "baseline_value": fnum(low48["mean_ret_pct"], 3, "%"),
            "stressed_value": fnum(boot48["mean_p05_pct"], 3, "%"),
            "change": f"n={int(low48['n'])}",
            "fragility_status": "fragile",
            "article_message": "PFより先に標本数と不確実性を出す。",
            "practical_response": "主張を弱め、サイズを落とす。",
        },
        {
            "article_section": "10 Crash Definition",
            "breakable_assumption": "急落定義に依存しない",
            "assumption_being_doubted": "結果は定義に依存しない",
            "stress_case": "48h full_sample_q025",
            "metric": "mean_ret_pct / PF",
            "baseline_value": f"{fnum(low48['mean_ret_pct'], 3, '%')} / PF {fnum(low48['profit_factor'], 3)}",
            "stressed_value": f"{fnum(q025['mean_ret_pct'], 3, '%')} / PF {fnum(q025['profit_factor'], 3)}",
            "change": fnum(float(q025["mean_ret_pct"]) - float(low48["mean_ret_pct"]), 3, "pp"),
            "fragility_status": "broken",
            "article_message": "定義変更だけで48h平均がマイナスに反転する。",
            "practical_response": "複数定義で確認し、定義ロバスト性を先に公開する。",
        },
        {
            "article_section": "11 Regime",
            "breakable_assumption": "特定レジームだけでない",
            "assumption_being_doubted": "レジームを跨いで有効",
            "stress_case": "48h 2022 stress period",
            "metric": "mean_ret_pct / PF",
            "baseline_value": f"{fnum(low48['mean_ret_pct'], 3, '%')} / PF {fnum(low48['profit_factor'], 3)}",
            "stressed_value": f"{fnum(period2022['mean_ret_pct'], 3, '%')} / PF {fnum(period2022['profit_factor'], 3)}",
            "change": f"n={int(period2022['n'])}",
            "fragility_status": "broken",
            "article_message": "2022年ストレス期では小標本かつマイナス。",
            "practical_response": "期間分割で主張を弱める、または限定する。",
        },
        {
            "article_section": "11 Cost",
            "breakable_assumption": "コスト後も残る",
            "assumption_being_doubted": "グロスの優位はコストに耐える",
            "stress_case": "48h cost_x5",
            "metric": "mean_ret_pct / PF",
            "baseline_value": f"{fnum(low48['mean_ret_pct'], 3, '%')} / PF {fnum(low48['profit_factor'], 3)}",
            "stressed_value": f"{fnum(cost5['mean_ret_pct'], 3, '%')} / PF {fnum(cost5['profit_factor'], 3)}",
            "change": fnum(float(cost5["mean_ret_pct"]) - float(low48["mean_ret_pct"]), 3, "pp"),
            "fragility_status": "fragile",
            "article_message": "消えはしないが、急落時コストでエッジは圧縮される。",
            "practical_response": "コスト上限を設定し、ネットで報告する。",
        },
        {
            "article_section": "11 Execution",
            "breakable_assumption": "想定通り約定できる",
            "assumption_being_doubted": "次の4H始値で約定できる",
            "stress_case": "48h delay_4h",
            "metric": "mean_ret_pct / PF",
            "baseline_value": f"{fnum(low48['mean_ret_pct'], 3, '%')} / PF {fnum(low48['profit_factor'], 3)}",
            "stressed_value": f"{fnum(delay4['mean_ret_pct'], 3, '%')} / PF {fnum(delay4['profit_factor'], 3)}",
            "change": fnum(float(delay4["mean_ret_pct"]) - float(low48["mean_ret_pct"]), 3, "pp"),
            "fragility_status": "fragile",
            "article_message": "反発初動を取り逃すと候補リターンは縮む。",
            "practical_response": "約定遅延耐性を確認し、指値/成行ルールを再設計する。",
        },
        {
            "article_section": "11 Leverage",
            "breakable_assumption": "含み損に耐えられる",
            "assumption_being_doubted": "経路リスクは許容範囲",
            "stress_case": "48h 3x leverage",
            "metric": "worst_mae_pct",
            "baseline_value": fnum(low48["worst_mae_pct"], 3, "%"),
            "stressed_value": fnum(lev3["worst_mae_pct"], 3, "%"),
            "change": "3x path loss",
            "fragility_status": "watch",
            "article_message": "平均リターンは経路損失とセットで読む。",
            "practical_response": "MAE/DDからレバレッジ上限と強制縮小ルールを設計する。",
        },
        {
            "article_section": "12 Risk Proxy",
            "breakable_assumption": "proxyは1つで十分",
            "assumption_being_doubted": "Nasdaqだけで文脈は足りる",
            "stress_case": "48h S&P500 5D up",
            "metric": "mean_ret_pct / PF",
            "baseline_value": f"{fnum(low48['mean_ret_pct'], 3, '%')} / PF {fnum(low48['profit_factor'], 3)}",
            "stressed_value": f"{fnum(sp500['mean_ret_pct'], 3, '%')} / PF {fnum(sp500['profit_factor'], 3)}",
            "change": fnum(float(sp500["mean_ret_pct"]) - float(low48["mean_ret_pct"]), 3, "pp"),
            "fragility_status": "fragile",
            "article_message": "外部市場は直接予測因子ではなく文脈proxy。",
            "practical_response": "risk-on proxyを複数化し、因果表現を避ける。",
        },
    ]
    return pd.DataFrame(rows)


def build_key_metrics(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = tables["btc_crash_baseline"]
    boot = tables["btc_bootstrap_uncertainty"]
    definition = tables["btc_definition_robustness"]
    period = tables["btc_subperiod_results"]

    low24 = one(base[(base["horizon"].eq("24h")) & (base["group"].eq("funding_low_x_risk_on"))])
    low48 = one(base[(base["horizon"].eq("48h")) & (base["group"].eq("funding_low_x_risk_on"))])
    high48 = one(base[(base["horizon"].eq("48h")) & (base["group"].eq("funding_high_x_risk_off"))])
    all48 = one(base[(base["horizon"].eq("48h")) & (base["group"].eq("all_funding_covered_crashes"))])
    boot24 = one(boot[(boot["horizon"].eq("24h")) & (boot["group"].eq("funding_low_x_risk_on"))])
    boot48 = one(boot[(boot["horizon"].eq("48h")) & (boot["group"].eq("funding_low_x_risk_on"))])
    q025 = one(
        definition[
            (definition["horizon"].eq("48h"))
            & (definition["event_def"].eq("full_sample_q025"))
            & (definition["group"].eq("funding_low_x_risk_on"))
        ]
    )
    stress2022 = one(
        period[
            (period["horizon"].eq("48h"))
            & (period["period"].eq("2022_stress"))
            & (period["group"].eq("funding_low_x_risk_on"))
        ]
    )

    rows = [
        {
            "topic": "48h Funding low x risk-on baseline",
            "value": f"n={int(low48['n'])}, mean {fnum(low48['mean_ret_pct'], 3, '%')}, PF {fnum(low48['profit_factor'], 3)}",
            "article_role": "面白い候補だが結論ではない基準線",
        },
        {
            "topic": "24h Funding low x risk-on baseline",
            "value": f"n={int(low24['n'])}, mean {fnum(low24['mean_ret_pct'], 3, '%')}, PF {fnum(low24['profit_factor'], 3)}",
            "article_role": "24hでも小標本制約は同じ",
        },
        {
            "topic": "48h bootstrap lower bound",
            "value": f"mean 5% {fnum(boot48['mean_p05_pct'], 3, '%')}",
            "article_role": "error on errorの中心証拠",
        },
        {
            "topic": "24h bootstrap lower bound",
            "value": f"mean 5% {fnum(boot24['mean_p05_pct'], 3, '%')}",
            "article_role": "24hでも下限は0を下回る",
        },
        {
            "topic": "Crash definition stress",
            "value": f"full_sample_q025 mean {fnum(q025['mean_ret_pct'], 3, '%')}, PF {fnum(q025['profit_factor'], 3)}",
            "article_role": "急落定義を動かすと候補が壊れる",
        },
        {
            "topic": "2022 stress period",
            "value": f"n={int(stress2022['n'])}, mean {fnum(stress2022['mean_ret_pct'], 3, '%')}, PF {fnum(stress2022['profit_factor'], 3)}",
            "article_role": "レジーム依存を示す",
        },
        {
            "topic": "48h Funding high x risk-off",
            "value": f"mean {fnum(high48['mean_ret_pct'], 3, '%')}, PF {fnum(high48['profit_factor'], 3)}",
            "article_role": "避ける急落候補",
        },
        {
            "topic": "48h all crashes",
            "value": f"MaxDD {fnum(all48['maxdd_pct'], 3, '%')}",
            "article_role": "一律の急落買いは左尾・DDが重い",
        },
    ]
    return pd.DataFrame(rows)


def save_fragility_status_figure(matrix: pd.DataFrame) -> None:
    order = ["broken", "fragile", "watch"]
    counts = matrix["fragility_status"].value_counts().reindex(order, fill_value=0)
    colors = ["#B84A3A", "#D99A2B", "#5B82A6"]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(counts.index, counts.values, color=colors, alpha=0.9)
    ax.set_title("BTC Fragility Matrix status counts")
    ax.set_ylabel("Number of article findings")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "fragility_matrix_status.png", dpi=180)
    plt.close(fig)


def make_fragility_report(matrix: pd.DataFrame) -> str:
    cols = [
        "breakable_assumption",
        "stress_case",
        "metric",
        "baseline_value",
        "stressed_value",
        "fragility_status",
        "practical_response",
    ]
    counts = matrix["fragility_status"].value_counts().rename_axis("status").reset_index(name="count")
    return f"""# BTC Fragility Matrix

Source article: {ARTICLE_URL}

## Purpose

This matrix is the experiment-side support for article sections 10-12. It does not prove a BTC edge. It converts the attractive-looking `Funding low x risk-on` candidate into break conditions and practical responses.

## Status Counts

{markdown_table(counts, ["status", "count"], digits=0)}

## Matrix

{markdown_table(matrix, cols, digits=3)}

## Article Interpretation

- `Funding low x risk-on` is an interesting baseline, not a tradable conclusion.
- The article-supported evidence is strongest where the candidate breaks or becomes fragile: `n=15`, bootstrap lower bound below zero, crash-definition reversal, 2022 stress-period weakness, cost compression, execution delay, and levered MAE.
- External-market variables are risk-environment proxies. They must not be described as direct BTC predictors.
"""


def make_experiment_report(tables: dict[str, pd.DataFrame], matrix: pd.DataFrame, key_metrics: pd.DataFrame) -> str:
    base = tables["btc_crash_baseline"]
    boot = tables["btc_bootstrap_uncertainty"]
    definition = tables["btc_definition_robustness"]
    period = tables["btc_subperiod_results"]
    cost = tables["btc_cost_stress"]
    entry = tables["btc_entry_execution_stress"]
    leverage = tables["btc_leverage_tolerance"]

    base_focus = base[
        base["group"].isin(
            ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
        )
    ][
        [
            "horizon",
            "group",
            "n",
            "mean_ret_pct",
            "profit_factor",
            "mean_mae_pct",
            "worst_mae_pct",
            "maxdd_pct",
            "fragility_status",
        ]
    ]
    boot_focus = boot[boot["group"].eq("funding_low_x_risk_on")][
        ["horizon", "n", "mean_p05_pct", "mean_p50_pct", "mean_p95_pct", "pf_p05", "pf_p50", "pf_p95"]
    ]
    definition_focus = definition[
        (definition["group"].eq("funding_low_x_risk_on")) & (definition["horizon"].eq("48h"))
    ][["event_def", "n", "mean_ret_pct", "profit_factor", "maxdd_pct", "fragility_status"]]
    period_focus = period[
        (period["group"].eq("funding_low_x_risk_on")) & (period["horizon"].eq("48h"))
    ][["period", "n", "mean_ret_pct", "profit_factor", "maxdd_pct", "fragility_status"]]
    cost_focus = cost[
        (cost["group"].eq("funding_low_x_risk_on"))
        & (cost["horizon"].eq("48h"))
        & (cost["cost_case"].isin(["gross", "base_cost", "cost_x2", "cost_x5"]))
    ][["cost_case", "cost_bps", "n", "mean_ret_pct", "profit_factor", "maxdd_pct", "fragility_status"]]
    entry_focus = entry[
        (entry["group"].eq("funding_low_x_risk_on"))
        & (entry["horizon"].eq("48h"))
        & (entry["entry_case"].isin(["next_open", "delay_4h", "delay_8h", "adverse_25bps"]))
    ][["entry_case", "entry_lag_bars", "adverse_entry_bps", "n", "mean_ret_pct", "profit_factor", "fragility_status"]]
    leverage_focus = leverage[
        (leverage["group"].eq("funding_low_x_risk_on"))
        & (leverage["horizon"].eq("48h"))
        & (leverage["leverage"].isin([1.0, 2.0, 3.0]))
    ][["leverage", "n", "mean_ret_pct", "worst_mae_pct", "maxdd_pct", "margin_breach_30pct_count"]]

    return f"""# lab_10 BTC Article-Support Experiment Report

Source article: {ARTICLE_URL}

## Executive Summary

This lab now supports the published BTC-only article. The experiment does not try to re-prove `Funding low x risk-on` as an edge. It treats that candidate as a baseline estimate and asks where the estimate breaks.

The core article claim is supported: `Funding low x risk-on` looks interesting at the point-estimate level, but the claim is fragile under small-sample uncertainty, crash-definition changes, 2022 stress-period slicing, cost, execution delay, and leverage path risk.

## Key Metrics For The Article

{markdown_table(key_metrics, ["topic", "value", "article_role"], digits=3)}

## Baseline: Measure First

{markdown_table(base_focus, list(base_focus.columns), digits=3)}

## Error On Error: Bootstrap Uncertainty

{markdown_table(boot_focus, list(boot_focus.columns), digits=3)}

Article reading:

- The 48h point estimate is positive, but the 5% bootstrap lower bound is negative.
- This does not prove the edge is absent. It means the positive expectation cannot be stated strongly with `n=15`.

## Definition Stress

{markdown_table(definition_focus, list(definition_focus.columns), digits=3)}

Article reading:

- The `full_sample_q025` stress changes the 48h mean from positive to negative.
- This is the clearest definition-dependence result and should remain near the center of the article.

## Regime, Cost, Execution, And Leverage

Subperiod:

{markdown_table(period_focus, list(period_focus.columns), digits=3)}

Cost:

{markdown_table(cost_focus, list(cost_focus.columns), digits=3)}

Execution:

{markdown_table(entry_focus, list(entry_focus.columns), digits=3)}

Leverage:

{markdown_table(leverage_focus, list(leverage_focus.columns), digits=3)}

## Fragility Matrix

{markdown_table(matrix, ["breakable_assumption", "stress_case", "baseline_value", "stressed_value", "fragility_status", "practical_response"], digits=3)}

## Article-Safe Conclusion

BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、`n=15`、bootstrap下限、crash定義、期間分割、コスト、約定、レバレッジを動かすと、強い主張はできない。ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。
"""


def make_alignment_report(matrix: pd.DataFrame, key_metrics: pd.DataFrame) -> str:
    rows = pd.DataFrame(
        [
            {
                "article_section": "8 まず見るべきは平均ではなくn",
                "experiment_support": "48h Funding low x risk-on is n=15.",
                "status": "support",
            },
            {
                "article_section": "9 error on error",
                "experiment_support": "48h bootstrap mean 5% lower bound is -0.380%; 24h is -0.057%.",
                "status": "support",
            },
            {
                "article_section": "10 crash定義を動かす",
                "experiment_support": "48h full_sample_q025 changes mean to -1.082% and PF to 0.666.",
                "status": "support",
            },
            {
                "article_section": "11 期間・コスト・約定・レバレッジ",
                "experiment_support": "2022 stress is negative; cost_x5 and delay_4h compress the estimate; 3x MAE reaches -28.277%.",
                "status": "support",
            },
            {
                "article_section": "12 Fragility Matrix",
                "experiment_support": f"{len(matrix)} rows map breakable assumptions to practical responses.",
                "status": "support",
            },
            {
                "article_section": "14 避けるべき誤解",
                "experiment_support": "Baseline and stress results support weaker wording: candidate, not proven strategy.",
                "status": "support",
            },
        ]
    )
    return f"""# Article Alignment Report

Source article: {ARTICLE_URL}

## Purpose

This report checks whether the lab_10 outputs support the published article. The answer is yes: the outputs now focus on the BTC `Funding low x risk-on` candidate and the assumptions that make it fragile.

## Alignment Table

{markdown_table(rows, ["article_section", "experiment_support", "status"], digits=3)}

## Key Metrics

{markdown_table(key_metrics, ["topic", "value", "article_role"], digits=3)}

## Remaining Guardrails

- Do not call `Funding low x risk-on` a proven edge.
- Do not describe Nasdaq or S&P500 as direct BTC predictors.
- Keep `n=15` and bootstrap lower bounds near the first mention of the candidate.
- Treat the Fragility Matrix as a conversion table from weak assumptions to operating rules, not as proof of profitability.
"""


def make_figure_selection_report() -> str:
    rows = pd.DataFrame(
        [
            {
                "priority": 1,
                "figure": "btc_bootstrap_mean_return.png",
                "article_section": "9 error on error",
                "role": "Show small-sample uncertainty and negative bootstrap lower bounds.",
                "include": "body",
            },
            {
                "priority": 2,
                "figure": "btc_definition_robustness_heatmap.png",
                "article_section": "10 crash definition",
                "role": "Show sign reversal under full_sample_q025.",
                "include": "body",
            },
            {
                "priority": 3,
                "figure": "btc_cost_stress_heatmap.png",
                "article_section": "11 cost",
                "role": "Show gross-to-net compression under cost stress.",
                "include": "body",
            },
            {
                "priority": 4,
                "figure": "btc_entry_execution_stress.png",
                "article_section": "11 execution",
                "role": "Show delay sensitivity.",
                "include": "appendix",
            },
            {
                "priority": 5,
                "figure": "btc_leverage_tolerance.png",
                "article_section": "11 leverage",
                "role": "Show path-risk and levered MAE.",
                "include": "appendix",
            },
            {
                "priority": 6,
                "figure": "btc_risk_env_robustness.png",
                "article_section": "12 risk proxy",
                "role": "Show proxy sensitivity without causal wording.",
                "include": "appendix",
            },
            {
                "priority": 7,
                "figure": "fragility_matrix_status.png",
                "article_section": "12 Fragility Matrix",
                "role": "Summarize broken/fragile/watch counts.",
                "include": "appendix",
            },
        ]
    )
    return f"""# Article Figure Selection

Source article: {ARTICLE_URL}

## Recommended Figures

{markdown_table(rows, ["priority", "figure", "article_section", "role", "include"], digits=0)}

## Minimal Set For AI Review

Use only these files when asking another model to analyze the article:

1. `article_materials_btc_minimal_ai/01_ANALYZE_THIS.ja.md`
2. `article_materials_btc_minimal_ai/02_fragility_matrix.csv`
3. `article_materials_btc_minimal_ai/03_bootstrap_uncertainty.png`
4. `article_materials_btc_minimal_ai/04_crash_definition_robustness.png`
5. `article_materials_btc_minimal_ai/05_cost_stress.png`
"""


def main() -> None:
    ensure_dirs()
    tables = load_tables()
    matrix = build_article_fragility_matrix(tables)
    key_metrics = build_key_metrics(tables)

    matrix.to_csv(TABLE_DIR / "fragility_matrix.csv", index=False)
    key_metrics.to_csv(TABLE_DIR / "article_key_metrics.csv", index=False)
    save_fragility_status_figure(matrix)

    (REPORT_DIR / "fragility_matrix.md").write_text(make_fragility_report(matrix), encoding="utf-8")
    (REPORT_DIR / "lab_10_experiment_report.md").write_text(
        make_experiment_report(tables, matrix, key_metrics),
        encoding="utf-8",
    )
    (REPORT_DIR / "article_outline_alignment.md").write_text(
        make_alignment_report(matrix, key_metrics),
        encoding="utf-8",
    )
    (REPORT_DIR / "article_figure_selection.md").write_text(
        make_figure_selection_report(),
        encoding="utf-8",
    )

    print(f"Wrote {TABLE_DIR / 'fragility_matrix.csv'}")
    print(f"Wrote {TABLE_DIR / 'article_key_metrics.csv'}")
    print(f"Wrote {REPORT_DIR / 'fragility_matrix.md'}")
    print(f"Wrote {REPORT_DIR / 'lab_10_experiment_report.md'}")
    print(f"Wrote {REPORT_DIR / 'article_outline_alignment.md'}")
    print(f"Wrote {REPORT_DIR / 'article_figure_selection.md'}")
    print(f"Wrote {FIGURE_DIR / 'fragility_matrix_status.png'}")


if __name__ == "__main__":
    main()
