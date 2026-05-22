#!/usr/bin/env python3
"""Run direction-control ablations for the lab_5 trend-following experiment.

This script keeps the original MA 20/80 strategy fixed and only changes how
short exposure is allowed:
- baseline_long_short: original long/short reversal logic
- long_only: no short entries
- short_filter_ma80_slope: short entries only when MA80 is falling
- short_filter_ma200_down: short entries only when price is below a falling MA200
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from run_trend_following_experiment import (
    PRIMARY_COST_PIPS,
    PRIMARY_LONG_WINDOW,
    PRIMARY_SHORT_WINDOW,
    calculate_metrics,
    ensure_dir,
    make_trade_row,
    markdown_table,
    read_price_csv,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_60M = SCRIPT_DIR / "USDJPY60.csv"
DEFAULT_INPUT_240M = SCRIPT_DIR / "USDJPY240.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs" / "trend_following_direction_ablation"

VARIANTS = [
    "baseline_long_short",
    "long_only",
    "short_filter_ma80_slope",
    "short_filter_ma200_down",
]

VARIANT_LABELS = {
    "baseline_long_short": "Baseline long/short",
    "long_only": "Long only",
    "short_filter_ma80_slope": "Short only if MA80 is falling",
    "short_filter_ma200_down": "Short only if close < falling MA200",
}

TRADE_COLUMNS = [
    "variant",
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
        description="Run long-only and short-suppression ablations for lab_5.",
    )
    parser.add_argument("--input-60m", type=Path, default=DEFAULT_INPUT_60M)
    parser.add_argument("--input-240m", type=Path, default=DEFAULT_INPUT_240M)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-01-01")
    parser.add_argument("--dev-end", default="2025-01-01")
    parser.add_argument("--short-window", type=int, default=PRIMARY_SHORT_WINDOW)
    parser.add_argument("--long-window", type=int, default=PRIMARY_LONG_WINDOW)
    parser.add_argument("--round-trip-cost-pips", type=float, default=PRIMARY_COST_PIPS)
    parser.add_argument("--slope-lookback-bars", type=int, default=20)
    parser.add_argument("--regime-ma-window", type=int, default=200)
    parser.add_argument("--dpi", type=int, default=180)
    return parser.parse_args()


def add_variant_signal(
    df: pd.DataFrame,
    short_window: int,
    long_window: int,
    variant: str,
    slope_lookback_bars: int,
    regime_ma_window: int,
) -> pd.DataFrame:
    out = df.copy()
    out["short_ma"] = out["close"].rolling(short_window, min_periods=short_window).mean()
    out["long_ma"] = out["close"].rolling(long_window, min_periods=long_window).mean()
    out["regime_ma"] = out["close"].rolling(regime_ma_window, min_periods=regime_ma_window).mean()

    valid = out["short_ma"].notna() & out["long_ma"].notna()
    signal = pd.Series(0, index=out.index, dtype="int64")
    signal.loc[valid & (out["short_ma"] > out["long_ma"])] = 1
    signal.loc[valid & (out["short_ma"] < out["long_ma"])] = -1

    if variant == "baseline_long_short":
        pass
    elif variant == "long_only":
        signal.loc[signal < 0] = 0
    elif variant == "short_filter_ma80_slope":
        ma_down = out["long_ma"] < out["long_ma"].shift(slope_lookback_bars)
        signal.loc[(signal < 0) & ~ma_down.fillna(False)] = 0
    elif variant == "short_filter_ma200_down":
        regime_down = out["regime_ma"] < out["regime_ma"].shift(slope_lookback_bars)
        price_below = out["close"] < out["regime_ma"]
        allow_short = regime_down.fillna(False) & price_below.fillna(False)
        signal.loc[(signal < 0) & ~allow_short] = 0
    else:
        raise ValueError(f"unknown variant: {variant}")

    out["signal"] = signal
    return out


def empty_trade_log() -> pd.DataFrame:
    return pd.DataFrame(columns=TRADE_COLUMNS)


def simulate_variant_trades(
    df: pd.DataFrame,
    *,
    variant: str,
    timeframe: str,
    period: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    short_window: int,
    long_window: int,
    round_trip_cost_pips: float,
    slope_lookback_bars: int,
    regime_ma_window: int,
) -> pd.DataFrame:
    work = add_variant_signal(
        df,
        short_window=short_window,
        long_window=long_window,
        variant=variant,
        slope_lookback_bars=slope_lookback_bars,
        regime_ma_window=regime_ma_window,
    )
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
        signal_i = j - 1
        target = int(signals[signal_i]) if signal_i >= 0 else 0

        if target == pos:
            continue

        if pos != 0 and entry_i is not None:
            row = make_trade_row(
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
                entry_delay_bars=0,
                exit_reason="signal_flip",
            )
            row["variant"] = variant
            rows.append(row)
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
        row = make_trade_row(
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
            entry_delay_bars=0,
            exit_reason="period_end",
        )
        row["variant"] = variant
        rows.append(row)

    if not rows:
        return empty_trade_log()
    return pd.DataFrame(rows)[TRADE_COLUMNS]


def metrics_row(
    trades: pd.DataFrame,
    *,
    variant: str,
    timeframe: str,
    period: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    short_window: int,
    long_window: int,
    cost_pips: float,
) -> dict[str, object]:
    return {
        "variant": variant,
        "variant_label": VARIANT_LABELS[variant],
        "timeframe": timeframe,
        "period": period,
        "start": start,
        "end_exclusive": end,
        "short_window": short_window,
        "long_window": long_window,
        "cost_pips": cost_pips,
        **calculate_metrics(trades),
    }


def build_direction_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if trades.empty:
        return pd.DataFrame()
    for (variant, timeframe, period, direction), subset in trades.groupby(
        ["variant", "timeframe", "period", "direction"],
        sort=False,
    ):
        rows.append(
            {
                "variant": variant,
                "variant_label": VARIANT_LABELS[variant],
                "timeframe": timeframe,
                "period": period,
                "direction": direction,
                **calculate_metrics(subset),
            }
        )
    return pd.DataFrame(rows)


def plot_variant_total_pnl(summary: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    full = summary[summary["period"] == "full_2023_2025"].copy()
    if full.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot = full.pivot(index="variant", columns="timeframe", values="total_pnl_pips")
    pivot = pivot.reindex(VARIANTS)
    x = range(len(pivot.index))
    width = 0.36
    ax.bar([i - width / 2 for i in x], pivot["60m"], width=width, label="60m")
    ax.bar([i + width / 2 for i in x], pivot["240m"], width=width, label="240m")
    ax.axhline(0.0, color="black", linewidth=1.0)
    ax.set_xticks(list(x), [VARIANT_LABELS[v] for v in pivot.index], rotation=18, ha="right")
    ax.set_ylabel("Total net pips")
    ax.set_title("Direction ablation total PnL, cost 1.0 pips")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "variant_total_pnl.png", dpi=dpi)
    plt.close(fig)


def plot_variant_oos(summary: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    oos = summary[summary["period"].isin(["dev_2023_2024", "oos_2025"])].copy()
    if oos.empty:
        return
    for timeframe, subset in oos.groupby("timeframe"):
        fig, ax = plt.subplots(figsize=(10, 5))
        pivot = subset.pivot(index="variant", columns="period", values="total_pnl_pips")
        pivot = pivot.reindex(VARIANTS)
        x = range(len(pivot.index))
        width = 0.36
        ax.bar([i - width / 2 for i in x], pivot["dev_2023_2024"], width=width, label="2023-2024 dev")
        ax.bar([i + width / 2 for i in x], pivot["oos_2025"], width=width, label="2025 OOS")
        ax.axhline(0.0, color="black", linewidth=1.0)
        ax.set_xticks(list(x), [VARIANT_LABELS[v] for v in pivot.index], rotation=18, ha="right")
        ax.set_ylabel("Total net pips")
        ax.set_title(f"{timeframe} fixed OOS direction ablation")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(figures_dir / f"variant_oos_{timeframe}.png", dpi=dpi)
        plt.close(fig)


def plot_short_pnl(direction: pd.DataFrame, figures_dir: Path, dpi: int) -> None:
    full_short = direction[
        (direction["period"] == "full_2023_2025") & (direction["direction"] == "short")
    ].copy()
    if full_short.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot = full_short.pivot(index="variant", columns="timeframe", values="total_pnl_pips")
    pivot = pivot.reindex(VARIANTS)
    x = range(len(pivot.index))
    width = 0.36
    ax.bar([i - width / 2 for i in x], pivot.get("60m", 0.0), width=width, label="60m")
    ax.bar([i + width / 2 for i in x], pivot.get("240m", 0.0), width=width, label="240m")
    ax.axhline(0.0, color="black", linewidth=1.0)
    ax.set_xticks(list(x), [VARIANT_LABELS[v] for v in pivot.index], rotation=18, ha="right")
    ax.set_ylabel("Short total net pips")
    ax.set_title("Short-side PnL after suppression filters")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "short_side_pnl.png", dpi=dpi)
    plt.close(fig)


def write_summary(output_dir: Path, summary: pd.DataFrame, direction: pd.DataFrame) -> None:
    lines = [
        "# Direction Ablation Result Summary",
        "",
        "Scope: MA 20/80 USDJPY trend-following ablation.",
        "",
        "- baseline_long_short: original long/short reversal logic",
        "- long_only: short signals become flat exits",
        "- short_filter_ma80_slope: short entries only when MA80 is falling over 20 bars",
        "- short_filter_ma200_down: short entries only when close is below a falling MA200",
        "- Execution and cost assumptions match the base experiment",
        "",
        "## Full Period Metrics",
        "",
    ]

    full = summary[summary["period"] == "full_2023_2025"].copy()
    cols = [
        "variant",
        "timeframe",
        "trade_count",
        "total_pnl_pips",
        "win_rate_pct",
        "profit_factor",
        "max_drawdown_pips",
    ]
    lines.append(markdown_table(full[cols], cols))
    lines.append("")

    lines.extend(["## Fixed OOS Metrics", ""])
    oos = summary[summary["period"].isin(["dev_2023_2024", "oos_2025"])].copy()
    lines.append(markdown_table(oos[cols + ["period"]], cols + ["period"]))
    lines.append("")

    lines.extend(["## Direction Breakdown", ""])
    direction_cols = [
        "variant",
        "timeframe",
        "period",
        "direction",
        "trade_count",
        "total_pnl_pips",
        "profit_factor",
        "max_drawdown_pips",
    ]
    lines.append(markdown_table(direction[direction_cols], direction_cols))
    lines.append("")

    lines.extend(
        [
            "## Interpretation Boundary",
            "",
            "These are ablations, not tuned production rules.",
            "If a short-suppression rule improves the full period but fails OOS, it should be treated as diagnostic evidence rather than a selected strategy.",
            "",
        ]
    )
    (output_dir / "direction_ablation_result_summary.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    dev_end = pd.Timestamp(args.dev_end)
    output_dir = ensure_dir(args.output_dir)
    figures_dir = ensure_dir(output_dir / "figures")

    frames = {}
    for timeframe, path in {"60m": args.input_60m, "240m": args.input_240m}.items():
        df, _ = read_price_csv(path)
        frames[timeframe] = df

    summary_rows = []
    trade_frames = []
    periods = [
        ("full_2023_2025", start, end),
        ("dev_2023_2024", start, dev_end),
        ("oos_2025", dev_end, end),
    ]

    for variant in VARIANTS:
        for timeframe, df in frames.items():
            for period, period_start, period_end in periods:
                trades = simulate_variant_trades(
                    df,
                    variant=variant,
                    timeframe=timeframe,
                    period=period,
                    start=period_start,
                    end=period_end,
                    short_window=args.short_window,
                    long_window=args.long_window,
                    round_trip_cost_pips=args.round_trip_cost_pips,
                    slope_lookback_bars=args.slope_lookback_bars,
                    regime_ma_window=args.regime_ma_window,
                )
                summary_rows.append(
                    metrics_row(
                        trades,
                        variant=variant,
                        timeframe=timeframe,
                        period=period,
                        start=period_start,
                        end=period_end,
                        short_window=args.short_window,
                        long_window=args.long_window,
                        cost_pips=args.round_trip_cost_pips,
                    )
                )
                trade_frames.append(trades)

    summary = pd.DataFrame(summary_rows)
    all_trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else empty_trade_log()
    direction = build_direction_breakdown(all_trades)

    summary.to_csv(output_dir / "direction_ablation_summary.csv", index=False)
    all_trades.to_csv(output_dir / "direction_ablation_trade_log.csv", index=False)
    direction.to_csv(output_dir / "direction_ablation_breakdown.csv", index=False)

    plot_variant_total_pnl(summary, figures_dir, args.dpi)
    plot_variant_oos(summary, figures_dir, args.dpi)
    plot_short_pnl(direction, figures_dir, args.dpi)
    write_summary(output_dir, summary, direction)

    print(f"Output directory: {output_dir}")
    print("\nFull period metrics:")
    full = summary[summary["period"] == "full_2023_2025"]
    print(
        full[
            [
                "variant",
                "timeframe",
                "trade_count",
                "total_pnl_pips",
                "win_rate_pct",
                "profit_factor",
                "max_drawdown_pips",
            ]
        ].to_string(index=False)
    )
    print("\nFixed OOS metrics:")
    oos = summary[summary["period"].isin(["dev_2023_2024", "oos_2025"])]
    print(
        oos[
            [
                "variant",
                "timeframe",
                "period",
                "trade_count",
                "total_pnl_pips",
                "profit_factor",
            ]
        ].to_string(index=False)
    )


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
