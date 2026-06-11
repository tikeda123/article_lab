#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USDJPY Quant Strategy Research / Backtest / Walk Forward Optimization

Design principles:
- Signals use only information available at the close of the current bar.
- Trades are assumed to be filled at the next bar open.
- Transaction cost is modeled as round-trip pips; half is charged on entry and half on exit.
- WFO separates train / validation / test. Test is treated as OOS and is reset flat at each fold start.
- Parameter grids are intentionally coarse to reduce overfitting risk.

Dependencies:
    pandas, numpy, matplotlib, scipy, scikit-learn
TA-Lib is not required.
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PIP_SIZE = 0.01  # USDJPY: 1 pip = 0.01 JPY


# ---------------------------------------------------------------------
# 1. Data loading / validation
# ---------------------------------------------------------------------

def load_data(path: str, column_map: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """
    Load CSV into canonical columns:
        datetime, open, high, low, close, volume(optional)

    Supports:
    - headerless tab/comma/space-separated OHLCV
    - headered CSV with common aliases
    - optional explicit column_map, e.g. {"timestamp":"datetime", "Open":"open"}
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    def _read(header):
        try:
            return pd.read_csv(path, sep=None, engine="python", header=header)
        except Exception:
            return pd.read_csv(path, sep="\t", header=header)

    probe = _read(0)
    lower_cols = [str(c).strip().lower() for c in probe.columns]
    header_like = any(x in lower_cols for x in ["datetime", "timestamp", "date", "open", "high", "low", "close"])
    df = probe if header_like else _read(None)

    if df.shape[1] == 1:
        df = pd.read_csv(path, sep="\t", header=0 if header_like else None)

    if column_map:
        df = df.rename(columns=column_map)

    # Normalize header names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # If headerless, assign by position
    if not any(c in df.columns for c in ["datetime", "timestamp", "date", "open"]):
        names = ["datetime", "open", "high", "low", "close", "volume"][: df.shape[1]]
        df = df.iloc[:, : len(names)].copy()
        df.columns = names

    # Alias inference
    aliases = {
        "datetime": ["datetime", "timestamp", "time", "date_time", "date"],
        "open": ["open", "o"],
        "high": ["high", "h"],
        "low": ["low", "l"],
        "close": ["close", "c", "last"],
        "volume": ["volume", "vol", "tick_volume"],
    }
    rename = {}
    for canonical, keys in aliases.items():
        if canonical in df.columns:
            continue
        for k in keys:
            if k in df.columns:
                rename[k] = canonical
                break
    df = df.rename(columns=rename)

    # Handle separate date and time columns if present
    if "datetime" not in df.columns and "date" in df.columns and "time" in df.columns:
        df["datetime"] = df["date"].astype(str) + " " + df["time"].astype(str)

    required = ["datetime", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        # Last fallback by position
        if df.shape[1] >= 5:
            names = ["datetime", "open", "high", "low", "close", "volume"][: df.shape[1]]
            df = df.iloc[:, : len(names)].copy()
            df.columns = names
        else:
            raise ValueError(f"Missing required columns: {missing}")

    keep = ["datetime", "open", "high", "low", "close"] + (["volume"] if "volume" in df.columns else [])
    df = df[keep].copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df = df.dropna(subset=["datetime", "open", "high", "low", "close"])
    df = df.sort_values("datetime").drop_duplicates("datetime", keep="last").reset_index(drop=True)
    return df


def infer_timeframe_minutes(datetime_values: Sequence[pd.Timestamp]) -> int:
    s = pd.Series(datetime_values).sort_values().drop_duplicates()
    deltas = s.diff().dropna().dt.total_seconds() / 60.0
    if deltas.empty:
        return 0
    med = deltas.median()
    small = deltas[deltas <= med * 3]
    mode = small.round().mode()
    return int(mode.iloc[0]) if len(mode) else int(round(med))


def bars_per_year_from_tf(tf_min: int) -> int:
    if tf_min <= 0:
        return 252
    # FX trades roughly 24h x 5d. This gives 30m=12523, 1h=6261, 4h=1565.
    return int(round((365.25 * 24 * 60 / tf_min) * 5 / 7))


def bars_per_year(df: pd.DataFrame) -> int:
    return bars_per_year_from_tf(infer_timeframe_minutes(df["datetime"]))


def validate_data(df: pd.DataFrame) -> Dict:
    """Return diagnostics without using future information for strategy signals."""
    tf = infer_timeframe_minutes(df["datetime"])
    ret = np.log(df["close"]).diff()
    med = ret.median()
    mad = (ret - med).abs().median()

    deltas = df["datetime"].diff().dt.total_seconds() / 60.0
    ohlc_bad = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
        | (df["high"] < df["low"])
    )

    bpy = bars_per_year(df)

    # Efficiency Ratio as a coarse trend/range diagnostic
    n = max(24, int(round((20 * 24 * 60 / max(tf, 1)) * 5 / 7)))
    n = min(n, max(24, len(df) // 5))
    change = df["close"].diff(n).abs()
    path = df["close"].diff().abs().rolling(n, min_periods=n).sum()
    er = change / path.replace(0, np.nan)

    ann_vol_by_year = (ret.groupby(df["datetime"].dt.year).std() * np.sqrt(bpy)).dropna()

    return {
        "start": df["datetime"].min(),
        "end": df["datetime"].max(),
        "rows": int(len(df)),
        "timeframe_minutes": int(tf),
        "duplicates": int(df["datetime"].duplicated().sum()),
        "missing_values": {k: int(v) for k, v in df.isna().sum().to_dict().items()},
        "ohlc_inconsistencies": int(ohlc_bad.sum()),
        "large_gaps_gt_3bars": int((deltas > 3 * tf).sum()) if tf else 0,
        "return_mean_bp": float(ret.mean() * 10000),
        "return_std_bp": float(ret.std() * 10000),
        "return_skew": float(ret.skew()),
        "return_kurtosis": float(ret.kurtosis()),
        "robust_outliers_10mad": int(((ret - med).abs() > 10 * 1.4826 * mad).sum()) if mad and np.isfinite(mad) else 0,
        "ann_vol_by_year": {int(k): float(v) for k, v in ann_vol_by_year.to_dict().items()},
        "efficiency_ratio_lookback": int(n),
        "efficiency_ratio_median": float(er.median()),
        "trend_fraction_er_gt_0_30": float((er > 0.30).mean()),
        "range_fraction_er_lt_0_15": float((er < 0.15).mean()),
    }


# ---------------------------------------------------------------------
# 2. Features / signals
# ---------------------------------------------------------------------

LOOKBACKS = sorted(set([10, 14, 20, 30, 40, 50, 60, 80, 100, 120, 160, 200, 240, 320, 400, 480, 640, 800, 960]))


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create only backward-looking features.
    Donchian highs/lows are shifted by one bar so current bar high/low does not leak into breakout thresholds.
    """
    f = df.copy()
    c, h, l = f["close"], f["high"], f["low"]
    prev_close = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    f["tr"] = tr
    abs_diff = c.diff().abs()

    for n in LOOKBACKS:
        f[f"sma_{n}"] = c.rolling(n, min_periods=n).mean()
        f[f"std_{n}"] = c.rolling(n, min_periods=n).std()
        f[f"atr_{n}"] = tr.rolling(n, min_periods=n).mean()
        f[f"high_{n}"] = h.shift(1).rolling(n, min_periods=n).max()
        f[f"low_{n}"] = l.shift(1).rolling(n, min_periods=n).min()
        f[f"er_{n}"] = c.diff(n).abs() / abs_diff.rolling(n, min_periods=n).sum().replace(0, np.nan)

    f["vol_ratio_40_240"] = f["atr_40"] / f["atr_240"]
    return f


def generate_signals(features: pd.DataFrame, strategy: str, params: Dict) -> pd.Series:
    """
    Strategies:
    - ma_trend: SMA fast/slow trend-following.
    - breakout: Donchian stop-and-reverse breakout.
    - mean_reversion: z-score mean reversion, gated by low Efficiency Ratio.
    - regime_trend: SMA trend only when Efficiency Ratio indicates trend.
    """
    n = len(features)
    c = features["close"].to_numpy(dtype=float)
    sig = np.zeros(n, dtype=np.int8)

    if strategy == "ma_trend":
        fast, slow = int(params["fast"]), int(params["slow"])
        sf = features[f"sma_{fast}"].to_numpy()
        ss = features[f"sma_{slow}"].to_numpy()
        sig = np.where(sf > ss, 1, np.where(sf < ss, -1, 0)).astype(np.int8)
        vr = features["vol_ratio_40_240"].to_numpy()
        mask = (
            (vr >= params.get("vol_min", 0.0))
            & (vr <= params.get("vol_max", np.inf))
            & np.isfinite(vr)
            & np.isfinite(sf)
            & np.isfinite(ss)
        )
        sig[~mask] = 0

    elif strategy == "breakout":
        lb = int(params["lookback"])
        upper = features[f"high_{lb}"].to_numpy()
        lower = features[f"low_{lb}"].to_numpy()
        vr = features["vol_ratio_40_240"].to_numpy()
        vmin = params.get("vol_min", 0.0)
        vmax = params.get("vol_max", np.inf)
        state = 0
        for i in range(n):
            if np.isfinite(upper[i]) and np.isfinite(lower[i]) and np.isfinite(c[i]) and np.isfinite(vr[i]) and vmin <= vr[i] <= vmax:
                if c[i] > upper[i]:
                    state = 1
                elif c[i] < lower[i]:
                    state = -1
            sig[i] = state

    elif strategy == "mean_reversion":
        lb = int(params["lookback"])
        entry = float(params["entry_z"])
        exit_z = float(params.get("exit_z", 0.0))
        er_max = float(params.get("er_max", 0.20))
        sma = features[f"sma_{lb}"].to_numpy()
        std = features[f"std_{lb}"].replace(0, np.nan).to_numpy()
        er = features[f"er_{lb}"].to_numpy()
        z = (c - sma) / std
        state = 0
        for i in range(n):
            zi, eri = z[i], er[i]
            if not (np.isfinite(zi) and np.isfinite(eri)):
                sig[i] = state
                continue

            if state == 1 and (zi >= -exit_z or eri > er_max * 1.5):
                state = 0
            elif state == -1 and (zi <= exit_z or eri > er_max * 1.5):
                state = 0

            if state == 0 and eri <= er_max:
                if zi <= -entry:
                    state = 1
                elif zi >= entry:
                    state = -1
            sig[i] = state

    elif strategy == "regime_trend":
        lb = int(params["lookback"])
        sma = features[f"sma_{lb}"].to_numpy()
        er = features[f"er_{lb}"].to_numpy()
        vr = features["vol_ratio_40_240"].to_numpy()
        raw = np.where(c > sma, 1, np.where(c < sma, -1, 0)).astype(np.int8)
        mask = (
            (er >= params.get("er_min", 0.10))
            & (vr >= params.get("vol_min", 0.0))
            & (vr <= params.get("vol_max", np.inf))
            & np.isfinite(sma)
            & np.isfinite(er)
            & np.isfinite(vr)
        )
        sig = raw
        sig[~mask] = 0

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return pd.Series(sig, index=features.index, name="signal")


def candidate_grid(strategy_filter: Optional[str] = None) -> List[Tuple[str, Dict]]:
    grids: List[Tuple[str, Dict]] = []

    for fast in [20, 50, 100]:
        for slow in [100, 200, 400]:
            for vol_min in [0.0, 0.6]:
                if fast < slow:
                    grids.append(("ma_trend", {"fast": fast, "slow": slow, "vol_min": vol_min, "vol_max": 3.0}))

    for lb in [40, 80, 160, 320]:
        for vol_min in [0.0, 0.8]:
            grids.append(("breakout", {"lookback": lb, "vol_min": vol_min, "vol_max": 3.5}))

    for lb in [40, 80, 160, 320]:
        for entry in [1.5, 2.0]:
            for er_max in [0.12, 0.20, 0.30]:
                grids.append(("mean_reversion", {"lookback": lb, "entry_z": entry, "exit_z": 0.0, "er_max": er_max}))

    for lb in [80, 160, 320, 640]:
        for er_min in [0.08, 0.12, 0.18]:
            for vol_min in [0.0, 0.6]:
                grids.append(("regime_trend", {"lookback": lb, "er_min": er_min, "vol_min": vol_min, "vol_max": 3.0}))

    if strategy_filter and strategy_filter.lower() not in ["all", "meta", "none"]:
        grids = [(s, p) for s, p in grids if s == strategy_filter]
    return grids


# ---------------------------------------------------------------------
# 3. Backtest / evaluation
# ---------------------------------------------------------------------

def backtest(
    df: pd.DataFrame,
    signal: pd.Series | np.ndarray,
    cost_pips: float = 1.0,
    start_i: Optional[int] = None,
    end_i: Optional[int] = None,
) -> pd.DataFrame:
    """
    Vectorized open-to-open backtest.

    Signal timing:
    - signal[t] is computed after close[t].
    - position[t+1] is filled at open[t+1].
    - pnl[t+1] accrues from open[t+1] to open[t+2].

    Cost:
    - cost_pips is round-trip pips.
    - entry or exit charges cost_pips/2.
    - a direct flip charges two sides.
    """
    o = df["open"].to_numpy(dtype=float)
    dt = pd.to_datetime(df["datetime"])
    n = len(o)

    sig = np.asarray(signal, dtype=float)
    sig = np.nan_to_num(sig, nan=0.0)
    sig = np.clip(sig, -1, 1)

    pos = np.zeros(n, dtype=float)
    pos[1:] = sig[:-1]

    if start_i is not None:
        pos[:start_i] = 0.0
    if end_i is not None:
        pos[end_i:] = 0.0

    price_ret = np.zeros(n, dtype=float)
    price_ret[:-1] = (o[1:] - o[:-1]) / o[:-1]

    prev_pos = np.r_[0.0, pos[:-1]]
    turnover = np.abs(pos - prev_pos)
    cost_ret = turnover * (cost_pips / 2.0) * PIP_SIZE / o

    ret = pos * price_ret - cost_ret

    if start_i is None:
        start_i = 0
    if end_i is None:
        end_i = n

    out = pd.DataFrame(
        {
            "ret": ret[start_i:end_i],
            "position": pos[start_i:end_i],
            "turnover": turnover[start_i:end_i],
            "cost_ret": cost_ret[start_i:end_i],
        },
        index=dt.iloc[start_i:end_i].values,
    )
    out.index.name = "datetime"
    out["equity"] = (1.0 + out["ret"]).cumprod()
    out["drawdown"] = out["equity"] / out["equity"].cummax() - 1.0
    return out


def _trade_stats(bt: pd.DataFrame, tf_min: int) -> Dict:
    pos = bt["position"].fillna(0.0).to_numpy()
    ret = bt["ret"].fillna(0.0).to_numpy()

    trades = []
    in_trade = False
    cur_pos = 0
    start = 0
    eq = 1.0
    bars = 0

    for i, (p, r) in enumerate(zip(pos, ret)):
        if p == 0:
            if in_trade:
                trades.append((cur_pos, start, i - 1, bars, eq - 1.0))
                in_trade, cur_pos, eq, bars = False, 0, 1.0, 0
            continue

        if (not in_trade) or p != cur_pos:
            if in_trade:
                trades.append((cur_pos, start, i - 1, bars, eq - 1.0))
            in_trade, cur_pos, start, eq, bars = True, p, i, 1.0, 0

        eq *= 1.0 + r
        bars += 1

    if in_trade:
        trades.append((cur_pos, start, len(pos) - 1, bars, eq - 1.0))

    if not trades:
        return {
            "trades": 0,
            "win_rate": np.nan,
            "profit_factor": np.nan,
            "avg_win": np.nan,
            "avg_loss": np.nan,
            "avg_hold_bars": np.nan,
            "avg_hold_hours": np.nan,
            "long_trades": 0,
            "short_trades": 0,
        }

    t = np.array(trades, dtype=float)
    pnl = t[:, 4]
    sides = t[:, 0]
    holds = t[:, 3]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    profit_factor = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() < 0 else np.inf

    return {
        "trades": int(len(pnl)),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": float(profit_factor) if np.isfinite(profit_factor) else np.inf,
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "avg_hold_bars": float(holds.mean()),
        "avg_hold_hours": float(holds.mean() * tf_min / 60.0),
        "long_trades": int((sides > 0).sum()),
        "short_trades": int((sides < 0).sum()),
    }


def evaluate_performance(bt: pd.DataFrame, bars_per_year_: int, tf_min: int) -> Dict:
    r = bt["ret"].fillna(0.0).to_numpy(dtype=float)
    pos = bt["position"].fillna(0.0).to_numpy(dtype=float)

    if len(r) == 0:
        return {}

    eq = np.cumprod(1.0 + r)
    total = eq[-1] - 1.0
    years = len(r) / bars_per_year_ if bars_per_year_ else np.nan
    annual = eq[-1] ** (1.0 / years) - 1.0 if years and years > 0 and eq[-1] > 0 else np.nan

    sd = r.std(ddof=0)
    sharpe = np.sqrt(bars_per_year_) * r.mean() / sd if sd > 0 else np.nan

    downside = r[r < 0]
    downside_sd = downside.std(ddof=0)
    sortino = np.sqrt(bars_per_year_) * r.mean() / downside_sd if downside_sd > 0 else np.nan

    dd = eq / np.maximum.accumulate(eq) - 1.0
    max_dd = dd.min()
    calmar = annual / abs(max_dd) if max_dd < 0 and np.isfinite(annual) else np.nan

    out = {
        "total_return": float(total),
        "annual_return": float(annual) if np.isfinite(annual) else np.nan,
        "sharpe": float(sharpe) if np.isfinite(sharpe) else np.nan,
        "sortino": float(sortino) if np.isfinite(sortino) else np.nan,
        "calmar": float(calmar) if np.isfinite(calmar) else np.nan,
        "max_drawdown": float(max_dd),
        "exposure": float((np.abs(pos) > 0).mean()),
        "final_equity": float(eq[-1]),
    }
    out.update(_trade_stats(bt, tf_min))
    return out


def monthly_returns(bt: pd.DataFrame) -> pd.Series:
    return (1.0 + bt["ret"].fillna(0.0)).resample("M").prod() - 1.0


# ---------------------------------------------------------------------
# 4. Walk Forward Optimization
# ---------------------------------------------------------------------

def _make_folds(
    df: pd.DataFrame,
    train_months: int = 24,
    val_months: int = 6,
    test_months: int = 3,
) -> List[Dict]:
    dt = pd.to_datetime(df["datetime"])
    start = dt.min()
    end = dt.max()

    folds = []
    train_start = start
    while True:
        train_end = train_start + pd.DateOffset(months=train_months)
        val_end = train_end + pd.DateOffset(months=val_months)
        test_end = val_end + pd.DateOffset(months=test_months)

        if test_end > end:
            break

        train_idx = np.flatnonzero((dt >= train_start) & (dt < train_end))
        val_idx = np.flatnonzero((dt >= train_end) & (dt < val_end))
        test_idx = np.flatnonzero((dt >= val_end) & (dt < test_end))

        if len(train_idx) > 100 and len(val_idx) > 10 and len(test_idx) > 10:
            folds.append(
                {
                    "train_start": train_start,
                    "train_end": train_end,
                    "val_end": val_end,
                    "test_end": test_end,
                    "train_idx": train_idx,
                    "val_idx": val_idx,
                    "test_idx": test_idx,
                }
            )
        train_start = train_start + pd.DateOffset(months=test_months)
    return folds


def _fast_perf(bt: pd.DataFrame, idx: np.ndarray, bars_per_year_: int) -> Dict:
    if len(idx) == 0:
        return {"total_return": 0.0, "annual_return": 0.0, "sharpe": np.nan, "max_drawdown": 0.0, "trades": 0, "exposure": 0.0, "profit_factor_bar": np.nan}

    r = bt["ret"].to_numpy(dtype=float)[idx]
    p = bt["position"].to_numpy(dtype=float)[idx]

    eq = np.cumprod(1.0 + r)
    total = eq[-1] - 1.0
    years = len(r) / bars_per_year_ if bars_per_year_ else np.nan
    annual = eq[-1] ** (1.0 / years) - 1.0 if years and years > 0 and eq[-1] > 0 else np.nan

    sd = r.std(ddof=0)
    sharpe = np.sqrt(bars_per_year_) * r.mean() / sd if sd > 0 else np.nan

    dd = eq / np.maximum.accumulate(eq) - 1.0
    max_dd = dd.min()
    prev = np.r_[0.0, p[:-1]]
    trades = int(((p != prev) & (p != 0)).sum())

    gross_pos = r[r > 0].sum()
    gross_neg = r[r < 0].sum()
    pf_bar = gross_pos / abs(gross_neg) if gross_neg < 0 else np.inf

    return {
        "total_return": float(total),
        "annual_return": float(annual) if np.isfinite(annual) else np.nan,
        "sharpe": float(sharpe) if np.isfinite(sharpe) else np.nan,
        "max_drawdown": float(max_dd),
        "trades": trades,
        "exposure": float((np.abs(p) > 0).mean()),
        "profit_factor_bar": float(pf_bar) if np.isfinite(pf_bar) else np.inf,
    }


def _selection_score(train_perf: Dict, val_perf: Dict) -> float:
    """
    Conservative validation-first objective.
    It rejects candidates with too few train/validation trades and penalizes train/validation instability.
    """
    if train_perf["trades"] < 8 or val_perf["trades"] < 2:
        return -np.inf

    sh_train = train_perf["sharpe"] if np.isfinite(train_perf["sharpe"]) else -3.0
    sh_val = val_perf["sharpe"] if np.isfinite(val_perf["sharpe"]) else -3.0

    instability = max(0.0, abs(sh_train - sh_val) - 1.0)
    score = 0.70 * sh_val + 0.30 * sh_train - 0.35 * instability - 2.0 * abs(val_perf["max_drawdown"])

    if train_perf["total_return"] < -0.02:
        score -= 0.50

    pf = val_perf["profit_factor_bar"]
    if np.isfinite(pf) and pf > 0:
        score += 0.10 * np.log(min(pf, 5.0))

    return float(score)


def walk_forward_optimization(
    df: pd.DataFrame,
    strategy_filter: Optional[str] = None,
    cost_pips: float = 1.0,
    train_months: int = 24,
    val_months: int = 6,
    test_months: int = 3,
) -> Dict:
    """
    Rolling WFO:
    - train window selects candidates eligible for consideration
    - validation window selects parameters
    - test window is OOS and is reset flat at fold start
    """
    tf_min = infer_timeframe_minutes(df["datetime"])
    bpy = bars_per_year(df)
    features = create_features(df)
    grids = candidate_grid(strategy_filter)

    # Precompute full-series signals/backtests for train/validation scoring
    signals: List[pd.Series] = []
    full_bts: List[pd.DataFrame] = []
    for strategy, params in grids:
        sig = generate_signals(features, strategy, params)
        bt = backtest(df, sig, cost_pips=cost_pips)
        signals.append(sig)
        full_bts.append(bt)

    folds = _make_folds(df, train_months, val_months, test_months)

    rows = []
    oos_parts = []
    selected_counts: Dict[str, int] = {}

    for fold_no, fold in enumerate(folds):
        best = None

        for k, (strategy, params) in enumerate(grids):
            train_perf = _fast_perf(full_bts[k], fold["train_idx"], bpy)
            val_perf = _fast_perf(full_bts[k], fold["val_idx"], bpy)
            score = _selection_score(train_perf, val_perf)

            if best is None or score > best["score"]:
                best = {
                    "k": k,
                    "strategy": strategy,
                    "params": params,
                    "score": score,
                    "train_perf": train_perf,
                    "val_perf": val_perf,
                }

        if best is None or not np.isfinite(best["score"]):
            test_idx = fold["test_idx"]
            test_bt = pd.DataFrame(
                {"ret": np.zeros(len(test_idx)), "position": np.zeros(len(test_idx)), "turnover": np.zeros(len(test_idx)), "cost_ret": np.zeros(len(test_idx))},
                index=pd.to_datetime(df["datetime"].iloc[test_idx]).values,
            )
            test_bt.index.name = "datetime"
            test_bt["equity"] = 1.0
            test_bt["drawdown"] = 0.0
            selected_strategy, selected_params = "NONE", {}
            test_perf = evaluate_performance(test_bt, bpy, tf_min)
        else:
            k = best["k"]
            test_idx = fold["test_idx"]
            start_i = int(test_idx[0])
            end_i = int(test_idx[-1]) + 1
            test_bt = backtest(df, signals[k], cost_pips=cost_pips, start_i=start_i, end_i=end_i)
            selected_strategy, selected_params = best["strategy"], best["params"]
            selected_counts[selected_strategy] = selected_counts.get(selected_strategy, 0) + 1
            test_perf = evaluate_performance(test_bt, bpy, tf_min)

        row = {
            "fold": fold_no,
            "strategy": selected_strategy,
            "params": json.dumps(selected_params, sort_keys=True),
            "score": best["score"] if best and np.isfinite(best["score"]) else np.nan,
            "train_start": fold["train_start"],
            "train_end": fold["train_end"],
            "val_end": fold["val_end"],
            "test_end": fold["test_end"],
        }

        if best and np.isfinite(best["score"]):
            row.update({f"train_{k}": v for k, v in best["train_perf"].items()})
            row.update({f"val_{k}": v for k, v in best["val_perf"].items()})
        row.update({f"oos_{k}": v for k, v in test_perf.items()})
        rows.append(row)
        oos_parts.append(test_bt[["ret", "position", "turnover", "cost_ret"]])

    fold_results = pd.DataFrame(rows)
    oos_bt = pd.concat(oos_parts).sort_index() if oos_parts else pd.DataFrame(columns=["ret", "position", "turnover", "cost_ret"])
    if not oos_bt.empty:
        oos_bt["equity"] = (1.0 + oos_bt["ret"]).cumprod()
        oos_bt["drawdown"] = oos_bt["equity"] / oos_bt["equity"].cummax() - 1.0

    oos_perf = evaluate_performance(oos_bt, bpy, tf_min) if not oos_bt.empty else {}

    return {
        "features": features,
        "grids": grids,
        "signals": signals,
        "fold_results": fold_results,
        "oos_bt": oos_bt,
        "oos_performance": oos_perf,
        "selected_counts": selected_counts,
        "timeframe_minutes": tf_min,
        "bars_per_year": bpy,
    }


# ---------------------------------------------------------------------
# 5. Robustness / plots
# ---------------------------------------------------------------------

def _bootstrap_block(ret: np.ndarray, block_size: int = 30, n_sims: int = 1000, seed: int = 42) -> Dict:
    rng = np.random.default_rng(seed)
    ret = np.asarray(ret, dtype=float)
    n = len(ret)
    if n == 0:
        return {}

    starts = np.arange(0, max(1, n - block_size + 1))
    terminal = np.zeros(n_sims)
    max_dd = np.zeros(n_sims)

    for i in range(n_sims):
        chunks = []
        total_len = 0
        while total_len < n:
            s = int(rng.choice(starts))
            block = ret[s : s + block_size]
            chunks.append(block)
            total_len += len(block)
        sim = np.concatenate(chunks)[:n]
        eq = np.cumprod(1.0 + sim)
        dd = eq / np.maximum.accumulate(eq) - 1.0
        terminal[i] = eq[-1] - 1.0
        max_dd[i] = dd.min()

    return {
        "mc_terminal_return_median": float(np.median(terminal)),
        "mc_terminal_return_5pct": float(np.quantile(terminal, 0.05)),
        "mc_terminal_return_95pct": float(np.quantile(terminal, 0.95)),
        "mc_maxdd_median": float(np.median(max_dd)),
        "mc_maxdd_5pct": float(np.quantile(max_dd, 0.05)),
        "mc_prob_terminal_loss": float((terminal < 0).mean()),
        "mc_prob_drawdown_gt_20pct": float((max_dd < -0.20).mean()),
        "mc_prob_drawdown_gt_30pct": float((max_dd < -0.30).mean()),
    }


def robustness_check(
    df: pd.DataFrame,
    strategy_filter: str = "breakout",
    costs: Sequence[float] = (0.5, 1.0, 2.0),
    base_cost: float = 1.0,
    n_bootstrap: int = 1000,
) -> Dict:
    """
    Robustness checks:
    - WFO re-run by transaction cost.
    - Fixed-parameter sensitivity over the WFO OOS span.
    - Block bootstrap on base OOS returns.
    """
    cost_rows = []
    wfo_by_cost = {}
    for c in costs:
        wfo = walk_forward_optimization(df, strategy_filter=strategy_filter, cost_pips=c)
        wfo_by_cost[c] = wfo
        row = {"cost_pips": c}
        row.update(wfo["oos_performance"])
        cost_rows.append(row)

    base = wfo_by_cost.get(base_cost) or walk_forward_optimization(df, strategy_filter=strategy_filter, cost_pips=base_cost)
    folds = _make_folds(df)
    if not folds:
        raise ValueError("Not enough data for WFO.")

    oos_start = int(folds[0]["test_idx"][0])
    oos_end = int(folds[-1]["test_idx"][-1]) + 1
    tf_min = infer_timeframe_minutes(df["datetime"])
    bpy = bars_per_year(df)
    features = base["features"]

    param_rows = []
    for strategy, params in candidate_grid(strategy_filter):
        sig = generate_signals(features, strategy, params)
        bt = backtest(df, sig, cost_pips=base_cost, start_i=oos_start, end_i=oos_end)
        perf = evaluate_performance(bt, bpy, tf_min)
        row = {"strategy": strategy, "params": json.dumps(params, sort_keys=True)}
        # Flatten common params for sorting
        for k, v in params.items():
            row[k] = v
        row.update(perf)
        param_rows.append(row)

    monthly = monthly_returns(base["oos_bt"])
    monthly_cvar_5 = float(monthly[monthly <= monthly.quantile(0.05)].mean()) if len(monthly) else np.nan
    mc = _bootstrap_block(base["oos_bt"]["ret"].to_numpy(), block_size=30, n_sims=n_bootstrap, seed=123)

    return {
        "cost_sensitivity": pd.DataFrame(cost_rows),
        "parameter_sensitivity": pd.DataFrame(param_rows),
        "monthly_returns": monthly,
        "monthly_cvar_5pct": monthly_cvar_5,
        "bootstrap": mc,
        "base_wfo": base,
    }


def plot_results(bt: pd.DataFrame, outdir: str, prefix: str = "strategy") -> Tuple[str, str]:
    os.makedirs(outdir, exist_ok=True)

    equity_path = os.path.join(outdir, f"{prefix}_equity.png")
    dd_path = os.path.join(outdir, f"{prefix}_drawdown.png")

    plt.figure(figsize=(10, 5))
    plt.plot(bt.index, bt["equity"])
    plt.title(f"{prefix} equity")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.tight_layout()
    plt.savefig(equity_path, dpi=150)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(bt.index, bt["drawdown"])
    plt.title(f"{prefix} drawdown")
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.tight_layout()
    plt.savefig(dd_path, dpi=150)
    plt.close()

    return equity_path, dd_path


def benchmark_buy_hold(df: pd.DataFrame, start_i: int, end_i: int, side: int = 1, cost_pips: float = 1.0) -> pd.DataFrame:
    sig = pd.Series(side, index=df.index)
    # For benchmark, enter at OOS start.
    return backtest(df, sig, cost_pips=cost_pips, start_i=start_i, end_i=end_i)


# ---------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------

def _safe_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0].replace("(", "_").replace(")", "_").replace(" ", "_")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="+", required=True, help="CSV files, e.g. USDJPY240.csv")
    parser.add_argument("--outdir", default="usdjpy_wfo_outputs")
    parser.add_argument("--strategy-filter", default="breakout", choices=["ma_trend", "breakout", "mean_reversion", "regime_trend", "all", "meta"])
    parser.add_argument("--cost-pips", type=float, default=1.0)
    parser.add_argument("--bootstrap-sims", type=int, default=500)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    summary_rows = []
    diagnostics_rows = []

    strategy_filter = None if args.strategy_filter in ["all", "meta"] else args.strategy_filter

    for path in args.files:
        name = _safe_name(path)
        print(f"\n=== {path} ===")
        df = load_data(path)
        diag = validate_data(df)
        print(json.dumps({k: v for k, v in diag.items() if k != "ann_vol_by_year"}, indent=2, default=str, ensure_ascii=False))
        diagnostics_rows.append({"file": os.path.basename(path), **{k: v for k, v in diag.items() if k != "ann_vol_by_year"}})

        wfo = walk_forward_optimization(df, strategy_filter=strategy_filter, cost_pips=args.cost_pips)
        perf = wfo["oos_performance"]
        print("OOS performance:", json.dumps(perf, indent=2, ensure_ascii=False))
        print("Selected counts:", wfo["selected_counts"])

        prefix = f"{name}_{args.strategy_filter}_cost{args.cost_pips:g}"
        wfo["fold_results"].to_csv(os.path.join(args.outdir, f"{prefix}_fold_results.csv"), index=False)
        wfo["oos_bt"].to_csv(os.path.join(args.outdir, f"{prefix}_oos_equity.csv"))
        monthly_returns(wfo["oos_bt"]).to_frame("monthly_return").to_csv(os.path.join(args.outdir, f"{prefix}_monthly_returns.csv"))
        plot_results(wfo["oos_bt"], args.outdir, prefix=prefix)

        row = {"file": os.path.basename(path), "strategy_filter": args.strategy_filter, "cost_pips": args.cost_pips}
        row.update(perf)
        summary_rows.append(row)

        # Run robustness only for a single explicit family, because all/meta re-optimization can obscure interpretation.
        if strategy_filter is not None:
            rb = robustness_check(df, strategy_filter=strategy_filter, base_cost=args.cost_pips, n_bootstrap=args.bootstrap_sims)
            rb["cost_sensitivity"].to_csv(os.path.join(args.outdir, f"{prefix}_cost_sensitivity.csv"), index=False)
            rb["parameter_sensitivity"].to_csv(os.path.join(args.outdir, f"{prefix}_parameter_sensitivity.csv"), index=False)
            rb["monthly_returns"].to_frame("monthly_return").to_csv(os.path.join(args.outdir, f"{prefix}_robustness_monthly_returns.csv"))
            pd.DataFrame([{**rb["bootstrap"], "monthly_cvar_5pct": rb["monthly_cvar_5pct"]}]).to_csv(
                os.path.join(args.outdir, f"{prefix}_bootstrap_summary.csv"), index=False
            )

        folds = _make_folds(df)
        if folds:
            start_i = int(folds[0]["test_idx"][0])
            end_i = int(folds[-1]["test_idx"][-1]) + 1
            long_bt = benchmark_buy_hold(df, start_i, end_i, side=1, cost_pips=args.cost_pips)
            long_perf = evaluate_performance(long_bt, bars_per_year(df), infer_timeframe_minutes(df["datetime"]))
            print("Buy&hold long benchmark:", json.dumps(long_perf, indent=2, ensure_ascii=False))

    pd.DataFrame(summary_rows).to_csv(os.path.join(args.outdir, "summary.csv"), index=False)
    pd.DataFrame(diagnostics_rows).to_csv(os.path.join(args.outdir, "diagnostics.csv"), index=False)
    print(f"\nSaved outputs to: {args.outdir}")


if __name__ == "__main__":
    main()
