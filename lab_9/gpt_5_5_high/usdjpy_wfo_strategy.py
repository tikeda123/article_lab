#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USDJPY robust quant strategy research script.

Purpose:
- Load OHLCV CSV data without assuming a header.
- Validate data quality and infer timeframe.
- Create past-only technical features.
- Compare simple strategy families.
- Run walk-forward optimization with train / validation / OOS test split.
- Evaluate cost-adjusted performance and robustness.

Default round-turn transaction cost: 1.0 pip for USDJPY.
Execution convention:
- Signal is calculated at bar close t from information available up to t.
- The desired position is entered at the next bar open t+1.
- Returns are measured open-to-open.
"""

from __future__ import annotations

import argparse
import os
import json
import math
import warnings
from collections import Counter
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")


# =============================================================================
# 1. Data loading / validation
# =============================================================================

def load_data(path: str) -> pd.DataFrame:
    """
    Load OHLCV data from CSV/TSV/whitespace-delimited file.
    Supported layouts:
      date time open high low close volume
      datetime open high low close volume
    """
    raw = pd.read_csv(path, sep=r"\s+|,|\t", header=None, engine="python")
    if raw.shape[1] >= 7:
        dt = raw.iloc[:, 0].astype(str) + " " + raw.iloc[:, 1].astype(str)
        rest = raw.iloc[:, 2:7].copy()
    elif raw.shape[1] >= 6:
        dt = raw.iloc[:, 0].astype(str)
        rest = raw.iloc[:, 1:6].copy()
    elif raw.shape[1] >= 5:
        dt = raw.iloc[:, 0].astype(str)
        rest = raw.iloc[:, 1:5].copy()
    else:
        raise ValueError(f"Unexpected column count: {raw.shape[1]}")

    columns = ["open", "high", "low", "close", "volume"][: rest.shape[1]]
    rest.columns = columns

    df = rest.copy()
    df.insert(0, "datetime", pd.to_datetime(dt, errors="coerce"))
    for c in columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    required = ["datetime", "open", "high", "low", "close"]
    df = df.dropna(subset=required)
    df = df.sort_values("datetime").drop_duplicates("datetime")
    df = df.set_index("datetime")

    if "volume" not in df.columns:
        df["volume"] = np.nan

    return df


def validate_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Return data diagnostics: period, rows, inferred timeframe, missing values,
    duplicates, OHLC consistency, return distribution, large gaps, and regime hints.
    """
    idx = df.index
    diffs = idx.to_series().diff().dropna()
    mode_interval = diffs.mode().iloc[0] if not diffs.mode().empty else pd.NaT
    median_interval = diffs.median() if len(diffs) else pd.NaT

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    bad_ohlc = ((h < np.maximum(o, c)) | (l > np.minimum(o, c)) | (h < l)).sum()

    ret = c.pct_change().dropna()
    z = (ret - ret.mean()) / ret.std() if ret.std() > 0 else ret * np.nan

    out = {
        "start": str(idx.min()),
        "end": str(idx.max()),
        "rows": int(len(df)),
        "median_interval": str(median_interval),
        "mode_interval": str(mode_interval),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_index": int(idx.duplicated().sum()),
        "ohlc_bad": int(bad_ohlc),
        "ret_mean": float(ret.mean()),
        "ret_std": float(ret.std()),
        "ret_skew": float(ret.skew()),
        "ret_kurt": float(ret.kurt()),
        "ret_min": float(ret.min()),
        "ret_max": float(ret.max()),
        "return_outliers_abs_z_gt_8": int((z.abs() > 8).sum()),
        "large_gaps_count": int((diffs > mode_interval * 1.5).sum()) if pd.notna(mode_interval) else 0,
    }

    return out


def infer_bars_per_year(index: pd.DatetimeIndex) -> float:
    elapsed_years = max((index[-1] - index[0]).total_seconds() / (365.25 * 24 * 3600), 1e-9)
    return len(index) / elapsed_years


