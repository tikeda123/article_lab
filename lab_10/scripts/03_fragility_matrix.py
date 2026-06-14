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


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLE_DIR / name)


def scalar(df: pd.DataFrame, col: str) -> object:
    if df.empty:
        return np.nan
    return df.iloc[0][col]


def fnum(value: object, digits: int = 3, suffix: str = "") -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(value):
        return "-"
    return f"{value:.{digits}f}{suffix}"


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


def build_fragility_matrix(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    # Internal full matrix. Article-facing outputs filter this to BTC rows in main().
    usd = tables["usdjpy_risk_summary"]
    usd_stress = tables["usdjpy_stress_dials"]
    usd_dd = tables["usdjpy_dd_capital_table"]
    usd_lev = tables["usdjpy_leverage_limits"]
    btc_base = tables["btc_crash_baseline"]
    btc_cost = tables["btc_cost_stress"]
    btc_entry = tables["btc_entry_execution_stress"]
    btc_definition = tables["btc_definition_robustness"]
    btc_risk = tables["btc_risk_env_robustness"]
    btc_funding = tables["btc_funding_definition_robustness"]
    btc_period = tables["btc_subperiod_results"]
    btc_boot = tables["btc_bootstrap_uncertainty"]
    btc_leverage = tables["btc_leverage_tolerance"]

    rows: list[dict[str, object]] = []

    full = usd[usd["window_name"].eq("full")]
    one_year = usd[usd["window_name"].eq("1y")]
    five_year = usd[usd["window_name"].eq("5y")]
    full_vol = usd_stress[(usd_stress["window_name"].eq("full")) & (usd_stress["stress_case"].eq("vol_x1.5"))]
    full_cost = usd_stress[(usd_stress["window_name"].eq("full")) & (usd_stress["stress_case"].eq("cost_x5"))]
    full_dd2 = usd_dd[(usd_dd["window_name"].eq("full")) & (usd_dd["dd_multiplier"].eq(2.0))]
    full_lev = usd_lev[
        (usd_lev["window_name"].eq("full"))
        & (usd_lev["dd_multiplier"].eq(2.0))
        & (usd_lev["max_allowed_dd_pct"].eq(30.0))
    ]

    rows.extend(
        [
            {
                "target": "USDJPY risk estimate",
                "fragility_source": "risk_method",
                "assumption_being_doubted": "A single VaR method is enough.",
                "stress_case": "Full window: normal VaR 99% vs historical ES 99%",
                "metric": "4H left-tail estimate",
                "baseline_value": fnum(scalar(full, "normal_var_99_pct"), 3, "%"),
                "stressed_value": fnum(scalar(full, "hist_es_99_pct"), 3, "%"),
                "change": fnum(float(scalar(full, "hist_es_99_pct")) - float(scalar(full, "normal_var_99_pct")), 3, "pp"),
                "break_condition": "Different methods produce materially different left-tail estimates.",
                "fragility_status": "fragile",
                "article_message": "Risk estimates are model outputs, not facts.",
                "practical_response": "Show VaR/ES by multiple methods; do not publish one number as the answer.",
            },
            {
                "target": "USDJPY risk estimate",
                "fragility_source": "window_length",
                "assumption_being_doubted": "A recent window represents the future risk surface.",
                "stress_case": "1y maxDD vs full-sample maxDD",
                "metric": "maxdd_pct",
                "baseline_value": fnum(scalar(one_year, "maxdd_pct"), 3, "%"),
                "stressed_value": fnum(scalar(full, "maxdd_pct"), 3, "%"),
                "change": fnum(float(scalar(full, "maxdd_pct")) - float(scalar(one_year, "maxdd_pct")), 3, "pp"),
                "break_condition": "Longer history exposes much larger realized drawdown.",
                "fragility_status": "fragile",
                "article_message": "Past data is a baseline, and window choice is a subjective dial.",
                "practical_response": "Monitor multiple windows; avoid sizing from the calmest recent window alone.",
            },
            {
                "target": "USDJPY risk estimate",
                "fragility_source": "vol_multiplier",
                "assumption_being_doubted": "Observed volatility continues unchanged.",
                "stress_case": "Full window volatility x1.5",
                "metric": "maxdd_pct",
                "baseline_value": fnum(scalar(full, "maxdd_pct"), 3, "%"),
                "stressed_value": fnum(scalar(full_vol, "maxdd_pct"), 3, "%"),
                "change": fnum(float(scalar(full_vol, "maxdd_pct")) - float(scalar(full, "maxdd_pct")), 3, "pp"),
                "break_condition": "Volatility stress pushes drawdown materially beyond history.",
                "fragility_status": "watch",
                "article_message": "Doubt dials convert subjective caution into measurable stress levels.",
                "practical_response": "Apply volatility-linked position reduction before crisis conditions.",
            },
            {
                "target": "USDJPY risk estimate",
                "fragility_source": "dd_multiplier",
                "assumption_being_doubted": "Historical max DD is a future upper bound.",
                "stress_case": "Full maxDD x2",
                "metric": "required capital for 1x",
                "baseline_value": fnum(abs(float(scalar(full, "maxdd_pct"))), 3, "%"),
                "stressed_value": fnum(scalar(full_dd2, "required_capital_pct_for_1x"), 3, "%"),
                "change": "x2.0",
                "break_condition": "A 2x DD dial changes capital and leverage decisions.",
                "fragility_status": "fragile",
                "article_message": "Historical max DD must not be treated as a hard loss cap.",
                "practical_response": "Translate DD multiples into capital reserves and stop rules.",
            },
            {
                "target": "USDJPY risk estimate",
                "fragility_source": "leverage_limit",
                "assumption_being_doubted": "Leverage remains acceptable under stressed DD.",
                "stress_case": "Full maxDD x2, 30% allowed DD",
                "metric": "leverage_limit",
                "baseline_value": "1.000",
                "stressed_value": fnum(scalar(full_lev, "leverage_limit"), 3),
                "change": "below 1x",
                "break_condition": "A 30% DD budget cannot support 1x if full-period maxDD doubles.",
                "fragility_status": "broken",
                "article_message": "Risk analysis must end in position sizing, not a chart.",
                "practical_response": "Set leverage caps from stressed drawdown, not from average volatility.",
            },
            {
                "target": "USDJPY risk estimate",
                "fragility_source": "cost_multiplier",
                "assumption_being_doubted": "Small repeated costs are harmless.",
                "stress_case": "Full window cost x5 dial",
                "metric": "maxdd_pct",
                "baseline_value": fnum(scalar(full, "maxdd_pct"), 3, "%"),
                "stressed_value": fnum(scalar(full_cost, "maxdd_pct"), 3, "%"),
                "change": "turnover stress",
                "break_condition": "Repeated costs dominate if every 4H bar is treated as a turnover event.",
                "fragility_status": "broken",
                "article_message": "A stress dial is not a forecast; it exposes cost sensitivity.",
                "practical_response": "State turnover assumptions explicitly before using cost-stressed results.",
            },
        ]
    )

    low48 = btc_base[
        (btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("funding_low_x_risk_on"))
    ]
    high48 = btc_base[
        (btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("funding_high_x_risk_off"))
    ]
    all48 = btc_base[
        (btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("all_funding_covered_crashes"))
    ]
    low48_boot = btc_boot[
        (btc_boot["horizon"].eq("48h")) & (btc_boot["group"].eq("funding_low_x_risk_on"))
    ]
    low48_cost5 = btc_cost[
        (btc_cost["horizon"].eq("48h"))
        & (btc_cost["cost_case"].eq("cost_x5"))
        & (btc_cost["group"].eq("funding_low_x_risk_on"))
    ]
    low48_delay = btc_entry[
        (btc_entry["horizon"].eq("48h"))
        & (btc_entry["entry_case"].eq("delay_4h"))
        & (btc_entry["group"].eq("funding_low_x_risk_on"))
    ]
    low48_q025 = btc_definition[
        (btc_definition["horizon"].eq("48h"))
        & (btc_definition["event_def"].eq("full_sample_q025"))
        & (btc_definition["group"].eq("funding_low_x_risk_on"))
    ]
    low48_sp500 = btc_risk[
        (btc_risk["horizon"].eq("48h"))
        & (btc_risk["risk_env"].eq("sp500_5d_up"))
        & (btc_risk["group"].eq("funding_low_x_risk_on"))
    ]
    low48_negative = btc_funding[
        (btc_funding["horizon"].eq("48h"))
        & (btc_funding["funding_case"].eq("negative"))
        & (btc_funding["group"].eq("funding_low_x_risk_on"))
    ]
    low48_2022 = btc_period[
        (btc_period["horizon"].eq("48h"))
        & (btc_period["period"].eq("2022_stress"))
        & (btc_period["group"].eq("funding_low_x_risk_on"))
    ]
    low48_lev3 = btc_leverage[
        (btc_leverage["horizon"].eq("48h"))
        & (btc_leverage["leverage"].eq(3.0))
        & (btc_leverage["group"].eq("funding_low_x_risk_on"))
    ]

    rows.extend(
        [
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "sample_size",
                "assumption_being_doubted": "The conditional mean is stable.",
                "stress_case": "Bootstrap, 48h Funding low x risk-on",
                "metric": "bootstrap mean return 5% lower bound",
                "baseline_value": fnum(scalar(low48, "mean_ret_pct"), 3, "%"),
                "stressed_value": fnum(scalar(low48_boot, "mean_p05_pct"), 3, "%"),
                "change": f"n={int(scalar(low48, 'n'))}",
                "break_condition": "Bootstrap lower bound falls below zero.",
                "fragility_status": "fragile",
                "article_message": "The subgroup is interesting, but n is too small for a strong claim.",
                "practical_response": "Lead with sample size and uncertainty before mentioning PF.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "cost",
                "assumption_being_doubted": "Gross edge survives realistic and stressed costs.",
                "stress_case": "48h cost x5",
                "metric": "mean_ret_pct / PF",
                "baseline_value": f"{fnum(scalar(low48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48, 'profit_factor'), 3)}",
                "stressed_value": f"{fnum(scalar(low48_cost5, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48_cost5, 'profit_factor'), 3)}",
                "change": fnum(float(scalar(low48_cost5, "mean_ret_pct")) - float(scalar(low48, "mean_ret_pct")), 3, "pp"),
                "break_condition": "Cost stress materially compresses the edge.",
                "fragility_status": "fragile",
                "article_message": "Gross backtests are not enough.",
                "practical_response": "Set cost ceilings and report net results.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "execution",
                "assumption_being_doubted": "The next 4H open is achievable.",
                "stress_case": "48h entry delayed by 4H",
                "metric": "mean_ret_pct / PF",
                "baseline_value": f"{fnum(scalar(low48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48, 'profit_factor'), 3)}",
                "stressed_value": f"{fnum(scalar(low48_delay, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48_delay, 'profit_factor'), 3)}",
                "change": fnum(float(scalar(low48_delay, "mean_ret_pct")) - float(scalar(low48, "mean_ret_pct")), 3, "pp"),
                "break_condition": "Delayed entry reduces the candidate return.",
                "fragility_status": "fragile",
                "article_message": "Execution assumptions are part of the risk model.",
                "practical_response": "Require entry-delay tolerance before treating the signal as usable.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "crash_definition",
                "assumption_being_doubted": "The result is independent of crash definition.",
                "stress_case": "48h full-sample lower 2.5%",
                "metric": "mean_ret_pct / PF",
                "baseline_value": f"{fnum(scalar(low48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48, 'profit_factor'), 3)}",
                "stressed_value": f"{fnum(scalar(low48_q025, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48_q025, 'profit_factor'), 3)}",
                "change": fnum(float(scalar(low48_q025, "mean_ret_pct")) - float(scalar(low48, "mean_ret_pct")), 3, "pp"),
                "break_condition": "A stricter tail definition turns the 48h mean negative.",
                "fragility_status": "broken",
                "article_message": "Edge estimates depend on definitions.",
                "practical_response": "Publish definition robustness before naming a condition buyable.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "risk_env_definition",
                "assumption_being_doubted": "Nasdaq risk-on is the only needed context proxy.",
                "stress_case": "48h S&P500 5D up",
                "metric": "mean_ret_pct / PF",
                "baseline_value": f"{fnum(scalar(low48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48, 'profit_factor'), 3)}",
                "stressed_value": f"{fnum(scalar(low48_sp500, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48_sp500, 'profit_factor'), 3)}",
                "change": fnum(float(scalar(low48_sp500, "mean_ret_pct")) - float(scalar(low48, "mean_ret_pct")), 3, "pp"),
                "break_condition": "Changing the risk-on proxy changes the estimate.",
                "fragility_status": "fragile",
                "article_message": "External markets are context filters, not direct BTC predictors.",
                "practical_response": "Use multiple risk-on proxies and avoid causal wording.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "funding_definition",
                "assumption_being_doubted": "The Funding-low threshold is objective.",
                "stress_case": "48h Funding negative only",
                "metric": "n / mean_ret_pct",
                "baseline_value": f"n={int(scalar(low48, 'n'))}, mean {fnum(scalar(low48, 'mean_ret_pct'), 3, '%')}",
                "stressed_value": f"n={int(scalar(low48_negative, 'n'))}, mean {fnum(scalar(low48_negative, 'mean_ret_pct'), 3, '%')}",
                "change": "threshold dial",
                "break_condition": "Threshold changes alter sample size and estimate.",
                "fragility_status": "fragile",
                "article_message": "Subjective thresholds must be explicit.",
                "practical_response": "Report Funding definitions side by side.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "subperiod",
                "assumption_being_doubted": "The candidate works across regimes.",
                "stress_case": "48h 2022 stress period",
                "metric": "mean_ret_pct / PF",
                "baseline_value": f"{fnum(scalar(low48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48, 'profit_factor'), 3)}",
                "stressed_value": f"{fnum(scalar(low48_2022, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(low48_2022, 'profit_factor'), 3)}",
                "change": f"n={int(scalar(low48_2022, 'n'))}",
                "break_condition": "The stress-period slice is weak and tiny.",
                "fragility_status": "broken",
                "article_message": "Regime dependence is central to edge uncertainty.",
                "practical_response": "Use period splits to weaken or qualify public claims.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "mae_dd_leverage",
                "assumption_being_doubted": "The path risk is tolerable under leverage.",
                "stress_case": "48h 3x leverage",
                "metric": "worst_mae_pct",
                "baseline_value": fnum(scalar(low48, "worst_mae_pct"), 3, "%"),
                "stressed_value": fnum(scalar(low48_lev3, "worst_mae_pct"), 3, "%"),
                "change": "x3 path loss",
                "break_condition": "Levered MAE approaches levels that can force risk reduction.",
                "fragility_status": "watch",
                "article_message": "Mean return must be read with path loss and leverage tolerance.",
                "practical_response": "Define leverage caps and forced-reduction rules from MAE/DD.",
            },
            {
                "target": "BTC crash edge candidate",
                "fragility_source": "avoid_condition",
                "assumption_being_doubted": "All BTC crashes are equivalent.",
                "stress_case": "48h Funding high x risk-off",
                "metric": "mean_ret_pct / PF",
                "baseline_value": f"All crashes {fnum(scalar(all48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(all48, 'profit_factor'), 3)}",
                "stressed_value": f"High funding x risk-off {fnum(scalar(high48, 'mean_ret_pct'), 3, '%')} / PF {fnum(scalar(high48, 'profit_factor'), 3)}",
                "change": fnum(float(scalar(high48, "mean_ret_pct")) - float(scalar(all48, "mean_ret_pct")), 3, "pp"),
                "break_condition": "A risky subgroup stays weaker than the broad baseline.",
                "fragility_status": "broken",
                "article_message": "The useful claim is classification, not universal dip buying.",
                "practical_response": "Use high-funding/risk-off as an avoid or size-reduction condition.",
            },
        ]
    )
    return pd.DataFrame(rows)


