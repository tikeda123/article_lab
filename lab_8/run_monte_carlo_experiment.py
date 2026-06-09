#!/usr/bin/env python3
"""Run lab_8 BTC crash-filter Monte Carlo experiments.

This script is intentionally self-contained inside lab_8. It reads only
``lab_8/data`` inputs and writes reproducible article materials under
``lab_8/outputs/monte_carlo``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from bisect import bisect_right, insort
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs" / "monte_carlo"

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
HORIZONS = {"24h": 6, "48h": 12}
PRIMARY_RISK_COL = "risk_on_nasdaq"
DEFAULT_N_SIMS = 5000
DEFAULT_SEED = 20260609
LEVERAGES = [1.0, 1.5, 2.0, 3.0, 4.0]
COST_BPS = [0.0, 5.0, 10.0, 20.0]

GROUP_ORDER = [
    "G0_all_crashes",
    "G1_funding_low",
    "G2_risk_on",
    "G3_funding_low_x_risk_on",
    "G4_avoid_high_funding_risk_off",
    "G5_high_funding_x_risk_off",
]

METHOD_ORDER = [
    "original_order",
    "shuffle",
    "iid_bootstrap",
    "block_bootstrap",
    "stationary_bootstrap",
    "regime_aware_bootstrap",
]

GROUP_LABELS = {
    "G0_all_crashes": "G0 all",
    "G1_funding_low": "G1 low funding",
    "G2_risk_on": "G2 risk-on",
    "G3_funding_low_x_risk_on": "G3 low x on",
    "G4_avoid_high_funding_risk_off": "G4 avoid bad",
    "G5_high_funding_x_risk_off": "G5 bad only",
}

METHOD_LABELS = {
    "original_order": "Original",
    "shuffle": "Shuffle",
    "iid_bootstrap": "i.i.d.",
    "block_bootstrap": "Block",
    "stationary_bootstrap": "Stationary",
    "regime_aware_bootstrap": "Regime-aware",
}

SERIES_COLORS = {
    "G0_all_crashes": "#315F9B",
    "G1_funding_low": "#3D8B6D",
    "G2_risk_on": "#7C65A9",
    "G3_funding_low_x_risk_on": "#D4882F",
    "G4_avoid_high_funding_risk_off": "#546A7B",
    "G5_high_funding_x_risk_off": "#B5524A",
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_price(path: Path, prefix: str) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_csv(path, sep="\t", header=None, names=PRICE_COLUMNS)
    df = raw.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    profile = {
        "asset": prefix,
        "file_name": path.name,
        "raw_rows": int(len(raw)),
        "timestamp_parse_fail_rows": int(df["timestamp"].isna().sum()),
        "duplicate_timestamps": int(df["timestamp"].duplicated().sum()),
        "missing_ohlc_rows": int(df[["open", "high", "low", "close"]].isna().any(axis=1).sum()),
        "missing_volume_rows": int(df["volume"].isna().sum()),
    }

    clean = (
        df.dropna(subset=["timestamp", "open", "high", "low", "close"])
        .drop_duplicates("timestamp", keep="last")
        .sort_values("timestamp")
        .set_index("timestamp")
    )
    profile.update(
        {
            "clean_rows": int(len(clean)),
            "start": clean.index.min(),
            "end": clean.index.max(),
            "nonpositive_ohlc_rows": int((clean[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        }
    )
    return clean.rename(columns={col: f"{prefix}_{col}" for col in ["open", "high", "low", "close", "volume"]}), profile


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


def read_funding(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_csv(path)
    funding = raw[raw["symbol"].astype(str).str.upper().eq("BTCUSDT")].copy()
    funding["timestamp"] = pd.to_datetime(funding["funding_timestamp"], errors="coerce")
    funding["funding_rate"] = pd.to_numeric(funding["funding_rate"], errors="coerce")
    funding = (
        funding.dropna(subset=["timestamp", "funding_rate"])
        .sort_values("timestamp")
        .drop_duplicates("timestamp", keep="last")
    )
    funding["funding_percentile_expanding"] = expanding_percentile(funding["funding_rate"])
    profile = {
        "asset": "BTCUSDT_funding",
        "file_name": path.name,
        "raw_rows": int(len(raw)),
        "clean_rows": int(len(funding)),
        "start": funding["timestamp"].min(),
        "end": funding["timestamp"].max(),
        "symbols": ",".join(sorted(raw["symbol"].astype(str).str.upper().unique())),
    }
    return funding[["timestamp", "funding_rate", "funding_percentile_expanding"]], profile


def future_trade_path(panel: pd.DataFrame, bars: int) -> pd.DataFrame:
    open_prices = panel["btc_open"].to_numpy(dtype=float)
    highs = panel["btc_high"].to_numpy(dtype=float)
    lows = panel["btc_low"].to_numpy(dtype=float)
    timestamps = panel.index.to_numpy()
    n = len(panel)

    entry_time = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    exit_time = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    entry_price = np.full(n, np.nan)
    exit_price = np.full(n, np.nan)
    future_return = np.full(n, np.nan)
    mae = np.full(n, np.nan)
    mfe = np.full(n, np.nan)

    for i in range(n):
        entry_i = i + 1
        exit_i = i + 1 + bars
        if exit_i >= n:
            continue
        entry = open_prices[entry_i]
        exit_ = open_prices[exit_i]
        if not math.isfinite(entry) or entry <= 0 or not math.isfinite(exit_):
            continue
        path_high = np.nanmax(highs[entry_i : exit_i + 1])
        path_low = np.nanmin(lows[entry_i : exit_i + 1])
        entry_time[i] = timestamps[entry_i]
        exit_time[i] = timestamps[exit_i]
        entry_price[i] = entry
        exit_price[i] = exit_
        future_return[i] = exit_ / entry - 1.0
        mae[i] = path_low / entry - 1.0 if path_low > 0 else np.nan
        mfe[i] = path_high / entry - 1.0 if path_high > 0 else np.nan

    return pd.DataFrame(
        {
            f"entry_time_{bars}bars": entry_time,
            f"exit_time_{bars}bars": exit_time,
            f"entry_price_{bars}bars": entry_price,
            f"exit_price_{bars}bars": exit_price,
            f"future_return_{bars}bars": future_return,
            f"mae_{bars}bars": mae,
            f"mfe_{bars}bars": mfe,
        },
        index=panel.index,
    )


def build_panel() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    frames = []
    profile_rows = []
    for prefix, file_name in ASSETS.items():
        frame, profile = read_price(DATA_DIR / file_name, prefix)
        frames.append(frame)
        profile_rows.append(profile)

    panel = pd.concat(frames, axis=1, join="inner").sort_index()
    panel["row_pos"] = np.arange(len(panel))

    for prefix in ASSETS:
        close = panel[f"{prefix}_close"]
        panel[f"{prefix}_ret_4h"] = close.pct_change()
        panel[f"{prefix}_log_ret_4h"] = np.log(close / close.shift(1))
        panel[f"{prefix}_log_ret_5d"] = np.log(close / close.shift(30))

    btc_log_ret = panel["btc_log_ret_4h"]
    past_mean = btc_log_ret.shift(1).rolling(ROLLING_SIGMA_WINDOW, min_periods=ROLLING_SIGMA_WINDOW).mean()
    past_std = btc_log_ret.shift(1).rolling(ROLLING_SIGMA_WINDOW, min_periods=ROLLING_SIGMA_WINDOW).std()
    panel["btc_sigma_score_180"] = (btc_log_ret - past_mean) / past_std
    panel["crash_rolling_2sigma"] = panel["btc_sigma_score_180"] <= -2.0

    panel["risk_on_nasdaq"] = panel["nasdaq_log_ret_5d"] > 0
    panel["risk_on_sp500"] = panel["sp500_log_ret_5d"] > 0
    risk_assets = ["nasdaq_log_ret_5d", "sp500_log_ret_5d", "dow_log_ret_5d", "dax_log_ret_5d"]
    panel["risk_on_broad_3of4"] = panel[risk_assets].gt(0).sum(axis=1) >= 3

    for horizon, bars in HORIZONS.items():
        path_df = future_trade_path(panel, bars)
        panel = panel.join(path_df)
        rename_map = {
            f"entry_time_{bars}bars": f"entry_time_{horizon}",
            f"exit_time_{bars}bars": f"exit_time_{horizon}",
            f"entry_price_{bars}bars": f"entry_price_{horizon}",
            f"exit_price_{bars}bars": f"exit_price_{horizon}",
            f"future_return_{bars}bars": f"future_return_{horizon}",
            f"mae_{bars}bars": f"mae_{horizon}",
            f"mfe_{bars}bars": f"mfe_{horizon}",
        }
        panel = panel.rename(columns=rename_map)

    funding, funding_profile = read_funding(DATA_DIR / "funding_rate_history.csv")
    profile_rows.append(funding_profile)
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
    merged["funding_high"] = merged["funding_percentile_expanding"] >= 0.80
    merged["has_funding_regime"] = merged["funding_percentile_expanding"].notna()
    merged["funding_bucket"] = np.select(
        [merged["funding_low"], merged["funding_high"]],
        ["low_or_negative", "high"],
        default="neutral",
    )
    merged.loc[~merged["has_funding_regime"], "funding_bucket"] = "missing"

    data_profile = pd.DataFrame(profile_rows)
    metadata = {
        "panel_rows": int(len(merged)),
        "panel_start": str(merged.index.min()),
        "panel_end": str(merged.index.max()),
        "rolling_sigma_window": ROLLING_SIGMA_WINDOW,
        "cooldown_bars": COOLDOWN_BARS,
        "risk_on_definition": "Nasdaq 5-day log return > 0",
        "funding_low_definition": "expanding percentile <= 20% or funding_rate < 0",
        "funding_high_definition": "expanding percentile >= 80%",
    }
    return merged.sort_index(), data_profile, metadata


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


def build_trade_events(panel: pd.DataFrame) -> pd.DataFrame:
    events = apply_cooldown(panel[panel["crash_rolling_2sigma"].fillna(False)].copy())
    events = events[events["has_funding_regime"]].copy()
    events["event_timestamp"] = events.index
    events["event_year"] = events.index.year
    events["risk_bucket"] = np.where(events[PRIMARY_RISK_COL], "risk_on", "risk_off")
    events["regime_label"] = (
        events["event_year"].astype(str) + "_" + events["risk_bucket"].astype(str) + "_" + events["funding_bucket"].astype(str)
    )
    keep_cols = [
        "event_timestamp",
        "row_pos",
        "event_year",
        "btc_open",
        "btc_high",
        "btc_low",
        "btc_close",
        "btc_log_ret_4h",
        "btc_sigma_score_180",
        "funding_rate",
        "funding_percentile_expanding",
        "funding_low",
        "funding_negative",
        "funding_high",
        "funding_bucket",
        PRIMARY_RISK_COL,
        "risk_on_sp500",
        "risk_on_broad_3of4",
        "risk_bucket",
        "regime_label",
    ]
    for horizon in HORIZONS:
        keep_cols.extend(
            [
                f"entry_time_{horizon}",
                f"exit_time_{horizon}",
                f"entry_price_{horizon}",
                f"exit_price_{horizon}",
                f"future_return_{horizon}",
                f"mae_{horizon}",
                f"mfe_{horizon}",
            ]
        )
    return events[keep_cols].reset_index(drop=True)


def group_masks(events: pd.DataFrame) -> dict[str, pd.Series]:
    risk_on = events[PRIMARY_RISK_COL].fillna(False)
    funding_low = events["funding_low"].fillna(False)
    funding_high = events["funding_high"].fillna(False)
    high_funding_risk_off = funding_high & (~risk_on)
    return {
        "G0_all_crashes": pd.Series(True, index=events.index),
        "G1_funding_low": funding_low,
        "G2_risk_on": risk_on,
        "G3_funding_low_x_risk_on": funding_low & risk_on,
        "G4_avoid_high_funding_risk_off": ~high_funding_risk_off,
        "G5_high_funding_x_risk_off": high_funding_risk_off,
    }


def net_trade_returns(gross_returns: np.ndarray, leverage: float, one_way_cost_bps: float) -> np.ndarray:
    round_trip_cost = 2.0 * one_way_cost_bps / 10_000.0
    return leverage * (gross_returns - round_trip_cost)


def max_losing_streak(returns: np.ndarray) -> int:
    longest = 0
    current = 0
    for ret in returns:
        if ret < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def path_metrics(returns: np.ndarray) -> dict[str, float | bool]:
    if len(returns) == 0:
        return {
            "final_equity": np.nan,
            "final_return_pct": np.nan,
            "max_drawdown_pct": np.nan,
            "max_losing_streak": np.nan,
            "ruined": False,
        }

    factors = 1.0 + returns
    ruined = bool(np.any(factors <= 0.0))
    if ruined:
        first_ruin = int(np.argmax(factors <= 0.0))
        safe_factors = factors[:first_ruin]
        if len(safe_factors):
            equity = np.concatenate([np.cumprod(safe_factors), np.zeros(len(factors) - first_ruin)])
        else:
            equity = np.zeros(len(factors))
    else:
        equity = np.cumprod(factors)

    running_max = np.maximum.accumulate(np.concatenate([[1.0], equity]))[1:]
    drawdown = np.divide(equity, running_max, out=np.zeros_like(equity), where=running_max > 0) - 1.0
    final_equity = float(equity[-1])
    return {
        "final_equity": final_equity,
        "final_return_pct": (final_equity - 1.0) * 100.0,
        "max_drawdown_pct": float(np.min(drawdown) * 100.0),
        "max_losing_streak": max_losing_streak(returns),
        "ruined": ruined,
    }


def profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = returns[returns < 0].sum()
    if losses < 0:
        return float(gains / abs(losses))
    if gains > 0:
        return math.inf
    return math.nan


def original_trade_metrics(
    events: pd.DataFrame,
    group_name: str,
    horizon: str,
    leverage: float,
    one_way_cost_bps: float,
) -> dict[str, object]:
    values = events[f"future_return_{horizon}"].dropna().astype(float).to_numpy()
    net_returns = net_trade_returns(values, leverage, one_way_cost_bps)
    metrics = path_metrics(net_returns)
    return {
        "group": group_name,
        "horizon": horizon,
        "leverage": leverage,
        "one_way_cost_bps": one_way_cost_bps,
        "n_trades": int(len(net_returns)),
        "mean_return_pct": float(np.mean(net_returns) * 100.0) if len(net_returns) else np.nan,
        "median_return_pct": float(np.median(net_returns) * 100.0) if len(net_returns) else np.nan,
        "win_rate_pct": float(np.mean(net_returns > 0) * 100.0) if len(net_returns) else np.nan,
        "profit_factor": profit_factor(net_returns),
        "best_trade_pct": float(np.max(net_returns) * 100.0) if len(net_returns) else np.nan,
        "worst_trade_pct": float(np.min(net_returns) * 100.0) if len(net_returns) else np.nan,
        "final_return_pct": metrics["final_return_pct"],
        "max_drawdown_pct": metrics["max_drawdown_pct"],
        "max_losing_streak": metrics["max_losing_streak"],
        "ruined": metrics["ruined"],
    }


def summarize_simulations(rows: list[dict[str, float | bool]]) -> dict[str, float]:
    if not rows:
        return {
            "n_sims": 0,
            "final_return_median_pct": np.nan,
            "final_return_q05_pct": np.nan,
            "final_return_q01_pct": np.nan,
            "final_return_cvar05_pct": np.nan,
            "mdd_median_pct": np.nan,
            "mdd_q05_pct": np.nan,
            "mdd_q01_pct": np.nan,
            "conditional_expected_drawdown_5_pct": np.nan,
            "prob_dd_30_pct": np.nan,
            "prob_dd_50_pct": np.nan,
            "prob_halving_pct": np.nan,
            "prob_ruin_pct": np.nan,
            "max_losing_streak_median": np.nan,
            "max_losing_streak_q95": np.nan,
        }

    final_returns = np.array([float(row["final_return_pct"]) for row in rows], dtype=float)
    final_equity = np.array([float(row["final_equity"]) for row in rows], dtype=float)
    mdd = np.array([float(row["max_drawdown_pct"]) for row in rows], dtype=float)
    streaks = np.array([float(row["max_losing_streak"]) for row in rows], dtype=float)
    ruined = np.array([bool(row["ruined"]) for row in rows], dtype=bool)

    final_q05 = float(np.nanquantile(final_returns, 0.05))
    mdd_q05 = float(np.nanquantile(mdd, 0.05))
    return {
        "n_sims": int(len(rows)),
        "final_return_median_pct": float(np.nanmedian(final_returns)),
        "final_return_q05_pct": final_q05,
        "final_return_q01_pct": float(np.nanquantile(final_returns, 0.01)),
        "final_return_cvar05_pct": float(np.nanmean(final_returns[final_returns <= final_q05])),
        "mdd_median_pct": float(np.nanmedian(mdd)),
        "mdd_q05_pct": mdd_q05,
        "mdd_q01_pct": float(np.nanquantile(mdd, 0.01)),
        "conditional_expected_drawdown_5_pct": float(np.nanmean(mdd[mdd <= mdd_q05])),
        "prob_dd_30_pct": float(np.nanmean(mdd <= -30.0) * 100.0),
        "prob_dd_50_pct": float(np.nanmean(mdd <= -50.0) * 100.0),
        "prob_halving_pct": float(np.nanmean(final_equity <= 0.50) * 100.0),
        "prob_ruin_pct": float(np.nanmean(ruined) * 100.0),
        "max_losing_streak_median": float(np.nanmedian(streaks)),
        "max_losing_streak_q95": float(np.nanquantile(streaks, 0.95)),
    }


def original_indices(n: int, rng: np.random.Generator, n_sims: int) -> list[np.ndarray]:
    return [np.arange(n)]


def shuffle_indices(n: int, rng: np.random.Generator, n_sims: int) -> list[np.ndarray]:
    return [rng.permutation(n) for _ in range(n_sims)]


def iid_bootstrap_indices(n: int, rng: np.random.Generator, n_sims: int) -> list[np.ndarray]:
    return [rng.integers(0, n, size=n) for _ in range(n_sims)]


def block_bootstrap_indices(n: int, rng: np.random.Generator, n_sims: int, block_len: int) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    n_blocks = int(math.ceil(n / block_len))
    offsets = np.arange(block_len)
    for _ in range(n_sims):
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(start + offsets) % n for start in starts])[:n]
        out.append(idx)
    return out


def stationary_bootstrap_indices(
    n: int,
    rng: np.random.Generator,
    n_sims: int,
    mean_block_len: int,
) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    restart_prob = 1.0 / max(mean_block_len, 1)
    for _ in range(n_sims):
        idx = np.empty(n, dtype=int)
        idx[0] = int(rng.integers(0, n))
        for j in range(1, n):
            if rng.random() < restart_prob:
                idx[j] = int(rng.integers(0, n))
            else:
                idx[j] = (idx[j - 1] + 1) % n
        out.append(idx)
    return out


def regime_aware_bootstrap_indices(
    labels: np.ndarray,
    rng: np.random.Generator,
    n_sims: int,
) -> list[np.ndarray]:
    positions_by_label: dict[object, np.ndarray] = {}
    for label in pd.unique(labels):
        positions_by_label[label] = np.flatnonzero(labels == label)

    out: list[np.ndarray] = []
    for _ in range(n_sims):
        idx = np.empty(len(labels), dtype=int)
        for i, label in enumerate(labels):
            choices = positions_by_label[label]
            idx[i] = int(rng.choice(choices))
        out.append(idx)
    return out


def make_index_sampler(
    method: str,
    labels: np.ndarray,
    block_len: int,
    stationary_mean_block_len: int,
) -> Callable[[int, np.random.Generator, int], list[np.ndarray]]:
    if method == "original_order":
        return original_indices
    if method == "shuffle":
        return shuffle_indices
    if method == "iid_bootstrap":
        return iid_bootstrap_indices
    if method == "block_bootstrap":
        return lambda n, rng, n_sims: block_bootstrap_indices(n, rng, n_sims, block_len)
    if method == "stationary_bootstrap":
        return lambda n, rng, n_sims: stationary_bootstrap_indices(n, rng, n_sims, stationary_mean_block_len)
    if method == "regime_aware_bootstrap":
        return lambda n, rng, n_sims: regime_aware_bootstrap_indices(labels, rng, n_sims)
    raise ValueError(f"Unknown Monte Carlo method: {method}")


def run_monte_carlo(
    selected: pd.DataFrame,
    group_name: str,
    horizon: str,
    method: str,
    n_sims: int,
    seed: int,
    leverage: float,
    one_way_cost_bps: float,
    block_len: int,
    stationary_mean_block_len: int,
) -> dict[str, object]:
    values = selected[f"future_return_{horizon}"].dropna().astype(float).to_numpy()
    selected = selected.dropna(subset=[f"future_return_{horizon}"]).copy()
    labels = selected["regime_label"].astype(str).to_numpy()
    if len(values) == 0:
        summary = summarize_simulations([])
    else:
        actual_sims = 1 if method == "original_order" else n_sims
        seed_key = f"{seed}|{group_name}|{horizon}|{method}|{leverage}|{one_way_cost_bps}"
        rng_seed = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:16], 16) % (2**32)
        rng = np.random.default_rng(rng_seed)
        sampler = make_index_sampler(method, labels, block_len, stationary_mean_block_len)
        index_paths = sampler(len(values), rng, actual_sims)
        sim_rows = []
        for idx in index_paths:
            sampled = values[idx]
            net_returns = net_trade_returns(sampled, leverage, one_way_cost_bps)
            sim_rows.append(path_metrics(net_returns))
        summary = summarize_simulations(sim_rows)

    row: dict[str, object] = {
        "group": group_name,
        "horizon": horizon,
        "method": method,
        "leverage": leverage,
        "one_way_cost_bps": one_way_cost_bps,
        "n_trades": int(len(values)),
    }
    row.update(summary)
    return row


def build_all_tables(
    events: pd.DataFrame,
    n_sims: int,
    seed: int,
    block_len: int,
    stationary_mean_block_len: int,
) -> dict[str, pd.DataFrame]:
    masks = group_masks(events)
    original_rows = []
    main_rows = []
    leverage_rows = []
    cost_rows = []

    for group_name in GROUP_ORDER:
        selected = events.loc[masks[group_name].fillna(False)].copy()
        for horizon in HORIZONS:
            for cost_bps in COST_BPS:
                original_rows.append(original_trade_metrics(selected, group_name, horizon, 1.0, cost_bps))

            for method in METHOD_ORDER:
                main_rows.append(
                    run_monte_carlo(
                        selected,
                        group_name,
                        horizon,
                        method,
                        n_sims,
                        seed,
                        leverage=1.0,
                        one_way_cost_bps=0.0,
                        block_len=block_len,
                        stationary_mean_block_len=stationary_mean_block_len,
                    )
                )

            for leverage in LEVERAGES:
                leverage_rows.append(
                    run_monte_carlo(
                        selected,
                        group_name,
                        horizon,
                        "iid_bootstrap",
                        n_sims,
                        seed,
                        leverage=leverage,
                        one_way_cost_bps=0.0,
                        block_len=block_len,
                        stationary_mean_block_len=stationary_mean_block_len,
                    )
                )

            for cost_bps in COST_BPS:
                cost_rows.append(
                    run_monte_carlo(
                        selected,
                        group_name,
                        horizon,
                        "iid_bootstrap",
                        n_sims,
                        seed,
                        leverage=1.0,
                        one_way_cost_bps=cost_bps,
                        block_len=block_len,
                        stationary_mean_block_len=stationary_mean_block_len,
                    )
                )

    main = pd.DataFrame(main_rows)
    leverage = pd.DataFrame(leverage_rows)
    cost = pd.DataFrame(cost_rows)
    original = pd.DataFrame(original_rows)

    exp1 = main[
        (main["method"].isin(["original_order", "shuffle", "iid_bootstrap", "block_bootstrap", "stationary_bootstrap", "regime_aware_bootstrap"]))
        & (main["horizon"].eq("24h"))
        & (main["group"].isin(["G0_all_crashes", "G1_funding_low", "G2_risk_on", "G3_funding_low_x_risk_on"]))
    ].copy()

    exp2 = main[
        (main["group"].eq("G3_funding_low_x_risk_on"))
        & (main["method"].eq("iid_bootstrap"))
        & (main["horizon"].isin(["24h", "48h"]))
    ].copy()

    exp3 = pd.concat(
        [
            main[
                (main["group"].eq("G3_funding_low_x_risk_on"))
                & (main["horizon"].isin(["24h", "48h"]))
                & (main["method"].eq("iid_bootstrap"))
            ],
            main[
                (main["group"].eq("G2_risk_on"))
                & (main["horizon"].eq("48h"))
                & (main["method"].eq("iid_bootstrap"))
            ],
        ],
        ignore_index=True,
    )

    exp4 = main[
        (main["group"].isin(["G0_all_crashes", "G4_avoid_high_funding_risk_off", "G5_high_funding_x_risk_off"]))
        & (main["method"].eq("iid_bootstrap"))
        & (main["horizon"].isin(["24h", "48h"]))
    ].copy()

    return {
        "original_trade_metrics": original,
        "monte_carlo_summary": main,
        "experiment1_group_comparison": exp1,
        "experiment2_small_sample_iid": exp2,
        "experiment3_horizon_tradeoff": exp3,
        "experiment4_avoid_filter_effect": exp4,
        "experiment5_leverage_sensitivity": leverage,
        "experiment6_cost_sensitivity": cost,
    }


def fmt(value: object, digits: int = 3) -> str:
    if isinstance(value, (bool, np.bool_)):
        return str(bool(value))
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(value):
        return "-"
    return f"{value:.{digits}f}"


def markdown_table(df: pd.DataFrame, columns: list[str], digits: int = 3, max_rows: int | None = None) -> str:
    if df.empty:
        return "_No rows._"
    view = df.loc[:, columns].copy()
    if max_rows is not None:
        view = view.head(max_rows)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in view.iterrows():
        cells = []
        for col in columns:
            value = row[col]
            if isinstance(value, (float, np.floating, int, np.integer, bool, np.bool_)):
                cells.append(fmt(value, digits))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def svg_escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def numeric_label(value: float, suffix: str = "%") -> str:
    if not math.isfinite(value):
        return "-"
    return f"{value:.1f}{suffix}"


def save_horizontal_bar_chart(
    path: Path,
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    subtitle: str,
    x_label: str,
    suffix: str = "%",
    positive_color: str = "#3D8B6D",
    negative_color: str = "#B5524A",
) -> None:
    rows = data[[label_col, value_col]].dropna().copy()
    rows[value_col] = rows[value_col].astype(float)
    width = 1000
    row_h = 38
    top = 92
    bottom = 72
    left = 245
    right = 150
    height = max(360, top + bottom + row_h * len(rows))
    plot_w = width - left - right

    if rows.empty:
        path.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1000\" height=\"220\"></svg>\n", encoding="utf-8")
        return

    min_val = min(0.0, float(rows[value_col].min()))
    max_val = max(0.0, float(rows[value_col].max()))
    if math.isclose(min_val, max_val):
        min_val -= 1.0
        max_val += 1.0
    pad = (max_val - min_val) * 0.08
    min_val -= pad
    max_val += pad

    def x_pos(value: float) -> float:
        return left + ((value - min_val) / (max_val - min_val)) * plot_w

    zero_x = x_pos(0.0)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#1f2933} .muted{fill:#617080} .grid{stroke:#d7dde5;stroke-width:1} .axis{stroke:#667085;stroke-width:1.2}</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="32" y="36" font-size="22" font-weight="700">{svg_escape(title)}</text>',
        f'<text x="32" y="62" font-size="13" class="muted">{svg_escape(subtitle)}</text>',
    ]

    for tick in np.linspace(min_val, max_val, 6):
        tx = x_pos(float(tick))
        parts.append(f'<line x1="{tx:.1f}" y1="{top - 18}" x2="{tx:.1f}" y2="{height - bottom + 6}" class="grid"/>')
        parts.append(f'<text x="{tx:.1f}" y="{height - bottom + 30}" font-size="11" text-anchor="middle" class="muted">{numeric_label(float(tick), suffix)}</text>')
    parts.append(f'<line x1="{zero_x:.1f}" y1="{top - 18}" x2="{zero_x:.1f}" y2="{height - bottom + 6}" class="axis"/>')

    for i, row in enumerate(rows.itertuples(index=False)):
        label = getattr(row, label_col)
        value = float(getattr(row, value_col))
        y = top + i * row_h
        bar_x = min(zero_x, x_pos(value))
        bar_w = abs(x_pos(value) - zero_x)
        color = positive_color if value >= 0 else negative_color
        parts.extend(
            [
                f'<text x="{left - 14}" y="{y + 18}" font-size="13" text-anchor="end">{svg_escape(label)}</text>',
                f'<rect x="{bar_x:.1f}" y="{y}" width="{max(bar_w, 1):.1f}" height="22" rx="3" fill="{color}"/>',
                f'<text x="{width - right + 24}" y="{y + 17}" font-size="12" font-weight="600">{numeric_label(value, suffix)}</text>',
            ]
        )

    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 18}" font-size="12" text-anchor="middle" class="muted">{svg_escape(x_label)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def save_line_chart(
    path: Path,
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    series_col: str,
    title: str,
    subtitle: str,
    x_label: str,
    y_label: str,
    y_suffix: str = "%",
) -> None:
    rows = data[[x_col, y_col, series_col]].dropna().copy()
    rows[x_col] = rows[x_col].astype(float)
    rows[y_col] = rows[y_col].astype(float)
    width = 1000
    height = 520
    left = 86
    right = 260
    top = 84
    bottom = 82
    plot_w = width - left - right
    plot_h = height - top - bottom

    if rows.empty:
        path.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1000\" height=\"220\"></svg>\n", encoding="utf-8")
        return

    x_values = sorted(rows[x_col].unique())
    x_min = min(x_values)
    x_max = max(x_values)
    if math.isclose(x_min, x_max):
        x_min -= 1.0
        x_max += 1.0
    y_min = min(0.0, float(rows[y_col].min()))
    y_max = max(1.0, float(rows[y_col].max()))
    y_max = min(100.0, y_max * 1.12 if y_max > 0 else 1.0)

    def x_pos(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_w

    def y_pos(value: float) -> float:
        return top + (1.0 - ((value - y_min) / (y_max - y_min))) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#1f2933} .muted{fill:#617080} .grid{stroke:#d7dde5;stroke-width:1} .axis{stroke:#667085;stroke-width:1.2}</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="32" y="36" font-size="22" font-weight="700">{svg_escape(title)}</text>',
        f'<text x="32" y="62" font-size="13" class="muted">{svg_escape(subtitle)}</text>',
    ]

    for tick in np.linspace(y_min, y_max, 6):
        ty = y_pos(float(tick))
        parts.append(f'<line x1="{left}" y1="{ty:.1f}" x2="{width - right}" y2="{ty:.1f}" class="grid"/>')
        parts.append(f'<text x="{left - 12}" y="{ty + 4:.1f}" font-size="11" text-anchor="end" class="muted">{numeric_label(float(tick), y_suffix)}</text>')

    for value in x_values:
        tx = x_pos(float(value))
        parts.append(f'<line x1="{tx:.1f}" y1="{top}" x2="{tx:.1f}" y2="{height - bottom}" class="grid"/>')
        parts.append(f'<text x="{tx:.1f}" y="{height - bottom + 26}" font-size="12" text-anchor="middle">{fmt(value, 1)}</text>')

    parts.append(f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" class="axis"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" class="axis"/>')

    legend_y = top
    for series in rows[series_col].drop_duplicates().tolist():
        series_rows = rows[rows[series_col] == series].sort_values(x_col)
        color = SERIES_COLORS.get(str(series), "#315F9B")
        points = " ".join(
            f"{x_pos(float(row[x_col])):.1f},{y_pos(float(row[y_col])):.1f}"
            for _, row in series_rows.iterrows()
        )
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        for _, row in series_rows.iterrows():
            cx = x_pos(float(row[x_col]))
            cy = y_pos(float(row[y_col]))
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="{color}"/>')
        parts.append(f'<rect x="{width - right + 34}" y="{legend_y - 11}" width="14" height="14" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{width - right + 56}" y="{legend_y + 1}" font-size="12">{svg_escape(GROUP_LABELS.get(str(series), series))}</text>')
        legend_y += 25

    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 20}" font-size="12" text-anchor="middle" class="muted">{svg_escape(x_label)}</text>')
    parts.append(f'<text x="22" y="{top + plot_h / 2:.1f}" font-size="12" text-anchor="middle" class="muted" transform="rotate(-90 22 {top + plot_h / 2:.1f})">{svg_escape(y_label)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def generate_figures(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    figure_dir = ensure_dir(OUTPUT_DIR / "figures")
    main = tables["monte_carlo_summary"]
    leverage = tables["experiment5_leverage_sensitivity"]
    cost = tables["experiment6_cost_sensitivity"]

    figure_rows: list[dict[str, str]] = []

    iid24 = main[(main["method"].eq("iid_bootstrap")) & (main["horizon"].eq("24h"))].copy()
    iid24["label"] = iid24["group"].map(GROUP_LABELS)
    iid24["group_order"] = iid24["group"].map({group: i for i, group in enumerate(GROUP_ORDER)})
    iid24 = iid24.sort_values("group_order")

    save_horizontal_bar_chart(
        figure_dir / "figure01_iid_24h_final_return_q05.svg",
        iid24,
        "label",
        "final_return_q05_pct",
        "Experiment 1: 24h Downside Return Tail",
        "i.i.d. bootstrap, 1x leverage, zero cost. Higher is better.",
        "Final return 5th percentile",
    )
    figure_rows.append(
        {
            "file_name": "figures/figure01_iid_24h_final_return_q05.svg",
            "title": "Experiment 1: 24h downside return tail",
            "description": "Compares the 5th percentile of final returns across the six crash groups.",
        }
    )

    iid24_mdd = iid24.copy()
    iid24_mdd["mdd_q05_abs_pct"] = -iid24_mdd["mdd_q05_pct"]
    save_horizontal_bar_chart(
        figure_dir / "figure02_iid_24h_mdd_q05.svg",
        iid24_mdd,
        "label",
        "mdd_q05_abs_pct",
        "Experiment 1: 24h Drawdown Tail",
        "i.i.d. bootstrap, 1x leverage, zero cost. Larger bars mean worse drawdown.",
        "Max drawdown 5th percentile, absolute value",
        positive_color="#B5524A",
    )
    figure_rows.append(
        {
            "file_name": "figures/figure02_iid_24h_mdd_q05.svg",
            "title": "Experiment 1: 24h drawdown tail",
            "description": "Compares adverse max-drawdown tails across the six crash groups.",
        }
    )

    g3_methods = main[main["group"].eq("G3_funding_low_x_risk_on")].copy()
    g3_methods["mdd_q05_abs_pct"] = -g3_methods["mdd_q05_pct"]
    g3_methods["method_order"] = g3_methods["method"].map({method: i for i, method in enumerate(METHOD_ORDER)})
    g3_methods["label"] = g3_methods["horizon"] + " " + g3_methods["method"].map(METHOD_LABELS)
    g3_methods = g3_methods.sort_values(["horizon", "method_order"])
    save_horizontal_bar_chart(
        figure_dir / "figure03_g3_method_mdd_q05.svg",
        g3_methods,
        "label",
        "mdd_q05_abs_pct",
        "Experiment 2: G3 Method Stress",
        "Funding low x risk-on has n=15. Larger bars mean worse drawdown.",
        "Max drawdown 5th percentile, absolute value",
        positive_color="#B5524A",
    )
    figure_rows.append(
        {
            "file_name": "figures/figure03_g3_method_mdd_q05.svg",
            "title": "Experiment 2: G3 method stress",
            "description": "Shows how G3 drawdown tail changes across Monte Carlo methods and horizons.",
        }
    )

    tradeoff = tables["experiment3_horizon_tradeoff"].copy()
    tradeoff["label"] = tradeoff["group"].map(GROUP_LABELS) + " " + tradeoff["horizon"]
    save_horizontal_bar_chart(
        figure_dir / "figure04_horizon_tradeoff_final_return_q05.svg",
        tradeoff,
        "label",
        "final_return_q05_pct",
        "Experiment 3: Horizon Tradeoff",
        "Compares G3 24h/48h with risk-on-only 48h. Higher is better.",
        "Final return 5th percentile",
    )
    figure_rows.append(
        {
            "file_name": "figures/figure04_horizon_tradeoff_final_return_q05.svg",
            "title": "Experiment 3: horizon tradeoff",
            "description": "Contrasts the small G3 cell against the broader 48h risk-on group.",
        }
    )

    leverage_focus = leverage[
        (leverage["group"].isin(["G0_all_crashes", "G3_funding_low_x_risk_on", "G4_avoid_high_funding_risk_off"]))
        & (leverage["horizon"].eq("24h"))
    ].copy()
    save_line_chart(
        figure_dir / "figure05_leverage_prob_dd30.svg",
        leverage_focus,
        "leverage",
        "prob_dd_30_pct",
        "group",
        "Experiment 5: Leverage Sensitivity",
        "i.i.d. bootstrap, 24h horizon, zero cost.",
        "Leverage",
        "Probability of reaching 30% DD",
    )
    figure_rows.append(
        {
            "file_name": "figures/figure05_leverage_prob_dd30.svg",
            "title": "Experiment 5: leverage sensitivity",
            "description": "Shows how 30% drawdown hit probability rises with leverage.",
        }
    )

    cost_focus = cost[
        (cost["group"].isin(["G0_all_crashes", "G3_funding_low_x_risk_on", "G4_avoid_high_funding_risk_off"]))
        & (cost["horizon"].eq("24h"))
    ].copy()
    save_line_chart(
        figure_dir / "figure06_cost_prob_dd30.svg",
        cost_focus,
        "one_way_cost_bps",
        "prob_dd_30_pct",
        "group",
        "Experiment 6: Cost Sensitivity",
        "i.i.d. bootstrap, 24h horizon, 1x leverage.",
        "One-way cost, bps",
        "Probability of reaching 30% DD",
    )
    figure_rows.append(
        {
            "file_name": "figures/figure06_cost_prob_dd30.svg",
            "title": "Experiment 6: cost sensitivity",
            "description": "Shows how 30% drawdown hit probability changes under transaction-cost stress.",
        }
    )

    return pd.DataFrame(figure_rows)


def make_report(
    metadata: dict[str, object],
    data_profile: pd.DataFrame,
    events: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
) -> str:
    main = tables["monte_carlo_summary"]
    original = tables["original_trade_metrics"]
    leverage = tables["experiment5_leverage_sensitivity"]
    cost = tables["experiment6_cost_sensitivity"]

    event_counts = pd.DataFrame(
        [
            {"group": group, "n_events": int(group_masks(events)[group].sum())}
            for group in GROUP_ORDER
        ]
    )

    original_focus = original[
        (original["one_way_cost_bps"].eq(0.0))
        & (original["horizon"].isin(["24h", "48h"]))
        & (original["group"].isin(["G0_all_crashes", "G1_funding_low", "G2_risk_on", "G3_funding_low_x_risk_on", "G4_avoid_high_funding_risk_off", "G5_high_funding_x_risk_off"]))
    ].copy()

    iid_focus = main[
        (main["method"].eq("iid_bootstrap"))
        & (main["horizon"].isin(["24h", "48h"]))
        & (main["group"].isin(["G0_all_crashes", "G1_funding_low", "G2_risk_on", "G3_funding_low_x_risk_on", "G4_avoid_high_funding_risk_off", "G5_high_funding_x_risk_off"]))
    ].copy()

    g3_methods = main[
        (main["group"].eq("G3_funding_low_x_risk_on"))
        & (main["horizon"].isin(["24h", "48h"]))
    ].copy()

    leverage_focus = leverage[
        (leverage["group"].isin(["G0_all_crashes", "G3_funding_low_x_risk_on", "G4_avoid_high_funding_risk_off"]))
        & (leverage["horizon"].eq("24h"))
    ].copy()

    cost_focus = cost[
        (cost["group"].isin(["G0_all_crashes", "G3_funding_low_x_risk_on", "G4_avoid_high_funding_risk_off"]))
        & (cost["horizon"].eq("24h"))
    ].copy()

    lines = [
        "# lab_8 Monte Carlo Experiment Report",
        "",
        "## Scope",
        "",
        "This report tests whether the BTC crash filter candidate from lab_7 survives Monte Carlo stress.",
        "All inputs are read from `lab_8/data`, and all generated artifacts are written under `lab_8/outputs/monte_carlo`.",
        "",
        "This is an educational article experiment, not investment advice or a production trading system.",
        "",
        "## Data and Parameters",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {"item": key, "value": value}
                    for key, value in metadata.items()
                    if key
                    in [
                        "panel_rows",
                        "panel_start",
                        "panel_end",
                        "rolling_sigma_window",
                        "cooldown_bars",
                        "n_sims",
                        "seed",
                        "block_len",
                        "stationary_mean_block_len",
                    ]
                ]
            ),
            ["item", "value"],
        ),
        "",
        "## Input Profile",
        "",
        markdown_table(data_profile, ["asset", "file_name", "clean_rows", "start", "end"], digits=0),
        "",
        "## Group Definitions",
        "",
        markdown_table(event_counts, ["group", "n_events"], digits=0),
        "",
        "## Visual Summary",
        "",
        "These SVG figures are generated without external plotting libraries, so the experiment remains runnable with only `numpy` and `pandas`.",
        "",
        "![Experiment 1 downside return tail](figures/figure01_iid_24h_final_return_q05.svg)",
        "",
        "![Experiment 1 drawdown tail](figures/figure02_iid_24h_mdd_q05.svg)",
        "",
        "![Experiment 2 G3 method stress](figures/figure03_g3_method_mdd_q05.svg)",
        "",
        "![Experiment 3 horizon tradeoff](figures/figure04_horizon_tradeoff_final_return_q05.svg)",
        "",
        "![Experiment 5 leverage sensitivity](figures/figure05_leverage_prob_dd30.svg)",
        "",
        "![Experiment 6 cost sensitivity](figures/figure06_cost_prob_dd30.svg)",
        "",
        "## Original Historical Order",
        "",
        markdown_table(
            original_focus.sort_values(["horizon", "group"]),
            [
                "group",
                "horizon",
                "n_trades",
                "mean_return_pct",
                "win_rate_pct",
                "profit_factor",
                "final_return_pct",
                "max_drawdown_pct",
                "max_losing_streak",
            ],
        ),
        "",
        "## Experiment 1: All Crashes vs Conditional Filters",
        "",
        "The table below uses i.i.d. bootstrap summaries at 1x leverage and zero cost.",
        "",
        markdown_table(
            iid_focus.sort_values(["horizon", "group"]),
            [
                "group",
                "horizon",
                "n_trades",
                "final_return_median_pct",
                "final_return_q05_pct",
                "mdd_median_pct",
                "mdd_q05_pct",
                "prob_dd_30_pct",
                "prob_dd_50_pct",
                "prob_halving_pct",
                "max_losing_streak_q95",
            ],
        ),
        "",
        "## Experiment 2: Small-Sample Stress for G3",
        "",
        markdown_table(
            g3_methods.sort_values(["horizon", "method"]),
            [
                "method",
                "horizon",
                "n_trades",
                "final_return_q05_pct",
                "mdd_q05_pct",
                "conditional_expected_drawdown_5_pct",
                "prob_dd_30_pct",
                "prob_halving_pct",
            ],
        ),
        "",
        "## Experiment 3: 24h Candidate vs 48h Risk-on",
        "",
        markdown_table(
            tables["experiment3_horizon_tradeoff"].sort_values(["horizon", "group"]),
            [
                "group",
                "horizon",
                "n_trades",
                "final_return_median_pct",
                "final_return_q05_pct",
                "mdd_q05_pct",
                "prob_dd_30_pct",
                "prob_halving_pct",
            ],
        ),
        "",
        "## Experiment 4: Avoiding High-Funding Risk-off Crashes",
        "",
        markdown_table(
            tables["experiment4_avoid_filter_effect"].sort_values(["horizon", "group"]),
            [
                "group",
                "horizon",
                "n_trades",
                "final_return_median_pct",
                "final_return_q05_pct",
                "mdd_median_pct",
                "mdd_q05_pct",
                "prob_dd_30_pct",
                "prob_halving_pct",
            ],
        ),
        "",
        "## Experiment 5: Leverage Sensitivity",
        "",
        markdown_table(
            leverage_focus.sort_values(["group", "leverage"]),
            [
                "group",
                "horizon",
                "leverage",
                "final_return_q05_pct",
                "mdd_q05_pct",
                "prob_dd_30_pct",
                "prob_dd_50_pct",
                "prob_halving_pct",
                "prob_ruin_pct",
            ],
        ),
        "",
        "## Experiment 6: Cost Sensitivity",
        "",
        "Costs are one-way bps. The simulation subtracts a round-trip cost of `2 * one_way_cost_bps` from each trade before leverage.",
        "",
        markdown_table(
            cost_focus.sort_values(["group", "one_way_cost_bps"]),
            [
                "group",
                "horizon",
                "one_way_cost_bps",
                "final_return_q05_pct",
                "mdd_q05_pct",
                "prob_dd_30_pct",
                "prob_halving_pct",
            ],
        ),
        "",
        "## Output Files",
        "",
        "- `data_profile.csv`: input data profile.",
        "- `feature_panel.csv`: full timestamp panel with crash, funding, risk-on, and future-return fields.",
        "- `trade_events.csv`: cooldown-filtered BTC crash event table used by Monte Carlo.",
        "- `original_trade_metrics.csv`: historical-order metrics by group, horizon, and cost.",
        "- `monte_carlo_summary.csv`: all main method summaries at 1x leverage and zero cost.",
        "- `experiment1_group_comparison.csv` through `experiment6_cost_sensitivity.csv`: article-focused experiment slices.",
        "- `figure_index.csv`: generated SVG figure inventory.",
        "- `figures/*.svg`: explanatory charts for article use.",
        "- `experiment_metadata.json`: reproducibility parameters.",
        "",
        "## Interpretation Notes",
        "",
        "- G3 has only 15 trades, so a good original-order drawdown is not enough to claim deployability.",
        "- Shuffle tests order risk, while i.i.d. bootstrap tests sample uncertainty.",
        "- Block and stationary bootstraps keep some loss-cluster structure.",
        "- Regime-aware bootstrap samples within year/risk/funding labels, preserving the original regime sequence.",
        "- Leveraged returns are simple returns after round-trip cost, multiplied by leverage. A trade return <= -100% is treated as ruin.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(
    panel: pd.DataFrame,
    data_profile: pd.DataFrame,
    metadata: dict[str, object],
    events: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
) -> None:
    ensure_dir(OUTPUT_DIR)
    data_profile.to_csv(OUTPUT_DIR / "data_profile.csv", index=False)
    panel.reset_index().rename(columns={"index": "timestamp"}).to_csv(OUTPUT_DIR / "feature_panel.csv", index=False)
    events.to_csv(OUTPUT_DIR / "trade_events.csv", index=False)
    for name, table in tables.items():
        table.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
    figure_index = generate_figures(tables)
    figure_index.to_csv(OUTPUT_DIR / "figure_index.csv", index=False)
    with (OUTPUT_DIR / "experiment_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
    report = make_report(metadata, data_profile, events, tables)
    (OUTPUT_DIR / "monte_carlo_experiment_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lab_8 Monte Carlo experiments.")
    parser.add_argument("--n-sims", type=int, default=DEFAULT_N_SIMS, help="Number of Monte Carlo simulations per non-original method.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Base random seed.")
    parser.add_argument("--block-len", type=int, default=5, help="Fixed block length for block bootstrap.")
    parser.add_argument("--stationary-mean-block-len", type=int, default=5, help="Mean block length for stationary bootstrap.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel, data_profile, metadata = build_panel()
    events = build_trade_events(panel)
    metadata.update(
        {
            "n_sims": int(args.n_sims),
            "seed": int(args.seed),
            "block_len": int(args.block_len),
            "stationary_mean_block_len": int(args.stationary_mean_block_len),
            "trade_events_after_cooldown_with_funding": int(len(events)),
            "output_dir": str(OUTPUT_DIR),
        }
    )
    tables = build_all_tables(
        events,
        n_sims=args.n_sims,
        seed=args.seed,
        block_len=args.block_len,
        stationary_mean_block_len=args.stationary_mean_block_len,
    )
    write_outputs(panel, data_profile, metadata, events, tables)
    print(f"Wrote lab_8 Monte Carlo outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