# =============================================================================
# 2. Features
# =============================================================================

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create past-only features:
    - ATR14
    - ATR percentage
    - ADX14
    - rolling median of ATR percentage
    """
    out = df.copy()
    high, low, close = out["high"], out["low"], out["close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    out["tr"] = tr
    out["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    out["atr_pct"] = out["atr14"] / close

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=out.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=out.index,
    )

    atr_w = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr_w
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr_w
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    out["adx14"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    out["atr_pct_med200"] = out["atr_pct"].rolling(200, min_periods=100).median()
    return out


# =============================================================================
# 3. Signal generation
# =============================================================================

def _signal_ma(df: pd.DataFrame, fast: int = 24, slow: int = 120) -> pd.Series:
    ema_fast = df["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    sig = pd.Series(0.0, index=df.index)
    sig[ema_fast > ema_slow] = 1.0
    sig[ema_fast < ema_slow] = -1.0
    return sig.fillna(0.0)


def _signal_ma_adx(df: pd.DataFrame, fast: int = 24, slow: int = 120, adx: int = 22) -> pd.Series:
    base = _signal_ma(df, fast, slow)
    return base.where(df["adx14"] >= adx, 0.0).fillna(0.0)


def _signal_ma_adx_vol(df: pd.DataFrame, fast: int = 24, slow: int = 120, adx: int = 22) -> pd.Series:
    base = _signal_ma(df, fast, slow)
    filt = (df["adx14"] >= adx) & (df["atr_pct"] >= df["atr_pct_med200"])
    return base.where(filt, 0.0).fillna(0.0)


def _signal_donchian(df: pd.DataFrame, n: int = 96) -> pd.Series:
    hh = df["high"].rolling(n, min_periods=n).max().shift(1)
    ll = df["low"].rolling(n, min_periods=n).min().shift(1)
    sig = pd.Series(np.nan, index=df.index)
    sig[df["close"] > hh] = 1.0
    sig[df["close"] < ll] = -1.0
    return sig.ffill().fillna(0.0)


def _signal_donchian_adx(df: pd.DataFrame, n: int = 96, adx: int = 22) -> pd.Series:
    hh = df["high"].rolling(n, min_periods=n).max().shift(1)
    ll = df["low"].rolling(n, min_periods=n).min().shift(1)
    sig = pd.Series(np.nan, index=df.index)
    ok = df["adx14"] >= adx
    sig[(df["close"] > hh) & ok] = 1.0
    sig[(df["close"] < ll) & ok] = -1.0
    sig[df["adx14"] < adx * 0.75] = 0.0
    return sig.ffill().fillna(0.0)


def _signal_meanrev_z(df: pd.DataFrame, n: int = 48, entry: float = 1.5, adx: int = 20) -> pd.Series:
    ma = df["close"].rolling(n, min_periods=n).mean()
    sd = df["close"].rolling(n, min_periods=n).std()
    z = (df["close"] - ma) / sd.replace(0, np.nan)

    sig = np.zeros(len(df))
    prev = 0.0
    z_values = z.values
    adx_values = df["adx14"].values

    for i in range(len(df)):
        zi = z_values[i]
        ai = adx_values[i]
        if np.isnan(zi) or np.isnan(ai):
            prev = 0.0
        elif prev == 0:
            if ai <= adx:
                if zi < -entry:
                    prev = 1.0
                elif zi > entry:
                    prev = -1.0
        elif prev == 1:
            if zi >= 0 or zi > entry or ai > adx * 1.25:
                prev = 0.0
        elif prev == -1:
            if zi <= 0 or zi < -entry or ai > adx * 1.25:
                prev = 0.0
        sig[i] = prev

    return pd.Series(sig, index=df.index)


def generate_signals(df: pd.DataFrame, strategy: str, params: Dict[str, Any]) -> pd.Series:
    funcs = {
        "ma_cross": _signal_ma,
        "ma_adx": _signal_ma_adx,
        "ma_adx_vol": _signal_ma_adx_vol,
        "donchian": _signal_donchian,
        "donchian_adx": _signal_donchian_adx,
        "meanrev_z": _signal_meanrev_z,
    }
    if strategy not in funcs:
        raise ValueError(f"Unknown strategy: {strategy}")
    return funcs[strategy](df, **params)


def make_param_grid() -> List[Tuple[str, Dict[str, Any]]]:
    grid: List[Tuple[str, Dict[str, Any]]] = []

    for fast in [12, 24, 48]:
        for slow in [72, 120, 200]:
            if fast < slow:
                grid.append(("ma_cross", {"fast": fast, "slow": slow}))

    for fast in [12, 24, 48]:
        for slow in [72, 120, 200]:
            if fast < slow:
                for adx in [18, 22, 26]:
                    grid.append(("ma_adx", {"fast": fast, "slow": slow, "adx": adx}))
                    grid.append(("ma_adx_vol", {"fast": fast, "slow": slow, "adx": adx}))

    for n in [48, 96, 144, 240]:
        grid.append(("donchian", {"n": n}))
        for adx in [18, 22, 26]:
            grid.append(("donchian_adx", {"n": n, "adx": adx}))

    for n in [24, 48, 96]:
        for entry in [1.5, 2.0]:
            for adx in [15, 20]:
                grid.append(("meanrev_z", {"n": n, "entry": entry, "adx": adx}))

    return grid


# =============================================================================
# 4. Backtest / performance
# =============================================================================

def backtest(
    df: pd.DataFrame,
    signal: pd.Series,
    cost_pips: float = 1.0,
    pip_size: float = 0.01,
) -> pd.DataFrame:
    """
    Cost-adjusted open-to-open backtest.

    signal[t] is calculated after bar t closes.
    position at open[t] = signal[t-1].
    forward return at row t = open[t+1] / open[t] - 1.
    """
    sig = signal.reindex(df.index).fillna(0.0).astype(float)
    pos_open = sig.shift(1).fillna(0.0)

    fwd_ret = df["open"].shift(-1) / df["open"] - 1.0
    gross_ret = pos_open * fwd_ret

    pos_change = pos_open.diff().abs().fillna(pos_open.abs())
    cost = pos_change * ((cost_pips * pip_size / 2.0) / df["open"])

    net_ret = (gross_ret - cost).fillna(0.0)
    if len(net_ret):
        net_ret.iloc[-1] = 0.0

    return pd.DataFrame(
        {
            "ret": net_ret,
            "gross_ret": gross_ret.fillna(0.0),
            "cost": cost.fillna(0.0),
            "position": pos_open,
        },
        index=df.index,
    )


def _extract_trade_stats(ret: pd.Series, pos: pd.Series) -> Dict[str, Any]:
    trade_pnls = []
    holds = []
    dirs = []

    cur_pos = 0.0
    pnl = 0.0
    hold = 0

    for r, p in zip(ret.fillna(0.0).values, pos.fillna(0.0).values):
        if cur_pos == 0:
            if p != 0:
                cur_pos = p
                pnl = r
                hold = 1
                dirs.append(p)
        else:
            if p == cur_pos:
                pnl = (1 + pnl) * (1 + r) - 1
                hold += 1
            else:
                trade_pnls.append(pnl)
                holds.append(hold)
                if p != 0:
                    cur_pos = p
                    pnl = r
                    hold = 1
                    dirs.append(p)
                else:
                    cur_pos = 0.0
                    pnl = 0.0
                    hold = 0

    if cur_pos != 0:
        trade_pnls.append(pnl)
        holds.append(hold)

    if not trade_pnls:
        return {
            "trades": 0,
            "win_rate": np.nan,
            "profit_factor": np.nan,
            "avg_win": np.nan,
            "avg_loss": np.nan,
            "avg_hold": np.nan,
            "long_trades": 0,
            "short_trades": 0,
        }

    arr = np.asarray(trade_pnls)
    wins = arr[arr > 0]
    losses = arr[arr < 0]

    return {
        "trades": int(len(arr)),
        "win_rate": float((arr > 0).mean()),
        "profit_factor": float(wins.sum() / abs(losses.sum())) if losses.size and abs(losses.sum()) > 0 else np.inf,
        "avg_win": float(wins.mean()) if wins.size else 0.0,
        "avg_loss": float(losses.mean()) if losses.size else 0.0,
        "avg_hold": float(np.mean(holds)) if holds else np.nan,
        "long_trades": int((np.asarray(dirs) == 1).sum()),
        "short_trades": int((np.asarray(dirs) == -1).sum()),
    }


def evaluate_performance(bt: pd.DataFrame, bars_per_year: float | None = None) -> Dict[str, Any]:
    ret = bt["ret"].fillna(0.0)
    pos = bt.get("position", pd.Series(0.0, index=bt.index)).fillna(0.0)

    if bars_per_year is None:
        bars_per_year = infer_bars_per_year(ret.index)

    equity = (1 + ret).cumprod()
    total = equity.iloc[-1] - 1 if len(equity) else np.nan

    years = max((ret.index[-1] - ret.index[0]).total_seconds() / (365.25 * 24 * 3600), 1e-9) if len(ret) > 1 else np.nan
    ann = (1 + total) ** (1 / years) - 1 if years and years > 0 and (1 + total) > 0 else np.nan

    std = ret.std()
    sharpe = ret.mean() / std * np.sqrt(bars_per_year) if std and std > 0 else np.nan

    downside = ret[ret < 0].std()
    sortino = ret.mean() / downside * np.sqrt(bars_per_year) if downside and downside > 0 else np.nan

    drawdown = equity / equity.cummax() - 1
    maxdd = drawdown.min() if len(drawdown) else np.nan
    calmar = ann / abs(maxdd) if maxdd < 0 and np.isfinite(ann) else np.nan

    out = {
        "total_return": float(total),
        "ann_return": float(ann) if np.isfinite(ann) else np.nan,
        "sharpe": float(sharpe) if np.isfinite(sharpe) else np.nan,
        "sortino": float(sortino) if np.isfinite(sortino) else np.nan,
        "calmar": float(calmar) if np.isfinite(calmar) else np.nan,
        "max_drawdown": float(maxdd),
        "exposure": float((pos.abs() > 0).mean()),
        "avg_bar_ret": float(ret.mean()),
    }
    out.update(_extract_trade_stats(ret, pos))
    return out


# =============================================================================
# 5. Walk-forward optimization
# =============================================================================

def _month_windows(
    index: pd.DatetimeIndex,
    train_months: int = 24,
    val_months: int = 6,
    test_months: int = 3,
    step_months: int = 3,
) -> List[Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    start = index.min()
    end = index.max()
    windows = []
    t0 = start

    while True:
        train_start = t0
        train_end = train_start + pd.DateOffset(months=train_months)
        val_end = train_end + pd.DateOffset(months=val_months)
        test_end = val_end + pd.DateOffset(months=test_months)
        if test_end > end:
            break
        windows.append((train_start, train_end, val_end, test_end))
        t0 = t0 + pd.DateOffset(months=step_months)

    return windows


def _fast_eval(ret_arr: np.ndarray, pos_arr: np.ndarray, start: int, end: int, bars_per_year: float) -> Dict[str, Any]:
    if end <= start + 2:
        return {
            "total_return": np.nan,
            "ann_return": np.nan,
            "sharpe": np.nan,
            "calmar": np.nan,
            "max_drawdown": np.nan,
            "trades": 0,
            "exposure": np.nan,
            "profit_factor": np.nan,
        }

    r = np.nan_to_num(ret_arr[start:end], nan=0.0)
    p = np.nan_to_num(pos_arr[start:end], nan=0.0)
    equity = np.cumprod(1 + r)
    total = equity[-1] - 1

    years = max((end - start) / bars_per_year, 1e-9)
    ann = (1 + total) ** (1 / years) - 1 if 1 + total > 0 else np.nan

    sd = r.std(ddof=1)
    sharpe = r.mean() / sd * np.sqrt(bars_per_year) if sd > 0 else np.nan

    dd = equity / np.maximum.accumulate(equity) - 1
    maxdd = float(dd.min())
    calmar = ann / abs(maxdd) if maxdd < 0 and np.isfinite(ann) else np.nan

    changes = np.abs(np.diff(np.r_[0, p])) > 1e-9
    trades = int(np.sum(changes & (p != 0)))

    pos_sum = r[r > 0].sum()
    neg_sum = -r[r < 0].sum()
    pf = pos_sum / neg_sum if neg_sum > 0 else (np.inf if pos_sum > 0 else np.nan)

    return {
        "total_return": float(total),
        "ann_return": float(ann) if np.isfinite(ann) else np.nan,
        "sharpe": float(sharpe) if np.isfinite(sharpe) else np.nan,
        "calmar": float(calmar) if np.isfinite(calmar) else np.nan,
        "max_drawdown": float(maxdd),
        "trades": trades,
        "exposure": float((np.abs(p) > 0).mean()),
        "profit_factor": float(pf) if np.isfinite(pf) else pf,
    }


def _score(train_metrics: Dict[str, Any], val_metrics: Dict[str, Any]) -> float:
    if train_metrics["trades"] < 10 or val_metrics["trades"] < 2:
        return -1e9
    if not np.isfinite(val_metrics["sharpe"]):
        return -1e9

    train_sh = train_metrics["sharpe"] if np.isfinite(train_metrics["sharpe"]) else -5.0
    val_sh = val_metrics["sharpe"]
    val_calmar = val_metrics["calmar"] if np.isfinite(val_metrics["calmar"]) else 0.0

    score = val_sh + 0.15 * np.tanh(val_calmar) - 0.15 * abs(val_sh - train_sh)
    if train_sh < 0:
        score -= abs(train_sh) * 0.3
    if val_metrics["max_drawdown"] < -0.08:
        score -= 0.5

    return float(score)


def walk_forward_optimization(
    df: pd.DataFrame,
    family: str,
    param_grid: List[Tuple[str, Dict[str, Any]]],
    cost_pips: float = 1.0,
    train_months: int = 24,
    val_months: int = 6,
    test_months: int = 3,
    step_months: int = 3,
) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """
    WFO by strategy family:
    - Optimize parameters on train / validation only.
    - Concatenate test periods as OOS performance.
    """
    family_grid = [(s, p) for s, p in param_grid if s == family]
    if not family_grid:
        raise ValueError(f"No parameters for family: {family}")

    precomputed: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], pd.DataFrame] = {}
    for strategy, params in family_grid:
        sig = generate_signals(df, strategy, params)
        bt = backtest(df, sig, cost_pips=cost_pips)
        key = (strategy, tuple(sorted(params.items())))
        precomputed[key] = bt

    windows = _month_windows(df.index, train_months, val_months, test_months, step_months)
    index_values = df.index.values
    bars_per_year = infer_bars_per_year(df.index)

    fold_rows = []
    oos_parts = []

    for fold_no, (train_start, train_end, val_end, test_end) in enumerate(windows, 1):
        i0 = np.searchsorted(index_values, np.datetime64(train_start))
        i1 = np.searchsorted(index_values, np.datetime64(train_end))
        i2 = np.searchsorted(index_values, np.datetime64(val_end))
        i3 = np.searchsorted(index_values, np.datetime64(test_end))

        best_score = -1e18
        best_key = None
        best_strategy = None
        best_params = None
        best_train = None
        best_val = None

        for strategy, params in family_grid:
            key = (strategy, tuple(sorted(params.items())))
            bt = precomputed[key]
            r = bt["ret"].values.astype(float)
            p = bt["position"].values.astype(float)

            mt = _fast_eval(r, p, i0, i1, bars_per_year)
            mv = _fast_eval(r, p, i1, i2, bars_per_year)
            score = _score(mt, mv)

            if score > best_score:
                best_score = score
                best_key = key
                best_strategy = strategy
                best_params = params
                best_train = mt
                best_val = mv

        bt_best = precomputed[best_key].iloc[i2:i3].copy()
        test_metrics = evaluate_performance(bt_best, bars_per_year=bars_per_year)
        bt_best["fold"] = fold_no
        oos_parts.append(bt_best)

        fold_rows.append(
            {
                "fold": fold_no,
                "train_start": train_start,
                "train_end": train_end,
                "val_end": val_end,
                "test_end": test_end,
                "family": family,
                "strategy": best_strategy,
                "params": json.dumps(best_params, ensure_ascii=False),
                "score": best_score,
                "train_sharpe": best_train["sharpe"],
                "val_sharpe": best_val["sharpe"],
                "test_total_return": test_metrics["total_return"],
                "test_ann_return": test_metrics["ann_return"],
                "test_sharpe": test_metrics["sharpe"],
                "test_sortino": test_metrics["sortino"],
                "test_calmar": test_metrics["calmar"],
                "test_maxdd": test_metrics["max_drawdown"],
                "test_trades": test_metrics["trades"],
                "test_win_rate": test_metrics["win_rate"],
                "test_pf": test_metrics["profit_factor"],
                "test_exposure": test_metrics["exposure"],
            }
        )

    fold_df = pd.DataFrame(fold_rows)

    if oos_parts:
        oos_bt = pd.concat(oos_parts).sort_index()
        oos_bt = oos_bt[~oos_bt.index.duplicated(keep="first")]
        overall = evaluate_performance(oos_bt, bars_per_year=bars_per_year)
        overall.update(
            {
                "folds": int(len(fold_df)),
                "positive_folds": float((fold_df["test_total_return"] > 0).mean()),
                "fold_avg_return": float(fold_df["test_total_return"].mean()),
                "fold_return_std": float(fold_df["test_total_return"].std()),
                "fold_avg_sharpe": float(fold_df["test_sharpe"].replace([np.inf, -np.inf], np.nan).mean()),
                "fold_total_trades": int(fold_df["test_trades"].sum()),
                "oos_start": str(oos_bt.index.min()),
                "oos_end": str(oos_bt.index.max()),
            }
        )
    else:
        oos_bt = pd.DataFrame()
        overall = {}

    return overall, fold_df, oos_bt


# =============================================================================
# 6. Robustness
# =============================================================================

def _max_drawdown_from_returns(r: np.ndarray) -> float:
    equity = np.cumprod(1 + r)
    dd = equity / np.maximum.accumulate(equity) - 1
    return float(dd.min())


def _block_bootstrap(ret: pd.Series, n_sims: int = 500, block_len: int = 48, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    r = np.nan_to_num(ret.values.astype(float), nan=0.0)
    n = len(r)
    n_blocks = int(np.ceil(n / block_len))
    starts = np.arange(0, max(n - block_len + 1, 1))

    totals = np.empty(n_sims)
    maxdds = np.empty(n_sims)

    for i in range(n_sims):
        chosen = rng.choice(starts, size=n_blocks, replace=True)
        sample = np.concatenate([r[j : j + block_len] for j in chosen])[:n]
        totals[i] = np.cumprod(1 + sample)[-1] - 1
        maxdds[i] = _max_drawdown_from_returns(sample)

    return pd.DataFrame({"total_return": totals, "max_drawdown": maxdds})


def robustness_check(oos_bt: pd.DataFrame, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Robustness checks:
    - Monte Carlo / block bootstrap
    - long vs short contribution
    - high/low ADX and high/low volatility contribution
    """
    features = df.loc[oos_bt.index]
    bars_per_year = infer_bars_per_year(df.index)

    long_ret = oos_bt["ret"].where(oos_bt["position"] > 0, 0.0)
    short_ret = oos_bt["ret"].where(oos_bt["position"] < 0, 0.0)

    long_metrics = evaluate_performance(
        pd.DataFrame({"ret": long_ret, "position": (oos_bt["position"] > 0).astype(float)}, index=oos_bt.index),
        bars_per_year=bars_per_year,
    )
    short_metrics = evaluate_performance(
        pd.DataFrame({"ret": short_ret, "position": -(oos_bt["position"] < 0).astype(float)}, index=oos_bt.index),
        bars_per_year=bars_per_year,
    )

    regimes = {}
    for label, mask in {
        "ADX>=20": features["adx14"] >= 20,
        "ADX<20": features["adx14"] < 20,
        "ATR>=rolling_median": features["atr_pct"] >= features["atr_pct_med200"],
        "ATR<rolling_median": features["atr_pct"] < features["atr_pct_med200"],
    }.items():
        r = oos_bt["ret"].where(mask, 0.0)
        p = oos_bt["position"].where(mask, 0.0)
        regimes[label] = evaluate_performance(pd.DataFrame({"ret": r, "position": p}), bars_per_year=bars_per_year)

    mc = _block_bootstrap(oos_bt["ret"], n_sims=500, block_len=48, seed=7)
    mc_summary = {
        "mc_total_median": float(mc["total_return"].median()),
        "mc_total_5pct": float(mc["total_return"].quantile(0.05)),
        "mc_total_95pct": float(mc["total_return"].quantile(0.95)),
        "mc_maxdd_median": float(mc["max_drawdown"].median()),
        "mc_maxdd_5pct_worst": float(mc["max_drawdown"].quantile(0.05)),
        "mc_maxdd_1pct_worst": float(mc["max_drawdown"].quantile(0.01)),
        "mc_cvar5_total": float(mc.loc[mc["total_return"] <= mc["total_return"].quantile(0.05), "total_return"].mean()),
        "mc_prob_loss": float((mc["total_return"] < 0).mean()),
        "mc_prob_dd_gt20": float((mc["max_drawdown"] < -0.20).mean()),
        "mc_prob_dd_gt30": float((mc["max_drawdown"] < -0.30).mean()),
    }

    return {
        "long_metrics": long_metrics,
        "short_metrics": short_metrics,
        "regime_metrics": regimes,
        "monte_carlo": mc_summary,
    }


