from __future__ import annotations

import math
from bisect import bisect_right, insort
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "lab_7"
OUTPUT_DIR = ROOT / "outputs" / "lab7_interaction_model_base"

PRICE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
ASSETS = {
    "btc": "BTCUSD240.csv",
    "nasdaq": "USATECHIDXUSD240.csv",
    "sp500": "USA500IDXUSD240.csv",
    "dow": "USA30IDXUSD240.csv",
    "dax": "DEUIDXEUR240.csv",
}

ROLLING_SIGMA_WINDOW = 180
COOLDOWN_BARS = 6
HORIZONS = {"24h": 6, "48h": 12, "5d": 30}
PRIMARY_EVENT = "rolling_2sigma"
PRIMARY_RISK_ENV = "nasdaq_5d_up"


def read_price(path: Path, prefix: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", header=None, names=PRICE_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df.rename(columns={col: f"{prefix}_{col}" for col in numeric_cols})


def expanding_percentile(values: pd.Series, min_periods: int = 180) -> pd.Series:
    sorted_values: list[float] = []
    out: list[float] = []
    for value in values.astype(float):
        if not math.isfinite(value):
            out.append(np.nan)
            continue
        insort(sorted_values, value)
        if len(sorted_values) < min_periods:
            out.append(np.nan)
        else:
            out.append(bisect_right(sorted_values, value) / len(sorted_values))
    return pd.Series(out, index=values.index, dtype=float)


def read_funding() -> pd.DataFrame:
    funding = pd.read_csv(DATA_DIR / "funding_rate_history.csv")
    funding = funding[funding["symbol"].astype(str).str.upper().eq("BTCUSDT")].copy()
    funding["timestamp"] = pd.to_datetime(funding["funding_timestamp"])
    funding["funding_rate"] = pd.to_numeric(funding["funding_rate"], errors="coerce")
    funding = funding.sort_values("timestamp").drop_duplicates("timestamp")
    funding["funding_percentile_expanding"] = expanding_percentile(funding["funding_rate"])
    return funding[["timestamp", "funding_rate", "funding_percentile_expanding"]]


def future_path_metrics(panel: pd.DataFrame, bars: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    open_prices = panel["btc_open"].to_numpy(dtype=float)
    highs = panel["btc_high"].to_numpy(dtype=float)
    lows = panel["btc_low"].to_numpy(dtype=float)
    future_ret = np.full(len(panel), np.nan)
    mae = np.full(len(panel), np.nan)
    mfe = np.full(len(panel), np.nan)

    for i in range(len(panel)):
        entry_i = i + 1
        exit_i = i + 1 + bars
        if exit_i >= len(panel):
            continue
        entry = open_prices[entry_i]
        exit_price = open_prices[exit_i]
        if not math.isfinite(entry) or entry <= 0 or not math.isfinite(exit_price):
            continue
        path_high = np.nanmax(highs[entry_i : exit_i + 1])
        path_low = np.nanmin(lows[entry_i : exit_i + 1])
        future_ret[i] = math.log(exit_price / entry)
        mae[i] = math.log(path_low / entry) if path_low > 0 else np.nan
        mfe[i] = math.log(path_high / entry) if path_high > 0 else np.nan

    index = panel.index
    return (
        pd.Series(future_ret, index=index),
        pd.Series(mae, index=index),
        pd.Series(mfe, index=index),
    )


def build_panel() -> tuple[pd.DataFrame, dict[str, str]]:
    frames = [read_price(DATA_DIR / file_name, prefix) for prefix, file_name in ASSETS.items()]
    panel = pd.concat(frames, axis=1, join="inner").sort_index()
    panel["row_pos"] = np.arange(len(panel))

    for prefix in ASSETS:
        close = panel[f"{prefix}_close"]
        panel[f"{prefix}_ret_4h"] = np.log(close / close.shift(1))
        panel[f"{prefix}_ret_5d"] = np.log(close / close.shift(30))

    btc_ret = panel["btc_ret_4h"]
    past_mean = btc_ret.shift(1).rolling(
        ROLLING_SIGMA_WINDOW, min_periods=ROLLING_SIGMA_WINDOW
    ).mean()
    past_std = btc_ret.shift(1).rolling(
        ROLLING_SIGMA_WINDOW, min_periods=ROLLING_SIGMA_WINDOW
    ).std()
    panel["btc_sigma_score_180"] = (btc_ret - past_mean) / past_std
    panel["crash_rolling_2sigma"] = panel["btc_sigma_score_180"] <= -2.0
    panel["crash_rolling_1_5sigma"] = panel["btc_sigma_score_180"] <= -1.5
    q05 = btc_ret.quantile(0.05)
    panel["crash_full_sample_q05"] = btc_ret <= q05

    for horizon, bars in HORIZONS.items():
        future_ret, mae, mfe = future_path_metrics(panel, bars)
        panel[f"btc_future_ret_{horizon}"] = future_ret
        panel[f"btc_mae_{horizon}"] = mae
        panel[f"btc_mfe_{horizon}"] = mfe

    panel["risk_on_nasdaq"] = panel["nasdaq_ret_5d"] > 0
    panel["risk_on_sp500"] = panel["sp500_ret_5d"] > 0
    risk_assets = ["nasdaq_ret_5d", "sp500_ret_5d", "dow_ret_5d", "dax_ret_5d"]
    panel["risk_on_broad_3of4"] = panel[risk_assets].gt(0).sum(axis=1) >= 3

    funding = read_funding()
    merged = pd.merge_asof(
        panel.reset_index().rename(columns={"index": "timestamp"}).sort_values("timestamp"),
        funding.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
        tolerance=pd.Timedelta(hours=12),
    ).set_index("timestamp")
    merged["funding_low"] = (
        (merged["funding_percentile_expanding"] <= 0.20) | (merged["funding_rate"] < 0)
    )
    merged["funding_negative"] = merged["funding_rate"] < 0
    merged["funding_low20"] = merged["funding_percentile_expanding"] <= 0.20
    merged["funding_high"] = merged["funding_percentile_expanding"] >= 0.80
    merged["has_funding_regime"] = merged["funding_percentile_expanding"].notna()

    metadata = {
        "start": str(merged.index.min()),
        "end": str(merged.index.max()),
        "rows": str(len(merged)),
        "btc_q05_pct": f"{q05 * 100:.4f}",
        "rolling_sigma_window": str(ROLLING_SIGMA_WINDOW),
    }
    return merged.sort_index(), metadata


def apply_cooldown(events: pd.DataFrame, cooldown_bars: int = COOLDOWN_BARS) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    keep: list[bool] = []
    last_pos = -10**12
    for pos in events["row_pos"].astype(int):
        take = pos - last_pos >= cooldown_bars
        keep.append(take)
        if take:
            last_pos = pos
    return events.loc[keep].copy()


def max_drawdown_pct(log_returns: pd.Series) -> float:
    ret = log_returns.dropna().astype(float)
    if ret.empty:
        return np.nan
    equity = np.exp(ret.cumsum())
    drawdown = equity / equity.cummax() - 1.0
    return drawdown.min() * 100


def trade_metrics(df: pd.DataFrame, horizon: str) -> dict[str, float]:
    ret = df[f"btc_future_ret_{horizon}"].dropna().astype(float)
    n = len(ret)
    if n == 0:
        return {
            "n": 0,
            "mean_ret_pct": np.nan,
            "median_ret_pct": np.nan,
            "win_rate_pct": np.nan,
            "profit_factor": np.nan,
            "t_stat": np.nan,
            "mean_mae_pct": np.nan,
            "worst_mae_pct": np.nan,
            "mean_mfe_pct": np.nan,
            "best_mfe_pct": np.nan,
            "maxdd_pct": np.nan,
        }

    aligned = df.loc[ret.index]
    gains = ret[ret > 0].sum()
    losses = ret[ret < 0].sum()
    pf = gains / abs(losses) if losses < 0 else np.inf
    if n >= 2 and ret.std(ddof=1) > 0:
        t_stat = stats.ttest_1samp(ret, 0.0, nan_policy="omit").statistic
    else:
        t_stat = np.nan

    mae = aligned[f"btc_mae_{horizon}"].dropna().astype(float)
    mfe = aligned[f"btc_mfe_{horizon}"].dropna().astype(float)
    return {
        "n": n,
        "mean_ret_pct": ret.mean() * 100,
        "median_ret_pct": ret.median() * 100,
        "win_rate_pct": (ret > 0).mean() * 100,
        "profit_factor": pf,
        "t_stat": float(t_stat) if math.isfinite(t_stat) else np.nan,
        "mean_mae_pct": mae.mean() * 100 if len(mae) else np.nan,
        "worst_mae_pct": mae.min() * 100 if len(mae) else np.nan,
        "mean_mfe_pct": mfe.mean() * 100 if len(mfe) else np.nan,
        "best_mfe_pct": mfe.max() * 100 if len(mfe) else np.nan,
        "maxdd_pct": max_drawdown_pct(ret),
    }


def ols_with_classic_se(y: np.ndarray, x: np.ndarray) -> pd.DataFrame:
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    n, k = x.shape
    if n <= k:
        se = np.full(k, np.nan)
        t_stat = np.full(k, np.nan)
        p_value = np.full(k, np.nan)
    else:
        sigma2 = float(residuals.T @ residuals) / (n - k)
        xtx_inv = np.linalg.pinv(x.T @ x)
        se = np.sqrt(np.diag(sigma2 * xtx_inv))
        t_stat = beta / se
        p_value = 2 * stats.t.sf(np.abs(t_stat), df=n - k)
    return pd.DataFrame(
        {
            "term": ["intercept_not_low_risk_off", "funding_low", "risk_on", "funding_low_x_risk_on"],
            "coef_pct": beta * 100,
            "se_pct": se * 100,
            "t_stat": t_stat,
            "naive_p": p_value,
        }
    )


def run_regression(events: pd.DataFrame, horizon: str, risk_col: str) -> pd.DataFrame:
    cols = [f"btc_future_ret_{horizon}", "funding_low", risk_col, "has_funding_regime"]
    model_df = events[cols].dropna()
    model_df = model_df[model_df["has_funding_regime"]].copy()
    if len(model_df) < 12:
        return pd.DataFrame(columns=["term", "coef_pct", "se_pct", "t_stat", "naive_p"])

    y = model_df[f"btc_future_ret_{horizon}"].astype(float).to_numpy()
    funding_low = model_df["funding_low"].astype(int).to_numpy()
    risk_on = model_df[risk_col].astype(int).to_numpy()
    interaction = funding_low * risk_on
    x = np.column_stack([np.ones(len(model_df)), funding_low, risk_on, interaction])
    return ols_with_classic_se(y, x)


def group_masks(events: pd.DataFrame, risk_col: str) -> dict[str, pd.Series]:
    return {
        "all_funding_covered_crashes": pd.Series(True, index=events.index),
        "funding_low_only": events["funding_low"],
        "risk_on_only": events[risk_col],
        "funding_low_x_risk_on": events["funding_low"] & events[risk_col],
        "funding_low_x_risk_off": events["funding_low"] & (~events[risk_col]),
        "funding_not_low_x_risk_on": (~events["funding_low"]) & events[risk_col],
        "funding_not_low_x_risk_off": (~events["funding_low"]) & (~events[risk_col]),
        "funding_high_x_risk_off": events["funding_high"] & (~events[risk_col]),
        "funding_high_x_risk_on": events["funding_high"] & events[risk_col],
        "funding_negative_x_risk_on": events["funding_negative"] & events[risk_col],
        "funding_low20_x_risk_on": events["funding_low20"] & events[risk_col],
    }


def group_stats(events: pd.DataFrame, event_def: str, horizon: str, risk_name: str, risk_col: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    usable = events[events["has_funding_regime"]].dropna(subset=[f"btc_future_ret_{horizon}"]).copy()
    for group, mask in group_masks(usable, risk_col).items():
        selected = usable.loc[mask.fillna(False)]
        row = {
            "event_def": event_def,
            "horizon": horizon,
            "risk_env": risk_name,
            "group": group,
        }
        row.update(trade_metrics(selected, horizon))
        rows.append(row)
    return pd.DataFrame(rows)


def period_slices(events: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "all": events,
        "2020_plus": events[events.index >= "2020-01-01"],
        "2021_plus": events[events.index >= "2021-01-01"],
        "2022_rate_hike": events[(events.index >= "2022-01-01") & (events.index < "2023-01-01")],
        "2023_plus": events[events.index >= "2023-01-01"],
        "post_btc_etf": events[events.index >= "2024-01-11"],
    }


def run_experiment(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    crash_defs = {
        "rolling_2sigma": panel["crash_rolling_2sigma"],
        "rolling_1_5sigma": panel["crash_rolling_1_5sigma"],
        "full_sample_q05": panel["crash_full_sample_q05"],
    }
    risk_envs = {
        "nasdaq_5d_up": "risk_on_nasdaq",
        "sp500_5d_up": "risk_on_sp500",
        "broad_3of4_5d_up": "risk_on_broad_3of4",
    }
    group_rows: list[pd.DataFrame] = []
    regression_rows: list[pd.DataFrame] = []
    contrast_rows: list[dict[str, object]] = []
    period_rows: list[dict[str, object]] = []

    for event_def, event_mask in crash_defs.items():
        events = apply_cooldown(panel[event_mask.fillna(False)].copy())
        for horizon in HORIZONS:
            for risk_name, risk_col in risk_envs.items():
                groups = group_stats(events, event_def, horizon, risk_name, risk_col)
                group_rows.append(groups)

                reg = run_regression(events, horizon, risk_col)
                reg.insert(0, "event_def", event_def)
                reg.insert(1, "horizon", horizon)
                reg.insert(2, "risk_env", risk_name)
                regression_rows.append(reg)

                pivot = groups.set_index("group")

                def mean_of(group: str) -> float:
                    if group not in pivot.index:
                        return np.nan
                    return float(pivot.loc[group, "mean_ret_pct"])

                low_on = mean_of("funding_low_x_risk_on")
                low_off = mean_of("funding_low_x_risk_off")
                not_low_on = mean_of("funding_not_low_x_risk_on")
                not_low_off = mean_of("funding_not_low_x_risk_off")
                contrast_rows.append(
                    {
                        "event_def": event_def,
                        "horizon": horizon,
                        "risk_env": risk_name,
                        "low_on_minus_all_pct": low_on - mean_of("all_funding_covered_crashes"),
                        "low_on_minus_funding_low_only_pct": low_on - mean_of("funding_low_only"),
                        "low_on_minus_risk_on_only_pct": low_on - mean_of("risk_on_only"),
                        "high_off_minus_all_pct": mean_of("funding_high_x_risk_off")
                        - mean_of("all_funding_covered_crashes"),
                        "difference_in_differences_pct": low_on - low_off - not_low_on + not_low_off,
                        "mean_low_on_pct": low_on,
                        "mean_low_off_pct": low_off,
                        "mean_not_low_on_pct": not_low_on,
                        "mean_not_low_off_pct": not_low_off,
                    }
                )

                if event_def == PRIMARY_EVENT and risk_name in [PRIMARY_RISK_ENV, "broad_3of4_5d_up"]:
                    usable = events[events["has_funding_regime"]].dropna(subset=[f"btc_future_ret_{horizon}"])
                    for period_name, period_df in period_slices(usable).items():
                        masks = group_masks(period_df, risk_col)
                        for group in ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]:
                            selected = period_df.loc[masks[group].fillna(False)]
                            row = {
                                "event_def": event_def,
                                "horizon": horizon,
                                "risk_env": risk_name,
                                "period": period_name,
                                "group": group,
                            }
                            row.update(trade_metrics(selected, horizon))
                            period_rows.append(row)

    return (
        pd.concat(group_rows, ignore_index=True),
        pd.concat(regression_rows, ignore_index=True),
        pd.DataFrame(contrast_rows),
        pd.DataFrame(period_rows),
    )


def fmt(value: object, digits: int = 3) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(value):
        return "-"
    return f"{value:.{digits}f}"


def markdown_table(df: pd.DataFrame, columns: list[str], digits: int = 3) -> str:
    if df.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            value = row[col]
            cells.append(fmt(value, digits) if isinstance(value, (float, np.floating)) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def save_bar_chart(
    path: Path,
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    ylabel: str,
    color: str = "#3366AA",
) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.8))
    labels = data[x_col].astype(str).tolist()
    values = data[y_col].astype(float).tolist()
    bars = ax.bar(range(len(values)), values, color=color, alpha=0.88)
    ax.axhline(0, color="#333333", linewidth=0.9)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        y = bar.get_height()
        va = "bottom" if y >= 0 else "top"
        offset = 0.05 if y >= 0 else -0.05
        ax.text(bar.get_x() + bar.get_width() / 2, y + offset, f"{value:.2f}", ha="center", va=va, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def generate_figures(group_table: pd.DataFrame, regression_table: pd.DataFrame, contrast_table: pd.DataFrame) -> None:
    figure_dir = OUTPUT_DIR / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    primary_48 = group_table[
        (group_table["event_def"] == PRIMARY_EVENT)
        & (group_table["risk_env"] == PRIMARY_RISK_ENV)
        & (group_table["horizon"] == "48h")
        & (group_table["group"].isin(
            [
                "all_funding_covered_crashes",
                "funding_low_only",
                "risk_on_only",
                "funding_low_x_risk_on",
                "funding_high_x_risk_off",
            ]
        ))
    ].copy()
    order = [
        "all_funding_covered_crashes",
        "funding_low_only",
        "risk_on_only",
        "funding_low_x_risk_on",
        "funding_high_x_risk_off",
    ]
    primary_48["group"] = pd.Categorical(primary_48["group"], categories=order, ordered=True)
    primary_48 = primary_48.sort_values("group")
    save_bar_chart(
        figure_dir / "figure02_primary_48h_mean_return.png",
        primary_48,
        "group",
        "mean_ret_pct",
        "Primary 48h mean return: BTC rolling 2-sigma crashes",
        "Mean return (%)",
        color="#2E6F9E",
    )

    four_cells = [
        "funding_not_low_x_risk_off",
        "funding_low_x_risk_off",
        "funding_not_low_x_risk_on",
        "funding_low_x_risk_on",
    ]
    for horizon in ["24h", "48h"]:
        cells = group_table[
            (group_table["event_def"] == PRIMARY_EVENT)
            & (group_table["risk_env"] == PRIMARY_RISK_ENV)
            & (group_table["horizon"] == horizon)
            & (group_table["group"].isin(four_cells))
        ].copy()
        cells["group"] = pd.Categorical(cells["group"], categories=four_cells, ordered=True)
        cells = cells.sort_values("group")
        save_bar_chart(
            figure_dir / f"figure0{'3' if horizon == '24h' else '4'}_four_cell_{horizon}_mean_return.png",
            cells,
            "group",
            "mean_ret_pct",
            f"Four-cell mean return ({horizon})",
            "Mean return (%)",
            color="#4B8B5B",
        )

    risk_compare = contrast_table[
        (contrast_table["event_def"] == PRIMARY_EVENT)
        & (contrast_table["horizon"].isin(["24h", "48h"]))
    ].copy()
    risk_compare["label"] = risk_compare["risk_env"] + " / " + risk_compare["horizon"]
    save_bar_chart(
        figure_dir / "figure05_risk_proxy_low_funding_risk_on.png",
        risk_compare.sort_values(["horizon", "risk_env"]),
        "label",
        "mean_low_on_pct",
        "Funding low x risk-on by risk proxy",
        "Mean return (%)",
        color="#8A6BBE",
    )

    coef = regression_table[
        (regression_table["event_def"] == PRIMARY_EVENT)
        & (regression_table["term"] == "funding_low_x_risk_on")
        & (regression_table["horizon"].isin(["24h", "48h"]))
    ].copy()
    coef["label"] = coef["risk_env"] + " / " + coef["horizon"]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    coef = coef.sort_values(["horizon", "risk_env"])
    x = np.arange(len(coef))
    ax.bar(x, coef["coef_pct"], yerr=coef["se_pct"], color="#B85C38", alpha=0.86, capsize=4)
    ax.axhline(0, color="#333333", linewidth=0.9)
    ax.set_title("Interaction coefficient with classic SE")
    ax.set_ylabel("Coefficient (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(coef["label"], rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "figure06_interaction_coefficients.png", dpi=180)
    plt.close(fig)


def make_report(
    metadata: dict[str, str],
    group_table: pd.DataFrame,
    regression_table: pd.DataFrame,
    contrast_table: pd.DataFrame,
    period_table: pd.DataFrame,
) -> str:
    primary_groups = group_table[
        (group_table["event_def"] == PRIMARY_EVENT)
        & (group_table["risk_env"] == PRIMARY_RISK_ENV)
        & (group_table["horizon"].isin(["24h", "48h"]))
        & (group_table["group"].isin(
            [
                "all_funding_covered_crashes",
                "funding_low_only",
                "risk_on_only",
                "funding_low_x_risk_on",
                "funding_high_x_risk_off",
            ]
        ))
    ].sort_values(["horizon", "group"])

    primary_reg = regression_table[
        (regression_table["event_def"] == PRIMARY_EVENT)
        & (regression_table["risk_env"] == PRIMARY_RISK_ENV)
        & (regression_table["horizon"].isin(["24h", "48h"]))
    ]

    contrast_focus = contrast_table[
        (contrast_table["horizon"].isin(["24h", "48h"]))
    ].sort_values(["event_def", "horizon", "risk_env"])

    period_focus = period_table[
        (period_table["horizon"].isin(["24h", "48h"]))
        & (period_table["risk_env"] == PRIMARY_RISK_ENV)
    ].sort_values(["horizon", "period", "group"])

    verdict = pd.DataFrame(
        [
            {
                "question": "主条件は全急落より良いか",
                "answer": "yes",
                "note": "rolling 2 sigma x Nasdaq 5d upでは、Funding低位 x risk-onが24h/48hとも全急落を上回る。",
            },
            {
                "question": "Funding単体より改善するか",
                "answer": "mixed",
                "note": "24h/48hとも改善はあるが、差は大きくない。主役はFunding単体ではなく条件分類。",
            },
            {
                "question": "risk-on単体より改善するか",
                "answer": "mixed",
                "note": "24hは改善、48hはrisk-on単体が強い。交互作用項の主張は慎重にする。",
            },
            {
                "question": "避けるべき急落は見えるか",
                "answer": "yes_directionally",
                "note": "Funding高位 x risk-offは24h/48hで弱く、避ける候補として使いやすい。",
            },
        ]
    )

    columns = [
        "event_def",
        "horizon",
        "risk_env",
        "group",
        "n",
        "mean_ret_pct",
        "median_ret_pct",
        "win_rate_pct",
        "profit_factor",
        "t_stat",
        "mean_mae_pct",
        "worst_mae_pct",
        "mean_mfe_pct",
        "maxdd_pct",
    ]
    contrast_cols = [
        "event_def",
        "horizon",
        "risk_env",
        "low_on_minus_all_pct",
        "low_on_minus_funding_low_only_pct",
        "low_on_minus_risk_on_only_pct",
        "high_off_minus_all_pct",
        "difference_in_differences_pct",
        "mean_low_on_pct",
        "mean_low_off_pct",
        "mean_not_low_on_pct",
        "mean_not_low_off_pct",
    ]

    return f"""# BTC crash rebound interaction model experiment

## Setup

```text
BTC crash future return
= BTC crash event
+ Funding
+ external risk environment
+ Funding x external risk environment
```

- Frequency: 4H.
- Primary crash definition: rolling 2 sigma, using the previous {metadata["rolling_sigma_window"]} 4H bars.
- Robustness crash definitions: rolling 1.5 sigma and full-sample lower 5%.
- Primary external risk-on: Nasdaq 5-day return > 0.
- Robustness external risk-on: S&P500 5-day return > 0 and broad 3-of-4 risk-on across Nasdaq/S&P500/Dow/DAX.
- Funding low: expanding lower 20% or negative Funding Rate known at signal time.
- Funding high: expanding upper 20%.
- Entry: next 4H open after signal confirmation.
- Exits: 24h, 48h, and supplementary 5d open-to-open.
- Event spacing: 24h cooldown.
- Metrics are gross of fees, spread, and slippage.
- P-values are naive and do not fully correct for time-series dependence.

## Data Coverage

- Common 4H panel: {metadata["rows"]} rows, {metadata["start"]} to {metadata["end"]}.
- Full-sample lower 5% BTC 4H threshold: {metadata["btc_q05_pct"]}%.

## Verdict

{markdown_table(verdict, list(verdict.columns), digits=3)}

## Primary Results

{markdown_table(primary_groups, columns, digits=3)}

## Figures

- `figures/figure02_primary_48h_mean_return.png`
- `figures/figure03_four_cell_24h_mean_return.png`
- `figures/figure04_four_cell_48h_mean_return.png`
- `figures/figure05_risk_proxy_low_funding_risk_on.png`
- `figures/figure06_interaction_coefficients.png`

## Primary Regression Coefficients

The intercept is `funding_not_low x risk_off`. The interaction coefficient is the extra effect of being both `funding_low` and `risk_on` beyond the separate Funding and risk-on effects.

{markdown_table(primary_reg, ["event_def", "horizon", "risk_env", "term", "coef_pct", "se_pct", "t_stat", "naive_p"], digits=4)}

## Robustness Contrasts

{markdown_table(contrast_focus, contrast_cols, digits=3)}

## Period Stability

{markdown_table(period_focus, ["event_def", "horizon", "risk_env", "period", "group", "n", "mean_ret_pct", "win_rate_pct", "profit_factor", "mean_mae_pct", "maxdd_pct"], digits=3)}

## Interpretation

- The cleanest article claim is not that Nasdaq predicts BTC.
- The practical claim is that Funding and external risk-on/off conditions help classify BTC crashes.
- `Funding low x risk-on` is a candidate for buyable drops.
- `Funding high x risk-off` is a candidate for avoidable drops.
- The linear interaction term is not guaranteed to be stable across definitions, so the article should emphasize conditional filtering and sample-size caveats.
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel, metadata = build_panel()
    group_table, regression_table, contrast_table, period_table = run_experiment(panel)

    panel.to_csv(OUTPUT_DIR / "interaction_feature_panel.csv")
    group_table.to_csv(OUTPUT_DIR / "interaction_group_stats.csv", index=False)
    regression_table.to_csv(OUTPUT_DIR / "interaction_regression_coefficients.csv", index=False)
    contrast_table.to_csv(OUTPUT_DIR / "interaction_contrasts.csv", index=False)
    period_table.to_csv(OUTPUT_DIR / "interaction_period_stability.csv", index=False)
    generate_figures(group_table, regression_table, contrast_table)
    (OUTPUT_DIR / "interaction_model_report.md").write_text(
        make_report(metadata, group_table, regression_table, contrast_table, period_table),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_DIR / 'interaction_feature_panel.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'interaction_group_stats.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'interaction_regression_coefficients.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'interaction_contrasts.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'interaction_period_stability.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'interaction_model_report.md'}")


if __name__ == "__main__":
    main()
