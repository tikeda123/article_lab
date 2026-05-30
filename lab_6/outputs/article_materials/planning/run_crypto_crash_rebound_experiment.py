#!/usr/bin/env python3
"""Run lab_6 crypto crash-rebound article experiments.

Phase 0 validates the BTC/ETH/SOL 240-minute OHLCV files and writes a
data-profile table plus an article-summary markdown file. Later phases should
reuse the same data-loading assumptions instead of re-inventing CSV parsing.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from statistics import NormalDist
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SYMBOL_FILES = {
    "BTCUSDT": "BTCUSDT240.csv",
    "ETHUSDT": "ETHUSDT240.csv",
    "SOLUSDT": "SOLUSDT240.csv",
}

COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
EXPECTED_INTERVAL = pd.Timedelta(hours=4)
HORIZONS = [1, 2, 3, 6, 12, 18]
HORIZON_HOURS = {horizon: horizon * 4 for horizon in HORIZONS}
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
BINANCE_OPEN_INTEREST_URL = "https://fapi.binance.com/futures/data/openInterestHist"
BINANCE_LIQUIDATION_URL = "https://fapi.binance.com/fapi/v1/allForceOrders"
FUNDING_INTERVAL = pd.Timedelta(hours=8)
OPEN_INTEREST_INTERVAL = pd.Timedelta(hours=4)
OPEN_INTEREST_PERIOD = "4h"
FUNDING_REGIME_ORDER = [
    "funding_low_or_negative",
    "funding_neutral",
    "funding_high",
]
OI_REGIME_ORDER = [
    "price_down_oi_down",
    "price_down_oi_up",
    "price_up_oi_down",
    "price_up_oi_up",
]
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
ANNUAL_YEARS = list(range(2020, 2027))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_t_stat(values: pd.Series) -> float:
    series = values.dropna().astype(float)
    if len(series) < 2:
        return math.nan
    std = series.std(ddof=1)
    if std == 0 or pd.isna(std):
        return math.nan
    return float(series.mean() / (std / math.sqrt(len(series))))


def rate_pct(mask: pd.Series) -> float:
    clean = mask.dropna()
    if len(clean) == 0:
        return math.nan
    return float(clean.mean() * 100.0)


def format_timestamp(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M")


def timestamp_to_ms(value: pd.Timestamp) -> int:
    return int(pd.Timestamp(value).timestamp() * 1000)


def read_ohlcv_csv(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_csv(path, sep="\t", names=COLUMNS, header=None)
    profile: dict[str, object] = {
        "source_file": path.name,
        "raw_rows": int(len(raw)),
    }

    df = raw.copy()
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], format="%Y-%m-%d %H:%M", errors="coerce"
    )

    numeric_parse_failures = {}
    for col in ["open", "high", "low", "close", "volume"]:
        before_na = df[col].isna()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        numeric_parse_failures[f"{col}_parse_fail_rows"] = int(
            df[col].isna().sum() - before_na.sum()
        )

    profile["missing_timestamp_rows"] = int(df["timestamp"].isna().sum())
    profile["duplicate_timestamps"] = int(df["timestamp"].duplicated().sum())
    profile["missing_ohlc_rows"] = int(
        df[["open", "high", "low", "close"]].isna().any(axis=1).sum()
    )
    profile["missing_volume_rows"] = int(df["volume"].isna().sum())
    profile.update(numeric_parse_failures)

    clean = (
        df.dropna(subset=["timestamp", "open", "high", "low", "close"])
        .drop_duplicates(subset=["timestamp"], keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    intervals = clean["timestamp"].diff().dropna()
    gap_mask = intervals != EXPECTED_INTERVAL
    gap_sizes = intervals[gap_mask]

    expected_rows = 0
    if not clean.empty:
        expected_rows = int(
            ((clean["timestamp"].max() - clean["timestamp"].min()) / EXPECTED_INTERVAL)
            + 1
        )

    profile["clean_rows"] = int(len(clean))
    profile["first_timestamp"] = clean["timestamp"].min()
    profile["last_timestamp"] = clean["timestamp"].max()
    profile["expected_rows_if_continuous"] = expected_rows
    profile["missing_rows_implied_by_range"] = int(max(expected_rows - len(clean), 0))
    profile["interval_break_count"] = int(gap_mask.sum())
    profile["max_interval_hours"] = (
        float(intervals.max() / pd.Timedelta(hours=1)) if not intervals.empty else 0.0
    )
    profile["min_interval_hours"] = (
        float(intervals.min() / pd.Timedelta(hours=1)) if not intervals.empty else 0.0
    )
    profile["largest_gap_hours"] = (
        float(gap_sizes.max() / pd.Timedelta(hours=1)) if not gap_sizes.empty else 0.0
    )
    profile["nonpositive_ohlc_rows"] = int(
        (clean[["open", "high", "low", "close"]] <= 0.0).any(axis=1).sum()
    )
    profile["nonpositive_volume_rows"] = int((clean["volume"] <= 0.0).sum())
    profile["high_low_inversion_rows"] = int((clean["high"] < clean["low"]).sum())
    profile["open_outside_high_low_rows"] = int(
        ((clean["open"] > clean["high"]) | (clean["open"] < clean["low"])).sum()
    )
    profile["close_outside_high_low_rows"] = int(
        ((clean["close"] > clean["high"]) | (clean["close"] < clean["low"])).sum()
    )

    return clean, profile


def build_gap_events(symbol: str, df: pd.DataFrame) -> pd.DataFrame:
    intervals = df["timestamp"].diff()
    gap_idx = df.index[(intervals.notna()) & (intervals != EXPECTED_INTERVAL)]
    rows = []
    for idx in gap_idx:
        previous_timestamp = df.loc[idx - 1, "timestamp"]
        current_timestamp = df.loc[idx, "timestamp"]
        interval = current_timestamp - previous_timestamp
        rows.append(
            {
                "symbol": symbol,
                "previous_timestamp": previous_timestamp,
                "current_timestamp": current_timestamp,
                "gap_hours": float(interval / pd.Timedelta(hours=1)),
                "missing_4h_bars": int((interval / EXPECTED_INTERVAL) - 1),
            }
        )
    return pd.DataFrame(rows)


def build_data_profile(
    data_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    frames: dict[str, pd.DataFrame] = {}
    gap_frames = []
    rows = []

    for symbol, file_name in SYMBOL_FILES.items():
        df, profile = read_ohlcv_csv(data_dir / file_name)
        profile["symbol"] = symbol
        frames[symbol] = df
        gap_frames.append(build_gap_events(symbol, df))
        rows.append(profile)

    common_start = max(df["timestamp"].min() for df in frames.values())
    common_end = min(df["timestamp"].max() for df in frames.values())
    expected_common_rows = int(((common_end - common_start) / EXPECTED_INTERVAL) + 1)

    profile_df = pd.DataFrame(rows)
    profile_df.insert(0, "symbol", profile_df.pop("symbol"))
    profile_df["common_start"] = common_start
    profile_df["common_end"] = common_end
    profile_df["expected_common_rows"] = expected_common_rows
    profile_df["common_rows"] = [
        int(
            frames[symbol]
            .loc[
                (frames[symbol]["timestamp"] >= common_start)
                & (frames[symbol]["timestamp"] <= common_end)
            ]
            .shape[0]
        )
        for symbol in profile_df["symbol"].tolist()
    ]
    profile_df["common_period_missing_rows"] = (
        profile_df["expected_common_rows"] - profile_df["common_rows"]
    ).clip(lower=0)

    checks = [
        "missing_timestamp_rows",
        "duplicate_timestamps",
        "missing_ohlc_rows",
        "interval_break_count",
        "missing_rows_implied_by_range",
        "nonpositive_ohlc_rows",
        "high_low_inversion_rows",
        "open_outside_high_low_rows",
        "close_outside_high_low_rows",
        "common_period_missing_rows",
    ]
    profile_df["phase0_status"] = profile_df[checks].sum(axis=1).map(
        lambda value: "PASS" if value == 0 else "WARN"
    )

    meta = {
        "common_start": common_start,
        "common_end": common_end,
        "expected_common_rows": expected_common_rows,
        "symbols": list(SYMBOL_FILES.keys()),
    }
    if gap_frames:
        gap_events = pd.concat(gap_frames, ignore_index=True)
    else:
        gap_events = pd.DataFrame(
            columns=[
                "symbol",
                "previous_timestamp",
                "current_timestamp",
                "gap_hours",
                "missing_4h_bars",
            ]
        )
    return profile_df, gap_events, meta


def load_clean_frames(data_dir: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for symbol, file_name in SYMBOL_FILES.items():
        frame, _ = read_ohlcv_csv(data_dir / file_name)
        frames[symbol] = frame
    return frames


def build_common_frames(
    frames: dict[str, pd.DataFrame], common_start: pd.Timestamp, common_end: pd.Timestamp
) -> dict[str, pd.DataFrame]:
    common_frames = {}
    for symbol, df in frames.items():
        common_frames[symbol] = df[
            (df["timestamp"] >= common_start) & (df["timestamp"] <= common_end)
        ].reset_index(drop=True)
    return common_frames


def fetch_binance_funding_history(
    symbol: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    sleep_seconds: float = 0.08,
) -> pd.DataFrame:
    rows = []
    start_ms = timestamp_to_ms(pd.Timestamp(start))
    end_ms = timestamp_to_ms(pd.Timestamp(end))
    current_ms = start_ms
    while current_ms <= end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "startTime": current_ms,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        request = urllib.request.Request(
            f"{BINANCE_FUNDING_URL}?{params}",
            headers={"User-Agent": "article-lab-phase6/1.0"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, dict):
            raise RuntimeError(f"Binance funding API error for {symbol}: {payload}")
        if not payload:
            break
        rows.extend(payload)
        last_time = int(payload[-1]["fundingTime"])
        next_ms = last_time + 1
        if next_ms <= current_ms:
            break
        current_ms = next_ms
        if len(payload) < 1000:
            break
        time.sleep(sleep_seconds)

    if not rows:
        return pd.DataFrame(
            columns=[
                "symbol",
                "funding_timestamp",
                "funding_time_ms",
                "funding_rate",
                "funding_rate_pct",
                "funding_mark_price",
            ]
        )

    out = pd.DataFrame(rows)
    out["funding_time_ms"] = pd.to_numeric(out["fundingTime"], errors="coerce")
    out["funding_timestamp"] = (
        pd.to_datetime(out["funding_time_ms"], unit="ms", utc=True)
        .dt.tz_convert(None)
        .dt.floor("s")
    )
    out["funding_rate"] = pd.to_numeric(out["fundingRate"], errors="coerce")
    out["funding_rate_pct"] = out["funding_rate"] * 100.0
    out["funding_mark_price"] = pd.to_numeric(out["markPrice"], errors="coerce")
    out = out[
        [
            "symbol",
            "funding_timestamp",
            "funding_time_ms",
            "funding_rate",
            "funding_rate_pct",
            "funding_mark_price",
        ]
    ].dropna(subset=["funding_timestamp", "funding_rate"])
    return out.drop_duplicates(["symbol", "funding_timestamp"]).sort_values(
        ["symbol", "funding_timestamp"]
    )


def load_or_fetch_funding_history(
    output_dir: Path,
    common_start: pd.Timestamp,
    common_end: pd.Timestamp,
    refresh: bool,
) -> pd.DataFrame:
    path = output_dir / "funding_rate_history.csv"
    fetch_start = pd.Timestamp(common_start) - FUNDING_INTERVAL
    fetch_end = pd.Timestamp(common_end) + FUNDING_INTERVAL
    if path.exists() and not refresh:
        cached = pd.read_csv(path)
        cached["funding_timestamp"] = pd.to_datetime(cached["funding_timestamp"])
        cached_symbols = set(cached["symbol"].dropna().unique())
        if set(SYMBOL_FILES.keys()).issubset(cached_symbols):
            min_ts = cached.groupby("symbol")["funding_timestamp"].min()
            max_ts = cached.groupby("symbol")["funding_timestamp"].max()
            if (min_ts <= fetch_start).all() and (max_ts >= common_end).all():
                return cached.sort_values(["symbol", "funding_timestamp"]).reset_index(
                    drop=True
                )

    frames = []
    for symbol in SYMBOL_FILES.keys():
        frames.append(fetch_binance_funding_history(symbol, fetch_start, fetch_end))
    funding = pd.concat(frames, ignore_index=True).sort_values(
        ["symbol", "funding_timestamp"]
    )
    save_csv(funding, path)
    return funding


def fetch_binance_open_interest_history(
    symbol: str, end: pd.Timestamp
) -> pd.DataFrame:
    params = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "period": OPEN_INTEREST_PERIOD,
            "endTime": timestamp_to_ms(pd.Timestamp(end)),
            "limit": 500,
        }
    )
    request = urllib.request.Request(
        f"{BINANCE_OPEN_INTEREST_URL}?{params}",
        headers={"User-Agent": "article-lab-phase7/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        raise RuntimeError(f"Binance OI API error for {symbol}: {payload}")
    if not payload:
        return pd.DataFrame(
            columns=[
                "symbol",
                "oi_timestamp",
                "oi_time_ms",
                "open_interest_contracts",
                "open_interest_value_usdt",
                "cmc_circulating_supply",
            ]
        )

    out = pd.DataFrame(payload)
    out["oi_time_ms"] = pd.to_numeric(out["timestamp"], errors="coerce")
    out["oi_timestamp"] = (
        pd.to_datetime(out["oi_time_ms"], unit="ms", utc=True)
        .dt.tz_convert(None)
        .dt.floor("s")
    )
    out["open_interest_contracts"] = pd.to_numeric(
        out["sumOpenInterest"], errors="coerce"
    )
    out["open_interest_value_usdt"] = pd.to_numeric(
        out["sumOpenInterestValue"], errors="coerce"
    )
    out["cmc_circulating_supply"] = pd.to_numeric(
        out.get("CMCCirculatingSupply"), errors="coerce"
    )
    return (
        out[
            [
                "symbol",
                "oi_timestamp",
                "oi_time_ms",
                "open_interest_contracts",
                "open_interest_value_usdt",
                "cmc_circulating_supply",
            ]
        ]
        .dropna(subset=["oi_timestamp", "open_interest_value_usdt"])
        .drop_duplicates(["symbol", "oi_timestamp"])
        .sort_values(["symbol", "oi_timestamp"])
    )


def load_or_fetch_open_interest_history(
    output_dir: Path, common_end: pd.Timestamp, refresh: bool
) -> pd.DataFrame:
    path = output_dir / "open_interest_history.csv"
    if path.exists() and not refresh:
        cached = pd.read_csv(path)
        cached["oi_timestamp"] = pd.to_datetime(cached["oi_timestamp"])
        cached_symbols = set(cached["symbol"].dropna().unique())
        if set(SYMBOL_FILES.keys()).issubset(cached_symbols):
            max_ts = cached.groupby("symbol")["oi_timestamp"].max()
            if (max_ts >= pd.Timestamp(common_end)).all():
                return cached.sort_values(["symbol", "oi_timestamp"]).reset_index(
                    drop=True
                )

    frames = []
    for symbol in SYMBOL_FILES.keys():
        frames.append(fetch_binance_open_interest_history(symbol, common_end))
    open_interest = pd.concat(frames, ignore_index=True).sort_values(
        ["symbol", "oi_timestamp"]
    )
    save_csv(open_interest, path)
    return open_interest


def probe_liquidation_history_endpoint() -> dict[str, object]:
    params = urllib.parse.urlencode({"symbol": "BTCUSDT", "limit": 1})
    url = f"{BINANCE_LIQUIDATION_URL}?{params}"
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "article-lab-phase7/1.0"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "endpoint": BINANCE_LIQUIDATION_URL,
            "http_status": 200,
            "api_status": "OK",
            "message": "endpoint returned data",
            "sample_type": type(payload).__name__,
        }
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        return {
            "endpoint": BINANCE_LIQUIDATION_URL,
            "http_status": exc.code,
            "api_status": "UNAVAILABLE",
            "message": message,
            "sample_type": "",
        }


def add_return_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    valid_interval = out["timestamp"].diff() == EXPECTED_INTERVAL
    out["log_return_pct"] = np.where(
        valid_interval, np.log(out["close"] / out["close"].shift(1)) * 100.0, np.nan
    )
    out["abs_log_return_pct"] = out["log_return_pct"].abs()
    out["vol20_pct"] = out["log_return_pct"].rolling(20, min_periods=20).std()
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
        valid_future_interval = (
            out["timestamp"].shift(-horizon) - out["timestamp"]
        ) == EXPECTED_INTERVAL * horizon
        out[f"future_return_{horizon}_pct"] = np.where(
            valid_future_interval,
            np.log(out["close"].shift(-horizon) / out["close"]) * 100.0,
            np.nan,
        )
    return out


def build_moment_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for symbol, df in frames.items():
        returns = df["log_return_pct"].dropna().astype(float)
        skipped_gap_returns = int(
            ((df["timestamp"].diff().notna()) & (df["timestamp"].diff() != EXPECTED_INTERVAL)).sum()
        )
        rows.append(
            {
                "symbol": symbol,
                "bar_count": int(len(df)),
                "return_count": int(len(returns)),
                "skipped_gap_return_count": skipped_gap_returns,
                "mean_pct": returns.mean(),
                "median_pct": returns.median(),
                "variance_pct2": returns.var(ddof=1),
                "std_pct": returns.std(ddof=1),
                "skew": returns.skew(),
                "excess_kurtosis": returns.kurt(),
                "min_pct": returns.min(),
                "max_pct": returns.max(),
                "q01_pct": returns.quantile(0.01),
                "q05_pct": returns.quantile(0.05),
                "q95_pct": returns.quantile(0.95),
                "q99_pct": returns.quantile(0.99),
            }
        )
    return pd.DataFrame(rows)


def build_direction_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    conditions = [
        ("up_bar", lambda series: series > 0.0, 1.0),
        ("down_bar", lambda series: series < 0.0, -1.0),
    ]
    for symbol, df in frames.items():
        for direction_label, predicate, continuation_sign in conditions:
            condition = predicate(df["log_return_pct"])
            for horizon in HORIZONS:
                future_col = f"future_return_{horizon}_pct"
                subset = df.loc[condition, ["log_return_pct", future_col]].dropna()
                future = subset[future_col]
                continuation = (future * continuation_sign) > 0.0
                rows.append(
                    {
                        "symbol": symbol,
                        "current_direction": direction_label,
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
    df: pd.DataFrame, tail: str, quantile: float
) -> tuple[pd.Series, float]:
    returns = df["log_return_pct"].dropna()
    if tail == "upper":
        threshold = float(returns.quantile(1.0 - quantile))
        return df["log_return_pct"] >= threshold, threshold
    if tail == "lower":
        threshold = float(returns.quantile(quantile))
        return df["log_return_pct"] <= threshold, threshold
    raise ValueError(f"unknown tail: {tail}")


def build_shock_mr_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for symbol, df in frames.items():
        for level_label, quantile in SHOCK_LEVELS:
            for tail in ["upper", "lower"]:
                condition, threshold = shock_condition(df, tail, quantile)
                mr_sign = -1.0 if tail == "upper" else 1.0
                for horizon in HORIZONS:
                    future_col = f"future_return_{horizon}_pct"
                    subset = df.loc[condition, ["log_return_pct", future_col]].dropna()
                    future = subset[future_col]
                    mr = future * mr_sign
                    rows.append(
                        {
                            "symbol": symbol,
                            "shock_side": tail,
                            "shock_level": level_label,
                            "shock_quantile": quantile,
                            "threshold_pct": threshold,
                            "horizon_bars": horizon,
                            "horizon_hours": HORIZON_HOURS[horizon],
                            "count": int(len(subset)),
                            "current_return_mean_pct": subset[
                                "log_return_pct"
                            ].mean(),
                            "future_return_mean_pct": future.mean(),
                            "future_return_median_pct": future.median(),
                            "future_return_std_pct": future.std(ddof=1),
                            "future_return_t_stat": safe_t_stat(future),
                            "mr_return_mean_pct": mr.mean(),
                            "mr_return_median_pct": mr.median(),
                            "mr_return_std_pct": mr.std(ddof=1),
                            "mr_return_t_stat": safe_t_stat(mr),
                            "mr_win_rate_pct": rate_pct(mr > 0.0),
                        }
                    )
    return pd.DataFrame(rows)


def build_phase2_candidate_summary(shock_mr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for symbol in SYMBOL_FILES.keys():
        for side in ["lower", "upper"]:
            for level_label, _ in SHOCK_LEVELS:
                subset = shock_mr[
                    (shock_mr["symbol"] == symbol)
                    & (shock_mr["shock_side"] == side)
                    & (shock_mr["shock_level"] == level_label)
                ].copy()
                if subset.empty:
                    continue
                best = subset.sort_values(
                    ["mr_return_mean_pct", "mr_win_rate_pct"], ascending=False
                ).iloc[0]
                direction = "long" if side == "lower" else "short"
                rows.append(
                    {
                        "candidate": f"{symbol} {side} {level_label} {direction} MR",
                        "symbol": symbol,
                        "shock_side": side,
                        "shock_level": level_label,
                        "direction": direction,
                        "threshold_pct": best["threshold_pct"],
                        "horizon_bars": int(best["horizon_bars"]),
                        "horizon_hours": int(best["horizon_hours"]),
                        "count": int(best["count"]),
                        "mr_return_mean_pct": best["mr_return_mean_pct"],
                        "mr_return_median_pct": best["mr_return_median_pct"],
                        "mr_win_rate_pct": best["mr_win_rate_pct"],
                        "mr_return_t_stat": best["mr_return_t_stat"],
                    }
                )
    return pd.DataFrame(rows)


def build_vol_regime_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for symbol, df in frames.items():
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
                        "symbol": symbol,
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


def build_shock_mr_by_vol_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for symbol, df in frames.items():
        for level_label, quantile in SHOCK_LEVELS:
            for tail in ["upper", "lower"]:
                shock_mask, threshold = shock_condition(df, tail, quantile)
                mr_sign = -1.0 if tail == "upper" else 1.0
                for regime in VOL_LABELS.values():
                    regime_mask = df["vol_regime"] == regime
                    condition = shock_mask & regime_mask
                    for horizon in HORIZONS:
                        future_col = f"future_return_{horizon}_pct"
                        subset = df.loc[
                            condition,
                            ["log_return_pct", "vol20_pct", future_col],
                        ].dropna()
                        future = subset[future_col]
                        mr = future * mr_sign
                        rows.append(
                            {
                                "symbol": symbol,
                                "vol_regime": regime,
                                "shock_side": tail,
                                "shock_level": level_label,
                                "shock_quantile": quantile,
                                "threshold_pct": threshold,
                                "horizon_bars": horizon,
                                "horizon_hours": HORIZON_HOURS[horizon],
                                "count": int(len(subset)),
                                "vol20_mean_pct": subset["vol20_pct"].mean(),
                                "current_return_mean_pct": subset[
                                    "log_return_pct"
                                ].mean(),
                                "future_return_mean_pct": future.mean(),
                                "future_return_median_pct": future.median(),
                                "future_return_std_pct": future.std(ddof=1),
                                "future_return_t_stat": safe_t_stat(future),
                                "mr_return_mean_pct": mr.mean(),
                                "mr_return_median_pct": mr.median(),
                                "mr_return_std_pct": mr.std(ddof=1),
                                "mr_return_t_stat": safe_t_stat(mr),
                                "mr_win_rate_pct": rate_pct(mr > 0.0),
                            }
                        )
    return pd.DataFrame(rows)


def build_phase3_lower5_by_vol_candidate_summary(
    shock_mr_by_vol: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    subset_all = shock_mr_by_vol[
        (shock_mr_by_vol["shock_side"] == "lower")
        & (shock_mr_by_vol["shock_level"] == "5pct")
    ].copy()
    for symbol in SYMBOL_FILES.keys():
        for regime in VOL_LABELS.values():
            subset = subset_all[
                (subset_all["symbol"] == symbol)
                & (subset_all["vol_regime"] == regime)
            ].copy()
            if subset.empty:
                continue
            best = subset.sort_values(
                ["mr_return_mean_pct", "mr_win_rate_pct"], ascending=False
            ).iloc[0]
            rows.append(
                {
                    "candidate": f"{symbol} lower 5pct {regime} long MR",
                    "symbol": symbol,
                    "vol_regime": regime,
                    "threshold_pct": best["threshold_pct"],
                    "horizon_bars": int(best["horizon_bars"]),
                    "horizon_hours": int(best["horizon_hours"]),
                    "count": int(best["count"]),
                    "vol20_mean_pct": best["vol20_mean_pct"],
                    "current_return_mean_pct": best["current_return_mean_pct"],
                    "mr_return_mean_pct": best["mr_return_mean_pct"],
                    "mr_return_median_pct": best["mr_return_median_pct"],
                    "mr_win_rate_pct": best["mr_win_rate_pct"],
                    "mr_return_t_stat": best["mr_return_t_stat"],
                }
            )
    return pd.DataFrame(rows)


def attach_funding_features(
    frames: dict[str, pd.DataFrame], funding: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, float]]]:
    funded_frames: dict[str, pd.DataFrame] = {}
    thresholds: dict[str, dict[str, float]] = {}
    for symbol, df in frames.items():
        symbol_funding = funding[funding["symbol"] == symbol].copy().sort_values(
            "funding_timestamp"
        )
        if symbol_funding.empty:
            out = df.copy()
            out["funding_timestamp"] = pd.NaT
            out["funding_rate"] = np.nan
            out["funding_rate_pct"] = np.nan
            out["funding_rate_24h_sum_pct"] = np.nan
            out["funding_mark_price"] = np.nan
            out["funding_regime"] = pd.NA
            thresholds[symbol] = {
                "funding_q20_pct": math.nan,
                "funding_q80_pct": math.nan,
            }
            funded_frames[symbol] = out
            continue

        symbol_funding["funding_rate_24h_sum_pct"] = (
            symbol_funding["funding_rate_pct"].rolling(3, min_periods=1).sum()
        )
        common_funding = symbol_funding[
            (symbol_funding["funding_timestamp"] >= df["timestamp"].min())
            & (symbol_funding["funding_timestamp"] <= df["timestamp"].max())
        ]
        q20 = float(common_funding["funding_rate_pct"].quantile(0.20))
        q80 = float(common_funding["funding_rate_pct"].quantile(0.80))
        thresholds[symbol] = {
            "funding_q20_pct": q20,
            "funding_q80_pct": q80,
        }
        out = pd.merge_asof(
            df.sort_values("timestamp"),
            symbol_funding[
                [
                    "funding_timestamp",
                    "funding_rate",
                    "funding_rate_pct",
                    "funding_rate_24h_sum_pct",
                    "funding_mark_price",
                ]
            ],
            left_on="timestamp",
            right_on="funding_timestamp",
            direction="backward",
            tolerance=FUNDING_INTERVAL + pd.Timedelta(minutes=1),
        )
        out["funding_regime"] = pd.NA
        rate = out["funding_rate_pct"]
        out.loc[rate >= q80, "funding_regime"] = "funding_high"
        out.loc[(rate <= q20) | (rate < 0.0), "funding_regime"] = (
            "funding_low_or_negative"
        )
        out.loc[rate.notna() & out["funding_regime"].isna(), "funding_regime"] = (
            "funding_neutral"
        )
        funded_frames[symbol] = out.reset_index(drop=True)
    return funded_frames, thresholds


def build_funding_profile(
    funding: pd.DataFrame,
    funded_frames: dict[str, pd.DataFrame],
    thresholds: dict[str, dict[str, float]],
) -> pd.DataFrame:
    rows = []
    for symbol in SYMBOL_FILES.keys():
        symbol_funding = funding[funding["symbol"] == symbol].copy().sort_values(
            "funding_timestamp"
        )
        frame = funded_frames[symbol]
        common_funding = symbol_funding[
            (symbol_funding["funding_timestamp"] >= frame["timestamp"].min())
            & (symbol_funding["funding_timestamp"] <= frame["timestamp"].max())
        ].copy()
        intervals = common_funding["funding_timestamp"].diff().dropna()
        interval_breaks = (
            (intervals - FUNDING_INTERVAL).abs() > pd.Timedelta(seconds=2)
        )
        lower5_mask, _ = shock_condition(frame, "lower", 0.05)
        lower5 = frame.loc[lower5_mask]
        rows.append(
            {
                "symbol": symbol,
                "source": "Binance USD-M Futures fundingRate API",
                "raw_funding_rows": int(len(symbol_funding)),
                "common_period_funding_rows": int(len(common_funding)),
                "first_funding_timestamp": common_funding[
                    "funding_timestamp"
                ].min(),
                "last_funding_timestamp": common_funding["funding_timestamp"].max(),
                "funding_interval_break_count": int(interval_breaks.sum()),
                "funding_rate_mean_pct": common_funding["funding_rate_pct"].mean(),
                "funding_rate_median_pct": common_funding[
                    "funding_rate_pct"
                ].median(),
                "funding_rate_q20_pct": thresholds[symbol]["funding_q20_pct"],
                "funding_rate_q80_pct": thresholds[symbol]["funding_q80_pct"],
                "funding_rate_min_pct": common_funding["funding_rate_pct"].min(),
                "funding_rate_max_pct": common_funding["funding_rate_pct"].max(),
                "negative_funding_share_pct": rate_pct(
                    common_funding["funding_rate_pct"] < 0.0
                ),
                "common_bar_count": int(len(frame)),
                "missing_funding_bar_count": int(frame["funding_rate_pct"].isna().sum()),
                "missing_funding_bar_share_pct": rate_pct(
                    frame["funding_rate_pct"].isna()
                ),
                "lower5_signal_count": int(len(lower5)),
                "lower5_missing_funding_count": int(
                    lower5["funding_rate_pct"].isna().sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_funding_lookup(
    funding: pd.DataFrame,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    lookup = {}
    for symbol, part in funding.sort_values("funding_timestamp").groupby("symbol"):
        timestamps = part["funding_timestamp"].to_numpy(dtype="datetime64[ns]")
        cumulative = np.concatenate(
            [[0.0], part["funding_rate_pct"].astype(float).cumsum().to_numpy()]
        )
        lookup[symbol] = (timestamps, cumulative)
    return lookup


def funding_sum_between(
    lookup: dict[str, tuple[np.ndarray, np.ndarray]],
    symbol: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> float:
    if symbol not in lookup or pd.isna(start) or pd.isna(end):
        return math.nan
    timestamps, cumulative = lookup[symbol]
    start_value = np.datetime64(pd.Timestamp(start), "ns")
    end_value = np.datetime64(pd.Timestamp(end), "ns")
    start_idx = int(np.searchsorted(timestamps, start_value, side="right"))
    end_idx = int(np.searchsorted(timestamps, end_value, side="right"))
    if end_idx < start_idx:
        return math.nan
    return float(cumulative[end_idx] - cumulative[start_idx])


def build_shock_mr_by_funding_events(
    frames: dict[str, pd.DataFrame],
    funding: pd.DataFrame,
    thresholds: dict[str, dict[str, float]],
) -> pd.DataFrame:
    rows = []
    funding_lookup = build_funding_lookup(funding)
    for symbol, df in frames.items():
        shock_mask, threshold = shock_condition(df, "lower", 0.05)
        for horizon in HORIZONS:
            future_col = f"future_return_{horizon}_pct"
            exit_timestamp = df["timestamp"].shift(-horizon)
            selected = df.loc[
                shock_mask & df["funding_regime"].notna(),
                [
                    "timestamp",
                    "log_return_pct",
                    "funding_timestamp",
                    "funding_rate_pct",
                    "funding_rate_24h_sum_pct",
                    "funding_regime",
                    future_col,
                ],
            ].dropna(subset=[future_col, "funding_rate_pct"])
            for idx, row in selected.iterrows():
                exit_ts = exit_timestamp.loc[idx]
                holding_funding_sum = funding_sum_between(
                    funding_lookup, symbol, row["timestamp"], exit_ts
                )
                gross_return = float(row[future_col])
                adjusted_return = gross_return - holding_funding_sum
                rows.append(
                    {
                        "symbol": symbol,
                        "shock_side": "lower",
                        "shock_level": "5pct",
                        "threshold_pct": threshold,
                        "horizon_bars": horizon,
                        "horizon_hours": HORIZON_HOURS[horizon],
                        "signal_timestamp": row["timestamp"],
                        "exit_timestamp": exit_ts,
                        "signal_return_pct": row["log_return_pct"],
                        "funding_timestamp": row["funding_timestamp"],
                        "funding_rate_pct": row["funding_rate_pct"],
                        "funding_rate_24h_sum_pct": row[
                            "funding_rate_24h_sum_pct"
                        ],
                        "funding_regime": row["funding_regime"],
                        "funding_q20_pct": thresholds[symbol]["funding_q20_pct"],
                        "funding_q80_pct": thresholds[symbol]["funding_q80_pct"],
                        "holding_funding_sum_pct": holding_funding_sum,
                        "gross_mr_return_pct": gross_return,
                        "funding_adjusted_mr_return_pct": adjusted_return,
                    }
                )
    return pd.DataFrame(rows)


def build_shock_mr_by_funding_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, part in events.groupby(
        ["symbol", "funding_regime", "horizon_bars", "horizon_hours"], sort=False
    ):
        symbol, funding_regime, horizon_bars, horizon_hours = keys
        gross = part["gross_mr_return_pct"].astype(float)
        adjusted = part["funding_adjusted_mr_return_pct"].astype(float)
        rows.append(
            {
                "symbol": symbol,
                "funding_regime": funding_regime,
                "shock_side": "lower",
                "shock_level": "5pct",
                "threshold_pct": part["threshold_pct"].iloc[0],
                "funding_q20_pct": part["funding_q20_pct"].iloc[0],
                "funding_q80_pct": part["funding_q80_pct"].iloc[0],
                "horizon_bars": int(horizon_bars),
                "horizon_hours": int(horizon_hours),
                "count": int(len(part)),
                "signal_return_mean_pct": part["signal_return_pct"].mean(),
                "funding_rate_mean_pct": part["funding_rate_pct"].mean(),
                "funding_rate_24h_sum_mean_pct": part[
                    "funding_rate_24h_sum_pct"
                ].mean(),
                "holding_funding_sum_mean_pct": part[
                    "holding_funding_sum_pct"
                ].mean(),
                "gross_mr_return_mean_pct": gross.mean(),
                "gross_mr_return_median_pct": gross.median(),
                "gross_mr_win_rate_pct": rate_pct(gross > 0.0),
                "gross_mr_return_t_stat": safe_t_stat(gross),
                "funding_adjusted_mr_return_mean_pct": adjusted.mean(),
                "funding_adjusted_mr_return_median_pct": adjusted.median(),
                "funding_adjusted_mr_win_rate_pct": rate_pct(adjusted > 0.0),
                "funding_adjusted_mr_return_t_stat": safe_t_stat(adjusted),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    regime_order = {label: idx for idx, label in enumerate(FUNDING_REGIME_ORDER)}
    out["_regime_order"] = out["funding_regime"].map(regime_order)
    return out.sort_values(["symbol", "_regime_order", "horizon_bars"]).drop(
        columns=["_regime_order"]
    )


def attach_open_interest_features(
    frames: dict[str, pd.DataFrame], open_interest: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    oi_frames: dict[str, pd.DataFrame] = {}
    for symbol, df in frames.items():
        symbol_oi = open_interest[open_interest["symbol"] == symbol].copy().sort_values(
            "oi_timestamp"
        )
        if symbol_oi.empty:
            out = df.copy()
            out["oi_timestamp"] = pd.NaT
            out["open_interest_contracts"] = np.nan
            out["open_interest_value_usdt"] = np.nan
            out["oi_value_change_4h_pct"] = np.nan
            out["oi_value_change_24h_pct"] = np.nan
            out["oi_regime"] = pd.NA
            oi_frames[symbol] = out
            continue

        valid_oi_interval = symbol_oi["oi_timestamp"].diff() == OPEN_INTEREST_INTERVAL
        symbol_oi["oi_value_change_4h_pct"] = np.where(
            valid_oi_interval,
            np.log(
                symbol_oi["open_interest_value_usdt"]
                / symbol_oi["open_interest_value_usdt"].shift(1)
            )
            * 100.0,
            np.nan,
        )
        valid_24h_interval = (
            symbol_oi["oi_timestamp"] - symbol_oi["oi_timestamp"].shift(6)
        ) == OPEN_INTEREST_INTERVAL * 6
        symbol_oi["oi_value_change_24h_pct"] = np.where(
            valid_24h_interval,
            np.log(
                symbol_oi["open_interest_value_usdt"]
                / symbol_oi["open_interest_value_usdt"].shift(6)
            )
            * 100.0,
            np.nan,
        )
        out = pd.merge_asof(
            df.sort_values("timestamp"),
            symbol_oi[
                [
                    "oi_timestamp",
                    "open_interest_contracts",
                    "open_interest_value_usdt",
                    "cmc_circulating_supply",
                    "oi_value_change_4h_pct",
                    "oi_value_change_24h_pct",
                ]
            ],
            left_on="timestamp",
            right_on="oi_timestamp",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=1),
        )
        out["oi_regime"] = pd.NA
        price_down = out["log_return_pct"] < 0.0
        price_up = out["log_return_pct"] > 0.0
        oi_up = out["oi_value_change_24h_pct"] > 0.0
        oi_down = out["oi_value_change_24h_pct"] <= 0.0
        out.loc[price_down & oi_down, "oi_regime"] = "price_down_oi_down"
        out.loc[price_down & oi_up, "oi_regime"] = "price_down_oi_up"
        out.loc[price_up & oi_down, "oi_regime"] = "price_up_oi_down"
        out.loc[price_up & oi_up, "oi_regime"] = "price_up_oi_up"
        oi_frames[symbol] = out.reset_index(drop=True)
    return oi_frames


def build_oi_profile(
    open_interest: pd.DataFrame, oi_frames: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    rows = []
    for symbol in SYMBOL_FILES.keys():
        symbol_oi = open_interest[open_interest["symbol"] == symbol].copy().sort_values(
            "oi_timestamp"
        )
        frame = oi_frames[symbol]
        intervals = symbol_oi["oi_timestamp"].diff().dropna()
        interval_breaks = intervals != OPEN_INTEREST_INTERVAL
        lower5_mask, _ = shock_condition(frame, "lower", 0.05)
        upper5_mask, _ = shock_condition(frame, "upper", 0.05)
        lower5 = frame.loc[lower5_mask]
        upper5 = frame.loc[upper5_mask]
        rows.append(
            {
                "symbol": symbol,
                "source": "Binance USD-M Futures openInterestHist API",
                "period": OPEN_INTEREST_PERIOD,
                "api_limitation": "API returned a recent rolling window only, not full 2020-2026 history",
                "oi_rows": int(len(symbol_oi)),
                "first_oi_timestamp": symbol_oi["oi_timestamp"].min(),
                "last_oi_timestamp": symbol_oi["oi_timestamp"].max(),
                "oi_interval_break_count": int(interval_breaks.sum()),
                "oi_window_days": (
                    float(
                        (
                            symbol_oi["oi_timestamp"].max()
                            - symbol_oi["oi_timestamp"].min()
                        )
                        / pd.Timedelta(days=1)
                    )
                    if not symbol_oi.empty
                    else math.nan
                ),
                "common_bar_count": int(len(frame)),
                "bars_with_oi_count": int(frame["open_interest_value_usdt"].notna().sum()),
                "bars_with_oi_share_pct": rate_pct(
                    frame["open_interest_value_usdt"].notna()
                ),
                "oi_value_mean_usdt": symbol_oi["open_interest_value_usdt"].mean(),
                "oi_value_min_usdt": symbol_oi["open_interest_value_usdt"].min(),
                "oi_value_max_usdt": symbol_oi["open_interest_value_usdt"].max(),
                "lower5_signal_count": int(len(lower5)),
                "lower5_with_oi_count": int(
                    lower5["oi_value_change_24h_pct"].notna().sum()
                ),
                "upper5_signal_count": int(len(upper5)),
                "upper5_with_oi_count": int(
                    upper5["oi_value_change_24h_pct"].notna().sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_shock_mr_by_oi_events(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for symbol, df in frames.items():
        for side in ["lower", "upper"]:
            shock_mask, threshold = shock_condition(df, side, 0.05)
            mr_sign = 1.0 if side == "lower" else -1.0
            for horizon in HORIZONS:
                future_col = f"future_return_{horizon}_pct"
                exit_timestamp = df["timestamp"].shift(-horizon)
                selected = df.loc[
                    shock_mask & df["oi_regime"].notna(),
                    [
                        "timestamp",
                        "log_return_pct",
                        "oi_timestamp",
                        "open_interest_contracts",
                        "open_interest_value_usdt",
                        "oi_value_change_4h_pct",
                        "oi_value_change_24h_pct",
                        "oi_regime",
                        future_col,
                    ],
                ].dropna(subset=[future_col, "oi_value_change_24h_pct"])
                for idx, row in selected.iterrows():
                    future_return = float(row[future_col])
                    rows.append(
                        {
                            "symbol": symbol,
                            "shock_side": side,
                            "shock_level": "5pct",
                            "threshold_pct": threshold,
                            "horizon_bars": horizon,
                            "horizon_hours": HORIZON_HOURS[horizon],
                            "signal_timestamp": row["timestamp"],
                            "exit_timestamp": exit_timestamp.loc[idx],
                            "signal_return_pct": row["log_return_pct"],
                            "oi_timestamp": row["oi_timestamp"],
                            "open_interest_contracts": row["open_interest_contracts"],
                            "open_interest_value_usdt": row[
                                "open_interest_value_usdt"
                            ],
                            "oi_value_change_4h_pct": row["oi_value_change_4h_pct"],
                            "oi_value_change_24h_pct": row[
                                "oi_value_change_24h_pct"
                            ],
                            "oi_regime": row["oi_regime"],
                            "future_return_pct": future_return,
                            "mr_return_pct": future_return * mr_sign,
                        }
                    )
    return pd.DataFrame(rows)


def build_shock_mr_by_oi_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if events.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "shock_side",
                "shock_level",
                "oi_regime",
                "horizon_bars",
                "horizon_hours",
                "count",
                "signal_return_mean_pct",
                "oi_value_change_24h_mean_pct",
                "future_return_mean_pct",
                "mr_return_mean_pct",
                "mr_return_median_pct",
                "mr_win_rate_pct",
                "mr_return_t_stat",
            ]
        )
    for keys, part in events.groupby(
        ["symbol", "shock_side", "oi_regime", "horizon_bars", "horizon_hours"],
        sort=False,
    ):
        symbol, shock_side, oi_regime, horizon_bars, horizon_hours = keys
        mr = part["mr_return_pct"].astype(float)
        rows.append(
            {
                "symbol": symbol,
                "shock_side": shock_side,
                "shock_level": "5pct",
                "threshold_pct": part["threshold_pct"].iloc[0],
                "oi_regime": oi_regime,
                "horizon_bars": int(horizon_bars),
                "horizon_hours": int(horizon_hours),
                "count": int(len(part)),
                "signal_return_mean_pct": part["signal_return_pct"].mean(),
                "oi_value_change_24h_mean_pct": part[
                    "oi_value_change_24h_pct"
                ].mean(),
                "future_return_mean_pct": part["future_return_pct"].mean(),
                "mr_return_mean_pct": mr.mean(),
                "mr_return_median_pct": mr.median(),
                "mr_win_rate_pct": rate_pct(mr > 0.0),
                "mr_return_t_stat": safe_t_stat(mr),
            }
        )
    out = pd.DataFrame(rows)
    regime_order = {label: idx for idx, label in enumerate(OI_REGIME_ORDER)}
    out["_regime_order"] = out["oi_regime"].map(regime_order)
    return out.sort_values(
        ["symbol", "shock_side", "_regime_order", "horizon_bars"]
    ).drop(columns=["_regime_order"])


def build_liquidation_profile(probe: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "source": "Binance USD-M Futures liquidation history endpoint",
                "endpoint": probe["endpoint"],
                "http_status": probe["http_status"],
                "api_status": probe["api_status"],
                "message": probe["message"],
                "historical_market_liquidation_available": probe[
                    "api_status"
                ]
                == "OK",
                "analysis_status": (
                    "SKIPPED_ENDPOINT_UNAVAILABLE"
                    if probe["api_status"] != "OK"
                    else "AVAILABLE_NOT_IMPLEMENTED"
                ),
                "note": "Public historical market liquidation data was not available from this endpoint in this run.",
            }
            for symbol in SYMBOL_FILES.keys()
        ]
    )


def valid_forward_window(df: pd.DataFrame, horizon: int) -> pd.Series:
    valid = pd.Series(True, index=df.index)
    for step in range(1, horizon + 1):
        valid &= (
            df["timestamp"].shift(-step) - df["timestamp"]
        ) == EXPECTED_INTERVAL * step
    return valid


def profit_factor(values: pd.Series) -> float:
    series = values.dropna().astype(float)
    gains = series[series > 0.0].sum()
    losses = -series[series < 0.0].sum()
    if losses == 0.0:
        return math.nan
    return float(gains / losses)


def return_path_stats(values: pd.Series) -> dict[str, float]:
    returns = values.dropna().astype(float)
    if returns.empty:
        return {
            "final_cumulative_log_return_pct": math.nan,
            "final_cumulative_return_pct": math.nan,
            "max_drawdown_pct": math.nan,
        }
    cumulative_log = returns.cumsum()
    equity = np.exp(cumulative_log / 100.0)
    running_peak = equity.cummax().clip(lower=1.0)
    drawdown = (equity / running_peak - 1.0) * 100.0
    return {
        "final_cumulative_log_return_pct": float(cumulative_log.iloc[-1]),
        "final_cumulative_return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "max_drawdown_pct": float(drawdown.min()),
    }


def build_phase4_candidate_table(
    phase2_candidate: pd.DataFrame, phase3_candidate: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    lower5_all = phase2_candidate[
        (phase2_candidate["shock_side"] == "lower")
        & (phase2_candidate["shock_level"] == "5pct")
    ].copy()
    for _, row in lower5_all.sort_values("symbol").iterrows():
        hours = int(row["horizon_hours"])
        symbol_short = str(row["symbol"]).replace("USDT", "")
        rows.append(
            {
                "candidate_id": f"{row['symbol']}_lower5_all_h{hours}",
                "candidate_label": f"{symbol_short} all {hours}H",
                "source_phase": "phase2_lower5_best",
                "symbol": row["symbol"],
                "shock_side": "lower",
                "shock_level": "5pct",
                "direction": "long",
                "vol_regime_filter": "all",
                "threshold_pct": row["threshold_pct"],
                "horizon_bars": int(row["horizon_bars"]),
                "horizon_hours": hours,
                "source_count": int(row["count"]),
                "source_mr_return_mean_pct": row["mr_return_mean_pct"],
                "source_mr_win_rate_pct": row["mr_win_rate_pct"],
            }
        )

    lower5_q5 = phase3_candidate[phase3_candidate["vol_regime"] == "Q5_high"].copy()
    for _, row in lower5_q5.sort_values("symbol").iterrows():
        hours = int(row["horizon_hours"])
        symbol_short = str(row["symbol"]).replace("USDT", "")
        rows.append(
            {
                "candidate_id": f"{row['symbol']}_lower5_Q5_high_h{hours}",
                "candidate_label": f"{symbol_short} Q5 {hours}H",
                "source_phase": "phase3_lower5_Q5_best",
                "symbol": row["symbol"],
                "shock_side": "lower",
                "shock_level": "5pct",
                "direction": "long",
                "vol_regime_filter": "Q5_high",
                "threshold_pct": row["threshold_pct"],
                "horizon_bars": int(row["horizon_bars"]),
                "horizon_hours": hours,
                "source_count": int(row["count"]),
                "source_mr_return_mean_pct": row["mr_return_mean_pct"],
                "source_mr_win_rate_pct": row["mr_win_rate_pct"],
            }
        )

    return pd.DataFrame(rows)


def build_path_risk_events(
    frames: dict[str, pd.DataFrame], candidates: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for _, candidate in candidates.iterrows():
        symbol = str(candidate["symbol"])
        horizon = int(candidate["horizon_bars"])
        df = frames[symbol]
        threshold = float(candidate["threshold_pct"])
        entry_open = df["open"].shift(-1)
        exit_close = df["close"].shift(-horizon)
        entry_timestamp = df["timestamp"].shift(-1)
        exit_timestamp = df["timestamp"].shift(-horizon)
        forward_low = pd.concat(
            [df["low"].shift(-step) for step in range(1, horizon + 1)], axis=1
        ).min(axis=1)
        forward_high = pd.concat(
            [df["high"].shift(-step) for step in range(1, horizon + 1)], axis=1
        ).max(axis=1)

        condition = (
            (df["log_return_pct"] <= threshold)
            & valid_forward_window(df, horizon)
            & entry_open.notna()
            & exit_close.notna()
            & forward_low.notna()
            & forward_high.notna()
        )
        vol_filter = str(candidate["vol_regime_filter"])
        if vol_filter != "all":
            condition &= df["vol_regime"] == vol_filter

        selected = df.loc[condition].copy()
        for idx, row in selected.iterrows():
            signal_close = float(row["close"])
            entry = float(entry_open.loc[idx])
            exit_value = float(exit_close.loc[idx])
            low_value = float(forward_low.loc[idx])
            high_value = float(forward_high.loc[idx])
            next_open_return = math.log(exit_value / entry) * 100.0
            close_to_close_return = math.log(exit_value / signal_close) * 100.0
            entry_gap = math.log(entry / signal_close) * 100.0
            mae = min(math.log(low_value / entry) * 100.0, 0.0)
            mfe = max(math.log(high_value / entry) * 100.0, 0.0)
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_label": candidate["candidate_label"],
                    "source_phase": candidate["source_phase"],
                    "symbol": symbol,
                    "shock_side": candidate["shock_side"],
                    "shock_level": candidate["shock_level"],
                    "direction": candidate["direction"],
                    "vol_regime_filter": vol_filter,
                    "threshold_pct": threshold,
                    "horizon_bars": horizon,
                    "horizon_hours": int(candidate["horizon_hours"]),
                    "signal_timestamp": row["timestamp"],
                    "entry_timestamp": entry_timestamp.loc[idx],
                    "exit_timestamp": exit_timestamp.loc[idx],
                    "signal_return_pct": row["log_return_pct"],
                    "vol_regime": row["vol_regime"],
                    "vol20_pct": row["vol20_pct"],
                    "signal_close": signal_close,
                    "entry_open": entry,
                    "exit_close": exit_value,
                    "forward_low": low_value,
                    "forward_high": high_value,
                    "entry_gap_pct": entry_gap,
                    "close_to_close_return_pct": close_to_close_return,
                    "next_open_return_pct": next_open_return,
                    "mae_pct": mae,
                    "mfe_pct": mfe,
                }
            )

    return pd.DataFrame(rows)


def summarize_event_returns(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for candidate_id, part in events.groupby("candidate_id", sort=False):
        returns = part["next_open_return_pct"].astype(float)
        path_stats = return_path_stats(returns)
        first = part.iloc[0]
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_label": first["candidate_label"],
                "source_phase": first["source_phase"],
                "symbol": first["symbol"],
                "vol_regime_filter": first["vol_regime_filter"],
                "threshold_pct": first["threshold_pct"],
                "horizon_bars": int(first["horizon_bars"]),
                "horizon_hours": int(first["horizon_hours"]),
                "event_count": int(len(part)),
                "entry_gap_mean_pct": part["entry_gap_pct"].mean(),
                "close_to_close_return_mean_pct": part[
                    "close_to_close_return_pct"
                ].mean(),
                "next_open_return_mean_pct": returns.mean(),
                "next_open_return_median_pct": returns.median(),
                "next_open_return_std_pct": returns.std(ddof=1),
                "next_open_return_t_stat": safe_t_stat(returns),
                "win_rate_pct": rate_pct(returns > 0.0),
                "profit_factor": profit_factor(returns),
                "mae_mean_pct": part["mae_pct"].mean(),
                "mae_median_pct": part["mae_pct"].median(),
                "mae_10pct": part["mae_pct"].quantile(0.10),
                "mae_worst_pct": part["mae_pct"].min(),
                "mfe_mean_pct": part["mfe_pct"].mean(),
                "mfe_median_pct": part["mfe_pct"].median(),
                "mfe_90pct": part["mfe_pct"].quantile(0.90),
                "mfe_best_pct": part["mfe_pct"].max(),
                "event_sequence_final_log_return_pct": path_stats[
                    "final_cumulative_log_return_pct"
                ],
                "event_sequence_final_return_pct": path_stats[
                    "final_cumulative_return_pct"
                ],
                "event_sequence_max_drawdown_pct": path_stats["max_drawdown_pct"],
            }
        )
    return pd.DataFrame(rows)


def build_simple_backtest_events(path_events: pd.DataFrame) -> pd.DataFrame:
    selected_rows = []
    for _, part in path_events.groupby("candidate_id", sort=False):
        part = part.sort_values("signal_timestamp")
        last_exit = pd.Timestamp.min
        for _, row in part.iterrows():
            entry_time = pd.Timestamp(row["entry_timestamp"])
            if entry_time <= last_exit:
                continue
            selected_rows.append(row.to_dict())
            last_exit = pd.Timestamp(row["exit_timestamp"])

    if not selected_rows:
        return pd.DataFrame()

    out = pd.DataFrame(selected_rows)
    out["event_number"] = 0
    out["cumulative_log_return_pct"] = np.nan
    out["equity_index"] = np.nan
    out["cumulative_return_pct"] = np.nan
    out["running_peak_equity"] = np.nan
    out["drawdown_pct"] = np.nan
    for _, part in out.groupby("candidate_id", sort=False):
        idx = part.index
        cumulative_log = part["next_open_return_pct"].astype(float).cumsum()
        equity = np.exp(cumulative_log / 100.0)
        running_peak = equity.cummax().clip(lower=1.0)
        drawdown = (equity / running_peak - 1.0) * 100.0
        out.loc[idx, "event_number"] = np.arange(1, len(part) + 1)
        out.loc[idx, "cumulative_log_return_pct"] = cumulative_log.to_numpy()
        out.loc[idx, "equity_index"] = equity.to_numpy()
        out.loc[idx, "cumulative_return_pct"] = ((equity - 1.0) * 100.0).to_numpy()
        out.loc[idx, "running_peak_equity"] = running_peak.to_numpy()
        out.loc[idx, "drawdown_pct"] = drawdown.to_numpy()
    return out


def build_simple_backtest_summary(
    path_events: pd.DataFrame, simple_events: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    all_counts = path_events.groupby("candidate_id").size().to_dict()
    for candidate_id, part in simple_events.groupby("candidate_id", sort=False):
        returns = part["next_open_return_pct"].astype(float)
        first = part.iloc[0]
        all_count = int(all_counts.get(candidate_id, 0))
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_label": first["candidate_label"],
                "source_phase": first["source_phase"],
                "symbol": first["symbol"],
                "vol_regime_filter": first["vol_regime_filter"],
                "threshold_pct": first["threshold_pct"],
                "horizon_bars": int(first["horizon_bars"]),
                "horizon_hours": int(first["horizon_hours"]),
                "all_event_count": all_count,
                "selected_event_count": int(len(part)),
                "skipped_overlap_count": int(all_count - len(part)),
                "mean_return_pct": returns.mean(),
                "median_return_pct": returns.median(),
                "return_t_stat": safe_t_stat(returns),
                "win_rate_pct": rate_pct(returns > 0.0),
                "profit_factor": profit_factor(returns),
                "mean_mae_pct": part["mae_pct"].mean(),
                "worst_mae_pct": part["mae_pct"].min(),
                "mean_mfe_pct": part["mfe_pct"].mean(),
                "best_mfe_pct": part["mfe_pct"].max(),
                "final_cumulative_log_return_pct": part[
                    "cumulative_log_return_pct"
                ].iloc[-1],
                "final_cumulative_return_pct": part[
                    "cumulative_return_pct"
                ].iloc[-1],
                "max_drawdown_pct": part["drawdown_pct"].min(),
            }
        )
    return pd.DataFrame(rows)


def format_event_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in [
        "signal_timestamp",
        "entry_timestamp",
        "exit_timestamp",
        "funding_timestamp",
        "oi_timestamp",
        "first_funding_timestamp",
        "last_funding_timestamp",
        "first_oi_timestamp",
        "last_oi_timestamp",
    ]:
        if col in out.columns:
            out[col] = out[col].map(format_timestamp)
    return out


def build_phase5_close_candidate_table(
    phase2_candidate: pd.DataFrame, phase3_candidate: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    phase2_focus = phase2_candidate[phase2_candidate["shock_level"] == "5pct"].copy()
    for _, row in phase2_focus.sort_values(["shock_side", "symbol"]).iterrows():
        hours = int(row["horizon_hours"])
        symbol_short = str(row["symbol"]).replace("USDT", "")
        side_label = "lower5" if row["shock_side"] == "lower" else "upper5"
        direction = str(row["direction"])
        rows.append(
            {
                "candidate_id": (
                    f"{row['symbol']}_{side_label}_all_close_h{hours}_{direction}"
                ),
                "candidate_label": (
                    f"P2 {symbol_short} {side_label} all close {hours}H {direction}"
                ),
                "event_set": "phase2_close",
                "source_phase": "phase2_best_5pct",
                "entry_model": "close_to_close",
                "symbol": row["symbol"],
                "shock_side": row["shock_side"],
                "shock_level": row["shock_level"],
                "direction": direction,
                "vol_regime_filter": "all",
                "threshold_pct": row["threshold_pct"],
                "horizon_bars": int(row["horizon_bars"]),
                "horizon_hours": hours,
            }
        )

    phase3_q5 = phase3_candidate[phase3_candidate["vol_regime"] == "Q5_high"].copy()
    for _, row in phase3_q5.sort_values("symbol").iterrows():
        hours = int(row["horizon_hours"])
        symbol_short = str(row["symbol"]).replace("USDT", "")
        rows.append(
            {
                "candidate_id": f"{row['symbol']}_lower5_Q5_close_h{hours}_long",
                "candidate_label": f"P3 {symbol_short} lower5 Q5 close {hours}H long",
                "event_set": "phase3_q5_close",
                "source_phase": "phase3_lower5_Q5_best",
                "entry_model": "close_to_close",
                "symbol": row["symbol"],
                "shock_side": "lower",
                "shock_level": "5pct",
                "direction": "long",
                "vol_regime_filter": "Q5_high",
                "threshold_pct": row["threshold_pct"],
                "horizon_bars": int(row["horizon_bars"]),
                "horizon_hours": hours,
            }
        )
    return pd.DataFrame(rows)


def build_close_to_close_candidate_events(
    frames: dict[str, pd.DataFrame], candidates: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for _, candidate in candidates.iterrows():
        symbol = str(candidate["symbol"])
        df = frames[symbol]
        horizon = int(candidate["horizon_bars"])
        threshold = float(candidate["threshold_pct"])
        future_col = f"future_return_{horizon}_pct"
        if candidate["shock_side"] == "lower":
            condition = df["log_return_pct"] <= threshold
        elif candidate["shock_side"] == "upper":
            condition = df["log_return_pct"] >= threshold
        else:
            raise ValueError(f"unknown shock_side: {candidate['shock_side']}")

        vol_filter = str(candidate["vol_regime_filter"])
        if vol_filter != "all":
            condition &= df["vol_regime"] == vol_filter

        selected = df.loc[
            condition,
            ["timestamp", "log_return_pct", "vol_regime", "vol20_pct", future_col],
        ].dropna()
        exit_timestamps = df["timestamp"].shift(-horizon)
        for idx, row in selected.iterrows():
            future_return = float(row[future_col])
            strategy_return = (
                future_return if candidate["direction"] == "long" else -future_return
            )
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_label": candidate["candidate_label"],
                    "event_set": candidate["event_set"],
                    "source_phase": candidate["source_phase"],
                    "entry_model": candidate["entry_model"],
                    "symbol": symbol,
                    "shock_side": candidate["shock_side"],
                    "shock_level": candidate["shock_level"],
                    "direction": candidate["direction"],
                    "vol_regime_filter": vol_filter,
                    "threshold_pct": threshold,
                    "horizon_bars": horizon,
                    "horizon_hours": int(candidate["horizon_hours"]),
                    "signal_timestamp": row["timestamp"],
                    "entry_timestamp": row["timestamp"],
                    "exit_timestamp": exit_timestamps.loc[idx],
                    "signal_return_pct": row["log_return_pct"],
                    "vol_regime": row["vol_regime"],
                    "vol20_pct": row["vol20_pct"],
                    "future_return_pct": future_return,
                    "return_pct": strategy_return,
                    "mae_pct": math.nan,
                    "mfe_pct": math.nan,
                    "is_nonoverlap": False,
                }
            )
    return pd.DataFrame(rows)


def normalize_phase4_events_for_annual(
    events: pd.DataFrame, event_set: str, label_prefix: str, is_nonoverlap: bool
) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    out = events.copy()
    out["event_set"] = event_set
    out["candidate_label"] = label_prefix + " " + out["candidate_label"].astype(str)
    out["entry_model"] = (
        "next_open_nonoverlap" if is_nonoverlap else "next_open_all_signals"
    )
    out["return_pct"] = out["next_open_return_pct"]
    out["future_return_pct"] = out["next_open_return_pct"]
    out["is_nonoverlap"] = is_nonoverlap
    keep_cols = [
        "candidate_id",
        "candidate_label",
        "event_set",
        "source_phase",
        "entry_model",
        "symbol",
        "shock_side",
        "shock_level",
        "direction",
        "vol_regime_filter",
        "threshold_pct",
        "horizon_bars",
        "horizon_hours",
        "signal_timestamp",
        "entry_timestamp",
        "exit_timestamp",
        "signal_return_pct",
        "vol_regime",
        "vol20_pct",
        "future_return_pct",
        "return_pct",
        "mae_pct",
        "mfe_pct",
        "is_nonoverlap",
    ]
    return out[keep_cols].copy()


def build_phase5_annual_events(
    close_events: pd.DataFrame, path_events: pd.DataFrame, simple_events: pd.DataFrame
) -> pd.DataFrame:
    frames = [
        close_events,
        normalize_phase4_events_for_annual(
            path_events,
            "phase4_next_open_all_signals",
            "P4 all-signal",
            False,
        ),
        normalize_phase4_events_for_annual(
            simple_events,
            "phase4_next_open_nonoverlap",
            "P4 nonoverlap",
            True,
        ),
    ]
    events = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True)
    events["signal_timestamp"] = pd.to_datetime(events["signal_timestamp"])
    events["entry_timestamp"] = pd.to_datetime(events["entry_timestamp"])
    events["exit_timestamp"] = pd.to_datetime(events["exit_timestamp"])
    events["year"] = events["signal_timestamp"].dt.year.astype(int)
    events["annual_candidate_id"] = events["event_set"] + ":" + events["candidate_id"]
    return events.sort_values(["annual_candidate_id", "signal_timestamp"]).reset_index(
        drop=True
    )


def build_annual_condition_summary(annual_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    meta_cols = [
        "annual_candidate_id",
        "candidate_id",
        "candidate_label",
        "event_set",
        "source_phase",
        "entry_model",
        "symbol",
        "shock_side",
        "shock_level",
        "direction",
        "vol_regime_filter",
        "threshold_pct",
        "horizon_bars",
        "horizon_hours",
        "is_nonoverlap",
    ]
    candidate_meta = (
        annual_events[meta_cols]
        .drop_duplicates("annual_candidate_id")
        .set_index("annual_candidate_id")
    )
    for annual_candidate_id, meta in candidate_meta.iterrows():
        candidate_events = annual_events[
            annual_events["annual_candidate_id"] == annual_candidate_id
        ]
        total_events = int(len(candidate_events))
        for year in ANNUAL_YEARS:
            part = candidate_events[candidate_events["year"] == year].sort_values(
                "signal_timestamp"
            )
            returns = part["return_pct"].astype(float)
            path_stats = return_path_stats(returns)
            row = meta.to_dict()
            row.update(
                {
                    "annual_candidate_id": annual_candidate_id,
                    "year": year,
                    "event_count": int(len(part)),
                    "total_event_count": total_events,
                    "annual_event_share_pct": (
                        float(len(part) / total_events * 100.0)
                        if total_events > 0
                        else math.nan
                    ),
                    "mean_return_pct": returns.mean() if len(part) else math.nan,
                    "median_return_pct": returns.median() if len(part) else math.nan,
                    "return_std_pct": returns.std(ddof=1) if len(part) > 1 else math.nan,
                    "return_t_stat": safe_t_stat(returns),
                    "win_rate_pct": rate_pct(returns > 0.0) if len(part) else math.nan,
                    "profit_factor": profit_factor(returns),
                    "mean_mae_pct": part["mae_pct"].mean() if len(part) else math.nan,
                    "worst_mae_pct": part["mae_pct"].min() if len(part) else math.nan,
                    "mean_mfe_pct": part["mfe_pct"].mean() if len(part) else math.nan,
                    "best_mfe_pct": part["mfe_pct"].max() if len(part) else math.nan,
                    "final_cumulative_log_return_pct": path_stats[
                        "final_cumulative_log_return_pct"
                    ],
                    "final_cumulative_return_pct": path_stats[
                        "final_cumulative_return_pct"
                    ],
                    "max_drawdown_pct": path_stats["max_drawdown_pct"],
                    "annual_status": (
                        "NO_EVENTS"
                        if len(part) == 0
                        else "LOW_COUNT"
                        if len(part) < 10
                        else "OK"
                    ),
                    "is_partial_year": year in {2020, 2026},
                }
            )
            rows.append(row)
    columns = [
        "annual_candidate_id",
        "candidate_id",
        "candidate_label",
        "event_set",
        "source_phase",
        "entry_model",
        "symbol",
        "shock_side",
        "shock_level",
        "direction",
        "vol_regime_filter",
        "threshold_pct",
        "horizon_bars",
        "horizon_hours",
        "is_nonoverlap",
        "year",
        "is_partial_year",
        "event_count",
        "total_event_count",
        "annual_event_share_pct",
        "mean_return_pct",
        "median_return_pct",
        "return_std_pct",
        "return_t_stat",
        "win_rate_pct",
        "profit_factor",
        "mean_mae_pct",
        "worst_mae_pct",
        "mean_mfe_pct",
        "best_mfe_pct",
        "final_cumulative_log_return_pct",
        "final_cumulative_return_pct",
        "max_drawdown_pct",
        "annual_status",
    ]
    return pd.DataFrame(rows)[columns]


def build_annual_stability_summary(annual_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for annual_candidate_id, part in annual_summary.groupby(
        "annual_candidate_id", sort=False
    ):
        active = part[part["event_count"] > 0].copy()
        meta = part.iloc[0]
        if active.empty:
            continue
        positive_years = active["mean_return_pct"] > 0.0
        ok_years = active["annual_status"] == "OK"
        total_events = int(active["event_count"].sum())
        positive_year_rate = float(positive_years.mean() * 100.0)
        mean_of_annual_means = active["mean_return_pct"].mean()
        max_event_share = float(active["annual_event_share_pct"].max())
        if (
            mean_of_annual_means > 0.0
            and positive_year_rate >= 70.0
            and ok_years.sum() >= 4
        ):
            stability_label = "broad_positive"
        elif (
            mean_of_annual_means > 0.0
            and positive_year_rate >= 55.0
            and ok_years.sum() >= 3
        ):
            stability_label = "positive_but_uneven"
        else:
            stability_label = "mixed_or_sparse"
        rows.append(
            {
                "annual_candidate_id": annual_candidate_id,
                "candidate_label": meta["candidate_label"],
                "event_set": meta["event_set"],
                "entry_model": meta["entry_model"],
                "symbol": meta["symbol"],
                "shock_side": meta["shock_side"],
                "shock_level": meta["shock_level"],
                "direction": meta["direction"],
                "vol_regime_filter": meta["vol_regime_filter"],
                "horizon_hours": int(meta["horizon_hours"]),
                "years_with_events": int(len(active)),
                "ok_years": int(ok_years.sum()),
                "low_count_years": int((active["annual_status"] == "LOW_COUNT").sum()),
                "total_event_count": total_events,
                "max_annual_event_share_pct": max_event_share,
                "positive_year_count": int(positive_years.sum()),
                "positive_year_rate_pct": positive_year_rate,
                "mean_of_annual_means_pct": mean_of_annual_means,
                "median_of_annual_means_pct": active["mean_return_pct"].median(),
                "min_annual_mean_pct": active["mean_return_pct"].min(),
                "max_annual_mean_pct": active["mean_return_pct"].max(),
                "worst_annual_drawdown_pct": active["max_drawdown_pct"].min(),
                "stability_label": stability_label,
            }
        )
    return pd.DataFrame(rows)


def save_moment_summary(moment: pd.DataFrame, output_dir: Path) -> None:
    moment.to_csv(
        output_dir / "moment_summary.csv",
        index=False,
        float_format="%.10f",
        lineterminator="\n",
    )


def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, float_format="%.10f", lineterminator="\n")


def write_phase2_event_study_report(
    output_dir: Path,
    direction: pd.DataFrame,
    shock_mr: pd.DataFrame,
    candidate: pd.DataFrame,
) -> None:
    lower5 = shock_mr[
        (shock_mr["shock_side"] == "lower") & (shock_mr["shock_level"] == "5pct")
    ].copy()
    upper5 = shock_mr[
        (shock_mr["shock_side"] == "upper") & (shock_mr["shock_level"] == "5pct")
    ].copy()
    lower_best = candidate[
        (candidate["shock_side"] == "lower") & (candidate["shock_level"] == "5pct")
    ].copy()
    upper_best = candidate[
        (candidate["shock_side"] == "upper") & (candidate["shock_level"] == "5pct")
    ].copy()

    lines = [
        "# Phase 2 Report: BTC/ETH/SOL 急落・急騰イベントスタディ",
        "",
        "作成日: 2026-05-30",
        "",
        "参照データ:",
        "",
        "- `direction_return_summary.csv`",
        "- `shock_mean_reversion_summary.csv`",
        "- `phase2_candidate_summary.csv`",
        "- `figures/fig_04_direction_future_returns.png`",
        "- `figures/fig_05_shock_mean_reversion_by_horizon.png`",
        "",
        "## 1. 目的",
        "",
        "Phase 2 の目的は、Phase 1 で確認した各銘柄の分布に基づいて、急落後ロングと急騰後ショートの平均回帰候補を検証することである。",
        "",
        "この段階では、全期間分位による探索分析として、下位5%、2.5%、1%急落と、上位5%、2.5%、1%急騰を定義する。これは本番売買ルールではなく、どの銘柄・どのホライズンに深掘り価値があるかを見るためのイベントスタディである。",
        "",
        "## 2. 分析条件",
        "",
        "| 項目 | 内容 |",
        "|---|---|",
        "| 対象 | BTCUSDT / ETHUSDT / SOLUSDT |",
        "| 足種 | 240分足 |",
        "| ホライズン | 4H / 8H / 12H / 24H / 48H / 72H |",
        "| 急落条件 | 各銘柄の4Hリターン分布の下位5%、2.5%、1% |",
        "| 急騰条件 | 各銘柄の4Hリターン分布の上位5%、2.5%、1% |",
        "| 急落後ロングMR | `+future_return` |",
        "| 急騰後ショートMR | `-future_return` |",
        "| 欠損処理 | 未来リターンが時刻飛びをまたぐ場合は除外 |",
        "",
        "## 3. 下位5%急落後ロング",
        "",
        "下位5%急落後ロングの全ホライズン結果は以下である。",
        "",
        lower5.round(6).to_markdown(index=False),
        "",
        "下位5%急落について、銘柄ごとに平均回帰リターンが最も高かったホライズンは以下である。",
        "",
        lower_best.round(6).to_markdown(index=False),
        "",
        "## 4. 上位5%急騰後ショート",
        "",
        "上位5%急騰後ショートの全ホライズン結果は以下である。",
        "",
        upper5.round(6).to_markdown(index=False),
        "",
        "上位5%急騰について、銘柄ごとに平均回帰リターンが最も高かったホライズンは以下である。",
        "",
        upper_best.round(6).to_markdown(index=False),
        "",
        "## 5. 全候補のベストホライズン",
        "",
        "下位/上位の5%、2.5%、1%条件ごとに、平均回帰リターンが最も高かったホライズンを抜き出す。",
        "",
        candidate.round(6).to_markdown(index=False),
        "",
        "## 6. 記事での使い方",
        "",
        "Phase 2 は、価格分布だけで見た急落後リバウンド候補を探す段階である。ここでプラスの平均回帰が見えても、同時終値エントリーの探索統計であり、完成した売買ルールではない。",
        "",
        "記事では、まず下位5%急落後ロングの平均回帰がどの銘柄・どの時間軸で出るかを示し、その後で Phase 3 のボラティリティ階層、Phase 4 の次足始値エントリーと MAE/MFE、Phase 5 の年別安定性へ進む流れにする。",
        "",
        "特に SOL は Phase 1 で高ボラ・厚いテール銘柄であることが分かっているため、平均リターンが大きく見えても、途中逆行やスリッページを確認するまで強く主張しない。",
        "",
    ]
    (output_dir / "phase2_event_study_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_phase3_vol_regime_report(
    output_dir: Path,
    vol_regime: pd.DataFrame,
    shock_mr_by_vol: pd.DataFrame,
    lower5_candidate: pd.DataFrame,
) -> None:
    h24_vol = vol_regime[vol_regime["horizon_hours"] == 24].copy()
    lower5_h24 = shock_mr_by_vol[
        (shock_mr_by_vol["shock_side"] == "lower")
        & (shock_mr_by_vol["shock_level"] == "5pct")
        & (shock_mr_by_vol["horizon_hours"] == 24)
    ].copy()
    lower5_h72 = shock_mr_by_vol[
        (shock_mr_by_vol["shock_side"] == "lower")
        & (shock_mr_by_vol["shock_level"] == "5pct")
        & (shock_mr_by_vol["horizon_hours"] == 72)
    ].copy()

    lines = [
        "# Phase 3 Report: ボラティリティ階層別分析",
        "",
        "作成日: 2026-05-30",
        "",
        "参照データ:",
        "",
        "- `vol_regime_summary.csv`",
        "- `shock_mean_reversion_by_vol_summary.csv`",
        "- `phase3_lower5_by_vol_candidate_summary.csv`",
        "- `figures/fig_06_vol_regime_future_abs_return_h6.png`",
        "- `figures/fig_07_lower5_mr_by_vol.png`",
        "",
        "## 1. 目的",
        "",
        "Phase 3 の目的は、急落後リバウンド候補がボラティリティ環境によってどう変わるかを確認することである。",
        "",
        "`vol20_pct` は過去20本の4時間足リターン標準偏差であり、各銘柄ごとに5分位へ分ける。これにより、同じ下位5%急落でも、低ボラ環境の急落と高ボラ環境の急落を区別する。",
        "",
        "## 2. ボラティリティ階層",
        "",
        "| ラベル | 意味 |",
        "|---|---|",
        "| `Q1_low` | 低ボラ |",
        "| `Q2_lower` | やや低ボラ |",
        "| `Q3_mid` | 中ボラ |",
        "| `Q4_higher` | やや高ボラ |",
        "| `Q5_high` | 高ボラ |",
        "",
        "## 3. 24H先の平均絶対リターン",
        "",
        "ボラティリティ階層ごとの24時間先平均絶対リターンは以下である。",
        "",
        h24_vol.round(6).to_markdown(index=False),
        "",
        "## 4. 下位5%急落後ロング: 24H",
        "",
        "下位5%急落後ロングの24時間MRをボラティリティ階層別に見る。",
        "",
        lower5_h24.round(6).to_markdown(index=False),
        "",
        "## 5. 下位5%急落後ロング: 72H",
        "",
        "下位5%急落後ロングの72時間MRをボラティリティ階層別に見る。",
        "",
        lower5_h72.round(6).to_markdown(index=False),
        "",
        "## 6. 下位5%急落後ロングの階層別ベストホライズン",
        "",
        "銘柄・ボラティリティ階層ごとに、下位5%急落後ロングMRが最も高かったホライズンを抜き出す。",
        "",
        lower5_candidate.round(6).to_markdown(index=False),
        "",
        "## 7. 記事での使い方",
        "",
        "Phase 3 は、Phase 2 で見えた急落後リバウンド候補を、ボラティリティ環境で分解するための材料である。",
        "",
        "ここで重要なのは、平均リターンが大きい階層ほど安全とは限らない点である。高ボラ階層では反発幅が大きく見える一方、Phase 4 で確認すべき MAE やスリッページも大きくなりやすい。",
        "",
        "記事では、低ボラ急落、中ボラ急落、高ボラ急落を同じものとして扱わず、特に SOL の高ボラ急落については「反発幅は大きいが、危険も大きい」と整理するのが妥当である。",
        "",
    ]
    (output_dir / "phase3_vol_regime_analysis_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_phase4_path_risk_report(
    output_dir: Path,
    candidates: pd.DataFrame,
    path_summary: pd.DataFrame,
    simple_summary: pd.DataFrame,
) -> None:
    path_cols = [
        "candidate_label",
        "event_count",
        "horizon_hours",
        "next_open_return_mean_pct",
        "next_open_return_median_pct",
        "win_rate_pct",
        "profit_factor",
        "mae_mean_pct",
        "mae_worst_pct",
        "mfe_mean_pct",
        "mfe_best_pct",
    ]
    simple_cols = [
        "candidate_label",
        "all_event_count",
        "selected_event_count",
        "skipped_overlap_count",
        "mean_return_pct",
        "win_rate_pct",
        "profit_factor",
        "final_cumulative_return_pct",
        "max_drawdown_pct",
    ]
    best_return = simple_summary.sort_values(
        "final_cumulative_return_pct", ascending=False
    ).iloc[0]
    worst_drawdown = simple_summary.sort_values("max_drawdown_pct").iloc[0]
    best_path_mean = path_summary.sort_values(
        "next_open_return_mean_pct", ascending=False
    ).iloc[0]

    lines = [
        "# Phase 4 Report: 次足始値エントリーと MAE/MFE",
        "",
        "作成日: 2026-05-30",
        "",
        "参照データ:",
        "",
        "- `phase4_candidate_table.csv`",
        "- `path_risk_summary.csv`",
        "- `path_risk_events.csv`",
        "- `simple_backtest_summary.csv`",
        "- `simple_backtest_events.csv`",
        "- `figures/fig_08_path_risk_mae_mfe.png`",
        "- `figures/fig_09_simple_equity_curve.png`",
        "- `figures/fig_10_simple_drawdown_curve.png`",
        "",
        "## 1. 目的",
        "",
        "Phase 4 の目的は、Phase 2 と Phase 3 で見えた急落後ロング候補を、実売買に近い次足始値エントリーへ置き換えたときに、優位性と途中逆行がどの程度残るかを確認することである。",
        "",
        "シグナルは4時間足終値で判定し、エントリーは次の4時間足始値、決済は候補ごとの時間決済とした。MAE/MFE はエントリー足から決済足までの高値・安値で測定している。",
        "",
        "## 2. 検証候補",
        "",
        candidates.round(6).to_markdown(index=False),
        "",
        "## 3. 全シグナルの経路リスク",
        "",
        "重複シグナルも含め、条件を満たす全イベントで次足始値ベースのリターンと MAE/MFE を集計した。",
        "",
        path_summary[path_cols].round(6).to_markdown(index=False),
        "",
        "## 4. 簡易バックテスト",
        "",
        "簡易バックテストでは、候補ごとに同時保有を1つに限定し、既存ポジションの決済前に出たシグナルをスキップした。これはポートフォリオ最終検証ではなく、イベント重複を取り除いた診断である。",
        "",
        "`final_cumulative_return_pct` は各イベントのログリターンを複利換算した参考値であり、手数料、スリッページ、資金制約、約定制約は入れていない。そのため、数値の大きさは売買成績としてそのまま扱わない。",
        "",
        simple_summary[simple_cols].round(6).to_markdown(index=False),
        "",
        "## 5. 記事での使い方",
        "",
        f"全シグナル平均で最も高い次足始値リターンは `{best_path_mean['candidate_label']}` の {best_path_mean['next_open_return_mean_pct']:.3f}% だった。",
        "",
        f"重複を除いた簡易累積の参考値では `{best_return['candidate_label']}` が {best_return['final_cumulative_return_pct']:.3f}% と最大だった。",
        "",
        f"一方、最大ドローダウンが最も深かったのは `{worst_drawdown['candidate_label']}` の {worst_drawdown['max_drawdown_pct']:.3f}% である。",
        "",
        "この結果は、急落後リバウンドが平均では残っても、実際には途中逆行とイベント重複の影響を受けることを示す。記事では、Phase 2/3 の平均回帰だけで結論を出さず、Phase 4 の MAE とドローダウンをセットで提示する。",
        "",
    ]
    (output_dir / "phase4_next_open_path_risk_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_phase5_annual_stability_report(
    output_dir: Path,
    annual_summary: pd.DataFrame,
    stability_summary: pd.DataFrame,
) -> None:
    stability_cols = [
        "candidate_label",
        "total_event_count",
        "years_with_events",
        "ok_years",
        "positive_year_count",
        "positive_year_rate_pct",
        "mean_of_annual_means_pct",
        "min_annual_mean_pct",
        "max_annual_mean_pct",
        "worst_annual_drawdown_pct",
        "stability_label",
    ]
    annual_cols = [
        "candidate_label",
        "year",
        "event_count",
        "mean_return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_drawdown_pct",
        "annual_status",
    ]
    phase4_nonoverlap = stability_summary[
        stability_summary["event_set"] == "phase4_next_open_nonoverlap"
    ].copy()
    phase4_q5_annual = annual_summary[
        (annual_summary["event_set"] == "phase4_next_open_nonoverlap")
        & (annual_summary["vol_regime_filter"] == "Q5_high")
    ].copy()
    phase2_upper = stability_summary[
        (stability_summary["event_set"] == "phase2_close")
        & (stability_summary["shock_side"] == "upper")
    ].copy()

    best_phase4 = phase4_nonoverlap.sort_values(
        ["mean_of_annual_means_pct", "positive_year_rate_pct"],
        ascending=False,
    ).iloc[0]
    weakest_phase4 = phase4_nonoverlap.sort_values(
        ["positive_year_rate_pct", "mean_of_annual_means_pct"],
        ascending=True,
    ).iloc[0]

    lines = [
        "# Phase 5 Report: 年別安定性",
        "",
        "作成日: 2026-05-30",
        "",
        "参照データ:",
        "",
        "- `annual_condition_summary.csv`",
        "- `annual_condition_events.csv`",
        "- `annual_stability_summary.csv`",
        "- `figures/fig_11_annual_condition_summary.png`",
        "",
        "## 1. 目的",
        "",
        "Phase 5 の目的は、Phase 2 から Phase 4 で見えた急落後リバウンド候補が、特定年だけの外れ値に依存していないかを確認することである。",
        "",
        "年別集計では、シグナル発生年を基準にイベントを分けた。2020年は SOL のデータ開始が途中であり、2026年は 2026-05-29 までの途中年であるため、どちらも部分年として扱う。",
        "",
        "## 2. 対象候補",
        "",
        "今回の年別確認では、以下を同じ形式に正規化した。",
        "",
        "- Phase 2 の下位5%急落後ロング候補",
        "- Phase 2 の上位5%急騰後ショート候補",
        "- Phase 3 の Q5 高ボラ下位5%急落後ロング候補",
        "- Phase 4 の次足始値エントリー候補",
        "- Phase 4 の重複除外済み次足始値エントリー候補",
        "",
        "## 3. 候補別の年別安定性サマリー",
        "",
        stability_summary[stability_cols].round(6).to_markdown(index=False),
        "",
        "## 4. Phase 4 重複除外候補の読み取り",
        "",
        phase4_nonoverlap[stability_cols].round(6).to_markdown(index=False),
        "",
        f"Phase 4 重複除外候補の中で、年別の陽性率と年別平均が最も強かったのは `{best_phase4['candidate_label']}` である。",
        "",
        f"一方、最も弱かったのは `{weakest_phase4['candidate_label']}` であり、Phase 4 単体で主張するには弱い。",
        "",
        "## 5. Q5高ボラ次足始値候補の年別詳細",
        "",
        phase4_q5_annual[annual_cols].round(6).to_markdown(index=False),
        "",
        "## 6. 急騰後ショート候補",
        "",
        "Phase 2 では急騰後ショート候補も確認しているが、年別安定性の観点では記事の主役にしにくい候補である。",
        "",
        phase2_upper[stability_cols].round(6).to_markdown(index=False),
        "",
        "## 7. 記事での使い方",
        "",
        "Phase 5 は、Phase 4 までの候補を記事でどこまで強く主張できるかを決めるための確認である。",
        "",
        "年別に見ると、平均リターンが高い候補でも、年によって成績が大きく変わる。特に高ボラ急落後ロングは、反発が大きい年では非常に強く見える一方、ドローダウンも深くなりやすい。",
        "",
        "記事では、全期間平均だけでなく、年別のばらつきを必ず併記する。2020年と2026年は部分年であり、SOLは2020年の件数が少ないため、強い結論には使わない。",
        "",
    ]
    (output_dir / "phase5_annual_stability_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_phase6_funding_report(
    output_dir: Path,
    funding_profile: pd.DataFrame,
    funding_summary: pd.DataFrame,
) -> None:
    profile = funding_profile.copy()
    for col in ["first_funding_timestamp", "last_funding_timestamp"]:
        profile[col] = profile[col].map(format_timestamp)
    h72 = funding_summary[funding_summary["horizon_hours"] == 72].copy()
    best = (
        funding_summary.sort_values(
            ["symbol", "funding_adjusted_mr_return_mean_pct"],
            ascending=[True, False],
        )
        .groupby("symbol", as_index=False)
        .head(1)
    )
    cols = [
        "symbol",
        "funding_regime",
        "horizon_hours",
        "count",
        "funding_rate_mean_pct",
        "holding_funding_sum_mean_pct",
        "gross_mr_return_mean_pct",
        "funding_adjusted_mr_return_mean_pct",
        "funding_adjusted_mr_win_rate_pct",
        "funding_adjusted_mr_return_t_stat",
    ]
    lines = [
        "# Phase 6 Report: Funding Rate 拡張",
        "",
        "作成日: 2026-05-30",
        "",
        "参照データ:",
        "",
        "- `funding_rate_history.csv`",
        "- `funding_profile.csv`",
        "- `shock_mr_by_funding_events.csv`",
        "- `shock_mr_by_funding_summary.csv`",
        "- `figures/fig_12_lower5_mr_by_funding.png`",
        "",
        "## 1. 目的",
        "",
        "Phase 6 の目的は、急落後ロングを Funding Rate の状態で分類し、ロング過熱の巻き戻しと悲観過剰を分けることである。",
        "",
        "Funding は Binance USD-M Futures の `fundingRate` API から取得した。4時間足シグナルには、シグナル時刻以前の直近 Funding をひも付けた。",
        "",
        "Funding 分類は銘柄ごとの共通期間分布に基づく。",
        "",
        "| 分類 | 条件 | 解釈 |",
        "|---|---|---|",
        "| `funding_high` | Funding が銘柄内80%分位以上 | ロング過熱寄り |",
        "| `funding_low_or_negative` | Funding が20%分位以下、またはマイナス | 悲観・ショート過熱寄り |",
        "| `funding_neutral` | 上記以外 | 中立 |",
        "",
        "ロングの Funding 調整後リターンは、保有期間中の Funding 合計をグロスMRから差し引いた簡易値である。プラスFundingではロングが支払い、マイナスFundingではロングが受け取る前提で計算した。",
        "",
        "## 2. Funding データ確認",
        "",
        profile.round(8).to_markdown(index=False),
        "",
        "## 3. 72H 急落後ロング: Funding階層別",
        "",
        h72[cols].round(6).to_markdown(index=False),
        "",
        "## 4. 銘柄別の最良Funding条件",
        "",
        best[cols].round(6).to_markdown(index=False),
        "",
        "## 5. 記事での使い方",
        "",
        "Phase 6 は、価格だけで見た急落後リバウンドを、Perpetual Futures 固有の需給状態で分解する材料である。",
        "",
        "記事では、急落後リバウンドが Funding 高止まり局面でも成立するのか、または Funding 低下・マイナス局面で強いのかを比較する。Funding 高い局面の急落は、ロング過熱の巻き戻しであり、単純な押し目とは限らない。",
        "",
        "この結果は Binance USD-M Funding に依存するため、現在の OHLCV が Spot 由来の場合は、価格データとFundingデータの市場が完全には一致しない可能性を注記する。",
        "",
    ]
    (output_dir / "phase6_funding_rate_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_phase7_oi_liquidation_report(
    output_dir: Path,
    oi_profile: pd.DataFrame,
    oi_summary: pd.DataFrame,
    liquidation_profile: pd.DataFrame,
) -> None:
    profile = oi_profile.copy()
    for col in ["first_oi_timestamp", "last_oi_timestamp"]:
        profile[col] = profile[col].map(format_timestamp)
    lower72 = oi_summary[
        (oi_summary["shock_side"] == "lower") & (oi_summary["horizon_hours"] == 72)
    ].copy()
    upper24 = oi_summary[
        (oi_summary["shock_side"] == "upper") & (oi_summary["horizon_hours"] == 24)
    ].copy()
    cols = [
        "symbol",
        "shock_side",
        "oi_regime",
        "horizon_hours",
        "count",
        "oi_value_change_24h_mean_pct",
        "mr_return_mean_pct",
        "mr_win_rate_pct",
        "mr_return_t_stat",
    ]
    profile_cols = [
        "symbol",
        "api_limitation",
        "oi_rows",
        "first_oi_timestamp",
        "last_oi_timestamp",
        "oi_window_days",
        "lower5_signal_count",
        "lower5_with_oi_count",
        "upper5_signal_count",
        "upper5_with_oi_count",
    ]
    liquidation_cols = [
        "symbol",
        "endpoint",
        "http_status",
        "api_status",
        "analysis_status",
        "message",
    ]
    lines = [
        "# Phase 7 Report: Open Interest / 清算拡張",
        "",
        "作成日: 2026-05-30",
        "",
        "参照データ:",
        "",
        "- `open_interest_history.csv`",
        "- `oi_profile.csv`",
        "- `shock_mr_by_oi_events.csv`",
        "- `shock_mr_by_oi_summary.csv`",
        "- `liquidation_profile.csv`",
        "- `shock_mr_by_liquidation_summary.csv`",
        "- `figures/fig_13_lower5_mr_by_oi.png`",
        "- `figures/fig_14_liquidation_regime_summary.png`",
        "",
        "## 1. 目的",
        "",
        "Phase 7 の目的は、急落を Open Interest の増減で分解し、投げ売り完了に近い急落と、ポジションが積み上がったままの急落を分けることである。",
        "",
        "Binance の `openInterestHist` API は今回、全期間ではなく直近ローリングウィンドウだけを返した。そのため、Phase 7 は 2020-2026 の全期間結論ではなく、取得できた直近ウィンドウの診断として扱う。",
        "",
        "## 2. Open Interest データ確認",
        "",
        profile[profile_cols].round(6).to_markdown(index=False),
        "",
        "## 3. 下位5%急落後ロング: 72H",
        "",
        lower72[cols].round(6).to_markdown(index=False),
        "",
        "## 4. 上位5%急騰後ショート: 24H",
        "",
        upper24[cols].round(6).to_markdown(index=False),
        "",
        "## 5. 清算データ取得状況",
        "",
        liquidation_profile[liquidation_cols].to_markdown(index=False),
        "",
        "清算履歴は、今回の実行では公開APIから取得できなかった。そのため、Phase 7 の清算分類は未実施であり、`shock_mr_by_liquidation_summary.csv` は空のスキーマ出力として保存した。",
        "",
        "## 6. 記事での使い方",
        "",
        "Open Interest は、急落時にポジションが減ったのか増えたのかを見る補助材料になる。",
        "",
        "`price_down_oi_down` は、価格下落と同時にOIも減っており、デレバレッジや投げ売りが進んだ可能性を示す。一方、`price_down_oi_up` は、価格下落中にもOIが増えており、新規ショート増加またはロング捕まりが残っている可能性を示す。",
        "",
        "ただし今回のOIは直近ウィンドウだけで、イベント数も少ない。記事では結論として強く使わず、Phase 7は「本来必要な追加データ」と「今回のAPI制約」を示す材料にするのが妥当である。",
        "",
    ]
    (output_dir / "phase7_oi_liquidation_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def plot_moment_bars(moment: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    metrics = [
        ("std_pct", "Std dev of 4H log returns (%)"),
        ("skew", "Skewness"),
        ("excess_kurtosis", "Excess kurtosis"),
    ]
    colors = ["#4c78a8", "#f58518", "#54a24b"]
    for ax, (metric, title), color in zip(axes, metrics, colors):
        ax.bar(moment["symbol"], moment[metric], color=color)
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
    ax.set_xticklabels(moment["symbol"])
    ax.set_title("Observed extreme 4H log returns (%)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(fig_dir / "fig_02_extreme_returns.png", dpi=dpi)
    plt.close(fig)


def plot_return_distributions(
    frames: dict[str, pd.DataFrame], fig_dir: Path, dpi: int
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for ax, (symbol, df) in zip(axes, frames.items()):
        returns = df["log_return_pct"].dropna().astype(float)
        lo, hi = returns.quantile([0.005, 0.995])
        ax.hist(returns.clip(lo, hi), bins=80, color="#4c78a8", alpha=0.85)
        ax.axvline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(f"{symbol} 4H return distribution")
        ax.set_xlabel("4H log return (%)")
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.25)
    fig.savefig(fig_dir / "fig_03_return_distribution_histograms.png", dpi=dpi)
    plt.close(fig)


def plot_return_qq(frames: dict[str, pd.DataFrame], fig_dir: Path, dpi: int) -> None:
    normal = NormalDist()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for ax, (symbol, df) in zip(axes, frames.items()):
        returns = df["log_return_pct"].dropna().astype(float).sort_values().to_numpy()
        if len(returns) < 2:
            continue
        standardized = (returns - returns.mean()) / returns.std(ddof=1)
        sample_size = min(len(standardized), 2500)
        sample_idx = np.linspace(0, len(standardized) - 1, sample_size, dtype=int)
        probs = (sample_idx + 0.5) / len(standardized)
        theoretical = np.array([normal.inv_cdf(float(p)) for p in probs])
        observed = standardized[sample_idx]
        ax.scatter(theoretical, observed, s=4, alpha=0.35, color="#4c78a8")
        lim = max(abs(theoretical).max(), abs(observed).max())
        ax.plot([-lim, lim], [-lim, lim], color="#333333", linewidth=0.8)
        ax.set_title(f"{symbol} normal QQ plot")
        ax.set_xlabel("Theoretical normal quantile")
        ax.set_ylabel("Observed standardized return")
        ax.grid(alpha=0.25)
    fig.savefig(fig_dir / "fig_03b_return_distribution_qq_plots.png", dpi=dpi)
    plt.close(fig)


def plot_direction_summary(
    direction: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True, constrained_layout=True)
    colors = {"up_bar": "#4c78a8", "down_bar": "#e45756"}
    for ax, symbol in zip(axes, SYMBOL_FILES.keys()):
        symbol_df = direction[direction["symbol"] == symbol]
        for current_direction, part in symbol_df.groupby("current_direction"):
            part = part.sort_values("horizon_bars")
            ax.plot(
                part["horizon_hours"],
                part["future_return_mean_pct"],
                marker="o",
                label=current_direction,
                color=colors[current_direction],
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(symbol)
        ax.set_xlabel("Future horizon (hours)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Mean future log return (%)")
    axes[-1].legend(loc="best")
    fig.savefig(fig_dir / "fig_04_direction_future_returns.png", dpi=dpi)
    plt.close(fig)


def plot_shock_mr_summary(shock_mr: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True, constrained_layout=True)
    colors = {
        ("lower", "5pct"): "#4c78a8",
        ("lower", "2_5pct"): "#72b7b2",
        ("lower", "1pct"): "#54a24b",
        ("upper", "5pct"): "#e45756",
        ("upper", "2_5pct"): "#f58518",
        ("upper", "1pct"): "#b279a2",
    }
    for ax, symbol in zip(axes, SYMBOL_FILES.keys()):
        symbol_df = shock_mr[shock_mr["symbol"] == symbol]
        for (side, level), part in symbol_df.groupby(["shock_side", "shock_level"]):
            part = part.sort_values("horizon_bars")
            ax.plot(
                part["horizon_hours"],
                part["mr_return_mean_pct"],
                marker="o",
                linewidth=1.3,
                label=f"{side} {level}",
                color=colors[(side, level)],
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(symbol)
        ax.set_xlabel("Future horizon (hours)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Mean reversion return (%)")
    axes[-1].legend(loc="best", fontsize=7)
    fig.savefig(fig_dir / "fig_05_shock_mean_reversion_by_horizon.png", dpi=dpi)
    plt.close(fig)


def plot_vol_abs_returns(vol_regime: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    data = vol_regime[vol_regime["horizon_hours"] == 24].copy()
    fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    regimes = list(VOL_LABELS.values())
    x = np.arange(len(regimes))
    width = 0.24
    offsets = [-width, 0.0, width]
    colors = ["#4c78a8", "#f58518", "#54a24b"]
    for offset, symbol, color in zip(offsets, SYMBOL_FILES.keys(), colors):
        part = data[data["symbol"] == symbol].set_index("vol_regime").reindex(regimes)
        ax.bar(
            x + offset,
            part["future_abs_return_mean_pct"],
            width,
            label=symbol,
            color=color,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(["Q1", "Q2", "Q3", "Q4", "Q5"])
    ax.set_title("Mean absolute 24H future return by vol20 regime")
    ax.set_xlabel("vol20 quintile")
    ax.set_ylabel("Mean abs future return (%)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.savefig(fig_dir / "fig_06_vol_regime_future_abs_return_h6.png", dpi=dpi)
    plt.close(fig)


def plot_lower5_mr_by_vol(
    shock_mr_by_vol: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    data = shock_mr_by_vol[
        (shock_mr_by_vol["shock_side"] == "lower")
        & (shock_mr_by_vol["shock_level"] == "5pct")
    ].copy()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True, constrained_layout=True)
    colors = ["#4c78a8", "#72b7b2", "#54a24b", "#f58518", "#e45756"]
    for ax, symbol in zip(axes, SYMBOL_FILES.keys()):
        symbol_data = data[data["symbol"] == symbol]
        for color, regime in zip(colors, VOL_LABELS.values()):
            part = symbol_data[symbol_data["vol_regime"] == regime].sort_values(
                "horizon_hours"
            )
            ax.plot(
                part["horizon_hours"],
                part["mr_return_mean_pct"],
                marker="o",
                linewidth=1.2,
                label=regime,
                color=color,
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(symbol)
        ax.set_xlabel("Future horizon (hours)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Lower 5% long MR mean return (%)")
    axes[-1].legend(loc="best", fontsize=7)
    fig.savefig(fig_dir / "fig_07_lower5_mr_by_vol.png", dpi=dpi)
    plt.close(fig)


def plot_phase4_path_risk(path_summary: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    labels = path_summary["candidate_label"].tolist()
    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
    ax.bar(
        x - width,
        path_summary["next_open_return_mean_pct"],
        width,
        label="Entry-to-exit mean",
        color="#4c78a8",
    )
    ax.bar(
        x,
        path_summary["mae_mean_pct"],
        width,
        label="Mean MAE",
        color="#e45756",
    )
    ax.bar(
        x + width,
        path_summary["mfe_mean_pct"],
        width,
        label="Mean MFE",
        color="#54a24b",
    )
    ax.axhline(0.0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("Next-open entry return, MAE, and MFE")
    ax.set_ylabel("Log return (%)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.savefig(fig_dir / "fig_08_path_risk_mae_mfe.png", dpi=dpi)
    plt.close(fig)


def plot_phase4_simple_equity(
    simple_events: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
    for _, part in simple_events.groupby("candidate_id", sort=False):
        ax.plot(
            part["event_number"],
            part["cumulative_return_pct"],
            linewidth=1.4,
            label=part["candidate_label"].iloc[0],
        )
    ax.axhline(0.0, color="#333333", linewidth=0.8)
    ax.set_title("Simple non-overlap event equity curve")
    ax.set_xlabel("Selected event number")
    ax.set_ylabel("Cumulative return (%)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.savefig(fig_dir / "fig_09_simple_equity_curve.png", dpi=dpi)
    plt.close(fig)


def plot_phase4_simple_drawdown(
    simple_events: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
    for _, part in simple_events.groupby("candidate_id", sort=False):
        ax.plot(
            part["event_number"],
            part["drawdown_pct"],
            linewidth=1.4,
            label=part["candidate_label"].iloc[0],
        )
    ax.axhline(0.0, color="#333333", linewidth=0.8)
    ax.set_title("Simple non-overlap event drawdown curve")
    ax.set_xlabel("Selected event number")
    ax.set_ylabel("Drawdown from event-sequence peak (%)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.savefig(fig_dir / "fig_10_simple_drawdown_curve.png", dpi=dpi)
    plt.close(fig)


def plot_phase5_annual_summary(
    annual_summary: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    plot_data = annual_summary[
        annual_summary["event_set"].isin(
            [
                "phase2_close",
                "phase3_q5_close",
                "phase4_next_open_nonoverlap",
            ]
        )
    ].copy()
    plot_data["row_label"] = plot_data["candidate_label"].str.replace(
        "P4 nonoverlap ", "P4 ", regex=False
    )
    pivot = plot_data.pivot_table(
        index="row_label",
        columns="year",
        values="mean_return_pct",
        aggfunc="first",
    ).reindex(columns=ANNUAL_YEARS)
    order = (
        plot_data[["row_label", "event_set", "symbol", "shock_side", "vol_regime_filter"]]
        .drop_duplicates("row_label")
        .sort_values(["event_set", "symbol", "shock_side", "vol_regime_filter"])
        ["row_label"]
        .tolist()
    )
    pivot = pivot.reindex(order)
    values = pivot.to_numpy(dtype=float)
    finite_values = values[np.isfinite(values)]
    limit = max(float(np.nanpercentile(np.abs(finite_values), 95)), 1.0)

    fig_height = max(6.0, 0.38 * len(pivot.index))
    fig, ax = plt.subplots(figsize=(12, fig_height), constrained_layout=True)
    masked = np.ma.masked_invalid(values)
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color="#eeeeee")
    im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=-limit, vmax=limit)
    ax.set_xticks(np.arange(len(ANNUAL_YEARS)))
    ax.set_xticklabels(ANNUAL_YEARS)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_title("Annual mean return by condition (%)")
    ax.set_xlabel("Signal year")
    ax.set_ylabel("Condition")
    for i, row_label in enumerate(pivot.index):
        for j, year in enumerate(ANNUAL_YEARS):
            value = pivot.loc[row_label, year]
            if pd.isna(value):
                text = ""
            else:
                text = f"{value:.1f}"
            ax.text(j, i, text, ha="center", va="center", fontsize=6, color="#111111")
    cbar = fig.colorbar(im, ax=ax, shrink=0.82)
    cbar.set_label("Annual mean return (%)")
    fig.savefig(fig_dir / "fig_11_annual_condition_summary.png", dpi=dpi)
    plt.close(fig)


def plot_phase6_funding_summary(
    funding_summary: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True, constrained_layout=True)
    colors = {
        "funding_low_or_negative": "#4c78a8",
        "funding_neutral": "#f58518",
        "funding_high": "#e45756",
    }
    for ax, symbol in zip(axes, SYMBOL_FILES.keys()):
        symbol_data = funding_summary[funding_summary["symbol"] == symbol]
        for regime in FUNDING_REGIME_ORDER:
            part = symbol_data[symbol_data["funding_regime"] == regime].sort_values(
                "horizon_hours"
            )
            if part.empty:
                continue
            ax.plot(
                part["horizon_hours"],
                part["funding_adjusted_mr_return_mean_pct"],
                marker="o",
                linewidth=1.4,
                label=regime.replace("funding_", ""),
                color=colors[regime],
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(symbol)
        ax.set_xlabel("Future horizon (hours)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Funding-adjusted lower 5% long return (%)")
    axes[-1].legend(loc="best", fontsize=8)
    fig.savefig(fig_dir / "fig_12_lower5_mr_by_funding.png", dpi=dpi)
    plt.close(fig)


def plot_phase7_oi_summary(oi_summary: pd.DataFrame, fig_dir: Path, dpi: int) -> None:
    data = oi_summary[oi_summary["shock_side"] == "lower"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True, constrained_layout=True)
    colors = {
        "price_down_oi_down": "#4c78a8",
        "price_down_oi_up": "#e45756",
    }
    for ax, symbol in zip(axes, SYMBOL_FILES.keys()):
        symbol_data = data[data["symbol"] == symbol]
        for regime, label in [
            ("price_down_oi_down", "OI down"),
            ("price_down_oi_up", "OI up"),
        ]:
            part = symbol_data[symbol_data["oi_regime"] == regime].sort_values(
                "horizon_hours"
            )
            if part.empty:
                continue
            ax.plot(
                part["horizon_hours"],
                part["mr_return_mean_pct"],
                marker="o",
                linewidth=1.4,
                label=label,
                color=colors[regime],
            )
        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(symbol)
        ax.set_xlabel("Future horizon (hours)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Lower 5% long MR mean return (%)")
    axes[-1].legend(loc="best", fontsize=8)
    fig.savefig(fig_dir / "fig_13_lower5_mr_by_oi.png", dpi=dpi)
    plt.close(fig)


def plot_phase7_liquidation_status(
    liquidation_profile: pd.DataFrame, fig_dir: Path, dpi: int
) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    ax.axis("off")
    status = liquidation_profile["api_status"].iloc[0]
    message = str(liquidation_profile["message"].iloc[0])
    text = (
        "Liquidation History Status\n\n"
        f"API status: {status}\n"
        "Historical market liquidation data was not available\n"
        "from the tested Binance endpoint in this run.\n\n"
        f"Message: {message[:160]}"
    )
    ax.text(
        0.03,
        0.92,
        text,
        ha="left",
        va="top",
        fontsize=12,
        family="monospace",
        transform=ax.transAxes,
    )
    fig.savefig(fig_dir / "fig_14_liquidation_regime_summary.png", dpi=dpi)
    plt.close(fig)


def write_markdown_summary(
    output_dir: Path,
    data_profile: pd.DataFrame,
    gap_events: pd.DataFrame,
    meta: dict[str, object],
    moment_summary: pd.DataFrame | None = None,
    direction_summary: pd.DataFrame | None = None,
    shock_mr_summary: pd.DataFrame | None = None,
    vol_regime_summary: pd.DataFrame | None = None,
    shock_mr_by_vol_summary: pd.DataFrame | None = None,
    path_risk_summary: pd.DataFrame | None = None,
    simple_backtest_summary: pd.DataFrame | None = None,
    annual_condition_summary: pd.DataFrame | None = None,
    annual_stability_summary: pd.DataFrame | None = None,
    funding_profile: pd.DataFrame | None = None,
    funding_summary: pd.DataFrame | None = None,
    oi_profile: pd.DataFrame | None = None,
    oi_summary: pd.DataFrame | None = None,
    liquidation_profile: pd.DataFrame | None = None,
) -> None:
    summary = data_profile.copy()
    timestamp_cols = ["first_timestamp", "last_timestamp", "common_start", "common_end"]
    for col in timestamp_cols:
        summary[col] = summary[col].map(format_timestamp)

    pass_count = int((summary["phase0_status"] == "PASS").sum())
    warn_count = int((summary["phase0_status"] == "WARN").sum())
    gap_summary = gap_events.copy()
    for col in ["previous_timestamp", "current_timestamp"]:
        if col in gap_summary.columns:
            gap_summary[col] = gap_summary[col].map(format_timestamp)

    lines = [
        "# BTC/ETH/SOL Crypto Crash-Rebound Experiment",
        "",
        "## Phase 0 Data Profile",
        "",
        "- Phase: 0",
        "- Purpose: validate input 240-minute OHLCV CSV files before return-distribution and crash-rebound analysis.",
        f"- Symbols: {', '.join(meta['symbols'])}",
        f"- Common period: {format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}",
        f"- Expected common rows per symbol: {meta['expected_common_rows']}",
        f"- Status counts: PASS={pass_count}, WARN={warn_count}",
        "- Input format assumption: headerless tab-separated columns `timestamp, open, high, low, close, volume`.",
        "",
        "## Data Profile",
        "",
        summary.to_markdown(index=False),
        "",
        "## Phase 0 Interpretation",
        "",
    ]

    if warn_count == 0:
        lines.extend(
            [
                "All three files passed the Phase 0 structural checks used by this script.",
                "",
                "The three-symbol common period is ready for OHLCV-only Phase 1 to Phase 5 experiments.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "At least one file has a Phase 0 warning. Inspect `data_profile.csv` before using the dataset for return analysis.",
                "",
                "The detected timestamp gaps are listed in `timestamp_gap_events.csv`.",
                "",
            ]
        )

    lines.extend(["## Timestamp Gap Events", ""])
    if gap_summary.empty:
        lines.extend(["No timestamp gaps were detected.", ""])
    else:
        lines.extend([gap_summary.to_markdown(index=False), ""])

    lines.extend(
        [
            "Open items before Perpetual-specific claims:",
            "",
            "- Confirm whether the current OHLCV files are spot or futures/perpetual data.",
            "- Confirm whether `volume` is base volume or quote volume.",
            "- Add separate Funding Rate, Open Interest, and liquidation datasets before Phase 6 and Phase 7.",
            "",
        ]
    )

    if moment_summary is not None:
        moment = moment_summary.copy()
        lines.extend(
            [
                "## Phase 1 Moment Summary",
                "",
                "- Phase: 1",
                "- Purpose: compare BTC/ETH/SOL 4H return distributions over the common period.",
                "- Return definition: `log(close_t / close_{t-1}) * 100`.",
                "- Gap handling: returns that cross a non-4H timestamp gap are set to missing and excluded from distribution statistics.",
                "",
                moment.round(6).to_markdown(index=False),
                "",
                "## Phase 1 Figures",
                "",
                "- `figures/fig_01_moment_std_skew_kurtosis.png`",
                "- `figures/fig_02_extreme_returns.png`",
                "- `figures/fig_03_return_distribution_histograms.png`",
                "- `figures/fig_03b_return_distribution_qq_plots.png`",
                "",
            ]
        )

    if direction_summary is not None and shock_mr_summary is not None:
        direction = direction_summary.copy()
        shock = shock_mr_summary.copy()
        lower5 = shock[
            (shock["shock_side"] == "lower") & (shock["shock_level"] == "5pct")
        ]
        upper5 = shock[
            (shock["shock_side"] == "upper") & (shock["shock_level"] == "5pct")
        ]
        lines.extend(
            [
                "## Phase 2 Event Study Summary",
                "",
                "- Phase: 2",
                "- Purpose: compare future returns after upper/lower tail 4H moves.",
                "- Horizons: 4H, 8H, 12H, 24H, 48H, and 72H.",
                "- Shock thresholds: full-sample per-symbol 5%, 2.5%, and 1% tails. This is exploratory and not a production trading rule.",
                "- Gap handling: future returns that cross a non-4H timestamp gap are excluded.",
                "",
                "### Direction Summary",
                "",
                direction.round(6).to_markdown(index=False),
                "",
                "### Lower 5% Crash Long Mean-Reversion Summary",
                "",
                lower5.round(6).to_markdown(index=False),
                "",
                "### Upper 5% Rally Short Mean-Reversion Summary",
                "",
                upper5.round(6).to_markdown(index=False),
                "",
                "## Phase 2 Figures",
                "",
                "- `figures/fig_04_direction_future_returns.png`",
                "- `figures/fig_05_shock_mean_reversion_by_horizon.png`",
                "",
            ]
        )

    if vol_regime_summary is not None and shock_mr_by_vol_summary is not None:
        vol_h24 = vol_regime_summary[
            vol_regime_summary["horizon_hours"] == 24
        ].copy()
        lower5_h24 = shock_mr_by_vol_summary[
            (shock_mr_by_vol_summary["shock_side"] == "lower")
            & (shock_mr_by_vol_summary["shock_level"] == "5pct")
            & (shock_mr_by_vol_summary["horizon_hours"] == 24)
        ].copy()
        lower5_h72 = shock_mr_by_vol_summary[
            (shock_mr_by_vol_summary["shock_side"] == "lower")
            & (shock_mr_by_vol_summary["shock_level"] == "5pct")
            & (shock_mr_by_vol_summary["horizon_hours"] == 72)
        ].copy()
        lines.extend(
            [
                "## Phase 3 Volatility Regime Summary",
                "",
                "- Phase: 3",
                "- Purpose: split future returns and lower-tail mean reversion by 20-bar realized-volatility quintile.",
                "- Volatility definition: rolling 20-bar standard deviation of 4H log returns.",
                "- Regimes: Q1_low, Q2_lower, Q3_mid, Q4_higher, Q5_high.",
                "",
                "### 24H Future Absolute Return by Vol Regime",
                "",
                vol_h24.round(6).to_markdown(index=False),
                "",
                "### Lower 5% Crash Long MR by Vol Regime at 24H",
                "",
                lower5_h24.round(6).to_markdown(index=False),
                "",
                "### Lower 5% Crash Long MR by Vol Regime at 72H",
                "",
                lower5_h72.round(6).to_markdown(index=False),
                "",
                "## Phase 3 Figures",
                "",
                "- `figures/fig_06_vol_regime_future_abs_return_h6.png`",
                "- `figures/fig_07_lower5_mr_by_vol.png`",
                "",
            ]
        )

    if path_risk_summary is not None and simple_backtest_summary is not None:
        path_cols = [
            "candidate_label",
            "event_count",
            "horizon_hours",
            "next_open_return_mean_pct",
            "win_rate_pct",
            "mae_mean_pct",
            "mfe_mean_pct",
        ]
        simple_cols = [
            "candidate_label",
            "selected_event_count",
            "final_cumulative_return_pct",
            "max_drawdown_pct",
            "profit_factor",
        ]
        lines.extend(
            [
                "## Phase 4 Next-Open Path Risk Summary",
                "",
                "- Phase: 4",
                "- Purpose: replace same-close event-study returns with next-4H-open entry returns and measure MAE/MFE.",
                "- Entry: next 4H open after the crash signal close.",
                "- Exit: fixed time exit at the candidate horizon.",
                "- Simple backtest: one position at a time per candidate; overlapping signals are skipped.",
                "",
                "### All Signal Path Risk",
                "",
                path_risk_summary[path_cols].round(6).to_markdown(index=False),
                "",
                "### Non-Overlapping Simple Backtest",
                "",
                simple_backtest_summary[simple_cols].round(6).to_markdown(
                    index=False
                ),
                "",
                "## Phase 4 Figures",
                "",
                "- `figures/fig_08_path_risk_mae_mfe.png`",
                "- `figures/fig_09_simple_equity_curve.png`",
                "- `figures/fig_10_simple_drawdown_curve.png`",
                "",
            ]
        )

    if annual_condition_summary is not None and annual_stability_summary is not None:
        stability_cols = [
            "candidate_label",
            "total_event_count",
            "years_with_events",
            "positive_year_rate_pct",
            "mean_of_annual_means_pct",
            "min_annual_mean_pct",
            "worst_annual_drawdown_pct",
            "stability_label",
        ]
        lines.extend(
            [
                "## Phase 5 Annual Stability Summary",
                "",
                "- Phase: 5",
                "- Purpose: check whether candidate returns depend on only one or two years.",
                "- Year definition: signal year.",
                "- Partial years: 2020 and 2026.",
                "",
                annual_stability_summary[stability_cols]
                .round(6)
                .to_markdown(index=False),
                "",
                "## Phase 5 Figures",
                "",
                "- `figures/fig_11_annual_condition_summary.png`",
                "",
            ]
        )

    if funding_profile is not None and funding_summary is not None:
        funding_cols = [
            "symbol",
            "funding_regime",
            "horizon_hours",
            "count",
            "holding_funding_sum_mean_pct",
            "gross_mr_return_mean_pct",
            "funding_adjusted_mr_return_mean_pct",
            "funding_adjusted_mr_win_rate_pct",
        ]
        h72 = funding_summary[funding_summary["horizon_hours"] == 72].copy()
        lines.extend(
            [
                "## Phase 6 Funding Rate Summary",
                "",
                "- Phase: 6",
                "- Purpose: classify lower-tail crash long candidates by Binance USD-M Funding Rate state.",
                "- Funding regime: per-symbol 20% / 80% funding quantiles, with negative funding included in low-or-negative.",
                "- Funding adjustment: long return minus funding paid during the holding window.",
                "",
                h72[funding_cols].round(6).to_markdown(index=False),
                "",
                "## Phase 6 Figures",
                "",
                "- `figures/fig_12_lower5_mr_by_funding.png`",
                "",
            ]
        )

    if (
        oi_profile is not None
        and oi_summary is not None
        and liquidation_profile is not None
    ):
        oi_cols = [
            "symbol",
            "oi_regime",
            "horizon_hours",
            "count",
            "oi_value_change_24h_mean_pct",
            "mr_return_mean_pct",
            "mr_win_rate_pct",
        ]
        lower72 = oi_summary[
            (oi_summary["shock_side"] == "lower") & (oi_summary["horizon_hours"] == 72)
        ].copy()
        lines.extend(
            [
                "## Phase 7 Open Interest / Liquidation Summary",
                "",
                "- Phase: 7",
                "- Purpose: classify lower-tail crash events by 24H Open Interest change.",
                "- Important limitation: Binance `openInterestHist` returned only a recent rolling window in this run.",
                "- Liquidation history: unavailable from the tested public endpoint in this run.",
                "",
                lower72[oi_cols].round(6).to_markdown(index=False),
                "",
                "## Phase 7 Figures",
                "",
                "- `figures/fig_13_lower5_mr_by_oi.png`",
                "- `figures/fig_14_liquidation_regime_summary.png`",
                "",
            ]
        )

    (output_dir / "article_experiment_summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def save_data_profile(profile: pd.DataFrame, output_dir: Path) -> None:
    out = profile.copy()
    for col in ["first_timestamp", "last_timestamp", "common_start", "common_end"]:
        out[col] = out[col].map(format_timestamp)
    out.to_csv(output_dir / "data_profile.csv", index=False, lineterminator="\n")


def save_gap_events(gap_events: pd.DataFrame, output_dir: Path) -> None:
    out = gap_events.copy()
    for col in ["previous_timestamp", "current_timestamp"]:
        if col in out.columns:
            out[col] = out[col].map(format_timestamp)
    out.to_csv(output_dir / "timestamp_gap_events.csv", index=False, lineterminator="\n")


def run_phase0(data_dir: Path, output_dir: Path) -> None:
    output_dir = ensure_dir(output_dir)
    profile, gap_events, meta = build_data_profile(data_dir)
    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    write_markdown_summary(output_dir, profile, gap_events, meta)
    print(
        "Phase 0 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase1(data_dir: Path, output_dir: Path, dpi: int) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    write_markdown_summary(output_dir, profile, gap_events, meta, moment)

    print(
        "Phase 1 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase2(data_dir: Path, output_dir: Path, dpi: int) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)
    direction = build_direction_summary(featured_frames)
    shock_mr = build_shock_mr_summary(featured_frames)
    candidate = build_phase2_candidate_summary(shock_mr)

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(candidate, output_dir / "phase2_candidate_summary.csv")
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    write_markdown_summary(
        output_dir, profile, gap_events, meta, moment, direction, shock_mr
    )
    write_phase2_event_study_report(output_dir, direction, shock_mr, candidate)

    print(
        "Phase 2 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase3(data_dir: Path, output_dir: Path, dpi: int) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)
    direction = build_direction_summary(featured_frames)
    shock_mr = build_shock_mr_summary(featured_frames)
    phase2_candidate = build_phase2_candidate_summary(shock_mr)
    vol_regime = build_vol_regime_summary(featured_frames)
    shock_mr_by_vol = build_shock_mr_by_vol_summary(featured_frames)
    phase3_candidate = build_phase3_lower5_by_vol_candidate_summary(shock_mr_by_vol)

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(phase2_candidate, output_dir / "phase2_candidate_summary.csv")
    save_csv(vol_regime, output_dir / "vol_regime_summary.csv")
    save_csv(shock_mr_by_vol, output_dir / "shock_mean_reversion_by_vol_summary.csv")
    save_csv(
        phase3_candidate, output_dir / "phase3_lower5_by_vol_candidate_summary.csv"
    )
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    plot_vol_abs_returns(vol_regime, fig_dir, dpi)
    plot_lower5_mr_by_vol(shock_mr_by_vol, fig_dir, dpi)
    write_markdown_summary(
        output_dir,
        profile,
        gap_events,
        meta,
        moment,
        direction,
        shock_mr,
        vol_regime,
        shock_mr_by_vol,
    )
    write_phase2_event_study_report(output_dir, direction, shock_mr, phase2_candidate)
    write_phase3_vol_regime_report(
        output_dir, vol_regime, shock_mr_by_vol, phase3_candidate
    )

    print(
        "Phase 3 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase4(data_dir: Path, output_dir: Path, dpi: int) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)
    direction = build_direction_summary(featured_frames)
    shock_mr = build_shock_mr_summary(featured_frames)
    phase2_candidate = build_phase2_candidate_summary(shock_mr)
    vol_regime = build_vol_regime_summary(featured_frames)
    shock_mr_by_vol = build_shock_mr_by_vol_summary(featured_frames)
    phase3_candidate = build_phase3_lower5_by_vol_candidate_summary(shock_mr_by_vol)
    phase4_candidates = build_phase4_candidate_table(
        phase2_candidate, phase3_candidate
    )
    path_events = build_path_risk_events(featured_frames, phase4_candidates)
    path_summary = summarize_event_returns(path_events)
    simple_events = build_simple_backtest_events(path_events)
    simple_summary = build_simple_backtest_summary(path_events, simple_events)

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(phase2_candidate, output_dir / "phase2_candidate_summary.csv")
    save_csv(vol_regime, output_dir / "vol_regime_summary.csv")
    save_csv(shock_mr_by_vol, output_dir / "shock_mean_reversion_by_vol_summary.csv")
    save_csv(
        phase3_candidate, output_dir / "phase3_lower5_by_vol_candidate_summary.csv"
    )
    save_csv(phase4_candidates, output_dir / "phase4_candidate_table.csv")
    save_csv(path_summary, output_dir / "path_risk_summary.csv")
    save_csv(format_event_timestamps(path_events), output_dir / "path_risk_events.csv")
    save_csv(simple_summary, output_dir / "simple_backtest_summary.csv")
    save_csv(
        format_event_timestamps(simple_events),
        output_dir / "simple_backtest_events.csv",
    )
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    plot_vol_abs_returns(vol_regime, fig_dir, dpi)
    plot_lower5_mr_by_vol(shock_mr_by_vol, fig_dir, dpi)
    plot_phase4_path_risk(path_summary, fig_dir, dpi)
    plot_phase4_simple_equity(simple_events, fig_dir, dpi)
    plot_phase4_simple_drawdown(simple_events, fig_dir, dpi)
    write_markdown_summary(
        output_dir,
        profile,
        gap_events,
        meta,
        moment,
        direction,
        shock_mr,
        vol_regime,
        shock_mr_by_vol,
        path_summary,
        simple_summary,
    )
    write_phase2_event_study_report(output_dir, direction, shock_mr, phase2_candidate)
    write_phase3_vol_regime_report(
        output_dir, vol_regime, shock_mr_by_vol, phase3_candidate
    )
    write_phase4_path_risk_report(
        output_dir, phase4_candidates, path_summary, simple_summary
    )

    print(
        "Phase 4 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase5(data_dir: Path, output_dir: Path, dpi: int) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)
    direction = build_direction_summary(featured_frames)
    shock_mr = build_shock_mr_summary(featured_frames)
    phase2_candidate = build_phase2_candidate_summary(shock_mr)
    vol_regime = build_vol_regime_summary(featured_frames)
    shock_mr_by_vol = build_shock_mr_by_vol_summary(featured_frames)
    phase3_candidate = build_phase3_lower5_by_vol_candidate_summary(shock_mr_by_vol)
    phase4_candidates = build_phase4_candidate_table(
        phase2_candidate, phase3_candidate
    )
    path_events = build_path_risk_events(featured_frames, phase4_candidates)
    path_summary = summarize_event_returns(path_events)
    simple_events = build_simple_backtest_events(path_events)
    simple_summary = build_simple_backtest_summary(path_events, simple_events)
    phase5_close_candidates = build_phase5_close_candidate_table(
        phase2_candidate, phase3_candidate
    )
    close_events = build_close_to_close_candidate_events(
        featured_frames, phase5_close_candidates
    )
    annual_events = build_phase5_annual_events(close_events, path_events, simple_events)
    annual_summary = build_annual_condition_summary(annual_events)
    annual_stability = build_annual_stability_summary(annual_summary)

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(phase2_candidate, output_dir / "phase2_candidate_summary.csv")
    save_csv(vol_regime, output_dir / "vol_regime_summary.csv")
    save_csv(shock_mr_by_vol, output_dir / "shock_mean_reversion_by_vol_summary.csv")
    save_csv(
        phase3_candidate, output_dir / "phase3_lower5_by_vol_candidate_summary.csv"
    )
    save_csv(phase4_candidates, output_dir / "phase4_candidate_table.csv")
    save_csv(path_summary, output_dir / "path_risk_summary.csv")
    save_csv(format_event_timestamps(path_events), output_dir / "path_risk_events.csv")
    save_csv(simple_summary, output_dir / "simple_backtest_summary.csv")
    save_csv(
        format_event_timestamps(simple_events),
        output_dir / "simple_backtest_events.csv",
    )
    save_csv(phase5_close_candidates, output_dir / "phase5_close_candidate_table.csv")
    save_csv(
        format_event_timestamps(annual_events),
        output_dir / "annual_condition_events.csv",
    )
    save_csv(annual_summary, output_dir / "annual_condition_summary.csv")
    save_csv(annual_stability, output_dir / "annual_stability_summary.csv")
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    plot_vol_abs_returns(vol_regime, fig_dir, dpi)
    plot_lower5_mr_by_vol(shock_mr_by_vol, fig_dir, dpi)
    plot_phase4_path_risk(path_summary, fig_dir, dpi)
    plot_phase4_simple_equity(simple_events, fig_dir, dpi)
    plot_phase4_simple_drawdown(simple_events, fig_dir, dpi)
    plot_phase5_annual_summary(annual_summary, fig_dir, dpi)
    write_markdown_summary(
        output_dir,
        profile,
        gap_events,
        meta,
        moment,
        direction,
        shock_mr,
        vol_regime,
        shock_mr_by_vol,
        path_summary,
        simple_summary,
        annual_summary,
        annual_stability,
    )
    write_phase2_event_study_report(output_dir, direction, shock_mr, phase2_candidate)
    write_phase3_vol_regime_report(
        output_dir, vol_regime, shock_mr_by_vol, phase3_candidate
    )
    write_phase4_path_risk_report(
        output_dir, phase4_candidates, path_summary, simple_summary
    )
    write_phase5_annual_stability_report(
        output_dir, annual_summary, annual_stability
    )

    print(
        "Phase 5 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase6(
    data_dir: Path, output_dir: Path, dpi: int, refresh_funding: bool
) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)
    direction = build_direction_summary(featured_frames)
    shock_mr = build_shock_mr_summary(featured_frames)
    phase2_candidate = build_phase2_candidate_summary(shock_mr)
    vol_regime = build_vol_regime_summary(featured_frames)
    shock_mr_by_vol = build_shock_mr_by_vol_summary(featured_frames)
    phase3_candidate = build_phase3_lower5_by_vol_candidate_summary(shock_mr_by_vol)
    phase4_candidates = build_phase4_candidate_table(
        phase2_candidate, phase3_candidate
    )
    path_events = build_path_risk_events(featured_frames, phase4_candidates)
    path_summary = summarize_event_returns(path_events)
    simple_events = build_simple_backtest_events(path_events)
    simple_summary = build_simple_backtest_summary(path_events, simple_events)
    phase5_close_candidates = build_phase5_close_candidate_table(
        phase2_candidate, phase3_candidate
    )
    close_events = build_close_to_close_candidate_events(
        featured_frames, phase5_close_candidates
    )
    annual_events = build_phase5_annual_events(close_events, path_events, simple_events)
    annual_summary = build_annual_condition_summary(annual_events)
    annual_stability = build_annual_stability_summary(annual_summary)
    funding = load_or_fetch_funding_history(
        output_dir,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
        refresh_funding,
    )
    funded_frames, funding_thresholds = attach_funding_features(
        featured_frames, funding
    )
    funding_profile = build_funding_profile(
        funding, funded_frames, funding_thresholds
    )
    funding_events = build_shock_mr_by_funding_events(
        funded_frames, funding, funding_thresholds
    )
    funding_summary = build_shock_mr_by_funding_summary(funding_events)

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(phase2_candidate, output_dir / "phase2_candidate_summary.csv")
    save_csv(vol_regime, output_dir / "vol_regime_summary.csv")
    save_csv(shock_mr_by_vol, output_dir / "shock_mean_reversion_by_vol_summary.csv")
    save_csv(
        phase3_candidate, output_dir / "phase3_lower5_by_vol_candidate_summary.csv"
    )
    save_csv(phase4_candidates, output_dir / "phase4_candidate_table.csv")
    save_csv(path_summary, output_dir / "path_risk_summary.csv")
    save_csv(format_event_timestamps(path_events), output_dir / "path_risk_events.csv")
    save_csv(simple_summary, output_dir / "simple_backtest_summary.csv")
    save_csv(
        format_event_timestamps(simple_events),
        output_dir / "simple_backtest_events.csv",
    )
    save_csv(phase5_close_candidates, output_dir / "phase5_close_candidate_table.csv")
    save_csv(
        format_event_timestamps(annual_events),
        output_dir / "annual_condition_events.csv",
    )
    save_csv(annual_summary, output_dir / "annual_condition_summary.csv")
    save_csv(annual_stability, output_dir / "annual_stability_summary.csv")
    save_csv(
        format_event_timestamps(funding_profile), output_dir / "funding_profile.csv"
    )
    save_csv(
        format_event_timestamps(funding_events),
        output_dir / "shock_mr_by_funding_events.csv",
    )
    save_csv(funding_summary, output_dir / "shock_mr_by_funding_summary.csv")
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    plot_vol_abs_returns(vol_regime, fig_dir, dpi)
    plot_lower5_mr_by_vol(shock_mr_by_vol, fig_dir, dpi)
    plot_phase4_path_risk(path_summary, fig_dir, dpi)
    plot_phase4_simple_equity(simple_events, fig_dir, dpi)
    plot_phase4_simple_drawdown(simple_events, fig_dir, dpi)
    plot_phase5_annual_summary(annual_summary, fig_dir, dpi)
    plot_phase6_funding_summary(funding_summary, fig_dir, dpi)
    write_markdown_summary(
        output_dir,
        profile,
        gap_events,
        meta,
        moment,
        direction,
        shock_mr,
        vol_regime,
        shock_mr_by_vol,
        path_summary,
        simple_summary,
        annual_summary,
        annual_stability,
        funding_profile,
        funding_summary,
    )
    write_phase2_event_study_report(output_dir, direction, shock_mr, phase2_candidate)
    write_phase3_vol_regime_report(
        output_dir, vol_regime, shock_mr_by_vol, phase3_candidate
    )
    write_phase4_path_risk_report(
        output_dir, phase4_candidates, path_summary, simple_summary
    )
    write_phase5_annual_stability_report(
        output_dir, annual_summary, annual_stability
    )
    write_phase6_funding_report(output_dir, funding_profile, funding_summary)

    print(
        "Phase 6 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def run_phase7(
    data_dir: Path,
    output_dir: Path,
    dpi: int,
    refresh_funding: bool,
    refresh_open_interest: bool,
) -> None:
    output_dir = ensure_dir(output_dir)
    fig_dir = ensure_dir(output_dir / "figures")
    profile, gap_events, meta = build_data_profile(data_dir)
    frames = load_clean_frames(data_dir)
    common_frames = build_common_frames(
        frames,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
    )
    featured_frames = {
        symbol: add_return_features(frame) for symbol, frame in common_frames.items()
    }
    moment = build_moment_summary(featured_frames)
    direction = build_direction_summary(featured_frames)
    shock_mr = build_shock_mr_summary(featured_frames)
    phase2_candidate = build_phase2_candidate_summary(shock_mr)
    vol_regime = build_vol_regime_summary(featured_frames)
    shock_mr_by_vol = build_shock_mr_by_vol_summary(featured_frames)
    phase3_candidate = build_phase3_lower5_by_vol_candidate_summary(shock_mr_by_vol)
    phase4_candidates = build_phase4_candidate_table(
        phase2_candidate, phase3_candidate
    )
    path_events = build_path_risk_events(featured_frames, phase4_candidates)
    path_summary = summarize_event_returns(path_events)
    simple_events = build_simple_backtest_events(path_events)
    simple_summary = build_simple_backtest_summary(path_events, simple_events)
    phase5_close_candidates = build_phase5_close_candidate_table(
        phase2_candidate, phase3_candidate
    )
    close_events = build_close_to_close_candidate_events(
        featured_frames, phase5_close_candidates
    )
    annual_events = build_phase5_annual_events(close_events, path_events, simple_events)
    annual_summary = build_annual_condition_summary(annual_events)
    annual_stability = build_annual_stability_summary(annual_summary)
    funding = load_or_fetch_funding_history(
        output_dir,
        pd.Timestamp(meta["common_start"]),
        pd.Timestamp(meta["common_end"]),
        refresh_funding,
    )
    funded_frames, funding_thresholds = attach_funding_features(
        featured_frames, funding
    )
    funding_profile = build_funding_profile(
        funding, funded_frames, funding_thresholds
    )
    funding_events = build_shock_mr_by_funding_events(
        funded_frames, funding, funding_thresholds
    )
    funding_summary = build_shock_mr_by_funding_summary(funding_events)
    open_interest = load_or_fetch_open_interest_history(
        output_dir, pd.Timestamp(meta["common_end"]), refresh_open_interest
    )
    oi_frames = attach_open_interest_features(featured_frames, open_interest)
    oi_profile = build_oi_profile(open_interest, oi_frames)
    oi_events = build_shock_mr_by_oi_events(oi_frames)
    oi_summary = build_shock_mr_by_oi_summary(oi_events)
    liquidation_probe = probe_liquidation_history_endpoint()
    liquidation_profile = build_liquidation_profile(liquidation_probe)
    liquidation_summary = pd.DataFrame(
        columns=[
            "symbol",
            "liquidation_regime",
            "shock_side",
            "shock_level",
            "horizon_bars",
            "horizon_hours",
            "count",
            "mr_return_mean_pct",
            "mr_win_rate_pct",
            "mr_return_t_stat",
            "analysis_status",
        ]
    )

    save_data_profile(profile, output_dir)
    save_gap_events(gap_events, output_dir)
    save_moment_summary(moment, output_dir)
    save_csv(direction, output_dir / "direction_return_summary.csv")
    save_csv(shock_mr, output_dir / "shock_mean_reversion_summary.csv")
    save_csv(phase2_candidate, output_dir / "phase2_candidate_summary.csv")
    save_csv(vol_regime, output_dir / "vol_regime_summary.csv")
    save_csv(shock_mr_by_vol, output_dir / "shock_mean_reversion_by_vol_summary.csv")
    save_csv(
        phase3_candidate, output_dir / "phase3_lower5_by_vol_candidate_summary.csv"
    )
    save_csv(phase4_candidates, output_dir / "phase4_candidate_table.csv")
    save_csv(path_summary, output_dir / "path_risk_summary.csv")
    save_csv(format_event_timestamps(path_events), output_dir / "path_risk_events.csv")
    save_csv(simple_summary, output_dir / "simple_backtest_summary.csv")
    save_csv(
        format_event_timestamps(simple_events),
        output_dir / "simple_backtest_events.csv",
    )
    save_csv(phase5_close_candidates, output_dir / "phase5_close_candidate_table.csv")
    save_csv(
        format_event_timestamps(annual_events),
        output_dir / "annual_condition_events.csv",
    )
    save_csv(annual_summary, output_dir / "annual_condition_summary.csv")
    save_csv(annual_stability, output_dir / "annual_stability_summary.csv")
    save_csv(
        format_event_timestamps(funding_profile), output_dir / "funding_profile.csv"
    )
    save_csv(
        format_event_timestamps(funding_events),
        output_dir / "shock_mr_by_funding_events.csv",
    )
    save_csv(funding_summary, output_dir / "shock_mr_by_funding_summary.csv")
    save_csv(format_event_timestamps(oi_profile), output_dir / "oi_profile.csv")
    save_csv(
        format_event_timestamps(oi_events), output_dir / "shock_mr_by_oi_events.csv"
    )
    save_csv(oi_summary, output_dir / "shock_mr_by_oi_summary.csv")
    save_csv(liquidation_profile, output_dir / "liquidation_profile.csv")
    save_csv(
        liquidation_summary, output_dir / "shock_mr_by_liquidation_summary.csv"
    )
    plot_moment_bars(moment, fig_dir, dpi)
    plot_return_distributions(featured_frames, fig_dir, dpi)
    plot_return_qq(featured_frames, fig_dir, dpi)
    plot_direction_summary(direction, fig_dir, dpi)
    plot_shock_mr_summary(shock_mr, fig_dir, dpi)
    plot_vol_abs_returns(vol_regime, fig_dir, dpi)
    plot_lower5_mr_by_vol(shock_mr_by_vol, fig_dir, dpi)
    plot_phase4_path_risk(path_summary, fig_dir, dpi)
    plot_phase4_simple_equity(simple_events, fig_dir, dpi)
    plot_phase4_simple_drawdown(simple_events, fig_dir, dpi)
    plot_phase5_annual_summary(annual_summary, fig_dir, dpi)
    plot_phase6_funding_summary(funding_summary, fig_dir, dpi)
    plot_phase7_oi_summary(oi_summary, fig_dir, dpi)
    plot_phase7_liquidation_status(liquidation_profile, fig_dir, dpi)
    write_markdown_summary(
        output_dir,
        profile,
        gap_events,
        meta,
        moment,
        direction,
        shock_mr,
        vol_regime,
        shock_mr_by_vol,
        path_summary,
        simple_summary,
        annual_summary,
        annual_stability,
        funding_profile,
        funding_summary,
        oi_profile,
        oi_summary,
        liquidation_profile,
    )
    write_phase2_event_study_report(output_dir, direction, shock_mr, phase2_candidate)
    write_phase3_vol_regime_report(
        output_dir, vol_regime, shock_mr_by_vol, phase3_candidate
    )
    write_phase4_path_risk_report(
        output_dir, phase4_candidates, path_summary, simple_summary
    )
    write_phase5_annual_stability_report(
        output_dir, annual_summary, annual_stability
    )
    write_phase6_funding_report(output_dir, funding_profile, funding_summary)
    write_phase7_oi_liquidation_report(
        output_dir, oi_profile, oi_summary, liquidation_profile
    )

    print(
        "Phase 7 common period: "
        f"{format_timestamp(meta['common_start'])} to {format_timestamp(meta['common_end'])}"
    )
    print(f"Wrote outputs to: {output_dir}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run lab_6 crypto crash-rebound article experiments."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing BTCUSDT240.csv, ETHUSDT240.csv, and SOLUSDT240.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent
        / "outputs"
        / "crypto_crash_rebound_ohlcv",
        help="Directory for generated CSV and Markdown outputs.",
    )
    parser.add_argument(
        "--phase",
        choices=[
            "phase0",
            "phase1",
            "phase2",
            "phase3",
            "phase4",
            "phase5",
            "phase6",
            "phase7",
        ],
        default="phase7",
        help="Experiment phase to run. Later phases refresh earlier outputs.",
    )
    parser.add_argument(
        "--refresh-funding",
        action="store_true",
        help="Fetch Binance funding history even when a cached CSV exists.",
    )
    parser.add_argument(
        "--refresh-open-interest",
        action="store_true",
        help="Fetch Binance Open Interest history even when a cached CSV exists.",
    )
    parser.add_argument("--dpi", type=int, default=180, help="Figure DPI.")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.phase == "phase0":
        run_phase0(args.data_dir, args.output_dir)
    elif args.phase == "phase1":
        run_phase1(args.data_dir, args.output_dir, args.dpi)
    elif args.phase == "phase2":
        run_phase2(args.data_dir, args.output_dir, args.dpi)
    elif args.phase == "phase3":
        run_phase3(args.data_dir, args.output_dir, args.dpi)
    elif args.phase == "phase4":
        run_phase4(args.data_dir, args.output_dir, args.dpi)
    elif args.phase == "phase5":
        run_phase5(args.data_dir, args.output_dir, args.dpi)
    elif args.phase == "phase6":
        run_phase6(args.data_dir, args.output_dir, args.dpi, args.refresh_funding)
    elif args.phase == "phase7":
        run_phase7(
            args.data_dir,
            args.output_dir,
            args.dpi,
            args.refresh_funding,
            args.refresh_open_interest,
        )


if __name__ == "__main__":
    main()