# =============================================================================
# 7. Plotting
# =============================================================================

def plot_results(oos_bt: pd.DataFrame, out_prefix: str) -> None:
    equity = (1 + oos_bt["ret"]).cumprod()
    drawdown = equity / equity.cummax() - 1

    plt.figure(figsize=(10, 5))
    plt.plot(equity.index, equity.values)
    plt.title("WFO OOS Equity")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.tight_layout()
    plt.savefig(f"{out_prefix}_equity.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(drawdown.index, drawdown.values)
    plt.title("WFO OOS Drawdown")
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.tight_layout()
    plt.savefig(f"{out_prefix}_drawdown.png", dpi=150)
    plt.close()


# =============================================================================
# 8. Runner
# =============================================================================

def run_one_file(path: str, outdir: str, cost_pips: float = 1.0) -> pd.DataFrame:
    name = os.path.splitext(os.path.basename(path))[0]
    df = load_data(path)
    diagnostics = validate_data(df)
    df = create_features(df)

    os.makedirs(outdir, exist_ok=True)
    pd.DataFrame([diagnostics]).to_csv(os.path.join(outdir, f"{name}_diagnostics.csv"), index=False)

    grid = make_param_grid()
    families = sorted(set(strategy for strategy, _ in grid))

    summary_rows = []
    best = None

    for family in families:
        overall, folds, oos_bt = walk_forward_optimization(
            df=df,
            family=family,
            param_grid=grid,
            cost_pips=cost_pips,
        )

        if not overall:
            continue

        folds.to_csv(os.path.join(outdir, f"{name}_{family}_folds.csv"), index=False)
        oos_bt.to_csv(os.path.join(outdir, f"{name}_{family}_oos_bt.csv"))

        row = {"data": os.path.basename(path), "family": family}
        row.update(overall)
        summary_rows.append(row)

        if best is None or row.get("sharpe", -999) > best[0].get("sharpe", -999):
            best = (row, family, oos_bt)

    summary = pd.DataFrame(summary_rows).sort_values(["sharpe", "ann_return"], ascending=False)
    summary.to_csv(os.path.join(outdir, f"{name}_wfo_summary.csv"), index=False)

    if best is not None:
        best_row, best_family, best_oos = best
        plot_results(best_oos, os.path.join(outdir, f"{name}_{best_family}"))
        robust = robustness_check(best_oos, df)
        with open(os.path.join(outdir, f"{name}_{best_family}_robustness.json"), "w", encoding="utf-8") as f:
            json.dump(robust, f, ensure_ascii=False, indent=2, default=str)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", nargs="+", required=True, help="CSV files to evaluate")
    parser.add_argument("--outdir", default="./usdjpy_wfo_output")
    parser.add_argument("--cost-pips", type=float, default=1.0)
    args = parser.parse_args()

    all_summaries = []
    for path in args.data:
        summary = run_one_file(path, args.outdir, cost_pips=args.cost_pips)
        all_summaries.append(summary)

    if all_summaries:
        final = pd.concat(all_summaries, ignore_index=True)
        final = final.sort_values(["sharpe", "ann_return"], ascending=False)
        final.to_csv(os.path.join(args.outdir, "ALL_wfo_summary.csv"), index=False)
        print(final[["data", "family", "total_return", "ann_return", "sharpe", "calmar", "max_drawdown", "positive_folds"]].to_string(index=False))


if __name__ == "__main__":
    main()
