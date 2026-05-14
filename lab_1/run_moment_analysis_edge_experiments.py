#!/usr/bin/env python3
"""Generate article-ready moment-analysis experiment tables and figures.

The input files are tab-separated 240-minute OHLCV CSVs with no header:

    timestamp, open, high, low, close, volume

The analysis intentionally uses close-to-close log returns for edge discovery.
It is not a trade backtest. A small next-open path-risk table is included only
to quantify the practical caveat raised in the article outline.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PAIR_FILES = {
    "USDJPY": "USDJPY240.csv",
    "EURUSD": "EURUSD240.csv",
    "AUDJPY": "AUDJPY240.csv",
}

COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
HORIZONS = [1, 3, 6, 12]
HORIZON_HOURS = {1: 4, 3: 12, 6: 24, 12: 48}
SHOCK_LEVELS = [
    ("5pct", 0.05),
    ("2_5pct", 0.025),
    ("1pct", 0.01),
]
VOL_LABELS = {
    1: "Q1_low",
    2: "Q2_lower",
    3: "Q3_mid",
    4: "Q4_higher",
    5: "Q5_high",
}


def safe_t_stat(values: pd.Series) -> float:
    x = values.dropna().astype(float)
    if len(x) < 2:
        return math.nan
    std = x.std(ddof=1)
    if std == 0 or pd.isna(std):
        return math.nan
    return float(x.mean() / (std / math.sqrt(len(x))))


def rate_pct(mask: pd.Series) -> float:
    x = mask.dropna()
    if len(x) == 0:
        return math.nan
    return float(x.mean() * 100.0)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_pair_csv(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_csv(path, sep="\t", names=COLUMNS, header=None)
    profile = {
        "source_file": path.name,
        "raw_rows": len(raw),
    }

    df = raw.copy()
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], format="%Y-%m-%d %H:%M", errors="coerce"
    )
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    profile["duplicate_timestamps"] = int(df["timestamp"].duplicated().sum())
    profile["missing_timestamp_rows"] = int(df["timestamp"].isna().sum())
    profile["missing_ohlc_rows"] = int(
        df[["open", "high", "low", "close"]].isna().any(axis=1).sum()
    )

    df = (
        df.dropna(subset=["timestamp", "open", "high", "low", "close"])
        .drop_duplicates(subset=["timestamp"], keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    profile["clean_rows"] = len(df)
    profile["first_timestamp"] = df["timestamp"].min()
    profile["last_timestamp"] = df["timestamp"].max()
    return df, profile


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["log_return_pct"] = np.log(out["close"] / out["close"].shift(1)) * 100.0
    out["abs_log_return_pct"] = out["log_return_pct"].abs()
    out["vol20_pct"] = out["log_return_pct"].rolling(20, min_periods=20).std()
    out["year"] = out["timestamp"].dt.year

    valid_vol = out["vol20_pct"].dropna()
    if len(valid_vol) > 0:
        codes = pd.qcut(valid_vol, q=5, labels=False, duplicates="drop")
        out.loc[valid_vol.index, "vol_bucket"] = codes.astype("float") + 1.0
        out["vol_bucket"] = out["vol_bucket"].astype("Int64")
        out["vol_regime"] = out["vol_bucket"].map(VOL_LABELS)
    else:
        out["vol_bucket"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        out["vol_regime"] = pd.NA

    for horizon in HORIZONS:
        out[f"future_return_{horizon}_pct"] = (
            np.log(out["close"].shift(-horizon) / out["close"]) * 100.0
        )

        forward_lows = pd.concat(
            [out["low"].shift(-i) for i in range(1, horizon + 1)], axis=1
        )
        forward_highs = pd.concat(
            [out["high"].shift(-i) for i in range(1, horizon + 1)], axis=1
        )
        out[f"entry_open_1"] = out["open"].shift(-1)
        out[f"exit_close_{horizon}"] = out["close"].shift(-horizon)
        out[f"forward_low_{horizon}"] = forward_lows.min(axis=1)
        out[f"forward_high_{horizon}"] = forward_highs.max(axis=1)
        out[f"next_open_long_return_{horizon}_pct"] = (
            np.log(out[f"exit_close_{horizon}"] / out["entry_open_1"]) * 100.0
        )
        out[f"next_open_long_mae_{horizon}_pct"] = (
            np.log(out[f"forward_low_{horizon}"] / out["entry_open_1"]) * 100.0
        )
        out[f"next_open_long_mfe_{horizon}_pct"] = (
            np.log(out[f"forward_high_{horizon}"] / out["entry_open_1"]) * 100.0
        )
    return out


def build_moment_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for pair, df in frames.items():
        r = df["log_return_pct"].dropna()
        rows.append(
            {
                "pair": pair,
                "return_count": int(len(r)),
                "mean_pct": r.mean(),
                "median_pct": r.median(),
                "variance_pct2": r.var(ddof=1),
                "std_pct": r.std(ddof=1),
                "skew": r.skew(),
                "excess_kurtosis": r.kurt(),
                "max_pct": r.max(),
                "min_pct": r.min(),
            }
        )
    return pd.DataFrame(rows)


def build_direction_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    conditions = [
        ("up_bar", lambda s: s > 0.0, 1),
        ("down_bar", lambda s: s < 0.0, -1),
    ]
    for pair, df in frames.items():
        for direction, predicate, sign in conditions:
            condition = predicate(df["log_return_pct"])
            for horizon in HORIZONS:
                future_col = f"future_return_{horizon}_pct"
                subset = df.loc[condition, ["log_return_pct", future_col]].dropna()
                future = subset[future_col]
                continuation = (future * sign) > 0.0
                rows.append(
                    {
                        "pair": pair,
                        "current_direction": direction,
                        "horizon_bars": horizon,
                        "horizon_hours": HORIZON_HOURS[horizon],
                        "count": int(len(subset)),
                        "current_return_mean_pct": subset["log_return_pct"].mean(),
                        "future_return_mean_pct": future.mean(),
                        "future_return_median_pct": future.median(),
                        "future_return_std_pct": future.std(ddof=1),
                        "future_return_t_stat": safe_t_stat(future),
                        "continuation_rate_pct": rate_pct(continuation),
                    }
                )
    return pd.DataFrame(rows)


def shock_condition(
    df: pd.DataFrame, tail: str, q: float
) -> tuple[pd.Series, float, str]:
    if tail == "upper":
        threshold = df["log_return_pct"].quantile(1.0 - q)
        return df["log_return_pct"] >= threshold, float(threshold), f"upper_{q:g}"
    if tail == "lower":
        threshold = df["log_return_pct"].quantile(q)
        return df["log_return_pct"] <= threshold, float(threshold), f"lower_{q:g}"
    raise ValueError(f"unknown tail: {tail}")


def build_shock_mr_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for pair, df in frames.items():
        for level_label, q in SHOCK_LEVELS:
            for tail in ["upper", "lower"]:
                condition, threshold, _ = shock_condition(df, tail, q)
                direction = -1.0 if tail == "upper" else 1.0
                for horizon in HORIZONS:
                    future_col = f"future_return_{horizon}_pct"
                    subset = df.loc[condition, ["log_return_pct", future_col]].dropna()
                    future = subset[future_col]
                    mr = future * direction
                    rows.append(
                        {
                            "pair": pair,
                            "shock_side": tail,
                            "shock_level": level_label,
                            "shock_quantile": q,
                            "threshold_pct": threshold,
                            "horizon_bars": horizon,
                            "horizon_hours": HORIZON_HOURS[horizon],
                            "count": int(len(subset)),
                            "current_return_mean_pct": subset[
                                "log_return_pct"
                            ].mean(),
                            "future_return_mean_pct": future.mean(),
                            "mr_return_mean_pct": mr.mean(),
                            "mr_return_median_pct": mr.median(),
                            "mr_return_std_pct": mr.std(ddof=1),
                            "mr_return_t_stat": safe_t_stat(mr),
                            "mr_win_rate_pct": rate_pct(mr > 0.0),
                        }
                    )
    return pd.DataFrame(rows)


def build_vol_regime_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for pair, df in frames.items():
        for regime in VOL_LABELS.values():
            regime_mask = df["vol_regime"] == regime
            for horizon in HORIZONS:
                future_col = f"future_return_{horizon}_pct"
                subset = df.loc[
                    regime_mask,
                    ["vol20_pct", "abs_log_return_pct", future_col],
                ].dropna()
                future = subset[future_col]
                rows.append(
                    {
                        "pair": pair,
                        "vol_regime": regime,
                        "horizon_bars": horizon,
                        "horizon_hours": HORIZON_HOURS[horizon],
                        "count": int(len(subset)),
                        "vol20_mean_pct": subset["vol20_pct"].mean(),
                        "current_abs_return_mean_pct": subset[
                            "abs_log_return_pct"
                        ].mean(),
                        "future_return_mean_pct": future.mean(),
                        "future_abs_return_mean_pct": future.abs().mean(),
                        "future_return_up_rate_pct": rate_pct(future > 0.0),
                    }
                )
    return pd.DataFrame(rows)


def build_shock_mr_by_vol_summary(
    frames: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    rows = []
    for pair, df in frames.items():
        for level_label, q in SHOCK_LEVELS:
            for tail in ["upper", "lower"]:
                shock_mask, threshold, _ = shock_condition(df, tail, q)
                direction = -1.0 if tail == "upper" else 1.0
                for regime in VOL_LABELS.values():
                    regime_mask = df["vol_regime"] == regime
                    condition = shock_mask & regime_mask
                    for horizon in HORIZONS:
                        future_col = f"future_return_{horizon}_pct"
                        subset = df.loc[
                            condition, ["log_return_pct", "vol20_pct", future_col]
                        ].dropna()
                        future = subset[future_col]
                        mr = future * direction
                        rows.append(
                            {
                                "pair": pair,
                                "vol_regime": regime,
                                "shock_side": tail,
                                "shock_level": level_label,
                                "shock_quantile": q,
                                "threshold_pct": threshold,
                                "horizon_bars": horizon,
                                "horizon_hours": HORIZON_HOURS[horizon],
                                "count": int(len(subset)),
                                "vol20_mean_pct": subset["vol20_pct"].mean(),
                                "current_return_mean_pct": subset[
                                    "log_return_pct"
                                ].mean(),
                                "future_return_mean_pct": future.mean(),
                                "mr_return_mean_pct": mr.mean(),
                                "mr_return_median_pct": mr.median(),
                                "mr_return_std_pct": mr.std(ddof=1),
                                "mr_return_t_stat": safe_t_stat(mr),
                                "mr_win_rate_pct": rate_pct(mr > 0.0),
                            }
                        )
    return pd.DataFrame(rows)


def build_candidate_summary(
    shock_mr: pd.DataFrame, shock_mr_by_vol: pd.DataFrame
) -> pd.DataFrame:
    rows = []

    def best_from_shock(pair: str, side: str, level: str, label: str) -> None:
        subset = shock_mr[
            (shock_mr["pair"] == pair)
            & (shock_mr["shock_side"] == side)
            & (shock_mr["shock_level"] == level)
        ].copy()
        if subset.empty:
            return
        best = subset.sort_values(
            ["mr_return_mean_pct", "mr_win_rate_pct"], ascending=False
        ).iloc[0]
        rows.append(
            {
                "candidate": label,
                "source_table": "shock_mr_summary.csv",
                "pair": pair,
                "condition": f"{side}_{level}",
                "vol_regime": "all",
                "horizon_bars": int(best["horizon_bars"]),
                "horizon_hours": int(best["horizon_hours"]),
                "count": int(best["count"]),
                "threshold_pct": best["threshold_pct"],
                "mr_return_mean_pct": best["mr_return_mean_pct"],
                "mr_win_rate_pct": best["mr_win_rate_pct"],
                "mr_return_t_stat": best["mr_return_t_stat"],
            }
        )

    best_from_shock("USDJPY", "lower", "5pct", "USDJPY lower-tail long MR")
    best_from_shock("EURUSD", "upper", "1pct", "EURUSD extreme-up short MR")
    best_from_shock("AUDJPY", "lower", "5pct", "AUDJPY lower-tail long MR")
    best_from_shock("AUDJPY", "lower", "1pct", "AUDJPY extreme-down long MR")

    subset = shock_mr_by_vol[
        (shock_mr_by_vol["pair"] == "AUDJPY")
        & (shock_mr_by_vol["shock_side"] == "lower")
        & (shock_mr_by_vol["shock_level"] == "5pct")
        & (shock_mr_by_vol["vol_regime"] == "Q5_high")
    ].copy()
    if not subset.empty:
        target = subset[subset["horizon_bars"] == 6]
        best = target.iloc[0] if not target.empty else subset.iloc[0]
        rows.append(
            {
                "candidate": "AUDJPY Q5 lower-tail long MR",
                "source_table": "shock_mr_by_vol_summary.csv",
                "pair": "AUDJPY",
                "condition": "lower_5pct",
                "vol_regime": "Q5_high",
                "horizon_bars": int(best["horizon_bars"]),
                "horizon_hours": int(best["horizon_hours"]),
                "count": int(best["count"]),
                "threshold_pct": best["threshold_pct"],
                "mr_return_mean_pct": best["mr_return_mean_pct"],
                "mr_win_rate_pct": best["mr_win_rate_pct"],
                "mr_return_t_stat": best["mr_return_t_stat"],
            }
        )

    return pd.DataFrame(rows)


def build_annual_candidate_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pair = "AUDJPY"
    horizon = 6
    df = frames[pair]
    shock_mask, threshold, _ = shock_condition(df, "lower", 0.05)
    condition = shock_mask & (df["vol_regime"] == "Q5_high")
    future_col = f"future_return_{horizon}_pct"
    subset = df.loc[
        condition, ["year", "timestamp", "log_return_pct", "vol20_pct", future_col]
    ].dropna()
    subset["mr_return_pct"] = subset[future_col]
    rows = []
    for year, year_df in subset.groupby("year"):
        mr = year_df["mr_return_pct"]
        rows.append(
            {
                "pair": pair,
                "candidate": "AUDJPY Q5 lower-tail long MR",
                "year": int(year),
                "horizon_bars": horizon,
                "horizon_hours": HORIZON_HOURS[horizon],
                "threshold_pct": threshold,
                "count": int(len(year_df)),
                "current_return_mean_pct": year_df["log_return_pct"].mean(),
                "vol20_mean_pct": year_df["vol20_pct"].mean(),
                "mr_return_mean_pct": mr.mean(),
                "mr_return_median_pct": mr.median(),
                "mr_win_rate_pct": rate_pct(mr > 0.0),
                "mr_return_t_stat": safe_t_stat(mr),
            }
        )
    return pd.DataFrame(rows)


def build_path_risk_summary(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair = "AUDJPY"
    horizon = 6
    df = frames[pair]
    shock_mask, threshold, _ = shock_condition(df, "lower", 0.05)
    conditions = [
        ("AUDJPY lower5 long h6 next-open", shock_mask),
        (
            "AUDJPY Q5 lower5 long h6 next-open",
            shock_mask & (df["vol_regime"] == "Q5_high"),
        ),
    ]

    event_rows = []
    summary_rows = []
    for name, condition in conditions:
        cols = [
            "timestamp",
            "log_return_pct",
            "vol_regime",
            "vol20_pct",
            "entry_open_1",
            f"exit_close_{horizon}",
            f"next_open_long_return_{horizon}_pct",
            f"next_open_long_mae_{horizon}_pct",
            f"next_open_long_mfe_{horizon}_pct",
        ]
        events = df.loc[condition, cols].dropna().copy()
        events.insert(0, "candidate", name)
        events.insert(1, "pair", pair)
        events["horizon_bars"] = horizon
        events["horizon_hours"] = HORIZON_HOURS[horizon]
        events["threshold_pct"] = threshold
        event_rows.append(events)

        returns = events[f"next_open_long_return_{horizon}_pct"]
        mae = events[f"next_open_long_mae_{horizon}_pct"]
        mfe = events[f"next_open_long_mfe_{horizon}_pct"]
        summary_rows.append(
            {
                "candidate": name,
                "pair": pair,
                "horizon_bars": horizon,
                "horizon_hours": HORIZON_HOURS[horizon],
                "threshold_pct": threshold,
                "count": int(len(events)),
                "next_open_return_mean_pct": returns.mean(),
                "next_open_return_median_pct": returns.median(),
                "next_open_win_rate_pct": rate_pct(returns > 0.0),
                "mae_mean_pct": mae.mean(),
                "mae_5pct_pct": mae.quantile(0.05),
                "mfe_mean_pct": mfe.mean(),
                "mfe_95pct_pct": mfe.quantile(0.95),
            }
        )

    all_events = pd.concat(event_rows, ignore_index=True)
    return pd.DataFrame(summary_rows), all_events


def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, float_format="%.10f")


def plot_moment_bars(moment: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    metrics = [
        ("std_pct", "Std dev of 4H log returns (%)"),
        ("skew", "Skewness"),
        ("excess_kurtosis", "Excess kurtosis"),
    ]
    colors = ["#4c78a8", "#f58518", "#54a24b"]
    for ax, (metric, title), color in zip(axes, metrics, colors):
        ax.bar(moment["pair"], moment[metric], color=color)
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
    fig.savefig(fig_dir / "fig_01_moment_std_skew_kurtosis.png", dpi=dpi)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    x = np.arange(len(moment))
    width = 0.35
    ax.bar(x - width / 2, moment["max_pct"], width, label="Max", color="#4c78a8")
    ax.bar(x + width / 2, moment["min_pct"], width, label="Min", color="#e45756")
    ax.axhline(0.0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(moment["pair"])
    ax.set_title("Observed extreme 4H log returns (%)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(fig_dir / "fig_02_extreme_returns.png", dpi=dpi)
    plt.close(fig)


def plot_return_distributions(
    frames: dict[str, pd.DataFrame], fig_dir: Path, dpi: int
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for ax, (pair, df) in zip(axes, frames.items()):
        r = df["log_return_pct"].dropna()
        lo, hi = r.quantile([0.005, 0.995])
        ax.hist(r.clip(lo, hi), bins=80, color="#4c78a8", alpha=0.85)
        ax.axvline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(f"{pair} return distribution")
        ax.set_xlabel("4H log return (%)")
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.25)
    fig.savefig(fig_dir / "fig_03_return_distribution_histograms.png", dpi=dpi)
    plt.close(fig)


def plot_direction_summary(
    direction: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True, constrained_layout=True)
    colors = {"up_bar": "#4c78a8", "down_bar": "#e45756"}
    for ax, pair in zip(axes, PAIR_FILES.keys()):
        pair_df = direction[direction["pair"] == pair]
        for current_direction, part in pair_df.groupby("current_direction"):
            part = part.sort_values("horizon_bars")
            ax.plot(
                part["horizon_bars"],
                part["future_return_mean_pct"],
                marker="o",
                label=current_direction,
                color=colors[current_direction],
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(pair)
        ax.set_xlabel("Future horizon (bars)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Mean future log return (%)")
    axes[-1].legend(loc="best")
    fig.savefig(fig_dir / "fig_04_direction_future_returns.png", dpi=dpi)
    plt.close(fig)


def plot_shock_mr_summary(shock_mr: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True, constrained_layout=True)
    colors = {
        ("lower", "5pct"): "#4c78a8",
        ("lower", "1pct"): "#72b7b2",
        ("upper", "5pct"): "#e45756",
        ("upper", "1pct"): "#f58518",
    }
    for ax, pair in zip(axes, PAIR_FILES.keys()):
        pair_df = shock_mr[
            (shock_mr["pair"] == pair)
            & (shock_mr["shock_level"].isin(["5pct", "1pct"]))
        ]
        for (side, level), part in pair_df.groupby(["shock_side", "shock_level"]):
            part = part.sort_values("horizon_bars")
            ax.plot(
                part["horizon_bars"],
                part["mr_return_mean_pct"],
                marker="o",
                label=f"{side} {level}",
                color=colors[(side, level)],
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(pair)
        ax.set_xlabel("Future horizon (bars)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Mean reversion return (%)")
    axes[-1].legend(loc="best", fontsize=8)
    fig.savefig(fig_dir / "fig_05_shock_mean_reversion_by_horizon.png", dpi=dpi)
    plt.close(fig)


def plot_vol_abs_returns(vol_summary: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    data = vol_summary[vol_summary["horizon_bars"] == 6].copy()
    fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    x = np.arange(len(VOL_LABELS))
    width = 0.24
    regimes = list(VOL_LABELS.values())
    offsets = [-width, 0.0, width]
    colors = ["#4c78a8", "#f58518", "#54a24b"]
    for offset, pair, color in zip(offsets, PAIR_FILES.keys(), colors):
        part = data[data["pair"] == pair].set_index("vol_regime").reindex(regimes)
        ax.bar(
            x + offset,
            part["future_abs_return_mean_pct"],
            width,
            label=pair,
            color=color,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(["Q1", "Q2", "Q3", "Q4", "Q5"])
    ax.set_title("Mean absolute 24H future return by vol regime")
    ax.set_ylabel("Mean abs future return (%)")
    ax.set_xlabel("vol20 quintile")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.savefig(fig_dir / "fig_06_vol_regime_future_abs_return_h6.png", dpi=dpi)
    plt.close(fig)


def plot_audjpy_q5_lower5(
    shock_mr_by_vol: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    data = shock_mr_by_vol[
        (shock_mr_by_vol["pair"] == "AUDJPY")
        & (shock_mr_by_vol["shock_side"] == "lower")
        & (shock_mr_by_vol["shock_level"] == "5pct")
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), constrained_layout=True)
    colors = ["#4c78a8", "#72b7b2", "#54a24b", "#f58518", "#e45756"]
    for color, regime in zip(colors, VOL_LABELS.values()):
        part = data[data["vol_regime"] == regime].sort_values("horizon_bars")
        axes[0].plot(
            part["horizon_bars"],
            part["mr_return_mean_pct"],
            marker="o",
            label=regime,
            color=color,
        )
    axes[0].axhline(0.0, color="#333333", linewidth=0.8)
    axes[0].set_title("AUDJPY lower 5% MR by vol regime")
    axes[0].set_xlabel("Future horizon (bars)")
    axes[0].set_ylabel("Mean MR return (%)")
    axes[0].grid(alpha=0.3)
    axes[0].legend(fontsize=8)

    h6 = data[data["horizon_bars"] == 6].set_index("vol_regime").reindex(VOL_LABELS.values())
    axes[1].bar(
        ["Q1", "Q2", "Q3", "Q4", "Q5"],
        h6["mr_win_rate_pct"],
        color=colors,
    )
    axes[1].axhline(50.0, color="#333333", linewidth=0.8)
    axes[1].set_ylim(0, max(65, h6["mr_win_rate_pct"].max() + 5))
    axes[1].set_title("AUDJPY lower 5% MR win rate at 24H")
    axes[1].set_xlabel("vol20 quintile")
    axes[1].set_ylabel("Win rate (%)")
    axes[1].grid(axis="y", alpha=0.3)
    fig.savefig(fig_dir / "fig_07_audjpy_lower5_mr_by_vol.png", dpi=dpi)
    plt.close(fig)


def plot_annual_candidate(
    annual: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 4.5), constrained_layout=True)
    annual = annual.sort_values("year")
    ax1.bar(
        annual["year"].astype(str),
        annual["mr_return_mean_pct"],
        color="#4c78a8",
        label="Mean MR return",
    )
    ax1.axhline(0.0, color="#333333", linewidth=0.8)
    ax1.set_ylabel("Mean MR return (%)")
    ax1.set_xlabel("Year")
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(axis="y", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(
        annual["year"].astype(str),
        annual["mr_win_rate_pct"],
        color="#e45756",
        marker="o",
        label="Win rate",
    )
    ax2.axhline(50.0, color="#e45756", linewidth=0.8, linestyle="--", alpha=0.6)
    ax2.set_ylabel("Win rate (%)")
    ax2.set_ylim(0, max(70, annual["mr_win_rate_pct"].max() + 5))
    fig.suptitle("AUDJPY Q5 lower 5% long MR at 24H by year")
    fig.savefig(fig_dir / "fig_08_audjpy_q5_lower5_annual.png", dpi=dpi)
    plt.close(fig)


def write_markdown_summary(
    output_dir: Path,
    analysis_start: pd.Timestamp,
    analysis_end: pd.Timestamp,
    requested_start: pd.Timestamp | None,
    requested_end: pd.Timestamp | None,
    profile: pd.DataFrame,
    moment: pd.DataFrame,
    candidate: pd.DataFrame,
    path_risk: pd.DataFrame,
) -> None:
    requested_start_text = (
        f"{requested_start:%Y-%m-%d %H:%M}" if requested_start is not None else "none"
    )
    requested_end_text = (
        f"{requested_end:%Y-%m-%d %H:%M}" if requested_end is not None else "none"
    )
    lines = [
        "# Moment Analysis Edge Experiments",
        "",
        f"- Requested period: start={requested_start_text}, end={requested_end_text}",
        f"- Analysis period: {analysis_start:%Y-%m-%d %H:%M} to {analysis_end:%Y-%m-%d %H:%M}",
        "- Return definition: close-to-close log return in percent.",
        "- Screening horizons: 1, 3, 6, and 12 bars on 240-minute data.",
        "- Caveat: these are edge-discovery statistics, not net trade backtests.",
        "",
        "## Data Profile",
        "",
        profile.to_markdown(index=False),
        "",
        "## Moment Summary",
        "",
        moment.round(6).to_markdown(index=False),
        "",
        "## Article Candidate Summary",
        "",
        candidate.round(6).to_markdown(index=False),
        "",
        "## Next-open Path-risk Check",
        "",
        path_risk.round(6).to_markdown(index=False),
        "",
        "## Main Figures",
        "",
        "- fig_01_moment_std_skew_kurtosis.png",
        "- fig_02_extreme_returns.png",
        "- fig_03_return_distribution_histograms.png",
        "- fig_04_direction_future_returns.png",
        "- fig_05_shock_mean_reversion_by_horizon.png",
        "- fig_06_vol_regime_future_abs_return_h6.png",
        "- fig_07_audjpy_lower5_mr_by_vol.png",
        "- fig_08_audjpy_q5_lower5_annual.png",
        "",
    ]
    (output_dir / "article_experiment_summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def parse_optional_timestamp(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    return pd.Timestamp(value)


def run(
    data_dir: Path,
    output_dir: Path,
    dpi: int,
    requested_start: pd.Timestamp | None,
    requested_end: pd.Timestamp | None,
) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")

    raw_frames: dict[str, pd.DataFrame] = {}
    profile_rows = []
    for pair, file_name in PAIR_FILES.items():
        df, profile = read_pair_csv(data_dir / file_name)
        profile["pair"] = pair
        raw_frames[pair] = df
        profile_rows.append(profile)

    period_start = max(df["timestamp"].min() for df in raw_frames.values())
    period_end = min(df["timestamp"].max() for df in raw_frames.values())
    if requested_start is not None:
        period_start = max(period_start, requested_start)
    if requested_end is not None:
        period_end = min(period_end, requested_end)
    if period_start >= period_end:
        raise ValueError(
            f"empty analysis period after filtering: start={period_start}, end={period_end}"
        )

    frames = {}
    for pair, df in raw_frames.items():
        common = df[
            (df["timestamp"] >= period_start) & (df["timestamp"] <= period_end)
        ].reset_index(drop=True)
        if common.empty:
            raise ValueError(f"{pair} has no rows in requested period")
        frames[pair] = add_features(common)

    analysis_start = max(df["timestamp"].min() for df in frames.values())
    analysis_end = min(df["timestamp"].max() for df in frames.values())

    profile_df = pd.DataFrame(profile_rows)
    profile_df.insert(1, "requested_start", requested_start)
    profile_df.insert(2, "requested_end", requested_end)
    profile_df.insert(3, "analysis_start", analysis_start)
    profile_df.insert(4, "analysis_end", analysis_end)
    profile_df["common_rows"] = [
        int(len(frames[pair])) for pair in profile_df["pair"].tolist()
    ]

    moment = build_moment_summary(frames)
    direction = build_direction_summary(frames)
    shock_mr = build_shock_mr_summary(frames)
    vol_regime = build_vol_regime_summary(frames)
    shock_mr_by_vol = build_shock_mr_by_vol_summary(frames)
    candidate = build_candidate_summary(shock_mr, shock_mr_by_vol)
    annual_candidate = build_annual_candidate_summary(frames)
    path_risk, path_events = build_path_risk_summary(frames)

    save_csv(profile_df, output_dir / "data_profile.csv")
    save_csv(moment, output_dir / "moment_summary.csv")
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(vol_regime, output_dir / "vol_regime_summary.csv")
    save_csv(shock_mr_by_vol, output_dir / "shock_mean_reversion_by_vol_summary.csv")
    save_csv(candidate, output_dir / "edge_candidate_summary.csv")
    save_csv(annual_candidate, output_dir / "annual_audjpy_q5_lower5_h6.csv")
    save_csv(path_risk, output_dir / "audjpy_path_risk_summary.csv")
    save_csv(path_events, output_dir / "audjpy_path_risk_events.csv")

    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    plot_vol_abs_returns(vol_regime, fig_dir, dpi)
    plot_audjpy_q5_lower5(shock_mr_by_vol, fig_dir, dpi)
    plot_annual_candidate(annual_candidate, fig_dir, dpi)

    write_markdown_summary(
        output_dir,
        analysis_start,
        analysis_end,
        requested_start,
        requested_end,
        profile_df,
        moment,
        candidate,
        path_risk,
    )

    print(f"Analysis period: {analysis_start:%Y-%m-%d %H:%M} to {analysis_end:%Y-%m-%d %H:%M}")
    print(f"Wrote outputs to: {output_dir}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the 240-minute FX moment-analysis article experiments."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing USDJPY240.csv, EURUSD240.csv, and AUDJPY240.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "moment_analysis_outputs_2022plus",
        help="Directory for generated CSV tables and figures.",
    )
    parser.add_argument(
        "--start-date",
        default="2022-01-01",
        help="Inclusive analysis start timestamp. Use an empty string for no start filter.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Inclusive analysis end timestamp. Defaults to the common data end.",
    )
    parser.add_argument("--dpi", type=int, default=180, help="Figure DPI.")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    start_date = args.start_date.strip() if args.start_date is not None else None
    requested_start = parse_optional_timestamp(start_date or None)
    requested_end = parse_optional_timestamp(args.end_date)
    run(args.data_dir, args.output_dir, args.dpi, requested_start, requested_end)


if __name__ == "__main__":
    main()
