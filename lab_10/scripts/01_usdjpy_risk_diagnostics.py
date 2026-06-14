from __future__ import annotations

import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "usdjpy" / "USDJPY240.csv"
TABLE_DIR = ROOT / "outputs" / "tables"
FIGURE_DIR = ROOT / "outputs" / "figures"
REPORT_DIR = ROOT / "outputs" / "report"

PRICE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
WINDOWS = {
    "1y": pd.Timedelta(days=365),
    "3y": pd.Timedelta(days=365 * 3),
    "5y": pd.Timedelta(days=365 * 5),
    "full": None,
}
ROLLING_WINDOWS = {"1y": 365, "3y": 365 * 3, "5y": 365 * 5}
BARS_PER_YEAR = 6 * 252
VOL_MULTIPLIERS = [1.0, 1.1, 1.2, 1.5]
DD_MULTIPLIERS = [1.0, 1.5, 2.0, 3.0]
COST_MULTIPLIERS = [1.0, 2.0, 5.0]
MEAN_DEGRADATIONS = [0.0, 0.25, 0.50, 1.0]
BASE_COST_BPS = 1.0
MAX_ALLOWED_DD = [20.0, 30.0, 50.0]


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_price() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, sep="\t", header=None, names=PRICE_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "close"]).set_index("timestamp")
    df["close_to_close_log_ret"] = np.log(df["close"] / df["close"].shift(1))
    df["open_to_open_log_ret"] = np.log(df["open"] / df["open"].shift(1))
    return df


def max_drawdown_pct(log_returns: pd.Series) -> float:
    ret = log_returns.dropna().astype(float)
    if ret.empty:
        return np.nan
    equity = np.exp(ret.cumsum())
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min() * 100)


def max_recovery_bars(log_returns: pd.Series) -> int:
    ret = log_returns.dropna().astype(float)
    if ret.empty:
        return 0
    equity = np.exp(ret.cumsum()).to_numpy(dtype=float)
    high_water = -np.inf
    current_underwater = 0
    max_underwater = 0
    for value in equity:
        if value >= high_water:
            high_water = value
            current_underwater = 0
        else:
            current_underwater += 1
            max_underwater = max(max_underwater, current_underwater)
    return int(max_underwater)


def var_es(ret: pd.Series, q: float) -> tuple[float, float]:
    values = ret.dropna().astype(float)
    if values.empty:
        return np.nan, np.nan
    var = float(values.quantile(q))
    tail = values[values <= var]
    es = float(tail.mean()) if len(tail) else np.nan
    return var * 100, es * 100


def normal_var(ret: pd.Series, q: float) -> float:
    values = ret.dropna().astype(float)
    if len(values) < 2:
        return np.nan
    return float((values.mean() + values.std(ddof=1) * stats.norm.ppf(q)) * 100)


def student_t_var(ret: pd.Series, q: float) -> float:
    values = ret.dropna().astype(float)
    if len(values) < 30:
        return np.nan
    try:
        df, loc, scale = stats.t.fit(values.to_numpy())
        return float(stats.t.ppf(q, df, loc=loc, scale=scale) * 100)
    except Exception:
        return np.nan


def summarize_returns(name: str, ret: pd.Series) -> dict[str, object]:
    values = ret.dropna().astype(float)
    hist_var_95, hist_es_95 = var_es(values, 0.05)
    hist_var_99, hist_es_99 = var_es(values, 0.01)
    if values.empty:
        start = end = ""
    else:
        start = str(values.index.min())
        end = str(values.index.max())
    return {
        "window_name": name,
        "start": start,
        "end": end,
        "n": int(len(values)),
        "mean_ret_pct": values.mean() * 100 if len(values) else np.nan,
        "vol_pct": values.std(ddof=1) * 100 if len(values) > 1 else np.nan,
        "annualized_vol_pct": values.std(ddof=1) * math.sqrt(BARS_PER_YEAR) * 100
        if len(values) > 1
        else np.nan,
        "skew": values.skew() if len(values) > 2 else np.nan,
        "kurtosis": values.kurtosis() if len(values) > 3 else np.nan,
        "hist_var_95_pct": hist_var_95,
        "hist_var_99_pct": hist_var_99,
        "hist_es_95_pct": hist_es_95,
        "hist_es_99_pct": hist_es_99,
        "normal_var_95_pct": normal_var(values, 0.05),
        "normal_var_99_pct": normal_var(values, 0.01),
        "student_t_var_95_pct": student_t_var(values, 0.05),
        "student_t_var_99_pct": student_t_var(values, 0.01),
        "maxdd_pct": max_drawdown_pct(values),
        "max_recovery_bars": max_recovery_bars(values),
    }