def save_fragility_status_figure(matrix: pd.DataFrame) -> None:
    counts = matrix.groupby(["target", "fragility_status"]).size().unstack(fill_value=0)
    statuses = ["broken", "fragile", "watch", "survives_this_test"]
    for status in statuses:
        if status not in counts.columns:
            counts[status] = 0
    counts = counts[statuses]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bottom = np.zeros(len(counts))
    colors = {
        "broken": "#B84A3A",
        "fragile": "#D99A2B",
        "watch": "#5B82A6",
        "survives_this_test": "#5B9A70",
    }
    x = np.arange(len(counts))
    for status in statuses:
        values = counts[status].to_numpy(dtype=float)
        ax.bar(x, values, bottom=bottom, label=status, color=colors[status], alpha=0.9)
        bottom += values
    ax.set_title("Fragility Matrix status counts")
    ax.set_ylabel("Number of findings")
    ax.set_xticks(x)
    ax.set_xticklabels(counts.index, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "fragility_matrix_status.png", dpi=180)
    plt.close(fig)


# Legacy combined USDJPY+BTC report builders are retained for internal comparison only.
# main() writes the BTC-only article-facing reports defined below.
def make_fragility_report(matrix: pd.DataFrame) -> str:
    cols = [
        "target",
        "fragility_source",
        "stress_case",
        "metric",
        "baseline_value",
        "stressed_value",
        "fragility_status",
        "practical_response",
    ]
    status_counts = matrix.groupby(["target", "fragility_status"]).size().reset_index(name="count")
    return f"""# Fragility Matrix

## Purpose

This matrix converts Phase 1 and Phase 2 outputs into the article's practical question: which assumptions break first, and what should an operator do with that information?

## Status Counts

{markdown_table(status_counts, ["target", "fragility_status", "count"], digits=0)}

## Matrix

{markdown_table(matrix, cols, digits=3)}

## Interpretation

- USDJPY supports the article's risk-estimation point: VaR, ES, max DD, and leverage limits move when the method or stress dial changes.
- BTC supports the edge-fragility point: `Funding low x risk-on` is interesting, but sample size, crash definition, period, execution, and bootstrap uncertainty keep the claim fragile.
- `Funding high x risk-off` is useful as a contrast: not all BTC crashes should be treated as the same event.
- `survives_this_test`, if it appears in later runs, should mean only that the tested assumption did not break in this run. It must not be read as live-trading readiness.
"""


