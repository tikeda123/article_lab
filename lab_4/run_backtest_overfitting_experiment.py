#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USDJPY 60分足を使ったバックテスト過学習・簡易PBO検証。

実験概要:
- 対象: USDJPY 60分足 OHLC
- 期間: 2020-01-01 <= timestamp < 2026-01-01
- 戦略: 移動平均クロス（終値確定後に判定し、次足始値で約定）
- 候補: short MA [5,10,20,30] × long MA [50,100,150,200]
        × SL [なし, ATR1.0, ATR1.5] × TP [なし, ATR1.5, ATR2.0] = 144通り
- 取引コスト: 往復1.0 pips（片道0.5 pips、USDJPY 1 pip = 0.01円）
- ATR: 14期間SMA、SL/TP判定に使用。エントリー時点では直前足までのATRのみ使用。
- CSCV/PBO: 8ブロック、4ブロックIS・4ブロックOOSの全70通り。

注意:
本コードは教育・記事用の実験コードです。投資助言や本番売買システムではありません。
"""

from __future__ import annotations

import argparse
import csv
import gzip
import itertools
import json
import math
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# matplotlib is used only for saving figures.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


DATE_FMT = "%Y-%m-%d %H:%M"
DEFAULT_START = "2020-01-01 00:00"
DEFAULT_END_EXCLUSIVE = "2026-01-01 00:00"
ANNUALIZATION_BARS = 24 * 252
PIP_SIZE = 0.01
ROUND_TRIP_COST_PIPS = 1.0
SIDE_COST_PRICE = (ROUND_TRIP_COST_PIPS * PIP_SIZE) / 2.0
ATR_PERIOD = 14
S_BLOCKS = 8
IS_BLOCKS = 4

SHORT_MA_LIST = [5, 10, 20, 30]
LONG_MA_LIST = [50, 100, 150, 200]
SL_OPTIONS = [None, 1.0, 1.5]
TP_OPTIONS = [None, 1.5, 2.0]


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    short_ma: int
    long_ma: int
    sl_atr: Optional[float]
    tp_atr: Optional[float]


@dataclass
class TradeStats:
    trade_count: int
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    median_trade_return: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run USDJPY simple PBO overfitting experiment.")
    parser.add_argument("--input", default="/mnt/data/USDJPY60(29).csv", help="Input tab-separated OHLCV CSV without header.")
    parser.add_argument("--outdir", default="/mnt/data/backtest_overfitting_submission", help="Output directory.")
    parser.add_argument("--start", default=DEFAULT_START, help="Experiment start timestamp inclusive, format YYYY-MM-DD HH:MM.")
    parser.add_argument("--end-exclusive", default=DEFAULT_END_EXCLUSIVE, help="Experiment end timestamp exclusive, format YYYY-MM-DD HH:MM.")
    parser.add_argument("--no-plots", action="store_true", help="Skip figure generation.")
    return parser.parse_args()


def load_ohlcv(path: str) -> Tuple[List[datetime], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    timestamps: List[datetime] = []
    opens: List[float] = []
    highs: List[float] = []
    lows: List[float] = []
    closes: List[float] = []
    vols: List[float] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        # 入力はタブ区切り。まれに空行がある場合は無視する。
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or len(row) < 5:
                continue
            row = [x.strip() for x in row if x.strip() != ""]
            if len(row) < 5:
                continue
            try:
                ts = datetime.strptime(row[0], DATE_FMT)
                o, h, l, c = map(float, row[1:5])
                v = float(row[5]) if len(row) >= 6 else 0.0
            except ValueError as exc:
                raise ValueError(f"Could not parse row: {row}") from exc
            timestamps.append(ts)
            opens.append(o)
            highs.append(h)
            lows.append(l)
            closes.append(c)
            vols.append(v)
    return timestamps, np.array(opens), np.array(highs), np.array(lows), np.array(closes), np.array(vols)


def data_quality(timestamps: Sequence[datetime], open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> Dict[str, object]:
    duplicate_count = len(timestamps) - len(set(timestamps))
    non_monotonic = sum(1 for i in range(1, len(timestamps)) if timestamps[i] <= timestamps[i - 1])
    ohlc_invalid = int(np.sum((high < np.maximum(open_, close)) | (low > np.minimum(open_, close)) | (high < low)))
    gaps_hours: List[float] = []
    for i in range(1, len(timestamps)):
        delta_h = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600.0
        if delta_h > 1.01:
            gaps_hours.append(delta_h)
    return {
        "rows": len(timestamps),
        "start": timestamps[0].strftime(DATE_FMT) if timestamps else None,
        "end": timestamps[-1].strftime(DATE_FMT) if timestamps else None,
        "duplicate_timestamps": duplicate_count,
        "non_monotonic_steps": non_monotonic,
        "ohlc_invalid_rows": ohlc_invalid,
        "gaps_over_1h_count": len(gaps_hours),
        "max_gap_hours": max(gaps_hours) if gaps_hours else 0.0,
        "note": "Forex weekend/holiday gaps are counted as gaps; no interpolation was applied.",
    }


def first_index_at_or_after(timestamps: Sequence[datetime], dt: datetime) -> int:
    # timestamps are sorted; simple binary search.
    lo, hi = 0, len(timestamps)
    while lo < hi:
        mid = (lo + hi) // 2
        if timestamps[mid] < dt:
            lo = mid + 1
        else:
            hi = mid
    return lo


def rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=float)
    if window <= 0 or len(arr) < window:
        return out
    csum = np.cumsum(np.insert(arr.astype(float), 0, 0.0))
    out[window - 1:] = (csum[window:] - csum[:-window]) / float(window)
    return out


def calc_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = ATR_PERIOD) -> np.ndarray:
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    return rolling_mean(tr, period)


def make_strategies() -> List[StrategySpec]:
    strategies: List[StrategySpec] = []
    for short_ma, long_ma, sl_atr, tp_atr in itertools.product(SHORT_MA_LIST, LONG_MA_LIST, SL_OPTIONS, TP_OPTIONS):
        sl_label = "none" if sl_atr is None else f"atr{str(sl_atr).replace('.', '_')}"
        tp_label = "none" if tp_atr is None else f"atr{str(tp_atr).replace('.', '_')}"
        sid = f"ma_s{short_ma}_l{long_ma}_sl_{sl_label}_tp_{tp_label}"
        strategies.append(StrategySpec(sid, short_ma, long_ma, sl_atr, tp_atr))
    return strategies


def compute_signals(close: np.ndarray, strategies: Sequence[StrategySpec]) -> Dict[Tuple[int, int], np.ndarray]:
    unique_windows = sorted(set([s.short_ma for s in strategies] + [s.long_ma for s in strategies]))
    ma = {w: rolling_mean(close, w) for w in unique_windows}
    signals: Dict[Tuple[int, int], np.ndarray] = {}
    for short_ma in SHORT_MA_LIST:
        for long_ma in LONG_MA_LIST:
            s = ma[short_ma]
            l = ma[long_ma]
            sig = np.zeros(len(close), dtype=np.int8)
            valid = np.isfinite(s) & np.isfinite(l)
            sig[valid & (s > l)] = 1
            sig[valid & (s < l)] = -1
            signals[(short_ma, long_ma)] = sig
    return signals


def simulate_strategy(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
    signal: np.ndarray,
    spec: StrategySpec,
    start_i: int,
    end_i_exclusive: int,
) -> Tuple[np.ndarray, TradeStats]:
    """Return per-bar simple returns for timestamps[start_i:end_i_exclusive-1].

    i-th output row corresponds to holding/return during source bar src_i = start_i + i,
    measured from open[src_i] to open[src_i + 1], unless SL/TP exits intra-bar.
    """
    n_out = max(0, end_i_exclusive - start_i - 1)
    ret = np.zeros(n_out, dtype=float)

    pos = 0  # 1 long, -1 short, 0 flat
    entry_price = math.nan
    stop_price = math.nan
    take_price = math.nan
    current_trade_pnl = 0.0
    trade_returns: List[float] = []

    def close_position(out_idx: int, price_for_cost: float) -> None:
        nonlocal pos, entry_price, stop_price, take_price, current_trade_pnl
        if pos == 0:
            return
        cost = SIDE_COST_PRICE / price_for_cost
        ret[out_idx] -= cost
        current_trade_pnl -= cost
        trade_returns.append(current_trade_pnl)
        pos = 0
        entry_price = math.nan
        stop_price = math.nan
        take_price = math.nan
        current_trade_pnl = 0.0

    def open_position(out_idx: int, desired_pos: int, src_i: int) -> None:
        nonlocal pos, entry_price, stop_price, take_price, current_trade_pnl
        if desired_pos == 0:
            return
        needs_atr = spec.sl_atr is not None or spec.tp_atr is not None
        atr_entry = atr[src_i - 1] if src_i - 1 >= 0 else math.nan
        if needs_atr and not math.isfinite(float(atr_entry)):
            return
        pos = desired_pos
        entry_price = open_[src_i]
        stop_price = math.nan
        take_price = math.nan
        if spec.sl_atr is not None:
            stop_price = entry_price - pos * spec.sl_atr * atr_entry
        if spec.tp_atr is not None:
            take_price = entry_price + pos * spec.tp_atr * atr_entry
        cost = SIDE_COST_PRICE / open_[src_i]
        ret[out_idx] -= cost
        current_trade_pnl = -cost

    for out_idx, src_i in enumerate(range(start_i, end_i_exclusive - 1)):
        desired = int(signal[src_i - 1]) if src_i - 1 >= 0 else 0

        # シグナルは前足終値で確定し、この足の始値で約定する。
        if desired != pos:
            if pos != 0:
                close_position(out_idx, open_[src_i])
            if desired != 0:
                open_position(out_idx, desired, src_i)

        if pos == 0:
            continue

        exit_price = None
        # SL/TPは当該足の高値・安値で判定する。両方到達時は保守的に損切り優先。
        if pos == 1:
            stop_hit = spec.sl_atr is not None and low[src_i] <= stop_price
            take_hit = spec.tp_atr is not None and high[src_i] >= take_price
            if stop_hit:
                exit_price = stop_price
            elif take_hit:
                exit_price = take_price
        else:
            stop_hit = spec.sl_atr is not None and high[src_i] >= stop_price
            take_hit = spec.tp_atr is not None and low[src_i] <= take_price
            if stop_hit:
                exit_price = stop_price
            elif take_hit:
                exit_price = take_price

        if exit_price is None:
            bar_ret = pos * (open_[src_i + 1] - open_[src_i]) / open_[src_i]
            ret[out_idx] += bar_ret
            current_trade_pnl += bar_ret
        else:
            bar_ret = pos * (exit_price - open_[src_i]) / open_[src_i]
            ret[out_idx] += bar_ret
            current_trade_pnl += bar_ret
            close_position(out_idx, max(abs(exit_price), 1e-12))

    # 最終足の始値で強制クローズし、片道コストだけ最終リターンに反映する。
    if n_out > 0 and pos != 0:
        close_position(n_out - 1, open_[end_i_exclusive - 1])

    stats = summarize_trades(trade_returns)
    return ret, stats


def summarize_trades(trade_returns: Sequence[float]) -> TradeStats:
    if not trade_returns:
        return TradeStats(0, math.nan, math.nan, math.nan, math.nan)
    arr = np.array(trade_returns, dtype=float)
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    win_rate = float(len(wins) / len(arr))
    gross_profit = float(np.sum(wins))
    gross_loss = float(-np.sum(losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else math.inf
    return TradeStats(
        trade_count=int(len(arr)),
        win_rate=win_rate,
        profit_factor=pf,
        avg_trade_return=float(np.mean(arr)),
        median_trade_return=float(np.median(arr)),
    )


def sharpe_ratio(returns: np.ndarray, annualization: int = ANNUALIZATION_BARS) -> float:
    if returns.size == 0:
        return math.nan
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1)) if returns.size > 1 else 0.0
    if std <= 0 or not math.isfinite(std):
        return 0.0
    return mean / std * math.sqrt(annualization)


def cum_return(returns: np.ndarray) -> float:
    if returns.size == 0:
        return math.nan
    return float(np.prod(1.0 + returns) - 1.0)


def max_drawdown(returns: np.ndarray) -> float:
    if returns.size == 0:
        return math.nan
    equity = np.cumprod(1.0 + returns)
    peaks = np.maximum.accumulate(equity)
    dd = equity / peaks - 1.0
    return float(np.min(dd))


def profit_factor_from_returns(returns: np.ndarray) -> float:
    pos = float(np.sum(returns[returns > 0]))
    neg = float(-np.sum(returns[returns < 0]))
    if neg == 0:
        return math.inf if pos > 0 else math.nan
    return pos / neg


def summarize_candidates(pnl: np.ndarray, strategies: Sequence[StrategySpec], trade_stats: Sequence[TradeStats]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for j, spec in enumerate(strategies):
        r = pnl[:, j]
        ts = trade_stats[j]
        rows.append({
            "strategy_id": spec.strategy_id,
            "short_ma": spec.short_ma,
            "long_ma": spec.long_ma,
            "sl_atr": "none" if spec.sl_atr is None else spec.sl_atr,
            "tp_atr": "none" if spec.tp_atr is None else spec.tp_atr,
            "full_sample_sharpe": sharpe_ratio(r),
            "full_sample_cum_return": cum_return(r),
            "full_sample_max_drawdown": max_drawdown(r),
            "bar_profit_factor": profit_factor_from_returns(r),
            "trade_count": ts.trade_count,
            "win_rate": ts.win_rate,
            "trade_profit_factor": ts.profit_factor,
            "avg_trade_return": ts.avg_trade_return,
            "median_trade_return": ts.median_trade_return,
        })
    rows.sort(key=lambda x: x["full_sample_sharpe"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["full_sample_rank"] = rank
    return rows


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: Optional[Sequence[str]] = None) -> None:
    if not rows and fieldnames is None:
        raise ValueError("fieldnames required for empty rows")
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_pnl_matrix_gz(path: Path, timestamps: Sequence[datetime], pnl: np.ndarray, strategies: Sequence[StrategySpec]) -> None:
    header = ["timestamp"] + [s.strategy_id for s in strategies]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for i, ts in enumerate(timestamps):
            writer.writerow([ts.strftime(DATE_FMT)] + [f"{x:.10g}" for x in pnl[i, :]])


def build_pbo(pnl: np.ndarray, strategies: Sequence[StrategySpec], timestamps: Sequence[datetime]) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    n_rows, n_strats = pnl.shape
    indices = np.arange(n_rows)
    blocks = np.array_split(indices, S_BLOCKS)
    rows: List[Dict[str, object]] = []

    for combo_id, is_blocks_tuple in enumerate(itertools.combinations(range(S_BLOCKS), IS_BLOCKS), start=1):
        is_blocks_set = set(is_blocks_tuple)
        oos_blocks_tuple = tuple(i for i in range(S_BLOCKS) if i not in is_blocks_set)
        is_idx = np.concatenate([blocks[i] for i in is_blocks_tuple])
        oos_idx = np.concatenate([blocks[i] for i in oos_blocks_tuple])

        is_sharpes = np.array([sharpe_ratio(pnl[is_idx, j]) for j in range(n_strats)])
        oos_sharpes = np.array([sharpe_ratio(pnl[oos_idx, j]) for j in range(n_strats)])
        best_j = int(np.nanargmax(is_sharpes))
        best_oos_sharpe = float(oos_sharpes[best_j])
        oos_sorted_desc = np.argsort(-oos_sharpes)
        oos_rank = int(np.where(oos_sorted_desc == best_j)[0][0] + 1)
        oos_median = float(np.nanmedian(oos_sharpes))
        selected_oos_cum = cum_return(pnl[oos_idx, best_j])
        selected_is_cum = cum_return(pnl[is_idx, best_j])
        rows.append({
            "combo_id": combo_id,
            "is_blocks": ";".join(map(str, is_blocks_tuple)),
            "oos_blocks": ";".join(map(str, oos_blocks_tuple)),
            "is_start": timestamps[int(is_idx[0])].strftime(DATE_FMT),
            "is_end": timestamps[int(is_idx[-1])].strftime(DATE_FMT),
            "oos_start": timestamps[int(oos_idx[0])].strftime(DATE_FMT),
            "oos_end": timestamps[int(oos_idx[-1])].strftime(DATE_FMT),
            "selected_strategy_id": strategies[best_j].strategy_id,
            "selected_strategy_index": best_j,
            "selected_is_sharpe": float(is_sharpes[best_j]),
            "selected_oos_sharpe": best_oos_sharpe,
            "selected_is_cum_return": selected_is_cum,
            "selected_oos_cum_return": selected_oos_cum,
            "oos_rank_desc_1_best": oos_rank,
            "oos_percentile_desc_1_best": oos_rank / n_strats,
            "oos_median_sharpe": oos_median,
            "oos_median_or_worse": bool(best_oos_sharpe <= oos_median),
            "oos_loss": bool(selected_oos_cum < 0),
            "best_oos_strategy_id": strategies[int(oos_sorted_desc[0])].strategy_id,
            "best_oos_sharpe": float(oos_sharpes[int(oos_sorted_desc[0])]),
        })

    pbo = float(np.mean([r["oos_median_or_worse"] for r in rows]))
    oos_loss_prob = float(np.mean([r["oos_loss"] for r in rows]))
    summary = {
        "pbo_median_or_worse_rate": pbo,
        "oos_loss_probability": oos_loss_prob,
        "combinations": len(rows),
        "s_blocks": S_BLOCKS,
        "is_blocks": IS_BLOCKS,
        "oos_blocks": S_BLOCKS - IS_BLOCKS,
        "n_strategies": n_strats,
        "mean_selected_is_sharpe": float(np.mean([r["selected_is_sharpe"] for r in rows])),
        "mean_selected_oos_sharpe": float(np.mean([r["selected_oos_sharpe"] for r in rows])),
        "median_selected_is_sharpe": float(np.median([r["selected_is_sharpe"] for r in rows])),
        "median_selected_oos_sharpe": float(np.median([r["selected_oos_sharpe"] for r in rows])),
        "mean_oos_rank": float(np.mean([r["oos_rank_desc_1_best"] for r in rows])),
        "median_oos_rank": float(np.median([r["oos_rank_desc_1_best"] for r in rows])),
    }
    return rows, summary


def make_figures(outdir: Path, candidate_rows: Sequence[Dict[str, object]], pbo_rows: Sequence[Dict[str, object]], best_ts_rows: Sequence[Dict[str, object]], summary: Dict[str, object]) -> None:
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    sharpes = np.array([float(r["full_sample_sharpe"]) for r in candidate_rows])
    plt.figure(figsize=(8, 5))
    plt.hist(sharpes, bins=20)
    plt.axvline(np.max(sharpes), linestyle="--", linewidth=1.5, label="Best")
    plt.title("Figure 1: Full-sample Sharpe distribution across 144 candidates")
    plt.xlabel("Annualized Sharpe Ratio")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / "fig1_sharpe_distribution.png", dpi=160)
    plt.close()

    is_sr = np.array([float(r["selected_is_sharpe"]) for r in pbo_rows])
    oos_sr = np.array([float(r["selected_oos_sharpe"]) for r in pbo_rows])
    lim_min = float(min(np.min(is_sr), np.min(oos_sr))) - 0.1
    lim_max = float(max(np.max(is_sr), np.max(oos_sr))) + 0.1
    plt.figure(figsize=(6, 6))
    plt.scatter(is_sr, oos_sr, alpha=0.75)
    plt.axhline(0, linewidth=1)
    plt.axvline(0, linewidth=1)
    plt.plot([lim_min, lim_max], [lim_min, lim_max], linestyle="--", linewidth=1)
    plt.title("Figure 2: IS Sharpe vs OOS Sharpe for selected strategies")
    plt.xlabel("Selected strategy IS Sharpe")
    plt.ylabel("Selected strategy OOS Sharpe")
    plt.xlim(lim_min, lim_max)
    plt.ylim(lim_min, lim_max)
    plt.tight_layout()
    plt.savefig(figdir / "fig2_is_vs_oos_sharpe.png", dpi=160)
    plt.close()

    ranks = np.array([int(r["oos_rank_desc_1_best"]) for r in pbo_rows])
    plt.figure(figsize=(8, 5))
    plt.hist(ranks, bins=range(1, 146, 8))
    plt.axvline(72.5, linestyle="--", linewidth=1.5, label="Median boundary")
    plt.title("Figure 3: OOS rank distribution of IS-best strategies")
    plt.xlabel("OOS rank among 144 candidates (1 = best)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / "fig3_oos_rank_distribution.png", dpi=160)
    plt.close()

    pbo = float(summary["pbo_median_or_worse_rate"])
    plt.figure(figsize=(6, 4))
    plt.bar(["Median-or-worse", "Above median"], [pbo, 1.0 - pbo])
    plt.ylim(0, 1)
    plt.title(f"Figure 4: Simplified PBO = {pbo:.1%}")
    plt.ylabel("Rate")
    plt.tight_layout()
    plt.savefig(figdir / "fig4_simplified_pbo.png", dpi=160)
    plt.close()

    loss_prob = float(summary["oos_loss_probability"])
    plt.figure(figsize=(6, 4))
    plt.bar(["OOS loss", "OOS gain"], [loss_prob, 1.0 - loss_prob])
    plt.ylim(0, 1)
    plt.title(f"Figure 5: OOS loss probability = {loss_prob:.1%}")
    plt.ylabel("Rate")
    plt.tight_layout()
    plt.savefig(figdir / "fig5_oos_loss_probability.png", dpi=160)
    plt.close()

    ts = [datetime.strptime(str(r["timestamp"]), DATE_FMT) for r in best_ts_rows]
    equity = np.array([float(r["equity_curve"] ) for r in best_ts_rows])
    plt.figure(figsize=(10, 5))
    plt.plot(ts, equity)
    plt.title("Figure 6: Cumulative equity curve of full-sample best strategy")
    plt.xlabel("Time")
    plt.ylabel("Equity, initial = 1.0")
    plt.tight_layout()
    plt.savefig(figdir / "fig6_best_strategy_equity_curve.png", dpi=160)
    plt.close()


def build_best_strategy_timeseries(timestamps: Sequence[datetime], pnl: np.ndarray, strategies: Sequence[StrategySpec], candidate_rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    best_strategy_id = str(candidate_rows[0]["strategy_id"])
    best_idx = next(i for i, s in enumerate(strategies) if s.strategy_id == best_strategy_id)
    r = pnl[:, best_idx]
    equity = np.cumprod(1.0 + r)
    rows: List[Dict[str, object]] = []
    for ts, rr, eq in zip(timestamps, r, equity):
        rows.append({
            "timestamp": ts.strftime(DATE_FMT),
            "strategy_id": best_strategy_id,
            "bar_return": rr,
            "equity_curve": eq,
            "cumulative_return": eq - 1.0,
        })
    return rows


def write_markdown_report(path: Path, summary: Dict[str, object], dataq_full: Dict[str, object], dataq_exp: Dict[str, object], top_rows: Sequence[Dict[str, object]]) -> None:
    lines: List[str] = []
    lines.append("# USDJPY 60分足 簡易PBO検証 実験レポート")
    lines.append("")
    lines.append("## 実験条件")
    lines.append("")
    for k, v in summary["experiment_conditions"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## データ品質")
    lines.append("")
    lines.append("### 入力全体")
    for k, v in dataq_full.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### 実験対象期間")
    for k, v in dataq_exp.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## 主要結果")
    lines.append("")
    lines.append(f"- 戦略候補数: {summary['n_strategies']}")
    lines.append(f"- CSCV組み合わせ数: {summary['combinations']}")
    lines.append(f"- 簡易PBO（IS最良がOOS中央値以下）: {summary['pbo_median_or_worse_rate']:.2%}")
    lines.append(f"- OOS損失確率: {summary['oos_loss_probability']:.2%}")
    lines.append(f"- 選択戦略の平均IS Sharpe: {summary['mean_selected_is_sharpe']:.4f}")
    lines.append(f"- 選択戦略の平均OOS Sharpe: {summary['mean_selected_oos_sharpe']:.4f}")
    lines.append(f"- 選択戦略のOOS順位平均: {summary['mean_oos_rank']:.2f} / {summary['n_strategies']}")
    lines.append("")
    lines.append("## フルサンプル上位5戦略")
    lines.append("")
    lines.append("| rank | strategy_id | Sharpe | CumReturn | MaxDD | Trades | WinRate |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for r in top_rows[:5]:
        lines.append(
            f"| {r['full_sample_rank']} | {r['strategy_id']} | {float(r['full_sample_sharpe']):.4f} | "
            f"{float(r['full_sample_cum_return']):.4%} | {float(r['full_sample_max_drawdown']):.4%} | "
            f"{int(r['trade_count'])} | {float(r['win_rate']):.2%} |"
        )
    lines.append("")
    lines.append("## 解釈")
    lines.append("")
    if summary["pbo_median_or_worse_rate"] >= 0.5:
        lines.append("簡易PBOが50%を超えているため、今回の候補群と選択プロセスでは、ISで最良だった戦略がOOSでは凡庸以下に落ちるケースが多いという結果になりました。これは、市場そのものにエッジがないという断定ではなく、今回の移動平均クロス候補群をIS Sharpe最大で選ぶ手順の再現性が弱いことを示唆します。")
    else:
        lines.append("簡易PBOは50%未満でした。ただし、PBOが低いだけで将来の収益性が保証されるわけではありません。別期間のHoldout、WFO、DryRun、コスト・スリッページ再評価が必要です。")
    lines.append("")
    lines.append("## 生成ファイル")
    lines.append("")
    lines.append("- candidate_summary.csv: 144戦略のフルサンプル評価")
    lines.append("- pbo_results.csv: 70通りのIS/OOS検証結果")
    lines.append("- pnl_matrix.csv.gz: T×Nの損益行列")
    lines.append("- best_strategy_timeseries.csv: フルサンプルSharpe最良戦略の時系列")
    lines.append("- figures/*.png: 記事用図表")
    lines.append("- results_summary.json: KPIと実験条件")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    inpath = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    timestamps, open_, high, low, close, _vol = load_ohlcv(str(inpath))
    if len(timestamps) < 1000:
        raise RuntimeError("Too few rows after loading input data.")
    dataq_full = data_quality(timestamps, open_, high, low, close)

    start_dt = datetime.strptime(args.start, DATE_FMT)
    end_excl_dt = datetime.strptime(args.end_exclusive, DATE_FMT)
    start_i = first_index_at_or_after(timestamps, start_dt)
    end_i = first_index_at_or_after(timestamps, end_excl_dt)
    if end_i - start_i < 1000:
        raise RuntimeError("Too few rows in experiment period.")

    exp_timestamps_raw = timestamps[start_i:end_i]
    dataq_exp = data_quality(exp_timestamps_raw, open_[start_i:end_i], high[start_i:end_i], low[start_i:end_i], close[start_i:end_i])

    strategies = make_strategies()
    atr = calc_atr(high, low, close, ATR_PERIOD)
    signals = compute_signals(close, strategies)

    # PnL matrix: rows are timestamps[start_i:end_i-1], columns are strategy candidates.
    ret_timestamps = timestamps[start_i:end_i - 1]
    pnl = np.zeros((len(ret_timestamps), len(strategies)), dtype=float)
    trade_stats: List[TradeStats] = []

    for j, spec in enumerate(strategies):
        r, ts = simulate_strategy(open_, high, low, atr, signals[(spec.short_ma, spec.long_ma)], spec, start_i, end_i)
        pnl[:, j] = r
        trade_stats.append(ts)

    candidate_rows = summarize_candidates(pnl, strategies, trade_stats)
    pbo_rows, pbo_summary = build_pbo(pnl, strategies, ret_timestamps)
    best_ts_rows = build_best_strategy_timeseries(ret_timestamps, pnl, strategies, candidate_rows)

    conditions = {
        "instrument": "USDJPY",
        "timeframe": "60 minutes",
        "source_file": str(inpath.name),
        "experiment_period": f"{args.start} <= timestamp < {args.end_exclusive}",
        "strategy_family": "Moving-average cross, long if short MA > long MA, short if short MA < long MA",
        "short_ma": ", ".join(map(str, SHORT_MA_LIST)),
        "long_ma": ", ".join(map(str, LONG_MA_LIST)),
        "sl_options": "none, ATR 1.0, ATR 1.5",
        "tp_options": "none, ATR 1.5, ATR 2.0",
        "atr_period": ATR_PERIOD,
        "candidate_count": len(strategies),
        "entry_timing": "Signal at confirmed close; execution at next bar open",
        "position_rule": "Single position; long/short; reverse on opposite signal; re-enter allowed after SL/TP on next bar",
        "intrabar_sl_tp_rule": "If both SL and TP are touched in one bar, stop-loss is prioritized conservatively",
        "transaction_cost": f"Round trip {ROUND_TRIP_COST_PIPS:.1f} pip; side cost {SIDE_COST_PRICE:.4f} JPY",
        "annualization_bars": ANNUALIZATION_BARS,
        "cscv_blocks": S_BLOCKS,
        "is_blocks_per_combo": IS_BLOCKS,
        "oos_blocks_per_combo": S_BLOCKS - IS_BLOCKS,
        "combo_count": math.comb(S_BLOCKS, IS_BLOCKS),
    }

    summary = {**pbo_summary, "experiment_conditions": conditions, "data_quality_full": dataq_full, "data_quality_experiment": dataq_exp}
    best = candidate_rows[0]
    summary["full_sample_best_strategy"] = {
        "strategy_id": best["strategy_id"],
        "sharpe": best["full_sample_sharpe"],
        "cum_return": best["full_sample_cum_return"],
        "max_drawdown": best["full_sample_max_drawdown"],
        "trade_count": best["trade_count"],
        "win_rate": best["win_rate"],
    }

    # Write outputs.
    candidate_fields = [
        "full_sample_rank", "strategy_id", "short_ma", "long_ma", "sl_atr", "tp_atr",
        "full_sample_sharpe", "full_sample_cum_return", "full_sample_max_drawdown",
        "bar_profit_factor", "trade_count", "win_rate", "trade_profit_factor",
        "avg_trade_return", "median_trade_return",
    ]
    write_csv(outdir / "candidate_summary.csv", candidate_rows, candidate_fields)

    pbo_fields = [
        "combo_id", "is_blocks", "oos_blocks", "is_start", "is_end", "oos_start", "oos_end",
        "selected_strategy_id", "selected_strategy_index", "selected_is_sharpe", "selected_oos_sharpe",
        "selected_is_cum_return", "selected_oos_cum_return", "oos_rank_desc_1_best",
        "oos_percentile_desc_1_best", "oos_median_sharpe", "oos_median_or_worse", "oos_loss",
        "best_oos_strategy_id", "best_oos_sharpe",
    ]
    write_csv(outdir / "pbo_results.csv", pbo_rows, pbo_fields)
    write_csv(outdir / "best_strategy_timeseries.csv", best_ts_rows, ["timestamp", "strategy_id", "bar_return", "equity_curve", "cumulative_return"])
    write_pnl_matrix_gz(outdir / "pnl_matrix.csv.gz", ret_timestamps, pnl, strategies)

    with open(outdir / "results_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, allow_nan=True)
    write_markdown_report(outdir / "experiment_report.md", summary, dataq_full, dataq_exp, candidate_rows)

    if not args.no_plots:
        make_figures(outdir, candidate_rows, pbo_rows, best_ts_rows, summary)

    # Copy this script into the output directory for submission/reproduction.
    script_path = Path(__file__).resolve()
    dst_script = outdir / script_path.name
    if script_path != dst_script:
        shutil.copy2(script_path, dst_script)

    print(json.dumps({
        "outdir": str(outdir),
        "n_rows": len(ret_timestamps),
        "n_strategies": len(strategies),
        "pbo": summary["pbo_median_or_worse_rate"],
        "oos_loss_probability": summary["oos_loss_probability"],
        "best_strategy": summary["full_sample_best_strategy"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