def window_returns(df: pd.DataFrame) -> dict[str, pd.Series]:
    ret = df["close_to_close_log_ret"].dropna()
    end = ret.index.max()
    out: dict[str, pd.Series] = {}
    for name, delta in WINDOWS.items():
        if delta is None:
            out[name] = ret
        else:
            out[name] = ret[ret.index >= end - delta]
    return out


def build_risk_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = [summarize_returns(name, ret) for name, ret in window_returns(df).items()]
    return pd.DataFrame(rows)


def build_rolling_var(df: pd.DataFrame) -> pd.DataFrame:
    ret = df["close_to_close_log_ret"].dropna()
    median_delta = ret.index.to_series().diff().median()
    bars_per_day = max(1, int(round(pd.Timedelta(days=1) / median_delta)))
    rows: list[pd.DataFrame] = []
    for name, days in ROLLING_WINDOWS.items():
        window = int(days * bars_per_day)
        min_periods = max(30, int(window * 0.6))
        rolling = ret.rolling(window=window, min_periods=min_periods)
        var_95 = rolling.quantile(0.05) * 100
        var_99 = rolling.quantile(0.01) * 100

        def es_func(values: np.ndarray, q: float) -> float:
            clean = values[np.isfinite(values)]
            if len(clean) < min_periods:
                return np.nan
            var = np.quantile(clean, q)
            tail = clean[clean <= var]
            return np.mean(tail) * 100 if len(tail) else np.nan

        es_95 = rolling.apply(lambda x: es_func(x, 0.05), raw=True)
        es_99 = rolling.apply(lambda x: es_func(x, 0.01), raw=True)
        rows.append(
            pd.DataFrame(
                {
                    "timestamp": ret.index,
                    "window_name": name,
                    "window_bars": window,
                    "hist_var_95_pct": var_95.to_numpy(),
                    "hist_var_99_pct": var_99.to_numpy(),
                    "hist_es_95_pct": es_95.to_numpy(),
                    "hist_es_99_pct": es_99.to_numpy(),
                }
            ).dropna()
        )
    return pd.concat(rows, ignore_index=True)