def make_experiment_report(tables: dict[str, pd.DataFrame], matrix: pd.DataFrame) -> str:
    usd = tables["usdjpy_risk_summary"]
    btc_base = tables["btc_crash_baseline"]
    btc_boot = tables["btc_bootstrap_uncertainty"]
    usd_cols = [
        "window_name",
        "n",
        "hist_var_99_pct",
        "hist_es_99_pct",
        "normal_var_99_pct",
        "student_t_var_99_pct",
        "maxdd_pct",
    ]
    btc_focus = btc_base[
        btc_base["group"].isin(
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
    boot_focus = btc_boot[btc_boot["group"].eq("funding_low_x_risk_on")][
        ["horizon", "n", "mean_p05_pct", "mean_p50_pct", "mean_p95_pct", "pf_p05", "pf_p50", "pf_p95", "is_ci_fragile"]
    ]
    matrix_focus = matrix[
        ["target", "fragility_source", "stress_case", "fragility_status", "article_message", "practical_response"]
    ]

    return f"""# lab_10 Experiment Report

## Executive Summary

Phase 0-5 completed the planned empirical package for the fat-tail article.

The result supports the article's core claim: fat-tail-aware practice is not about finding one correct future distribution. It is about treating risk estimates and edge estimates as fragile outputs, testing where they break, and translating the result into operating rules.

Key conclusions:

- USDJPY risk estimates move with method and window. The full-window normal 99% VaR is much less severe than full-window historical 99% ES, and max DD depends strongly on lookback and stress dials.
- BTC `Funding low x risk-on` remains an interesting crash-rebound candidate, but the primary 24h/48h subgroup has only `n=15`.
- Bootstrap uncertainty is enough to make the BTC candidate fragile: the 5% lower bound of the mean is below zero for both 24h and 48h.
- The right article claim is classification and fragility testing, not "BTC crashes are buys."

## 1. Purpose And Non-Purpose

Purpose:

- Show that risk estimates are assumption-dependent.
- Show that edge candidates are assumption-dependent.
- Convert the weak points into a Fragility Matrix.
- Check whether the article outline is supported by the empirical evidence.

Non-purpose:

- Forecast USDJPY's future risk.
- Prove a BTC trading strategy.
- Treat `Funding low x risk-on` as investment advice.
- Treat any single VaR, ES, PF, or p-value as a final truth.

## 2. Reproducibility

Main commands used:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/01_usdjpy_risk_diagnostics.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

Phase 0 reproduced the copied `lab_7` baseline. The regenerated major CSVs matched the copied reference CSVs.

## 3. USDJPY: How Much Risk Estimates Move

{markdown_table(usd, usd_cols, digits=3)}

Interpretation:

- The 5-year window gives the harshest historical 99% ES in this run.
- The full sample gives the largest historical max DD.
- Normal VaR is consistently less severe than historical ES, which is useful for explaining model-risk in a trader-facing way.
- These values are not forecasts. They are baseline measurements that become useful only after applying explicit doubt dials.

## 4. BTC: Where The Edge Candidate Breaks

{markdown_table(btc_focus, list(btc_focus.columns), digits=3)}

Bootstrap for `Funding low x risk-on`:

{markdown_table(boot_focus, list(boot_focus.columns), digits=3)}

Interpretation:

- `Funding low x risk-on` has attractive point estimates, but `n=15` makes the estimate fragile.
- The 48h bootstrap mean 5% lower bound is negative, so the article must not present this as a proven edge.
- `Funding high x risk-off` is weak in the baseline and works better as an avoid-condition example.
- Buying all crashes has a much larger drawdown surface, which supports the classification framing.

## 5. Fragility Matrix

{markdown_table(matrix_focus, list(matrix_focus.columns), digits=3)}

## 6. Figure Candidates

Recommended figures for the article body:

1. `outputs/figures/usdjpy_rolling_var.png`
2. `outputs/figures/usdjpy_risk_method_comparison.png`
3. `outputs/figures/btc_cost_stress_heatmap.png`
4. `outputs/figures/btc_definition_robustness_heatmap.png`
5. `outputs/figures/btc_bootstrap_mean_return.png`

Use `outputs/figures/fragility_matrix_status.png` as a summary or appendix figure.

## 7. What The Article Can Say

Strong enough:

- Risk estimates are unstable across methods, windows, and stress assumptions.
- Historical max DD is not a future upper bound.
- `Funding low x risk-on` is an interesting BTC crash-rebound candidate.
- The candidate remains fragile because of small sample size and assumption sensitivity.
- The practical conclusion is to find break conditions and map them into operating rules.

Too strong:

- USDJPY future risk has been predicted.
- BTC crashes are buys.
- `Funding low x risk-on` is a proven strategy.
- Nasdaq directly predicts BTC.
- Using VaR, ES, or Student-t means fat tails have been handled.

## 8. Remaining Limits

- BTC subgroup sample sizes are small.
- Bootstrap is iid event-level and does not fully model time dependence.
- Cost and execution assumptions are stress dials, not measured live execution costs.
- USDJPY cost stress treats every 4H return as turnover, so it should be interpreted as sensitivity, not a realistic trading-cost model.
- Fragility Matrix is a decision aid; it is not a production risk system.
"""


def make_alignment_report(tables: dict[str, pd.DataFrame], matrix: pd.DataFrame) -> str:
    usd = tables["usdjpy_risk_summary"]
    btc_base = tables["btc_crash_baseline"]
    btc_boot = tables["btc_bootstrap_uncertainty"]
    usd_full = usd[usd["window_name"].eq("full")]
    btc_low48 = btc_base[(btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("funding_low_x_risk_on"))]
    btc_boot48 = btc_boot[(btc_boot["horizon"].eq("48h")) & (btc_boot["group"].eq("funding_low_x_risk_on"))]

    rows = pd.DataFrame(
        [
            {
                "article_claim": "バックテストは未来の保証ではない",
                "evidence": "USDJPY full maxDD is "
                + fnum(scalar(usd_full, "maxdd_pct"), 3, "%")
                + "; BTC all-crash 48h maxDD is much worse than the selected subgroup.",
                "judgment": "support",
                "article_handling": "Use these as examples that realized paths and selected samples cannot be treated as limits.",
                "revision_needed": "No major revision. Add one sentence that these are diagnostics, not forecasts.",
            },
            {
                "article_claim": "一般的なファットテール対応手法は有用だが十分ではない",
                "evidence": "USDJPY normal VaR, historical VaR/ES, Student-t VaR, and maxDD differ by method and window.",
                "judgment": "support",
                "article_handling": "Use the USDJPY risk-method comparison figure.",
                "revision_needed": "Avoid implying one method is the correct replacement.",
            },
            {
                "article_claim": "リスク推定そのものにも error on error がある",
                "evidence": "Full-window normal VaR 99% is "
                + fnum(scalar(usd_full, "normal_var_99_pct"), 3, "%")
                + " while historical ES 99% is "
                + fnum(scalar(usd_full, "hist_es_99_pct"), 3, "%")
                + ".",
                "judgment": "support",
                "article_handling": "Explain the gap as model and estimator uncertainty, not as a forecast error.",
                "revision_needed": "Keep Taleb framing as a practical warning, not a formal proof.",
            },
            {
                "article_claim": "主観を隠さず、疑いのダイヤルとして扱う",
                "evidence": "DD multipliers, cost multipliers, Funding thresholds, crash definitions, and risk-on proxies all change conclusions.",
                "judgment": "support",
                "article_handling": "Name these settings explicitly as subjective dials.",
                "revision_needed": "Add a table listing the chosen dials and why they are not true future probabilities.",
            },
            {
                "article_claim": "エッジ候補は平均リターンではなく壊れる条件で見る",
                "evidence": "`Funding low x risk-on` 48h mean is "
                + fnum(scalar(btc_low48, "mean_ret_pct"), 3, "%")
                + " with PF "
                + fnum(scalar(btc_low48, "profit_factor"), 3)
                + ", but n="
                + str(int(scalar(btc_low48, "n")))
                + " and bootstrap mean 5% is "
                + fnum(scalar(btc_boot48, "mean_p05_pct"), 3, "%")
                + ".",
                "judgment": "support",
                "article_handling": "Present the candidate as a test subject, not a conclusion.",
                "revision_needed": "The article must include n=15 and bootstrap lower bound near the first mention of the candidate.",
            },
            {
                "article_claim": "Nasdaqなど外部市場は予測因子ではなく文脈変数である",
                "evidence": "Risk-on proxy changes the result; S&P500 and broad 3-of-4 variants do not replicate one identical estimate.",
                "judgment": "support",
                "article_handling": "Use context-filter wording.",
                "revision_needed": "Remove or soften any sentence that says Nasdaq predicts BTC.",
            },
            {
                "article_claim": "Fragility Matrixで運用ルールへ変換する",
                "evidence": f"{len(matrix)} matrix rows map assumptions to break conditions and practical responses.",
                "judgment": "support",
                "article_handling": "Use the Matrix as the final practical section.",
                "revision_needed": "Add examples: leverage cap, cost ceiling, size reduction, stop rule, and proxy diversification.",
            },
            {
                "article_claim": "結果が弱くても記事の主張は成立する",
                "evidence": "BTC candidate has attractive point estimates but is fragile; this strengthens, not weakens, the error-on-error theme.",
                "judgment": "support",
                "article_handling": "Make the weak point part of the lesson.",
                "revision_needed": "Avoid success-story structure. Lead with fragility.",
            },
        ]
    )

    return f"""# Article Outline Alignment

## Purpose

This report checks whether the Phase 0-5 empirical outputs support the article outline.

## Alignment Table

{markdown_table(rows, ["article_claim", "evidence", "judgment", "article_handling", "revision_needed"], digits=3)}

## Overall Judgment

The experiment package aligns with the article outline.

The strongest support is for three claims:

1. Risk estimates are assumption-dependent.
2. Edge candidates are assumption-dependent.
3. Practical fat-tail work should identify break conditions and convert them into operating rules.

The main article risk is overclaiming the BTC candidate. The empirical result is useful precisely because it is fragile: `Funding low x risk-on` looks interesting, but its small sample and bootstrap uncertainty keep it from being a proven strategy.

## Suggested Article Adjustment

Replace any success-story phrasing with this:

> BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、この条件は `n=15` と小さく、bootstrapの下限も0を下回る。したがって、ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。
"""


def make_figure_selection_report() -> str:
    rows = pd.DataFrame(
        [
            {
                "figure": "usdjpy_rolling_var.png",
                "priority": 1,
                "use": "Show that risk estimates move over time and by window.",
                "article_section": "USDJPYで見るリスク推定の揺れ",
                "include": "yes",
            },
            {
                "figure": "usdjpy_risk_method_comparison.png",
                "priority": 2,
                "use": "Show method dependence across VaR, ES, Student-t, and maxDD.",
                "article_section": "リスク推定そのものにも誤差がある",
                "include": "yes",
            },
            {
                "figure": "btc_cost_stress_heatmap.png",
                "priority": 3,
                "use": "Show gross-to-net fragility for the BTC candidate.",
                "article_section": "エッジ候補はどこで壊れるか",
                "include": "yes",
            },
            {
                "figure": "btc_definition_robustness_heatmap.png",
                "priority": 4,
                "use": "Show that crash definition changes the conclusion.",
                "article_section": "定義誤差とerror on error",
                "include": "yes",
            },
            {
                "figure": "btc_bootstrap_mean_return.png",
                "priority": 5,
                "use": "Show small-sample uncertainty around Funding low x risk-on.",
                "article_section": "標本誤差を隠さない",
                "include": "yes",
            },
            {
                "figure": "fragility_matrix_status.png",
                "priority": 6,
                "use": "Summarize broken/fragile/watch counts.",
                "article_section": "Fragility Matrix",
                "include": "appendix",
            },
            {
                "figure": "btc_risk_env_robustness.png",
                "priority": 7,
                "use": "Show that risk-on proxy selection matters.",
                "article_section": "補足",
                "include": "appendix",
            },
            {
                "figure": "btc_funding_definition_robustness.png",
                "priority": 8,
                "use": "Show threshold sensitivity for Funding definitions.",
                "article_section": "補足",
                "include": "appendix",
            },
            {
                "figure": "btc_entry_execution_stress.png",
                "priority": 9,
                "use": "Show execution-delay sensitivity.",
                "article_section": "補足",
                "include": "appendix",
            },
            {
                "figure": "btc_leverage_tolerance.png",
                "priority": 10,
                "use": "Show leveraged path-risk sensitivity.",
                "article_section": "補足",
                "include": "appendix",
            },
        ]
    )
    return f"""# Article Figure Selection

## Selection Rule

Use only the figures that directly support the article's core argument. Avoid turning the article into a catalogue of every robustness table.

## Recommended Figures

{markdown_table(rows, ["priority", "figure", "use", "article_section", "include"], digits=0)}

## Suggested Body Set

Use these 5 figures in the body:

1. `outputs/figures/usdjpy_rolling_var.png`
2. `outputs/figures/usdjpy_risk_method_comparison.png`
3. `outputs/figures/btc_cost_stress_heatmap.png`
4. `outputs/figures/btc_definition_robustness_heatmap.png`
5. `outputs/figures/btc_bootstrap_mean_return.png`

Keep the remaining figures for appendix or repo documentation.
"""


def make_btc_only_fragility_report(matrix: pd.DataFrame) -> str:
    cols = [
        "fragility_source",
        "stress_case",
        "metric",
        "baseline_value",
        "stressed_value",
        "fragility_status",
        "practical_response",
    ]
    status_counts = matrix.groupby("fragility_status").size().reset_index(name="count")
    return f"""# BTC Fragility Matrix

## 日本語要約

この記事ではBTCのみを扱う。したがって、このFragility Matrixも `BTC crash edge candidate` の行だけに絞っている。

主役は `Funding low x risk-on` というBTC急落後の反発候補である。ただし、目的はエッジの証明ではない。サンプル数、コスト、約定、crash定義、risk-on proxy、Funding閾値、期間、MAE/DD/レバレッジを動かしたときに、候補がどこで壊れるかを見る。

## Status Counts

{markdown_table(status_counts, ["fragility_status", "count"], digits=0)}

## Matrix

{markdown_table(matrix, cols, digits=3)}

## Interpretation

- `Funding low x risk-on` は、平均リターンとPFだけを見ると面白い候補に見える。
- しかし、主条件は `n=15` と小さく、bootstrap下限も0を下回るため、強い主張はできない。
- `full_sample_q025` や2022ストレス期では壊れるため、定義依存・期間依存を記事本文で必ず示す。
- `Funding high x risk-off` は、買える急落ではなく避ける急落候補として使いやすい。
- 記事の結論は「BTC急落は買い」ではなく、「エッジ候補にも error on error があり、壊れる条件を先に調べるべき」である。
"""


def make_btc_only_experiment_report(tables: dict[str, pd.DataFrame], matrix: pd.DataFrame) -> str:
    btc_base = tables["btc_crash_baseline"]
    btc_boot = tables["btc_bootstrap_uncertainty"]
    btc_cost = tables["btc_cost_stress"]
    btc_definition = tables["btc_definition_robustness"]
    btc_period = tables["btc_subperiod_results"]

    btc_focus = btc_base[
        btc_base["group"].isin(
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
    boot_focus = btc_boot[btc_boot["group"].eq("funding_low_x_risk_on")][
        ["horizon", "n", "mean_p05_pct", "mean_p50_pct", "mean_p95_pct", "pf_p05", "pf_p50", "pf_p95", "is_ci_fragile"]
    ]
    cost_focus = btc_cost[
        (btc_cost["group"].eq("funding_low_x_risk_on"))
        & (btc_cost["horizon"].isin(["24h", "48h"]))
    ][["horizon", "cost_case", "cost_bps", "n", "mean_ret_pct", "profit_factor", "fragility_status"]]
    definition_focus = btc_definition[
        (btc_definition["group"].eq("funding_low_x_risk_on"))
        & (btc_definition["horizon"].eq("48h"))
    ][["event_def", "n", "mean_ret_pct", "profit_factor", "maxdd_pct", "fragility_status"]]
    period_focus = btc_period[
        (btc_period["group"].eq("funding_low_x_risk_on"))
        & (btc_period["horizon"].eq("48h"))
    ][["period", "n", "mean_ret_pct", "profit_factor", "maxdd_pct", "fragility_status"]]
    matrix_focus = matrix[
        ["fragility_source", "stress_case", "fragility_status", "article_message", "practical_response"]
    ]

    return f"""# BTC-Only Experiment Report

## 日本語要約

この記事ではBTCのみを扱う。USDJPYの実験ログは残しているが、記事本文・図表選定・骨子整合性分析には使わない。

中心テーマは、BTC急落後の `Funding low x risk-on` が「買える急落」候補に見えるとしても、それをそのまま有効戦略として扱ってよいのか、という点である。

結論は明確である。`Funding low x risk-on` は面白い候補だが、主条件は `n=15` と小さく、bootstrapの下限も0を下回る。したがって、記事では成功例ではなく、`error on error` を説明するための「壊れる条件を調べる候補」として扱う。

## 1. Purpose And Non-Purpose

Purpose:

- BTC急落後の反発候補が、どの前提で壊れるかを見る。
- Funding、外部リスク環境、コスト、定義、期間、約定、MAE/DDを疑いのダイヤルとして扱う。
- 記事骨子の「エッジ候補にも error on error がある」を実データで説明する。

Non-purpose:

- BTC急落は買いだと主張すること。
- `Funding low x risk-on` を有効戦略として証明すること。
- NasdaqがBTCを直接予測すると主張すること。

## 2. Reproducibility

Main commands used:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

Phase 0 reproduced the copied `lab_7` baseline. The regenerated major CSVs matched the copied reference CSVs.

## 3. BTC Baseline

{markdown_table(btc_focus, list(btc_focus.columns), digits=3)}

## 4. Bootstrap Uncertainty

{markdown_table(boot_focus, list(boot_focus.columns), digits=3)}

Interpretation:

- 24h/48hとも点推定は良いが、`n=15` しかない。
- bootstrap mean 5% lower bound は24h/48hとも0を下回る。
- 記事本文では、平均リターンやPFより先に `n` と不確実性を出す。

## 5. Cost Stress

{markdown_table(cost_focus, list(cost_focus.columns), digits=3)}

## 6. Crash Definition Robustness

{markdown_table(definition_focus, list(definition_focus.columns), digits=3)}

## 7. Subperiod Stability

{markdown_table(period_focus, list(period_focus.columns), digits=3)}

## 8. BTC Fragility Matrix

{markdown_table(matrix_focus, list(matrix_focus.columns), digits=3)}

## 9. Article-Ready Conclusion

BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、この条件は `n=15` と小さく、bootstrapの下限も0を下回る。さらに、crash定義や期間分割を変えると壊れるケースがある。したがって、ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。
"""


def make_btc_only_alignment_report(tables: dict[str, pd.DataFrame], matrix: pd.DataFrame) -> str:
    btc_base = tables["btc_crash_baseline"]
    btc_boot = tables["btc_bootstrap_uncertainty"]
    btc_definition = tables["btc_definition_robustness"]
    btc_period = tables["btc_subperiod_results"]
    low48 = btc_base[(btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("funding_low_x_risk_on"))]
    high48 = btc_base[(btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("funding_high_x_risk_off"))]
    all48 = btc_base[(btc_base["horizon"].eq("48h")) & (btc_base["group"].eq("all_funding_covered_crashes"))]
    boot48 = btc_boot[(btc_boot["horizon"].eq("48h")) & (btc_boot["group"].eq("funding_low_x_risk_on"))]
    q025 = btc_definition[
        (btc_definition["horizon"].eq("48h"))
        & (btc_definition["group"].eq("funding_low_x_risk_on"))
        & (btc_definition["event_def"].eq("full_sample_q025"))
    ]
    stress2022 = btc_period[
        (btc_period["horizon"].eq("48h"))
        & (btc_period["group"].eq("funding_low_x_risk_on"))
        & (btc_period["period"].eq("2022_stress"))
    ]

    rows = pd.DataFrame(
        [
            {
                "article_claim": "BTC急落は一律に買えるわけではない",
                "evidence": "All crashes 48h MaxDD is "
                + fnum(scalar(all48, "maxdd_pct"), 3, "%")
                + "; Funding high x risk-off 48h mean is "
                + fnum(scalar(high48, "mean_ret_pct"), 3, "%")
                + ".",
                "judgment": "support",
                "article_handling": "Use classification framing instead of universal dip-buying.",
                "revision_needed": "Avoid any headline that reads as BTC crash buy signal.",
            },
            {
                "article_claim": "`Funding low x risk-on` は候補だが証明ではない",
                "evidence": "48h mean is "
                + fnum(scalar(low48, "mean_ret_pct"), 3, "%")
                + " with PF "
                + fnum(scalar(low48, "profit_factor"), 3)
                + ", but n="
                + str(int(scalar(low48, "n")))
                + ".",
                "judgment": "support",
                "article_handling": "Present it as a candidate to stress, not as an edge conclusion.",
                "revision_needed": "Place n=15 next to the first mention of the candidate.",
            },
            {
                "article_claim": "エッジ候補にも error on error がある",
                "evidence": "Bootstrap 48h mean 5% lower bound is "
                + fnum(scalar(boot48, "mean_p05_pct"), 3, "%")
                + ".",
                "judgment": "support",
                "article_handling": "Use bootstrap uncertainty as the clearest empirical expression of error-on-error.",
                "revision_needed": "Do not lead with PF; lead with estimate uncertainty.",
            },
            {
                "article_claim": "定義を変えると候補は壊れ得る",
                "evidence": "48h full-sample lower 2.5% mean is "
                + fnum(scalar(q025, "mean_ret_pct"), 3, "%")
                + " with PF "
                + fnum(scalar(q025, "profit_factor"), 3)
                + ".",
                "judgment": "support",
                "article_handling": "Use the crash-definition heatmap in the body.",
                "revision_needed": "Add a sentence that crash definition is a subjective stress dial.",
            },
            {
                "article_claim": "期間分割でレジーム依存を見る必要がある",
                "evidence": "2022 stress-period 48h mean is "
                + fnum(scalar(stress2022, "mean_ret_pct"), 3, "%")
                + " with n="
                + str(int(scalar(stress2022, "n")))
                + ".",
                "judgment": "support",
                "article_handling": "Use the 2022 slice as a warning against smooth all-period conclusions.",
                "revision_needed": "Do not claim the candidate is stable across regimes.",
            },
            {
                "article_claim": "外部市場はBTCの直接予測ではなく文脈変数である",
                "evidence": "Risk-on proxy changes the estimate in robustness tables.",
                "judgment": "support",
                "article_handling": "Use external risk-on/off as classification context.",
                "revision_needed": "Remove or soften any sentence saying Nasdaq predicts BTC.",
            },
            {
                "article_claim": "分析は運用ルールへ変換する",
                "evidence": f"{len(matrix)} BTC matrix rows map assumptions to practical responses.",
                "judgment": "support",
                "article_handling": "Use the BTC Fragility Matrix as the final practical section.",
                "revision_needed": "Add responses such as cost ceilings, entry-delay tolerance, leverage caps, and avoid-condition filters.",
            },
        ]
    )

    return f"""# BTC-Only Article Outline Alignment

## 日本語要約

この記事ではBTCのみを扱う。USDJPYは本文には出さない。

BTCのみでも、記事骨子の中心主張は成立する。むしろ `Funding low x risk-on` という一見よい候補が、サンプル数・bootstrap・定義変更・期間分割で脆さを見せるため、`error on error` の説明としてはBTCに絞った方が読みやすい。

## Alignment Table

{markdown_table(rows, ["article_claim", "evidence", "judgment", "article_handling", "revision_needed"], digits=3)}

## Overall Judgment

BTC-only構成で問題ない。記事の主張は、次の形に絞る。

> BTC急落の `Funding low x risk-on` は面白い候補に見える。しかし、`n=15`、bootstrap下限、定義依存、期間依存を考えると、これを有効戦略とは言えない。重要なのは、候補が壊れる条件を先に見つけることである。
"""


def make_btc_only_figure_selection_report() -> str:
    rows = pd.DataFrame(
        [
            {
                "priority": 1,
                "figure": "btc_bootstrap_mean_return.png",
                "use": "Show that the attractive candidate has small-sample uncertainty.",
                "article_section": "標本誤差とerror on error",
                "include": "yes",
            },
            {
                "priority": 2,
                "figure": "btc_definition_robustness_heatmap.png",
                "use": "Show that changing crash definitions can break the candidate.",
                "article_section": "定義を動かすと何が壊れるか",
                "include": "yes",
            },
            {
                "priority": 3,
                "figure": "btc_cost_stress_heatmap.png",
                "use": "Show gross-to-net fragility under cost assumptions.",
                "article_section": "コストでエッジは残るか",
                "include": "yes",
            },
            {
                "priority": 4,
                "figure": "btc_entry_execution_stress.png",
                "use": "Show that execution timing is part of the risk model.",
                "article_section": "約定前提を疑う",
                "include": "optional",
            },
            {
                "priority": 5,
                "figure": "btc_risk_env_robustness.png",
                "use": "Show risk-on proxy sensitivity.",
                "article_section": "外部リスク環境は文脈変数",
                "include": "appendix",
            },
            {
                "priority": 6,
                "figure": "btc_funding_definition_robustness.png",
                "use": "Show Funding threshold sensitivity.",
                "article_section": "Funding閾値の主観性",
                "include": "appendix",
            },
            {
                "priority": 7,
                "figure": "btc_leverage_tolerance.png",
                "use": "Show leveraged path-risk sensitivity.",
                "article_section": "MAE/DDとレバレッジ耐性",
                "include": "appendix",
            },
            {
                "priority": 8,
                "figure": "fragility_matrix_status.png",
                "use": "Summarize BTC broken/fragile/watch counts.",
                "article_section": "Fragility Matrix",
                "include": "appendix",
            },
        ]
    )
    return f"""# BTC-Only Article Figure Selection

## Selection Rule

記事ではBTCのみを扱うため、USDJPY図は本文・補足の候補から外す。

## Recommended Figures

{markdown_table(rows, ["priority", "figure", "use", "article_section", "include"], digits=0)}

## Suggested Body Set

本文ではまず以下の3枚に絞る。

1. `outputs/figures/btc_bootstrap_mean_return.png`
2. `outputs/figures/btc_definition_robustness_heatmap.png`
3. `outputs/figures/btc_cost_stress_heatmap.png`

記事が長くなる場合のみ、`btc_entry_execution_stress.png` を追加する。
"""


def main() -> None:
    ensure_dirs()
    tables = {
        "usdjpy_risk_summary": read_csv("usdjpy_risk_summary.csv"),
        "usdjpy_stress_dials": read_csv("usdjpy_stress_dials.csv"),
        "usdjpy_dd_capital_table": read_csv("usdjpy_dd_capital_table.csv"),
        "usdjpy_leverage_limits": read_csv("usdjpy_leverage_limits.csv"),
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
    full_matrix = build_fragility_matrix(tables)
    full_matrix.to_csv(TABLE_DIR / "fragility_matrix_all_internal.csv", index=False)
    matrix = full_matrix[full_matrix["target"].eq("BTC crash edge candidate")].reset_index(drop=True)
    matrix.to_csv(TABLE_DIR / "fragility_matrix.csv", index=False)
    save_fragility_status_figure(matrix)
    (REPORT_DIR / "fragility_matrix.md").write_text(make_btc_only_fragility_report(matrix), encoding="utf-8")
    (REPORT_DIR / "lab_10_experiment_report.md").write_text(
        make_btc_only_experiment_report(tables, matrix),
        encoding="utf-8",
    )
    (REPORT_DIR / "article_outline_alignment.md").write_text(
        make_btc_only_alignment_report(tables, matrix),
        encoding="utf-8",
    )
    (REPORT_DIR / "article_figure_selection.md").write_text(
        make_btc_only_figure_selection_report(),
        encoding="utf-8",
    )

    print(f"Wrote {TABLE_DIR / 'fragility_matrix.csv'}")
    print(f"Wrote {REPORT_DIR / 'fragility_matrix.md'}")
    print(f"Wrote {REPORT_DIR / 'lab_10_experiment_report.md'}")
    print(f"Wrote {REPORT_DIR / 'article_outline_alignment.md'}")
    print(f"Wrote {REPORT_DIR / 'article_figure_selection.md'}")
    print(f"Wrote {FIGURE_DIR / 'fragility_matrix_status.png'}")


if __name__ == "__main__":
    main()
