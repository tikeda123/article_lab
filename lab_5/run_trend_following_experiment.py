#!/usr/bin/env python3
"""Run the lab_5 USDJPY trend-following experiment.

The experiment intentionally stays simple:
- MA cross trend following
- close-confirmed signals
- next-open execution
- fixed round-trip pip costs
- no WFO and no OOS re-optimization
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


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_60M = SCRIPT_DIR / "USDJPY60.csv"
DEFAULT_INPUT_240M = SCRIPT_DIR / "USDJPY240.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs" / "trend_following_ma_cross"

COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]
PIP_MULTIPLIER = 100.0
PRIMARY_COST_PIPS = 1.0
PRIMARY_SHORT_WINDOW = 20
PRIMARY_LONG_WINDOW = 80
PARAM_SHORT_WINDOWS = [10, 20, 30, 40, 60]
PARAM_LONG_WINDOWS = [60, 80, 120, 160, 200]
ENTRY_DELAYS = [0, 1, 2, 4]
TOP_EXCLUSION_PCTS = [1, 5, 10]

TRADE_COLUMNS = [
    "timeframe",
    "period",
    "entry_time",
    "exit_time",
    "direction",
    "entry_price",
    "exit_price",
    "gross_pnl_pips",
    "cost_pips",
    "net_pnl_pips",
    "holding_bars",
    "short_window",
    "long_window",
    "entry_delay_bars",
    "exit_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the lab_5 USDJPY MA-cross trend-following experiment.",
    )
    parser.add_argument("--input-60m", type=Path, default=DEFAULT_INPUT_60M)
    parser.add_argument("--input-240m", type=Path, default=DEFAULT_INPUT_240M)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-01-01")
    parser.add_argument("--dev-end", default="2025-01-01")
    parser.add_argument("--short-window", type=int, default=PRIMARY_SHORT_WINDOW)
    parser.add_argument("--long-window", type=int, default=PRIMARY_LONG_WINDOW)
    parser.add_argument(
        "--costs",
        type=float,
        nargs="+",
        default=[0.0, 0.8, 1.0, 2.0],
        help="Round-trip costs in pips.",
    )
    parser.add_argument("--random-runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument(
        "--stage",
        choices=["audit", "baseline", "robustness", "oos", "all"],
        default="all",
        help="Run only a subset of the full experiment.",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_price_csv(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_csv(path, sep="\t", header=None, names=COLUMNS)
    profile: dict[str, object] = {
        "source_file": str(path),
        "raw_rows": int(len(raw)),
    }

    df = raw.copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    profile["missing_timestamp_rows"] = int(df["datetime"].isna().sum())
    profile["missing_ohlc_rows"] = int(
        df[["open", "high", "low", "close"]].isna().any(axis=1).sum()
    )
    profile["duplicate_timestamps"] = int(df["datetime"].duplicated().sum())

    invalid_ohlc = (
        (df["high"] < df[["open", "close"]].max(axis=1))
        | (df["low"] > df[["open", "close"]].min(axis=1))
        | (df["high"] < df["low"])
    )
    profile["invalid_ohlc_rows"] = int(invalid_ohlc.fillna(False).sum())

    df = (
        df.dropna(subset=["datetime", "open", "high", "low", "close"])
        .drop_duplicates(subset=["datetime"], keep="last")
        .sort_values("datetime")
        .reset_index(drop=True)
    )
    profile["clean_rows"] = int(len(df))
    profile["first_timestamp"] = df["datetime"].min()
    profile["last_timestamp"] = df["datetime"].max()
    return df, profile


def count_gaps(df: pd.DataFrame, expected_hours: float) -> tuple[int, float]:
    diffs = df["datetime"].diff().dt.total_seconds().div(3600.0)
    gaps = diffs[diffs > expected_hours * 1.5]
    if gaps.empty:
        return 0, 0.0
    return int(len(gaps)), float(gaps.max())


def build_data_audit(
    frames: dict[str, pd.DataFrame],
    profiles: dict[str, dict[str, object]],
    start: pd.Timestamp,
    dev_end: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    rows = []
    expected_hours = {"60m": 1.0, "240m": 4.0}
    for timeframe, df in frames.items():
        gap_count, max_gap_hours = count_gaps(df, expected_hours[timeframe])
        selected = df[(df["datetime"] >= start) & (df["datetime"] < end)]
        dev = df[(df["datetime"] >= start) & (df["datetime"] < dev_end)]
        oos = df[(df["datetime"] >= dev_end) & (df["datetime"] < end)]
        row = {
            "timeframe": timeframe,
            **profiles[timeframe],
            "gaps_count": gap_count,
            "max_gap_hours": max_gap_hours,
            "selected_start": start,
            "selected_end_exclusive": end,
            "selected_rows": int(len(selected)),
            "dev_rows": int(len(dev)),
            "oos_rows": int(len(oos)),
            "note": "Weekend/holiday gaps are counted; no interpolation is applied.",
        }
        rows.append(row)
    return pd.DataFrame(rows)


def add_ma_signal(df: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    out = df.copy()
    out["short_ma"] = out["close"].rolling(short_window, min_periods=short_window).mean()
    out["long_ma"] = out["close"].rolling(long_window, min_periods=long_window).mean()
    out["signal"] = 0
    valid = out["short_ma"].notna() & out["long_ma"].notna()
    out.loc[valid & (out["short_ma"] > out["long_ma"]), "signal"] = 1
    out.loc[valid & (out["short_ma"] < out["long_ma"]), "signal"] = -1
    return out


def empty_trade_log() -> pd.DataFrame:
    return pd.DataFrame(columns=TRADE_COLUMNS)


def simulate_trades(
    df: pd.DataFrame,
    timeframe: str,
    period: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    short_window: int,
    long_window: int,
    round_trip_cost_pips: float,
    entry_delay_bars: int = 0,
) -> pd.DataFrame:
    work = add_ma_signal(df, short_window, long_window)
    active = work[(work["datetime"] >= start) & (work["datetime"] < end)].index.to_numpy()
    if len(active) < 2:
        return empty_trade_log()

    opens = work["open"].to_numpy(dtype=float)
    timestamps = work["datetime"].to_numpy()
    signals = work["signal"].to_numpy(dtype=int)

    rows = []
    pos = 0
    entry_i: int | None = None
    entry_price = math.nan
    entry_time = None

    for j in active[:-1]:
        signal_i = j - 1 - entry_delay_bars
        target = int(signals[signal_i]) if signal_i >= 0 else 0

        if target == pos:
            continue

        if pos != 0 and entry_i is not None:
            rows.append(
                make_trade_row(
                    timeframe=timeframe,
                    period=period,
                    entry_time=entry_time,
                    exit_time=pd.Timestamp(timestamps[j]),
                    direction=pos,
                    entry_price=entry_price,
                    exit_price=float(opens[j]),
                    cost_pips=round_trip_cost_pips,
                    holding_bars=int(j - entry_i),
                    short_window=short_window,
                    long_window=long_window,
                    entry_delay_bars=entry_delay_bars,
                    exit_reason="signal_flip",
                )
            )
            pos = 0
            entry_i = None
            entry_price = math.nan
            entry_time = None

        if target != 0:
            pos = target
            entry_i = int(j)
            entry_price = float(opens[j])
            entry_time = pd.Timestamp(timestamps[j])

    final_i = int(active[-1])
    if pos != 0 and entry_i is not None:
        rows.append(
            make_trade_row(
                timeframe=timeframe,
                period=period,
                entry_time=entry_time,
                exit_time=pd.Timestamp(timestamps[final_i]),
                direction=pos,
                entry_price=entry_price,
                exit_price=float(opens[final_i]),
                cost_pips=round_trip_cost_pips,
                holding_bars=int(final_i - entry_i),
                short_window=short_window,
                long_window=long_window,
                entry_delay_bars=entry_delay_bars,
                exit_reason="period_end",
            )
        )

    if not rows:
        return empty_trade_log()
    return pd.DataFrame(rows, columns=TRADE_COLUMNS)


def make_trade_row(
    *,
    timeframe: str,
    period: str,
    entry_time: pd.Timestamp,
    exit_time: pd.Timestamp,
    direction: int,
    entry_price: float,
    exit_price: float,
    cost_pips: float,
    holding_bars: int,
    short_window: int,
    long_window: int,
    entry_delay_bars: int,
    exit_reason: str,
) -> dict[str, object]:
    gross_pnl_pips = (exit_price - entry_price) * PIP_MULTIPLIER * direction
    net_pnl_pips = gross_pnl_pips - cost_pips
    return {
        "timeframe": timeframe,
        "period": period,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "direction": "long" if direction == 1 else "short",
        "entry_price": entry_price,
        "exit_price": exit_price,
        "gross_pnl_pips": gross_pnl_pips,
        "cost_pips": cost_pips,
        "net_pnl_pips": net_pnl_pips,
        "holding_bars": holding_bars,
        "short_window": short_window,
        "long_window": long_window,
        "entry_delay_bars": entry_delay_bars,
        "exit_reason": exit_reason,
    }


def max_drawdown_pips(pnl: pd.Series) -> float:
    if pnl.empty:
        return math.nan
    equity = pnl.cumsum()
    drawdown = equity - equity.cummax()
    return float(-drawdown.min())


def profit_factor(pnl: pd.Series) -> float:
    wins = pnl[pnl > 0.0].sum()
    losses = -pnl[pnl < 0.0].sum()
    if losses == 0.0:
        return math.inf if wins > 0.0 else math.nan
    return float(wins / losses)


def top_win_contribution_pct(pnl: pd.Series, pct: int) -> float:
    wins = pnl[pnl > 0.0].sort_values(ascending=False)
    if wins.empty or wins.sum() == 0.0:
        return math.nan
    n = max(1, int(math.ceil(len(wins) * pct / 100.0)))
    return float(wins.head(n).sum() / wins.sum() * 100.0)


def calculate_metrics(trades: pd.DataFrame) -> dict[str, float | int]:
    if trades.empty:
        return {
            "trade_count": 0,
            "total_pnl_pips": 0.0,
            "win_rate_pct": math.nan,
            "profit_factor": math.nan,
            "max_drawdown_pips": math.nan,
            "avg_win_pips": math.nan,
            "avg_loss_pips": math.nan,
            "avg_win_loss_ratio": math.nan,
            "avg_trade_pips": math.nan,
            "median_trade_pips": math.nan,
            "max_win_pips": math.nan,
            "max_loss_pips": math.nan,
            "pnl_skew": math.nan,
            "avg_holding_bars": math.nan,
            "top_1pct_win_contribution_pct": math.nan,
            "top_5pct_win_contribution_pct": math.nan,
            "top_10pct_win_contribution_pct": math.nan,
        }

    pnl = trades["net_pnl_pips"].astype(float)
    wins = pnl[pnl > 0.0]
    losses = pnl[pnl < 0.0]
    avg_win = float(wins.mean()) if not wins.empty else math.nan
    avg_loss = float(losses.mean()) if not losses.empty else math.nan
    ratio = avg_win / abs(avg_loss) if avg_win == avg_win and avg_loss and avg_loss == avg_loss else math.nan
    return {
        "trade_count": int(len(pnl)),
        "total_pnl_pips": float(pnl.sum()),
        "win_rate_pct": float((pnl > 0.0).mean() * 100.0),
        "profit_factor": profit_factor(pnl),
        "max_drawdown_pips": max_drawdown_pips(pnl),
        "avg_win_pips": avg_win,
        "avg_loss_pips": avg_loss,
        "avg_win_loss_ratio": float(ratio) if ratio == ratio else math.nan,
        "avg_trade_pips": float(pnl.mean()),
        "median_trade_pips": float(pnl.median()),
        "max_win_pips": float(pnl.max()),
        "max_loss_pips": float(pnl.min()),
        "pnl_skew": float(pnl.skew()) if len(pnl) >= 3 else math.nan,
        "avg_holding_bars": float(trades["holding_bars"].mean()),
        "top_1pct_win_contribution_pct": top_win_contribution_pct(pnl, 1),
        "top_5pct_win_contribution_pct": top_win_contribution_pct(pnl, 5),
        "top_10pct_win_contribution_pct": top_win_contribution_pct(pnl, 10),
    }


def metrics_row(
    trades: pd.DataFrame,
    *,
    timeframe: str,
    period: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    short_window: int,
    long_window: int,
    cost_pips: float,
    entry_delay_bars: int,
) -> dict[str, object]:
    return {
        "timeframe": timeframe,
        "period": period,
        "start": start,
        "end_exclusive": end,
        "short_window": short_window,
        "long_window": long_window,
        "cost_pips": cost_pips,
        "entry_delay_bars": entry_delay_bars,
        **calculate_metrics(trades),
    }


def equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["exit_time", "equity_pips", "drawdown_pips"])
    out = trades[["exit_time", "net_pnl_pips"]].copy()
    out["exit_time"] = pd.to_datetime(out["exit_time"])
    out["equity_pips"] = out["net_pnl_pips"].cumsum()
    out["drawdown_pips"] = out["equity_pips"] - out["equity_pips"].cummax()
    return out[["exit_time", "equity_pips", "drawdown_pips"]]


def build_top_trade_exclusion(trades_by_timeframe: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for timeframe, trades in trades_by_timeframe.items():
        if trades.empty:
            continue
        pnl = trades["net_pnl_pips"].astype(float)
        rows.append(
            {
                "timeframe": timeframe,
                "excluded_top_win_pct": 0,
                "excluded_trade_count": 0,
                **calculate_metrics(trades),
            }
        )
        wins = pnl[pnl > 0.0].sort_values(ascending=False)
        for pct in TOP_EXCLUSION_PCTS:
            n = max(1, int(math.ceil(len(wins) * pct / 100.0))) if not wins.empty else 0
            drop_index = wins.head(n).index
            remaining = trades.drop(index=drop_index).reset_index(drop=True)
            rows.append(
                {
                    "timeframe": timeframe,
                    "excluded_top_win_pct": pct,
                    "excluded_trade_count": int(n),
                    **calculate_metrics(remaining),
                }
            )
    return pd.DataFrame(rows)


def build_direction_breakdown(
    trades_by_timeframe: dict[str, pd.DataFrame],
    dev_end: pd.Timestamp,
) -> pd.DataFrame:
    rows = []
    for timeframe, trades in trades_by_timeframe.items():
        if trades.empty:
            continue
        work = trades.copy()
        work["entry_time"] = pd.to_datetime(work["entry_time"])
        periods = {
            "full_2023_2025": work,
            "dev_2023_2024": work[work["entry_time"] < dev_end],
            "oos_2025": work[work["entry_time"] >= dev_end],
        }
        for period, period_trades in periods.items():
            for direction in ["long", "short"]:
                subset = period_trades[period_trades["direction"] == direction]
                rows.append(
                    {
                        "timeframe": timeframe,
                        "period": period,
                        "direction": direction,
                        **calculate_metrics(subset),
                    }
                )
    return pd.DataFrame(rows)


def calculate_metrics_from_pnl(pnl: np.ndarray) -> dict[str, float | int]:
    series = pd.Series(pnl, dtype=float)
    return {
        "trade_count": int(len(series)),
        "total_pnl_pips": float(series.sum()),
        "win_rate_pct": float((series > 0.0).mean() * 100.0) if len(series) else math.nan,
        "profit_factor": profit_factor(series),
        "max_drawdown_pips": max_drawdown_pips(series),
        "avg_trade_pips": float(series.mean()) if len(series) else math.nan,
        "pnl_skew": float(series.skew()) if len(series) >= 3 else math.nan,
    }


def build_random_direction_comparison(
    trades_by_timeframe: dict[str, pd.DataFrame],
    random_runs: int,
    seed: int,
) -> pd.DataFrame:
    records = []
    rng = np.random.default_rng(seed)
    for timeframe, trades in trades_by_timeframe.items():
        if trades.empty:
            continue
        entry = trades["entry_price"].to_numpy(dtype=float)
        exit_ = trades["exit_price"].to_numpy(dtype=float)
        cost = trades["cost_pips"].to_numpy(dtype=float)
        price_diff_pips = (exit_ - entry) * PIP_MULTIPLIER
        actual_metrics = calculate_metrics(trades)

        random_rows = []
        for run_id in range(random_runs):
            directions = rng.choice(np.array([-1.0, 1.0]), size=len(trades))
            pnl = price_diff_pips * directions - cost
            row = {
                "timeframe": timeframe,
                "variant": "random_direction",
                "run_id": run_id,
                **calculate_metrics_from_pnl(pnl),
            }
            random_rows.append(row)

        random_df = pd.DataFrame(random_rows)
        actual_total = float(actual_metrics["total_pnl_pips"])
        actual_pf = float(actual_metrics["profit_factor"])
        total_pctile = float((random_df["total_pnl_pips"] <= actual_total).mean() * 100.0)
        finite_pf = random_df["profit_factor"].replace([np.inf, -np.inf], np.nan).dropna()
        pf_pctile = (
            float((finite_pf <= actual_pf).mean() * 100.0)
            if len(finite_pf) and math.isfinite(actual_pf)
            else math.nan
        )

        for row in random_rows:
            row["actual_total_pnl_pips"] = actual_total
            row["actual_profit_factor"] = actual_pf
            row["actual_total_pnl_percentile"] = total_pctile
            row["actual_profit_factor_percentile"] = pf_pctile
            records.append(row)

        records.append(
            {
                "timeframe": timeframe,
                "variant": "actual",
                "run_id": -1,
                **actual_metrics,
                "actual_total_pnl_pips": actual_total,
                "actual_profit_factor": actual_pf,
                "actual_total_pnl_percentile": total_pctile,
                "actual_profit_factor_percentile": pf_pctile,
            }
        )
    return pd.DataFrame(records)


def build_parameter_heatmap(
    frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_pips: float,
) -> pd.DataFrame:
    rows = []
    for timeframe, df in frames.items():
        for short_window in PARAM_SHORT_WINDOWS:
            for long_window in PARAM_LONG_WINDOWS:
                if short_window >= long_window:
                    continue
                trades = simulate_trades(
                    df,
                    timeframe=timeframe,
                    period="full_2023_2025",
                    start=start,
                    end=end,
                    short_window=short_window,
                    long_window=long_window,
                    round_trip_cost_pips=cost_pips,
                    entry_delay_bars=0,
                )
                rows.append(
                    metrics_row(
                        trades,
                        timeframe=timeframe,
                        period="full_2023_2025",
                        start=start,
                        end=end,
                        short_window=short_window,
                        long_window=long_window,
                        cost_pips=cost_pips,
                        entry_delay_bars=0,
                    )
                )
    return pd.DataFrame(rows)


def build_entry_delay_sensitivity(
    frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    short_window: int,
    long_window: int,
    cost_pips: float,
) -> pd.DataFrame:
    rows = []
    for timeframe, df in frames.items():
        for delay in ENTRY_DELAYS:
            trades = simulate_trades(
                df,
                timeframe=timeframe,
                period="full_2023_2025",
                start=start,
                end=end,
                short_window=short_window,
                long_window=long_window,
                round_trip_cost_pips=cost_pips,
                entry_delay_bars=delay,
            )
            rows.append(
                metrics_row(
                    trades,
                    timeframe=timeframe,
                    period="full_2023_2025",
                    start=start,
                    end=end,
                    short_window=short_window,
                    long_window=long_window,
                    cost_pips=cost_pips,
                    entry_delay_bars=delay,
                )
            )
    return pd.DataFrame(rows)


def build_fixed_oos_summary(
    frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    dev_end: pd.Timestamp,
    end: pd.Timestamp,
    short_window: int,
    long_window: int,
    costs: Iterable[float],
) -> pd.DataFrame:
    rows = []
    periods = [
        ("dev_2023_2024", start, dev_end),
        ("oos_2025", dev_end, end),
    ]
    for timeframe, df in frames.items():
        for cost in costs:
            for period, period_start, period_end in periods:
                trades = simulate_trades(
                    df,
                    timeframe=timeframe,
                    period=period,
                    start=period_start,
                    end=period_end,
                    short_window=short_window,
                    long_window=long_window,
                    round_trip_cost_pips=cost,
                    entry_delay_bars=0,
                )
                rows.append(
                    metrics_row(
                        trades,
                        timeframe=timeframe,
                        period=period,
                        start=period_start,
                        end=period_end,
                        short_window=short_window,
                        long_window=long_window,
                        cost_pips=cost,
                        entry_delay_bars=0,
                    )
                )
    return pd.DataFrame(rows)


def save_trade_logs(trades_by_timeframe: dict[str, pd.DataFrame], output_dir: Path) -> None:
    for timeframe, trades in trades_by_timeframe.items():
        trades.to_csv(output_dir / f"trade_log_{timeframe}.csv", index=False)


def finite_for_plot(values: pd.Series) -> pd.Series:
    return values.replace([np.inf, -np.inf], np.nan)


def markdown_table(df: pd.DataFrame, columns: list[str], float_digits: int = 3) -> str:
    if df.empty:
        return ""
    view = df[columns].copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]) or pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: format_markdown_value(x, float_digits))
        else:
            view[col] = view[col].astype(str)

    header = "| " + " | ".join(view.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in view.astype(str).to_numpy()]
    return "\n".join([header, separator, *rows])


def format_markdown_value(value: object, float_digits: int) -> str:
    if pd.isna(value):
        return "nan"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isinf(number):
        return "inf" if number > 0 else "-inf"
    return f"{number:.{float_digits}f}"


def plot_equity_curves(trades_by_timeframe: dict[str, pd.DataFrame], figures_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for timeframe, trades in trades_by_timeframe.items():
        eq = equity_curve(trades)
        if eq.empty:
            continue
        ax.plot(eq["exit_time"], eq["equity_pips"], label=timeframe)
    ax.set_title("MA 20/80 equity curve, cost 1.0 pips")
    ax.set_xlabel("Exit time")
    ax.set_ylabel("Cumulative net pips")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "equity_curve.png", dpi=dpi)
    plt.close(fig)


def plot_drawdowns(trades_by_timeframe: dict[str, pd.DataFrame], figures_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for timeframe, trades in trades_by_timeframe.items():
        eq = equity_curve(trades)
        if eq.empty:
            continue
        ax.plot(eq["exit_time"], eq["drawdown_pips"], label=timeframe)
    ax.set_title("MA 20/80 drawdown, cost 1.0 pips")
    ax.set_xlabel("Exit time")
    ax.set_ylabel("Drawdown pips")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "drawdown_curve.png", dpi=dpi)
    plt.close(fig)


def plot_trade_histograms(trades_by_timeframe: dict[str, pd.DataFrame], figures_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for ax, (timeframe, trades) in zip(axes, trades_by_timeframe.items()):
        pnl = trades["net_pnl_pips"].astype(float) if not trades.empty else pd.Series(dtype=float)
        ax.hist(pnl, bins=40, alpha=0.8)
        ax.axvline(0.0, color="black", linewidth=1.0)
        ax.set_title(f"{timeframe} trade PnL")
        ax.set_xlabel("Net pips")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Trade count")
    fig.tight_layout()
    fig.savefig(figures_dir / "trade_pnl_histogram.png", dpi=dpi)
    plt.close(fig)


def plot_direction_breakdown(direction_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    full = direction_df[direction_df["period"] == "full_2023_2025"].copy()
    if full.empty:
        return

    labels = []
    values = []
    colors = []
    for timeframe in ["60m", "240m"]:
        for direction in ["long", "short"]:
            subset = full[(full["timeframe"] == timeframe) & (full["direction"] == direction)]
            if subset.empty:
                continue
            labels.append(f"{timeframe}\n{direction}")
            values.append(float(subset.iloc[0]["total_pnl_pips"]))
            colors.append("#2f7ed8" if direction == "long" else "#d84a3a")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color=colors)
    ax.axhline(0.0, color="black", linewidth=1.0)
    ax.set_title("Direction PnL breakdown, MA 20/80 cost 1.0 pips")
    ax.set_ylabel("Total net pips")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "direction_pnl_breakdown.png", dpi=dpi)
    plt.close(fig)


def plot_cost_sensitivity(cost_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for timeframe, subset in cost_df.groupby("timeframe"):
        subset = subset.sort_values("cost_pips")
        ax.plot(subset["cost_pips"], subset["total_pnl_pips"], marker="o", label=timeframe)
    ax.set_title("Cost sensitivity")
    ax.set_xlabel("Round-trip cost (pips)")
    ax.set_ylabel("Total net pips")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "cost_sensitivity.png", dpi=dpi)
    plt.close(fig)


def plot_top_trade_exclusion(top_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for timeframe, subset in top_df.groupby("timeframe"):
        subset = subset.sort_values("excluded_top_win_pct")
        ax.plot(
            subset["excluded_top_win_pct"],
            subset["total_pnl_pips"],
            marker="o",
            label=timeframe,
        )
    ax.set_title("Top winning trade exclusion")
    ax.set_xlabel("Excluded top winning trades (%)")
    ax.set_ylabel("Remaining total net pips")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "top_trade_exclusion.png", dpi=dpi)
    plt.close(fig)


def plot_random_comparison(random_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    timeframes = list(random_df["timeframe"].drop_duplicates())
    fig, axes = plt.subplots(1, len(timeframes), figsize=(6 * len(timeframes), 4), squeeze=False)
    for ax, timeframe in zip(axes[0], timeframes):
        subset = random_df[random_df["timeframe"] == timeframe]
        random_rows = subset[subset["variant"] == "random_direction"]
        actual = subset[subset["variant"] == "actual"].iloc[0]
        ax.hist(random_rows["total_pnl_pips"], bins=40, alpha=0.75)
        ax.axvline(actual["total_pnl_pips"], color="red", linewidth=2.0, label="actual")
        pct = actual["actual_total_pnl_percentile"]
        ax.set_title(f"{timeframe} random direction ({pct:.1f} pctile)")
        ax.set_xlabel("Total net pips")
        ax.legend()
        ax.grid(True, alpha=0.3)
    axes[0][0].set_ylabel("Simulation count")
    fig.tight_layout()
    fig.savefig(figures_dir / "random_direction_comparison.png", dpi=dpi)
    plt.close(fig)


def plot_parameter_heatmap(heatmap_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    timeframes = list(heatmap_df["timeframe"].drop_duplicates())
    fig, axes = plt.subplots(1, len(timeframes), figsize=(6 * len(timeframes), 5), squeeze=False)
    for ax, timeframe in zip(axes[0], timeframes):
        subset = heatmap_df[heatmap_df["timeframe"] == timeframe]
        pivot = subset.pivot(index="long_window", columns="short_window", values="profit_factor")
        pivot = pivot.reindex(index=PARAM_LONG_WINDOWS, columns=PARAM_SHORT_WINDOWS)
        data = pivot.replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float)
        masked = np.ma.masked_invalid(data)
        im = ax.imshow(masked, aspect="auto", origin="lower", cmap="viridis")
        ax.set_xticks(range(len(PARAM_SHORT_WINDOWS)), labels=PARAM_SHORT_WINDOWS)
        ax.set_yticks(range(len(PARAM_LONG_WINDOWS)), labels=PARAM_LONG_WINDOWS)
        ax.set_xlabel("Short MA")
        ax.set_ylabel("Long MA")
        ax.set_title(f"{timeframe} PF heatmap")
        for y in range(data.shape[0]):
            for x in range(data.shape[1]):
                value = data[y, x]
                if np.isfinite(value):
                    ax.text(x, y, f"{value:.2f}", ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(figures_dir / "parameter_heatmap_pf.png", dpi=dpi)
    plt.close(fig)


def plot_entry_delay(delay_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for timeframe, subset in delay_df.groupby("timeframe"):
        subset = subset.sort_values("entry_delay_bars")
        ax.plot(
            subset["entry_delay_bars"],
            subset["total_pnl_pips"],
            marker="o",
            label=timeframe,
        )
    ax.set_title("Entry delay sensitivity")
    ax.set_xlabel("Extra delay bars")
    ax.set_ylabel("Total net pips")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "entry_delay_sensitivity.png", dpi=dpi)
    plt.close(fig)


def plot_fixed_oos(oos_df: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    filtered = oos_df[oos_df["cost_pips"].isin([PRIMARY_COST_PIPS])].copy()
    timeframes = list(filtered["timeframe"].drop_duplicates())
    fig, axes = plt.subplots(1, len(timeframes), figsize=(6 * len(timeframes), 4), squeeze=False)
    for ax, timeframe in zip(axes[0], timeframes):
        subset = filtered[filtered["timeframe"] == timeframe]
        ax.bar(subset["period"], subset["total_pnl_pips"])
        ax.set_title(f"{timeframe} fixed OOS, cost 1.0")
        ax.set_ylabel("Total net pips")
        ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "fixed_oos_comparison.png", dpi=dpi)
    plt.close(fig)


def write_article_summary(
    output_dir: Path,
    summary_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    direction_df: pd.DataFrame,
    top_df: pd.DataFrame,
    random_df: pd.DataFrame,
    delay_df: pd.DataFrame,
    oos_df: pd.DataFrame,
) -> None:
    primary = summary_df[
        (summary_df["cost_pips"] == PRIMARY_COST_PIPS)
        & (summary_df["entry_delay_bars"] == 0)
        & (summary_df["short_window"] == PRIMARY_SHORT_WINDOW)
        & (summary_df["long_window"] == PRIMARY_LONG_WINDOW)
    ].copy()

    lines = [
        "# Article Result Summary",
        "",
        "Scope: USDJPY MA cross trend-following experiment.",
        "",
        "- Strategy: MA 20 / 80",
        "- Execution: close-confirmed signal, next-open trade",
        "- Main cost: 1.0 round-trip pips",
        "- Main period: 2023-01-01 <= timestamp < 2026-01-01",
        "- Development period: 2023-2024",
        "- OOS period: 2025",
        "- No WFO and no OOS re-optimization",
        "",
        "## Baseline Metrics",
        "",
    ]

    if not primary.empty:
        cols = [
            "timeframe",
            "trade_count",
            "total_pnl_pips",
            "win_rate_pct",
            "profit_factor",
            "max_drawdown_pips",
            "avg_win_loss_ratio",
            "top_5pct_win_contribution_pct",
        ]
        lines.append(markdown_table(primary, cols))
        lines.append("")

    lines.extend(["## Cost Sensitivity", ""])
    if not cost_df.empty:
        cols = ["timeframe", "cost_pips", "total_pnl_pips", "profit_factor", "max_drawdown_pips"]
        lines.append(markdown_table(cost_df, cols))
        lines.append("")

    lines.extend(["## Direction Breakdown", ""])
    if not direction_df.empty:
        cols = [
            "timeframe",
            "period",
            "direction",
            "trade_count",
            "total_pnl_pips",
            "win_rate_pct",
            "profit_factor",
            "max_drawdown_pips",
        ]
        lines.append(markdown_table(direction_df, cols))
        lines.append("")

    lines.extend(["## Top Winning Trade Exclusion", ""])
    if not top_df.empty:
        cols = ["timeframe", "excluded_top_win_pct", "total_pnl_pips", "profit_factor", "max_drawdown_pips"]
        lines.append(markdown_table(top_df, cols))
        lines.append("")

    lines.extend(["## Random Direction Comparison", ""])
    actual_random = random_df[random_df["variant"] == "actual"].copy()
    if not actual_random.empty:
        cols = [
            "timeframe",
            "total_pnl_pips",
            "profit_factor",
            "actual_total_pnl_percentile",
            "actual_profit_factor_percentile",
        ]
        lines.append(markdown_table(actual_random, cols))
        lines.append("")

    lines.extend(["## Entry Delay Sensitivity", ""])
    if not delay_df.empty:
        cols = ["timeframe", "entry_delay_bars", "total_pnl_pips", "profit_factor", "max_drawdown_pips"]
        lines.append(markdown_table(delay_df, cols))
        lines.append("")

    lines.extend(["## Fixed Parameter OOS", ""])
    if not oos_df.empty:
        cols = ["timeframe", "period", "cost_pips", "total_pnl_pips", "profit_factor", "max_drawdown_pips"]
        lines.append(markdown_table(oos_df, cols))
        lines.append("")

    lines.extend(
        [
            "## Interpretation Boundary",
            "",
            "This experiment does not prove a permanent trend-following edge.",
            "It checks whether the expected trend-following PnL structure appears under this market, period, timeframe, and fixed-cost assumption.",
            "The results should be interpreted as an article experiment, not investment advice or a production trading system.",
            "",
        ]
    )

    (output_dir / "article_result_summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_experiment(args: argparse.Namespace) -> None:
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    dev_end = pd.Timestamp(args.dev_end)
    output_dir = ensure_dir(args.output_dir)
    figures_dir = ensure_dir(output_dir / "figures")

    frames: dict[str, pd.DataFrame] = {}
    profiles: dict[str, dict[str, object]] = {}
    for timeframe, path in {"60m": args.input_60m, "240m": args.input_240m}.items():
        df, profile = read_price_csv(path)
        frames[timeframe] = df
        profiles[timeframe] = profile

    audit_df = build_data_audit(frames, profiles, start, dev_end, end)
    audit_df.to_csv(output_dir / "data_audit.csv", index=False)

    if args.stage == "audit":
        print_summary(output_dir, audit_df)
        return

    baseline_trades: dict[str, pd.DataFrame] = {}
    summary_rows = []
    for timeframe, df in frames.items():
        for cost in args.costs:
            trades = simulate_trades(
                df,
                timeframe=timeframe,
                period="full_2023_2025",
                start=start,
                end=end,
                short_window=args.short_window,
                long_window=args.long_window,
                round_trip_cost_pips=cost,
                entry_delay_bars=0,
            )
            summary_rows.append(
                metrics_row(
                    trades,
                    timeframe=timeframe,
                    period="full_2023_2025",
                    start=start,
                    end=end,
                    short_window=args.short_window,
                    long_window=args.long_window,
                    cost_pips=cost,
                    entry_delay_bars=0,
                )
            )
            if cost == PRIMARY_COST_PIPS:
                baseline_trades[timeframe] = trades

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_dir / "summary_metrics.csv", index=False)
    save_trade_logs(baseline_trades, output_dir)
    plot_equity_curves(baseline_trades, figures_dir, args.dpi)
    plot_drawdowns(baseline_trades, figures_dir, args.dpi)
    plot_trade_histograms(baseline_trades, figures_dir, args.dpi)

    if args.stage == "baseline":
        print_summary(output_dir, audit_df, summary_df)
        return

    cost_df = summary_df.copy()
    cost_df.to_csv(output_dir / "cost_sensitivity.csv", index=False)
    direction_df = build_direction_breakdown(baseline_trades, dev_end=dev_end)
    top_df = build_top_trade_exclusion(baseline_trades)
    random_df = build_random_direction_comparison(
        baseline_trades,
        random_runs=args.random_runs,
        seed=args.seed,
    )
    heatmap_df = build_parameter_heatmap(
        frames,
        start=start,
        end=end,
        cost_pips=PRIMARY_COST_PIPS,
    )
    delay_df = build_entry_delay_sensitivity(
        frames,
        start=start,
        end=end,
        short_window=args.short_window,
        long_window=args.long_window,
        cost_pips=PRIMARY_COST_PIPS,
    )

    direction_df.to_csv(output_dir / "direction_breakdown.csv", index=False)
    top_df.to_csv(output_dir / "top_trade_exclusion.csv", index=False)
    random_df.to_csv(output_dir / "random_direction_comparison.csv", index=False)
    heatmap_df.to_csv(output_dir / "parameter_heatmap.csv", index=False)
    delay_df.to_csv(output_dir / "entry_delay_sensitivity.csv", index=False)

    plot_cost_sensitivity(cost_df, figures_dir, args.dpi)
    plot_direction_breakdown(direction_df, figures_dir, args.dpi)
    plot_top_trade_exclusion(top_df, figures_dir, args.dpi)
    plot_random_comparison(random_df, figures_dir, args.dpi)
    plot_parameter_heatmap(heatmap_df, figures_dir, args.dpi)
    plot_entry_delay(delay_df, figures_dir, args.dpi)

    if args.stage == "robustness":
        print_summary(output_dir, audit_df, summary_df, random_df=random_df)
        return

    oos_costs = [cost for cost in args.costs if cost in {0.8, 1.0, 2.0}]
    oos_df = build_fixed_oos_summary(
        frames,
        start=start,
        dev_end=dev_end,
        end=end,
        short_window=args.short_window,
        long_window=args.long_window,
        costs=oos_costs,
    )
    oos_df.to_csv(output_dir / "fixed_oos_summary.csv", index=False)
    plot_fixed_oos(oos_df, figures_dir, args.dpi)

    write_article_summary(
        output_dir=output_dir,
        summary_df=summary_df,
        cost_df=cost_df,
        direction_df=direction_df,
        top_df=top_df,
        random_df=random_df,
        delay_df=delay_df,
        oos_df=oos_df,
    )
    print_summary(output_dir, audit_df, summary_df, random_df=random_df, oos_df=oos_df)


def print_summary(
    output_dir: Path,
    audit_df: pd.DataFrame,
    summary_df: pd.DataFrame | None = None,
    random_df: pd.DataFrame | None = None,
    oos_df: pd.DataFrame | None = None,
) -> None:
    print(f"Output directory: {output_dir}")
    print("\nData audit:")
    print(
        audit_df[
            [
                "timeframe",
                "clean_rows",
                "first_timestamp",
                "last_timestamp",
                "selected_rows",
                "dev_rows",
                "oos_rows",
                "duplicate_timestamps",
                "invalid_ohlc_rows",
            ]
        ].to_string(index=False)
    )

    if summary_df is not None:
        primary = summary_df[
            (summary_df["cost_pips"] == PRIMARY_COST_PIPS)
            & (summary_df["entry_delay_bars"] == 0)
        ]
        print("\nBaseline MA 20/80, cost 1.0 pips:")
        print(
            primary[
                [
                    "timeframe",
                    "trade_count",
                    "total_pnl_pips",
                    "win_rate_pct",
                    "profit_factor",
                    "max_drawdown_pips",
                    "avg_win_loss_ratio",
                ]
            ].to_string(index=False)
        )

    if random_df is not None:
        actual = random_df[random_df["variant"] == "actual"]
        print("\nRandom direction comparison:")
        print(
            actual[
                [
                    "timeframe",
                    "total_pnl_pips",
                    "actual_total_pnl_percentile",
                    "actual_profit_factor_percentile",
                ]
            ].to_string(index=False)
        )

    if oos_df is not None:
        primary_oos = oos_df[oos_df["cost_pips"] == PRIMARY_COST_PIPS]
        print("\nFixed parameter OOS, cost 1.0 pips:")
        print(
            primary_oos[
                ["timeframe", "period", "trade_count", "total_pnl_pips", "profit_factor"]
            ].to_string(index=False)
        )


def main() -> None:
    args = parse_args()
    run_experiment(args)


if __name__ == "__main__":
    main()