def build_stress_tables(df: pd.DataFrame, summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stress_rows: list[dict[str, object]] = []
    dd_rows: list[dict[str, object]] = []
    leverage_rows: list[dict[str, object]] = []
    windows = window_returns(df)

    for name, ret in windows.items():
        values = ret.dropna().astype(float)
        if values.empty:
            continue
        mean = values.mean()
        demeaned = values - mean
        for mult in VOL_MULTIPLIERS:
            stressed = mean + demeaned * mult
            hist_var_99, hist_es_99 = var_es(stressed, 0.01)
            stress_rows.append(
                {
                    "window_name": name,
                    "dial": "vol_multiplier",
                    "stress_case": f"vol_x{mult:g}",
                    "stress_value": mult,
                    "mean_ret_pct": stressed.mean() * 100,
                    "hist_var_99_pct": hist_var_99,
                    "hist_es_99_pct": hist_es_99,
                    "maxdd_pct": max_drawdown_pct(stressed),
                    "note": "Scale deviations around the historical mean.",
                }
            )
        for degradation in MEAN_DEGRADATIONS:
            stressed = values - mean * degradation
            hist_var_99, hist_es_99 = var_es(stressed, 0.01)
            stress_rows.append(
                {
                    "window_name": name,
                    "dial": "mean_degradation",
                    "stress_case": f"mean_down_{int(degradation * 100)}pct",
                    "stress_value": degradation,
                    "mean_ret_pct": stressed.mean() * 100,
                    "hist_var_99_pct": hist_var_99,
                    "hist_es_99_pct": hist_es_99,
                    "maxdd_pct": max_drawdown_pct(stressed),
                    "note": "Reduce historical average return as an edge-decay dial.",
                }
            )
        for cost_mult in COST_MULTIPLIERS:
            cost = BASE_COST_BPS * cost_mult / 10000
            stressed = values - cost
            hist_var_99, hist_es_99 = var_es(stressed, 0.01)
            stress_rows.append(
                {
                    "window_name": name,
                    "dial": "cost_multiplier",
                    "stress_case": f"cost_x{cost_mult:g}",
                    "stress_value": cost_mult,
                    "mean_ret_pct": stressed.mean() * 100,
                    "hist_var_99_pct": hist_var_99,
                    "hist_es_99_pct": hist_es_99,
                    "maxdd_pct": max_drawdown_pct(stressed),
                    "note": f"Apply {BASE_COST_BPS:g}bps base cost per 4H return as a turnover stress dial.",
                }
            )

        base_maxdd = float(summary.loc[summary["window_name"].eq(name), "maxdd_pct"].iloc[0])
        for dd_mult in DD_MULTIPLIERS:
            stressed_maxdd = base_maxdd * dd_mult
            dd_rows.append(
                {
                    "window_name": name,
                    "dd_multiplier": dd_mult,
                    "historical_maxdd_pct": base_maxdd,
                    "stressed_maxdd_pct": stressed_maxdd,
                    "required_capital_pct_for_1x": abs(stressed_maxdd),
                    "note": "Treat historical max DD as a baseline, not a future upper bound.",
                }
            )
            for allowed in MAX_ALLOWED_DD:
                leverage_rows.append(
                    {
                        "window_name": name,
                        "dd_multiplier": dd_mult,
                        "max_allowed_dd_pct": allowed,
                        "stressed_maxdd_pct": stressed_maxdd,
                        "leverage_limit": allowed / abs(stressed_maxdd)
                        if math.isfinite(stressed_maxdd) and stressed_maxdd < 0
                        else np.nan,
                    }
                )

    return pd.DataFrame(stress_rows), pd.DataFrame(dd_rows), pd.DataFrame(leverage_rows)


def save_risk_method_figure(summary: pd.DataFrame) -> None:
    plot = summary.melt(
        id_vars=["window_name"],
        value_vars=[
            "hist_var_99_pct",
            "hist_es_99_pct",
            "normal_var_99_pct",
            "student_t_var_99_pct",
            "maxdd_pct",
        ],
        var_name="metric",
        value_name="value_pct",
    )
    fig, ax = plt.subplots(figsize=(11, 6))
    metrics = plot["metric"].unique().tolist()
    windows = summary["window_name"].tolist()
    x = np.arange(len(windows))
    width = 0.15
    for i, metric in enumerate(metrics):
        values = plot[plot["metric"].eq(metric)].set_index("window_name").loc[windows, "value_pct"]
        ax.bar(x + (i - 2) * width, values, width=width, label=metric)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("USDJPY risk estimates vary by method and window")
    ax.set_ylabel("Return / drawdown (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(windows)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "usdjpy_risk_method_comparison.png", dpi=180)
    plt.close(fig)


def save_rolling_var_figure(rolling: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    for name, group in rolling.groupby("window_name"):
        ax.plot(pd.to_datetime(group["timestamp"]), group["hist_var_99_pct"], label=f"{name} VaR 99%")
        ax.plot(pd.to_datetime(group["timestamp"]), group["hist_es_99_pct"], linestyle="--", label=f"{name} ES 99%")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("USDJPY rolling left-tail risk estimates")
    ax.set_ylabel("4H return (%)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "usdjpy_rolling_var.png", dpi=180)
    plt.close(fig)


def fmt(value: object, digits: int = 3) -> str:
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return "-"
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(df: pd.DataFrame, cols: list[str], digits: int = 3) -> str:
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(fmt(row[col], digits) for col in cols) + " |")
    return "\n".join(lines)


def make_report(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    stress: pd.DataFrame,
    dd_table: pd.DataFrame,
    leverage: pd.DataFrame,
) -> str:
    cols = [
        "window_name",
        "start",
        "end",
        "n",
        "hist_var_99_pct",
        "hist_es_99_pct",
        "normal_var_99_pct",
        "student_t_var_99_pct",
        "maxdd_pct",
        "max_recovery_bars",
    ]
    worst_window = summary.sort_values("hist_es_99_pct").iloc[0]
    maxdd_window = summary.sort_values("maxdd_pct").iloc[0]
    stress_focus = stress[
        stress["stress_case"].isin(["vol_x1.5", "cost_x5", "mean_down_100pct"])
    ].sort_values(["window_name", "dial"])
    leverage_focus = leverage[
        (leverage["dd_multiplier"].eq(2.0)) & (leverage["max_allowed_dd_pct"].eq(30.0))
    ]

    return f"""# USDJPY risk diagnostics

## Purpose

This experiment does not forecast the future risk of USDJPY. It shows how risk estimates move when the method, lookback window, and stress dial move.

## Data

- File: `data/usdjpy/USDJPY240.csv`
- Rows: {len(df):,}
- Range: {df.index.min()} to {df.index.max()}
- Frequency used for annualization: {BARS_PER_YEAR} 4H bars/year

## Window Risk Summary

{markdown_table(summary, cols, digits=4)}

## Key Read

- The weakest 99% ES window by this run is `{worst_window["window_name"]}`: {worst_window["hist_es_99_pct"]:.4f}% per 4H bar.
- The largest historical max drawdown window is `{maxdd_window["window_name"]}`: {maxdd_window["maxdd_pct"]:.3f}%.
- These values are baselines for doubt, not future upper bounds.

## Stress Dial Examples

{markdown_table(stress_focus, ["window_name", "dial", "stress_case", "mean_ret_pct", "hist_var_99_pct", "hist_es_99_pct", "maxdd_pct"], digits=4)}

## Leverage Dial Example

The table below asks how much leverage is compatible with a 30% max allowed drawdown if historical max DD is doubled.

{markdown_table(leverage_focus, ["window_name", "dd_multiplier", "max_allowed_dd_pct", "stressed_maxdd_pct", "leverage_limit"], digits=3)}

## Figures

- `outputs/figures/usdjpy_risk_method_comparison.png`
- `outputs/figures/usdjpy_rolling_var.png`

## Article Interpretation

- Risk estimates are not single truths. They move with method, lookback, and stress assumptions.
- Historical max DD is not a future loss cap.
- The practical article claim should be: use these numbers as a baseline, then explicitly apply doubt dials.
"""


def main() -> None:
    ensure_dirs()
    df = read_price()
    summary = build_risk_summary(df)
    rolling = build_rolling_var(df)
    stress, dd_table, leverage = build_stress_tables(df, summary)

    summary.to_csv(TABLE_DIR / "usdjpy_risk_summary.csv", index=False)
    rolling.to_csv(TABLE_DIR / "usdjpy_rolling_var.csv", index=False)
    stress.to_csv(TABLE_DIR / "usdjpy_stress_dials.csv", index=False)
    dd_table.to_csv(TABLE_DIR / "usdjpy_dd_capital_table.csv", index=False)
    leverage.to_csv(TABLE_DIR / "usdjpy_leverage_limits.csv", index=False)

    save_risk_method_figure(summary)
    save_rolling_var_figure(rolling)
    (REPORT_DIR / "usdjpy_risk_diagnostics.md").write_text(
        make_report(df, summary, stress, dd_table, leverage),
        encoding="utf-8",
    )

    print(f"Wrote {TABLE_DIR / 'usdjpy_risk_summary.csv'}")
    print(f"Wrote {TABLE_DIR / 'usdjpy_rolling_var.csv'}")
    print(f"Wrote {TABLE_DIR / 'usdjpy_stress_dials.csv'}")
    print(f"Wrote {TABLE_DIR / 'usdjpy_dd_capital_table.csv'}")
    print(f"Wrote {TABLE_DIR / 'usdjpy_leverage_limits.csv'}")
    print(f"Wrote {REPORT_DIR / 'usdjpy_risk_diagnostics.md'}")


if __name__ == "__main__":
    main()
