#!/usr/bin/env python3
"""Run the lab_11 two-pair 2Y yield-spread filter experiment.

The experiment uses FX Nexus local DuckDB data for FX prices, USD/EUR
sovereign yields, regimes, distortion, and cost context. JPY historical 2Y
yield data is pulled from the official Ministry of Finance historical CSV
because the current FX Nexus JPY adapter stores only the current-month CSV.
All experiment artifacts are written under lab_11 only.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

import duckdb
import numpy as np
import pandas as pd
import requests


PAIRS = ("EURUSD", "USDJPY")
SINCE = pd.Timestamp("2021-06-16")
HORIZONS = (5, 10, 20)

LAB_DIR = Path(__file__).resolve().parent
OUT_DIR = LAB_DIR / "outputs" / "yield_spread_filter"
DATA_DIR = OUT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
TABLE_DIR = OUT_DIR / "tables"
FIGURE_DIR = OUT_DIR / "figures"
REPORT_DIR = OUT_DIR / "report"

FX_NEXUS_ROOT = Path(
    os.environ.get("FX_NEXUS_ROOT", "/Users/tikeda/workspace/fx_nexus")
)
FX_NEXUS_DB = Path(
    os.environ.get("FX_NEXUS_DB", str(FX_NEXUS_ROOT / "var" / "fx_nexus.duckdb"))
)

MOF_JGB_HISTORICAL_CSV_URL = (
    "https://www.mof.go.jp/english/policy/jgbs/reference/"
    "interest_rate/historical/jgbcme_all.csv"
)
MOF_JGB_PAGE_URL = (
    "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm"
)


@dataclass(frozen=True)
class ChartSeries:
    label: str
    x: list[pd.Timestamp]
    y: list[float]
    color: str


def main() -> None:
    ensure_directories()
    con = duckdb.connect(str(FX_NEXUS_DB), read_only=True)

    ohlcv = read_ohlcv(con)
    fx_yields = read_fx_nexus_sovereign_yields(con)
    jpy_yields = fetch_mof_jpy_yields()
    sovereign_yields = merge_sovereign_yields(fx_yields, jpy_yields)
    pair_features = build_pair_yield_spread_features(sovereign_yields, ohlcv)
    context = read_pair_context(con)
    master = build_master(pair_features, ohlcv, context)
    experiment_sample = master.loc[master["fwd_ret_20d_bp"].notna()].copy()

    raw_save(fx_yields, "fx_nexus_sovereign_yields_usd_eur.csv")
    raw_save(jpy_yields, "mof_jpy_2y_yields.csv")
    raw_save(sovereign_yields, "combined_sovereign_2y_yields.csv")
    raw_save(pair_features, "pair_yield_spread_features_rebuilt.csv")

    data_coverage = build_data_coverage(
        sovereign_yields,
        pair_features,
        ohlcv,
        experiment_sample,
    )
    experiment1 = experiment_level_bucket(experiment_sample)
    experiment2 = experiment_change_bucket(experiment_sample)
    experiment3 = experiment_alignment(experiment_sample)
    experiment4 = experiment_divergence(experiment_sample)
    experiment5 = experiment_regime(experiment_sample)
    latest = latest_snapshot(master)

    save_df(master, DATA_DIR / "master_daily.csv")
    save_df(experiment_sample, DATA_DIR / "experiment_sample_daily.csv")
    save_df(data_coverage, TABLE_DIR / "data_coverage.csv")
    save_df(experiment1, TABLE_DIR / "experiment1_yield_level_bucket.csv")
    save_df(experiment2, TABLE_DIR / "experiment2_spread_change_bucket.csv")
    save_df(experiment3, TABLE_DIR / "experiment3_alignment_trend_follow.csv")
    save_df(experiment4, TABLE_DIR / "experiment4_divergence_mean_reversion.csv")
    save_df(experiment5, TABLE_DIR / "experiment5_regime_robustness.csv")
    save_df(latest, TABLE_DIR / "latest_snapshot.csv")

    metadata = build_metadata(
        data_coverage=data_coverage,
        master=master,
        experiment_sample=experiment_sample,
        pair_features=pair_features,
    )
    write_json(metadata, OUT_DIR / "experiment_metadata.json")

    build_figures(master, experiment1, experiment2, experiment3, experiment4, experiment5)
    report = build_report(
        data_coverage=data_coverage,
        experiment1=experiment1,
        experiment2=experiment2,
        experiment3=experiment3,
        experiment4=experiment4,
        experiment5=experiment5,
        latest=latest,
        metadata=metadata,
    )
    (REPORT_DIR / "analysis_report.ja.md").write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "output_dir": str(OUT_DIR),
                "master_rows": int(len(master)),
                "experiment_sample_rows": int(len(experiment_sample)),
                "pairs": list(PAIRS),
                "first_date": str(master["date"].min().date()),
                "last_date": str(master["date"].max().date()),
                "report": str(REPORT_DIR / "analysis_report.ja.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def ensure_directories() -> None:
    for directory in (RAW_DIR, TABLE_DIR, FIGURE_DIR, REPORT_DIR, DATA_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def read_ohlcv(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    query = """
        select pair, timestamp, open, high, low, close, volume
        from ohlcv
        where timeframe = '1d'
          and pair in ('EURUSD', 'USDJPY')
          and timestamp >= ?
        order by pair, timestamp
    """
    frame = con.execute(query, [SINCE]).fetchdf()
    frame["date"] = pd.to_datetime(frame["timestamp"]).dt.normalize()
    return frame


def read_fx_nexus_sovereign_yields(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    query = """
        select currency, country_code, tenor, observation_date, yield_percent,
               source, source_series_id, source_url, quality_status, loaded_at
        from sovereign_yields
        where tenor = '2Y'
          and currency in ('USD', 'EUR')
          and observation_date >= ?
        order by currency, observation_date
    """
    frame = con.execute(query, [SINCE]).fetchdf()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.normalize()
    return frame


def fetch_mof_jpy_yields() -> pd.DataFrame:
    response = requests.get(MOF_JGB_HISTORICAL_CSV_URL, timeout=60)
    response.raise_for_status()
    raw_path = RAW_DIR / "mof_jgbcme_all.csv"
    raw_path.write_bytes(response.content)

    raw = pd.read_csv(BytesIO(response.content), header=1)
    frame = pd.DataFrame(
        {
            "currency": "JPY",
            "country_code": None,
            "tenor": "2Y",
            "observation_date": pd.to_datetime(raw["Date"], errors="coerce"),
            "yield_percent": pd.to_numeric(raw["2Y"].replace("-", np.nan), errors="coerce"),
            "source": "mof_jgb_interest_rate_historical",
            "source_series_id": "2Y",
            "source_url": MOF_JGB_HISTORICAL_CSV_URL,
            "quality_status": "ok",
            "loaded_at": pd.Timestamp.utcnow().tz_localize(None),
        }
    )
    frame = frame.dropna(subset=["observation_date", "yield_percent"])
    frame["observation_date"] = frame["observation_date"].dt.normalize()
    frame = frame.loc[frame["observation_date"] >= SINCE].copy()
    return frame.sort_values("observation_date").reset_index(drop=True)


def merge_sovereign_yields(
    fx_yields: pd.DataFrame,
    jpy_yields: pd.DataFrame,
) -> pd.DataFrame:
    frame = pd.concat([fx_yields, jpy_yields], ignore_index=True)
    frame["currency"] = frame["currency"].astype(str).str.upper()
    frame["tenor"] = frame["tenor"].astype(str).str.upper()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.normalize()
    frame["yield_percent"] = pd.to_numeric(frame["yield_percent"], errors="coerce")
    frame = frame.dropna(subset=["currency", "observation_date", "yield_percent"])
    frame = (
        frame.sort_values(["currency", "observation_date", "loaded_at", "source"])
        .drop_duplicates(["currency", "observation_date", "tenor"], keep="last")
        .reset_index(drop=True)
    )
    return frame


def build_pair_yield_spread_features(
    yields: pd.DataFrame,
    ohlcv: pd.DataFrame,
) -> pd.DataFrame:
    prices = ohlcv[["pair", "date", "close"]].copy()
    prices = prices.sort_values(["pair", "date"]).drop_duplicates(["pair", "date"])
    prices["price_return_20d_bp"] = prices.groupby("pair")["close"].pct_change(20) * 10000.0

    pair_frames: list[pd.DataFrame] = []
    for pair in PAIRS:
        base, quote = pair[:3], pair[3:]
        base_yields = yields.loc[yields["currency"] == base].rename(
            columns={
                "currency": "base_currency",
                "yield_percent": "base_yield_percent",
                "quality_status": "base_quality_status",
            }
        )
        quote_yields = yields.loc[yields["currency"] == quote].rename(
            columns={
                "currency": "quote_currency",
                "yield_percent": "quote_yield_percent",
                "quality_status": "quote_quality_status",
            }
        )
        merged = base_yields.merge(
            quote_yields,
            on=["tenor", "observation_date"],
            how="inner",
            suffixes=("_base", "_quote"),
        )
        if merged.empty:
            continue
        result = pd.DataFrame(
            {
                "pair": pair,
                "tenor": "2Y",
                "observation_date": merged["observation_date"],
                "base_currency": base,
                "quote_currency": quote,
                "base_yield_percent": merged["base_yield_percent"],
                "quote_yield_percent": merged["quote_yield_percent"],
                "yield_spread_bp": (
                    merged["base_yield_percent"] - merged["quote_yield_percent"]
                )
                * 100.0,
                "quality_status": [
                    combine_quality(base_status, quote_status)
                    for base_status, quote_status in zip(
                        merged["base_quality_status"],
                        merged["quote_quality_status"],
                        strict=False,
                    )
                ],
            }
        )
        pair_frames.append(result)

    features = pd.concat(pair_frames, ignore_index=True)
    features = features.sort_values(["pair", "observation_date"]).reset_index(drop=True)
    grouped = features.groupby("pair", group_keys=False)
    for window in (1, 5, 20):
        features[f"spread_change_{window}d_bp"] = grouped["yield_spread_bp"].diff(window)
    features["spread_slope_20d_bp_per_day"] = grouped["yield_spread_bp"].transform(
        lambda series: rolling_slope(series, 20)
    )
    rolling = grouped["yield_spread_bp"].rolling(252, min_periods=20)
    mean = rolling.mean().reset_index(level=0, drop=True)
    std = rolling.std(ddof=0).reset_index(level=0, drop=True)
    features["spread_z_252"] = (features["yield_spread_bp"] - mean) / std.replace(0, np.nan)

    price_returns = prices.rename(columns={"date": "observation_date"})[
        ["pair", "observation_date", "price_return_20d_bp"]
    ]
    features = features.merge(price_returns, on=["pair", "observation_date"], how="left")
    features["price_trend_confirmation"] = features.apply(price_trend_confirmation, axis=1)
    features["rate_trend_bias"] = features.apply(rate_trend_bias, axis=1)
    features["feature_built_at"] = pd.Timestamp.utcnow().tz_localize(None)
    return features


def combine_quality(base_status: object, quote_status: object) -> str:
    statuses = {str(base_status).lower(), str(quote_status).lower()}
    if statuses == {"ok"}:
        return "ok"
    for status in ("missing", "stale", "delayed", "market_closed", "proxy"):
        if status in statuses:
            return status
    return sorted(statuses)[0]


def rolling_slope(series: pd.Series, window: int) -> pd.Series:
    def slope(values: np.ndarray) -> float:
        valid = values[~np.isnan(values)]
        if len(valid) < 2:
            return np.nan
        x = np.arange(len(valid), dtype=float)
        return float(np.polyfit(x, valid, 1)[0])

    return series.astype(float).rolling(window, min_periods=2).apply(slope, raw=True)


def price_trend_confirmation(row: pd.Series) -> str:
    spread_change = row.get("spread_change_5d_bp")
    price_return = row.get("price_return_20d_bp")
    if pd.isna(spread_change) or pd.isna(price_return):
        return "unknown"
    if spread_change == 0 or price_return == 0:
        return "neutral"
    return "confirmed" if spread_change * price_return > 0 else "divergent"


def rate_trend_bias(row: pd.Series) -> str:
    if row.get("quality_status") != "ok":
        return "neutral"
    spread_change = row.get("spread_change_5d_bp")
    slope = row.get("spread_slope_20d_bp_per_day")
    confirmation = row.get("price_trend_confirmation")
    if pd.isna(spread_change) or pd.isna(slope):
        return "neutral"
    if spread_change >= 10.0 and slope >= 0.0 and confirmation == "confirmed":
        return "long_base"
    if spread_change <= -10.0 and slope <= 0.0 and confirmation == "confirmed":
        return "short_base"
    return "neutral"


def read_pair_context(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    regime = con.execute(
        """
        select pair, timestamp, regime, volatility_level, correlation_level,
               carry_reversal_risk, recommended_action
        from regime_features
        where timeframe = '1d'
          and pair in ('EURUSD', 'USDJPY')
          and timestamp >= ?
        """,
        [SINCE],
    ).fetchdf()
    regime["date"] = pd.to_datetime(regime["timestamp"]).dt.normalize()
    regime = regime.drop(columns=["timestamp"])

    distortion = con.execute(
        """
        select pair, timestamp, fair_gap_bp, pair_residual_bp,
               pair_residual_z_score, abs_pair_residual_z_score, distortion_type
        from market_distortion_features
        where timeframe = '1d'
          and pair in ('EURUSD', 'USDJPY')
          and timestamp >= ?
        """,
        [SINCE],
    ).fetchdf()
    distortion["date"] = pd.to_datetime(distortion["timestamp"]).dt.normalize()
    distortion = distortion.drop(columns=["timestamp"])

    inefficiency = con.execute(
        """
        select pair, timestamp, total_cost_bp, net_distortion_bp,
               carry_adjusted_net_distortion_bp, cost_pass,
               carry_adjusted_cost_pass, candidate_status, classification,
               event_risk_level, event_impact
        from inefficiency_features
        where timeframe = '1d'
          and pair in ('EURUSD', 'USDJPY')
          and timestamp >= ?
        """,
        [SINCE],
    ).fetchdf()
    inefficiency["date"] = pd.to_datetime(inefficiency["timestamp"]).dt.normalize()
    inefficiency = inefficiency.drop(columns=["timestamp"])

    context = regime.merge(distortion, on=["pair", "date"], how="outer")
    context = context.merge(inefficiency, on=["pair", "date"], how="outer")
    return context.sort_values(["pair", "date"]).reset_index(drop=True)


def build_master(
    features: pd.DataFrame,
    ohlcv: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    price = ohlcv.sort_values(["pair", "date"]).copy()
    feature = features.sort_values(["pair", "observation_date"]).copy()
    price["date"] = pd.to_datetime(price["date"]).astype("datetime64[ns]")
    feature["observation_date"] = pd.to_datetime(feature["observation_date"]).astype(
        "datetime64[ns]"
    )
    feature["available_from"] = feature["observation_date"] + pd.Timedelta(days=1)
    feature["available_from"] = pd.to_datetime(feature["available_from"]).astype(
        "datetime64[ns]"
    )

    merged_frames = []
    for pair in PAIRS:
        left = price.loc[price["pair"] == pair].sort_values("date")
        right = feature.loc[feature["pair"] == pair].sort_values("available_from")
        merged = pd.merge_asof(
            left,
            right,
            left_on="date",
            right_on="available_from",
            by="pair",
            direction="backward",
            allow_exact_matches=True,
        )
        merged_frames.append(merged)
    master = pd.concat(merged_frames, ignore_index=True)
    master = master.merge(context, on=["pair", "date"], how="left")

    master = add_forward_returns(master)
    master["alignment"] = master.apply(classify_alignment, axis=1)
    master["divergence_pattern"] = master.apply(classify_divergence_pattern, axis=1)
    master["level_direction"] = np.sign(master["yield_spread_bp"])
    master["change5_direction"] = np.sign(master["spread_change_5d_bp"])
    master["slope20_direction"] = np.sign(master["spread_slope_20d_bp_per_day"])
    master["price_trend_direction"] = np.sign(master["price_return_20d_bp"])
    master["trend_filter_direction"] = master["alignment"].map(
        {"aligned_long_base": 1.0, "aligned_short_base": -1.0}
    )
    master["mean_reversion_direction"] = master["divergence_pattern"].map(
        {"price_up_spread_down": -1.0, "price_down_spread_up": 1.0}
    )
    master["rate_change_bucket"] = master.apply(classify_rate_change_bucket, axis=1)
    master["total_cost_bp"] = master["total_cost_bp"].fillna(0.0)

    usable = master.loc[
        (master["quality_status"] == "ok")
        & master["yield_spread_bp"].notna()
    ].copy()
    usable = assign_level_buckets(usable)
    return usable.sort_values(["pair", "date"]).reset_index(drop=True)


def add_forward_returns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.sort_values(["pair", "date"]).copy()
    for horizon in HORIZONS:
        result[f"fwd_ret_{horizon}d_bp"] = (
            result.groupby("pair")["close"].shift(-horizon) / result["close"] - 1.0
        ) * 10000.0
        mfe_values = []
        mae_values = []
        for _, group in result.groupby("pair", sort=False):
            closes = group["close"].to_numpy(dtype=float)
            mfe = np.full(len(group), np.nan)
            mae = np.full(len(group), np.nan)
            for i in range(len(group)):
                future = closes[i + 1 : i + horizon + 1]
                if len(future) < horizon or not np.isfinite(closes[i]):
                    continue
                path_returns = (future / closes[i] - 1.0) * 10000.0
                mfe[i] = float(np.nanmax(path_returns))
                mae[i] = float(np.nanmin(path_returns))
            mfe_values.extend(mfe)
            mae_values.extend(mae)
        result[f"mfe_{horizon}d_bp"] = mfe_values
        result[f"mae_{horizon}d_bp"] = mae_values
    return result


def classify_alignment(row: pd.Series) -> str:
    price = row.get("price_return_20d_bp")
    change = row.get("spread_change_5d_bp")
    slope = row.get("spread_slope_20d_bp_per_day")
    if pd.isna(price) or pd.isna(change) or pd.isna(slope):
        return "unknown"
    if price > 0 and change > 0 and slope > 0:
        return "aligned_long_base"
    if price < 0 and change < 0 and slope < 0:
        return "aligned_short_base"
    if price * change < 0:
        return "divergent"
    return "neutral"


def classify_divergence_pattern(row: pd.Series) -> str:
    price = row.get("price_return_20d_bp")
    change = row.get("spread_change_5d_bp")
    if pd.isna(price) or pd.isna(change):
        return "not_divergent"
    if price > 0 and change < 0:
        return "price_up_spread_down"
    if price < 0 and change > 0:
        return "price_down_spread_up"
    return "not_divergent"


def classify_rate_change_bucket(row: pd.Series) -> str:
    change = row.get("spread_change_5d_bp")
    slope = row.get("spread_slope_20d_bp_per_day")
    if pd.isna(change) or pd.isna(slope):
        return "unknown"
    if change >= 10 and slope > 0:
        return "spread_expanding"
    if change <= -10 and slope < 0:
        return "spread_contracting"
    if change >= 10:
        return "change_up_slope_mixed"
    if change <= -10:
        return "change_down_slope_mixed"
    return "neutral"


def assign_level_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    labels = ["Q1_low", "Q2_mid_low", "Q3_mid_high", "Q4_high"]
    result["yield_level_bucket"] = None
    for pair, group in result.groupby("pair"):
        try:
            buckets = pd.qcut(group["yield_spread_bp"], q=4, labels=labels, duplicates="drop")
            result.loc[group.index, "yield_level_bucket"] = buckets.astype(str)
        except ValueError:
            result.loc[group.index, "yield_level_bucket"] = "insufficient"
    return result


def experiment_level_bucket(master: pd.DataFrame) -> pd.DataFrame:
    return summarize_by_group(
        master,
        ["pair", "yield_level_bucket"],
        direction_col="level_direction",
        label="level_carry_direction",
    )


def experiment_change_bucket(master: pd.DataFrame) -> pd.DataFrame:
    return summarize_by_group(
        master,
        ["pair", "rate_change_bucket"],
        direction_col="change5_direction",
        label="spread_change_direction",
    )


def experiment_alignment(master: pd.DataFrame) -> pd.DataFrame:
    return summarize_by_group(
        master,
        ["pair", "alignment"],
        direction_col="price_trend_direction",
        label="price_trend_follow",
    )


def experiment_divergence(master: pd.DataFrame) -> pd.DataFrame:
    divergent = master.loc[master["divergence_pattern"] != "not_divergent"].copy()
    return summarize_by_group(
        divergent,
        ["pair", "divergence_pattern"],
        direction_col="mean_reversion_direction",
        label="divergent_mean_reversion",
    )


def experiment_regime(master: pd.DataFrame) -> pd.DataFrame:
    filtered = master.loc[master["regime"].notna()].copy()
    return summarize_by_group(
        filtered,
        ["pair", "regime", "volatility_level"],
        direction_col="price_trend_direction",
        label="price_trend_follow_by_regime",
    )


def summarize_by_group(
    frame: pd.DataFrame,
    group_cols: list[str],
    *,
    direction_col: str,
    label: str,
) -> pd.DataFrame:
    rows = []
    if frame.empty:
        return pd.DataFrame()
    for keys, group in frame.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(group_cols, keys, strict=True)}
        row["test"] = label
        row["n"] = int(len(group))
        for horizon in HORIZONS:
            raw = group[f"fwd_ret_{horizon}d_bp"]
            direction = group[direction_col]
            directed = raw * direction
            directed = directed.replace([np.inf, -np.inf], np.nan).dropna()
            cost_adjusted = directed - group.loc[directed.index, "total_cost_bp"].fillna(0.0)
            row[f"raw_mean_fwd_{horizon}d_bp"] = safe_mean(raw)
            row[f"strategy_mean_{horizon}d_bp"] = safe_mean(directed)
            row[f"strategy_median_{horizon}d_bp"] = safe_median(directed)
            row[f"strategy_win_rate_{horizon}d"] = safe_win_rate(directed)
            row[f"strategy_sharpe_{horizon}d"] = safe_sharpe(directed, horizon)
            row[f"strategy_max_dd_{horizon}d_bp"] = max_drawdown_bp(directed)
            row[f"cost_adj_mean_{horizon}d_bp"] = safe_mean(cost_adjusted)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def safe_mean(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return float(value.mean()) if len(value) else np.nan


def safe_median(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return float(value.median()) if len(value) else np.nan


def safe_win_rate(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return float((value > 0).mean()) if len(value) else np.nan


def safe_sharpe(series: pd.Series, horizon: int) -> float:
    value = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    std = value.std(ddof=1)
    if len(value) < 3 or std == 0 or pd.isna(std):
        return np.nan
    return float((value.mean() / std) * math.sqrt(252.0 / horizon))


def max_drawdown_bp(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if value.empty:
        return np.nan
    equity = value.cumsum()
    drawdown = equity.cummax() - equity
    return float(drawdown.max())


def latest_snapshot(master: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "pair",
        "date",
        "close",
        "observation_date",
        "base_yield_percent",
        "quote_yield_percent",
        "yield_spread_bp",
        "spread_change_5d_bp",
        "spread_slope_20d_bp_per_day",
        "spread_z_252",
        "price_return_20d_bp",
        "alignment",
        "rate_trend_bias",
        "regime",
        "volatility_level",
        "pair_residual_z_score",
        "total_cost_bp",
        "candidate_status",
    ]
    return (
        master.sort_values(["pair", "date"])
        .groupby("pair", as_index=False)
        .tail(1)[columns]
        .reset_index(drop=True)
    )


def build_data_coverage(
    yields: pd.DataFrame,
    features: pd.DataFrame,
    ohlcv: pd.DataFrame,
    master: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for currency, group in yields.groupby("currency"):
        rows.append(
            {
                "type": "sovereign_yield",
                "name": currency,
                "rows": int(len(group)),
                "first": str(group["observation_date"].min().date()),
                "last": str(group["observation_date"].max().date()),
                "quality": ",".join(sorted(group["quality_status"].dropna().unique())),
            }
        )
    for pair, group in features.groupby("pair"):
        rows.append(
            {
                "type": "pair_yield_spread",
                "name": pair,
                "rows": int(len(group)),
                "first": str(group["observation_date"].min().date()),
                "last": str(group["observation_date"].max().date()),
                "quality": ",".join(sorted(group["quality_status"].dropna().unique())),
            }
        )
    for pair, group in ohlcv.groupby("pair"):
        rows.append(
            {
                "type": "price_1d",
                "name": pair,
                "rows": int(len(group)),
                "first": str(group["date"].min().date()),
                "last": str(group["date"].max().date()),
                "quality": "fx_nexus_ohlcv",
            }
        )
    for pair, group in master.groupby("pair"):
        rows.append(
            {
                "type": "experiment_master",
                "name": pair,
                "rows": int(len(group)),
                "first": str(group["date"].min().date()),
                "last": str(group["date"].max().date()),
                "quality": "leak_shifted_t_plus_1",
            }
        )
    return pd.DataFrame(rows)


def build_metadata(
    *,
    data_coverage: pd.DataFrame,
    master: pd.DataFrame,
    experiment_sample: pd.DataFrame,
    pair_features: pd.DataFrame,
) -> dict[str, object]:
    return {
        "experiment_title": "FX 2Y yield-spread filter experiment",
        "pairs": list(PAIRS),
        "since": str(SINCE.date()),
        "fx_nexus_root": str(FX_NEXUS_ROOT),
        "fx_nexus_db": str(FX_NEXUS_DB),
        "mof_jgb_historical_csv_url": MOF_JGB_HISTORICAL_CSV_URL,
        "mof_jgb_page_url": MOF_JGB_PAGE_URL,
        "leakage_rule": "T-day yield features are available from T+1; daily forward returns start from the merged price date.",
        "horizons_days": list(HORIZONS),
        "master_rows": int(len(master)),
        "experiment_sample_rows": int(len(experiment_sample)),
        "pair_feature_rows": int(len(pair_features)),
        "data_coverage": data_coverage.to_dict(orient="records"),
    }


def build_figures(
    master: pd.DataFrame,
    experiment1: pd.DataFrame,
    experiment2: pd.DataFrame,
    experiment3: pd.DataFrame,
    experiment4: pd.DataFrame,
    experiment5: pd.DataFrame,
) -> None:
    build_time_series_svg(master)
    bar_chart_svg(
        experiment1,
        FIGURE_DIR / "figure02_yield_level_bucket_10d.svg",
        category_col="yield_level_bucket",
        value_col="cost_adj_mean_10d_bp",
        title="2Y yield-spread level bucket: 10d cost-adjusted strategy return",
    )
    bar_chart_svg(
        experiment2,
        FIGURE_DIR / "figure03_spread_change_bucket_10d.svg",
        category_col="rate_change_bucket",
        value_col="cost_adj_mean_10d_bp",
        title="2Y spread change bucket: 10d cost-adjusted strategy return",
    )
    bar_chart_svg(
        experiment3,
        FIGURE_DIR / "figure04_alignment_trend_follow_10d.svg",
        category_col="alignment",
        value_col="cost_adj_mean_10d_bp",
        title="Price/rate alignment: 10d trend-follow return",
    )
    bar_chart_svg(
        experiment4,
        FIGURE_DIR / "figure05_divergence_mean_reversion_10d.svg",
        category_col="divergence_pattern",
        value_col="cost_adj_mean_10d_bp",
        title="Divergence: 10d mean-reversion return",
    )
    top_regime = (
        experiment5.sort_values(["pair", "n"], ascending=[True, False])
        .groupby("pair")
        .head(6)
        .copy()
    )
    top_regime["regime_bucket"] = (
        top_regime["regime"].astype(str) + " / " + top_regime["volatility_level"].astype(str)
    )
    bar_chart_svg(
        top_regime,
        FIGURE_DIR / "figure06_regime_trend_follow_10d.svg",
        category_col="regime_bucket",
        value_col="cost_adj_mean_10d_bp",
        title="Regime robustness: 10d trend-follow return",
    )


def build_time_series_svg(master: pd.DataFrame) -> None:
    lines = []
    for pair in PAIRS:
        group = master.loc[master["pair"] == pair].tail(700).copy()
        if group.empty:
            continue
        close_z = zscore(group["close"])
        spread_z = zscore(group["yield_spread_bp"])
        lines.append(
            ChartSeries(
                label=f"{pair} close z",
                x=group["date"].tolist(),
                y=close_z.tolist(),
                color="#2563eb" if pair == "EURUSD" else "#0f766e",
            )
        )
        lines.append(
            ChartSeries(
                label=f"{pair} 2Y spread z",
                x=group["date"].tolist(),
                y=spread_z.tolist(),
                color="#dc2626" if pair == "EURUSD" else "#9333ea",
            )
        )
    line_chart_svg(
        lines,
        FIGURE_DIR / "figure01_price_vs_2y_spread.svg",
        title="Price and 2Y yield spread, normalized z-score",
    )


def zscore(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    std = series.std(ddof=0)
    if pd.isna(std) or std == 0:
        return series * np.nan
    return (series - series.mean()) / std


def line_chart_svg(series_list: list[ChartSeries], path: Path, *, title: str) -> None:
    width, height = 980, 520
    margin_left, margin_right, margin_top, margin_bottom = 70, 30, 60, 95
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    all_x = [x for series in series_list for x in series.x]
    all_y = [y for series in series_list for y in series.y if pd.notna(y)]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    y_pad = (y_max - y_min) * 0.08
    y_min -= y_pad
    y_max += y_pad

    def sx(value: pd.Timestamp) -> float:
        span = max((x_max - x_min).days, 1)
        return margin_left + ((value - x_min).days / span) * plot_w

    def sy(value: float) -> float:
        return margin_top + (1 - (value - y_min) / (y_max - y_min)) * plot_h

    elements = [
        svg_header(width, height),
        f'<text x="{width/2}" y="30" text-anchor="middle" class="title">{escape(title)}</text>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" class="axis"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" class="axis"/>',
    ]
    for tick in np.linspace(y_min, y_max, 7):
        y = sy(float(tick))
        elements.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_w}" y2="{y:.1f}" class="grid"/>')
        elements.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" class="tick">{tick:.1f}</text>')
    for tick in pd.date_range(x_min, x_max, periods=6):
        x = sx(tick)
        elements.append(f'<text x="{x:.1f}" y="{margin_top + plot_h + 28}" text-anchor="middle" class="tick">{tick.date()}</text>')
    legend_y = height - 45
    for idx, series in enumerate(series_list):
        points = [
            f"{sx(x):.1f},{sy(float(y)):.1f}"
            for x, y in zip(series.x, series.y, strict=False)
            if pd.notna(y)
        ]
        if points:
            elements.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{series.color}" stroke-width="2.2"/>'
            )
        legend_x = margin_left + (idx % 2) * 360
        legend_line_y = legend_y + (idx // 2) * 22
        elements.append(f'<line x1="{legend_x}" y1="{legend_line_y}" x2="{legend_x + 28}" y2="{legend_line_y}" stroke="{series.color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x + 36}" y="{legend_line_y + 5}" class="legend">{escape(series.label)}</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def bar_chart_svg(
    frame: pd.DataFrame,
    path: Path,
    *,
    category_col: str,
    value_col: str,
    title: str,
) -> None:
    width, height = 1040, 540
    margin_left, margin_right, margin_top, margin_bottom = 80, 30, 60, 145
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    data = frame.copy()
    if data.empty or value_col not in data.columns:
        path.write_text(svg_header(width, height) + f"<text x='30' y='50'>No data: {escape(title)}</text></svg>", encoding="utf-8")
        return
    data["label"] = data["pair"].astype(str) + " / " + data[category_col].astype(str)
    data = data.sort_values(["pair", category_col]).reset_index(drop=True)
    values = pd.to_numeric(data[value_col], errors="coerce").fillna(0.0)
    y_abs = max(abs(values.min()), abs(values.max()), 1.0)

    def sy(value: float) -> float:
        return margin_top + (1 - (value + y_abs) / (2 * y_abs)) * plot_h

    zero_y = sy(0.0)
    bar_gap = 8
    bar_w = max((plot_w - bar_gap * (len(data) - 1)) / max(len(data), 1), 10)
    elements = [
        svg_header(width, height),
        f'<text x="{width/2}" y="30" text-anchor="middle" class="title">{escape(title)}</text>',
        f'<line x1="{margin_left}" y1="{zero_y:.1f}" x2="{margin_left + plot_w}" y2="{zero_y:.1f}" class="axis"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" class="axis"/>',
    ]
    for tick in np.linspace(-y_abs, y_abs, 7):
        y = sy(float(tick))
        elements.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_w}" y2="{y:.1f}" class="grid"/>')
        elements.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" class="tick">{tick:.0f}</text>')
    for idx, row in data.iterrows():
        value = float(values.iloc[idx])
        x = margin_left + idx * (bar_w + bar_gap)
        y = sy(max(value, 0.0))
        h = abs(sy(value) - zero_y)
        color = "#2563eb" if row["pair"] == "EURUSD" else "#0f766e"
        if value < 0:
            y = zero_y
            color = "#dc2626" if row["pair"] == "EURUSD" else "#9333ea"
        elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" opacity="0.82"/>')
        elements.append(f'<text x="{x + bar_w/2:.1f}" y="{sy(value) - 6 if value >= 0 else sy(value) + 16:.1f}" text-anchor="middle" class="barlabel">{value:.1f}</text>')
        elements.append(
            f'<text transform="translate({x + bar_w/2:.1f},{margin_top + plot_h + 18}) rotate(48)" text-anchor="start" class="tick">{escape(str(row["label"]))}</text>'
        )
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def svg_header(width: int, height: int) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #111827; }}
  .title {{ font-size: 20px; font-weight: 700; }}
  .tick {{ font-size: 11px; fill: #4b5563; }}
  .legend {{ font-size: 13px; fill: #111827; }}
  .barlabel {{ font-size: 10px; fill: #111827; }}
  .axis {{ stroke: #374151; stroke-width: 1.2; }}
  .grid {{ stroke: #e5e7eb; stroke-width: 1; }}
</style>"""


def escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_report(
    *,
    data_coverage: pd.DataFrame,
    experiment1: pd.DataFrame,
    experiment2: pd.DataFrame,
    experiment3: pd.DataFrame,
    experiment4: pd.DataFrame,
    experiment5: pd.DataFrame,
    latest: pd.DataFrame,
    metadata: dict[str, object],
) -> str:
    eur_alignment = top_metric(experiment3, "EURUSD", "alignment", "cost_adj_mean_10d_bp")
    usdjpy_alignment = top_metric(experiment3, "USDJPY", "alignment", "cost_adj_mean_10d_bp")
    eur_change = top_metric(experiment2, "EURUSD", "rate_change_bucket", "cost_adj_mean_10d_bp")
    usdjpy_change = top_metric(experiment2, "USDJPY", "rate_change_bucket", "cost_adj_mean_10d_bp")

    sections = [
        "# FX 2年金利差フィルター実験レポート",
        "",
        "## 結論",
        "",
        "EURUSD と USDJPY の2ペアに絞れば、記事骨子に沿った検証は実施できる。"
        "ただし USDJPY は FX Nexus 標準DBのJPY履歴が当月分に限られるため、"
        "本実験では財務省公式の historical JGB CSV を lab_11 に保存して補助した。",
        "",
        "実験の読み方は売買シグナルの採用ではなく、2年金利差が価格トレンドを支える局面、"
        "支えない局面、または追随を疑うべき局面を分けられるかを見る診断である。",
        "",
        "## データ範囲",
        "",
        table_to_markdown(data_coverage),
        "",
        "## リーク防止",
        "",
        "- T日の金利データはT+1以降にだけ使った。",
        "- forward return は結合後の日次終値から5日、10日、20日先で計算した。",
        "- `quality_status != ok` はマスターから除外した。",
        "- USDJPY のJPY 2Y履歴は FX Nexus 設定済みMOF系ソースの historical CSV を補助入力として使い、raw CSVを保存した。",
        "- 集計表の最大DDは、日次に重なるイベントリターンを累積した診断値であり、独立した実運用ポートフォリオDDではない。",
        "",
        "## 図表",
        "",
        "![価格と2Y金利差](../figures/figure01_price_vs_2y_spread.svg)",
        "",
        "![金利差水準](../figures/figure02_yield_level_bucket_10d.svg)",
        "",
        "![金利差変化](../figures/figure03_spread_change_bucket_10d.svg)",
        "",
        "![Alignment](../figures/figure04_alignment_trend_follow_10d.svg)",
        "",
        "![Divergence](../figures/figure05_divergence_mean_reversion_10d.svg)",
        "",
        "![Regime](../figures/figure06_regime_trend_follow_10d.svg)",
        "",
        "## 実験1: 金利差水準は効くか",
        "",
        "水準テストは、金利差がプラスならbase通貨ロング、マイナスならbase通貨ショートという単純なキャリー方向で評価した。",
        "これは記事内の「高金利通貨を買えばよいのか」を疑うための素朴なベースラインである。",
        "",
        table_to_markdown(select_columns(experiment1, "yield_level_bucket")),
        "",
        "解釈: 水準だけの分類は、ペア内の状態差を見るには使えるが、単独で安定した売買根拠として扱うには弱い。"
        "特に水準が高い・低いことは、すでに価格へ織り込まれている可能性がある。",
        "",
        "## 実験2: 金利差の変化は効くか",
        "",
        f"EURUSDで10日コスト控除後が最も良かった変化分類は `{eur_change[0]}` ({eur_change[1]:.2f}bp)。"
        f"USDJPYでは `{usdjpy_change[0]}` ({usdjpy_change[1]:.2f}bp) だった。",
        "",
        table_to_markdown(select_columns(experiment2, "rate_change_bucket")),
        "",
        "解釈: 金利差の5日変化と20日傾きは、水準よりも「今どちらへ評価が変わっているか」を示す。"
        "記事では、絶対水準よりも変化方向を重視する説明に使える。",
        "",
        "## 実験3: 価格と金利差の一致はトレンドフォロー向きか",
        "",
        f"EURUSDで10日トレンド追随が最も良かった分類は `{eur_alignment[0]}` ({eur_alignment[1]:.2f}bp)。"
        f"USDJPYでは `{usdjpy_alignment[0]}` ({usdjpy_alignment[1]:.2f}bp) だった。",
        "",
        table_to_markdown(select_columns(experiment3, "alignment")),
        "",
        "解釈: `aligned_long_base` / `aligned_short_base` は、価格トレンドと金利差トレンドが同じ方向を向く局面である。"
        "ここでトレンド追随の損益が改善するなら、2年金利差はエントリーシグナルではなく環境フィルターとして有用と言える。",
        "",
        "## 実験4: 乖離は平均回帰向きか",
        "",
        table_to_markdown(select_columns(experiment4, "divergence_pattern")),
        "",
        "解釈: divergent は即逆張りの合図ではない。"
        "むしろ、価格トレンドに追随する前に金利差で説明できる動きかを疑う警告信号として扱うのが実務的である。",
        "",
        "## 実験5: レジーム別の効き方",
        "",
        table_to_markdown(select_columns(experiment5, "regime", extra_cols=["volatility_level"])),
        "",
        "解釈: トレンド、レンジ、高ボラ、キャリー巻き戻しでは、同じ金利差フィルターでも意味が変わる。"
        "高ボラや巻き戻し局面では、金利差よりもリスク管理と見送り判断を優先するべきである。",
        "",
        "## 最新スナップショット",
        "",
        table_to_markdown(latest_round(latest)),
        "",
        "## 記事への落とし込み",
        "",
        "記事の中心メッセージは、次の形にできる。",
        "",
        "> 2年金利差は売買シグナルではない。"
        "しかし、価格トレンドが金利市場に支えられているのか、"
        "金利差では説明しづらい需給・リスクオン・ポジション調整で動いているのかを分けるフィルターとして使える。",
        "",
        "## 生成物",
        "",
        "- `data/master_daily.csv`: 実験用マスターデータ",
        "- `data/experiment_sample_daily.csv`: 20日先リターンまで計算できる検証サンプル",
        "- `tables/*.csv`: 各実験の集計表",
        "- `figures/*.svg`: 記事用図表",
        "- `data/raw/*.csv`: FX Nexus由来データとMOF historical JGB CSV",
        "- `experiment_metadata.json`: データソースとリーク防止設定",
        "",
        "## メタデータ",
        "",
        "```json",
        json.dumps(metadata, ensure_ascii=False, indent=2)[:4000],
        "```",
        "",
    ]
    return "\n".join(sections)


def select_columns(
    frame: pd.DataFrame,
    category_col: str,
    *,
    extra_cols: list[str] | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    columns = ["pair", category_col]
    if extra_cols:
        columns.extend(extra_cols)
    columns.extend(
        [
            "n",
            "cost_adj_mean_5d_bp",
            "cost_adj_mean_10d_bp",
            "cost_adj_mean_20d_bp",
            "strategy_win_rate_10d",
            "strategy_sharpe_10d",
            "strategy_max_dd_10d_bp",
        ]
    )
    existing = [col for col in columns if col in frame.columns]
    return latest_round(frame[existing])


def latest_round(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for col in result.columns:
        if pd.api.types.is_float_dtype(result[col]):
            result[col] = result[col].round(3)
    return result


def top_metric(
    frame: pd.DataFrame,
    pair: str,
    category_col: str,
    metric_col: str,
) -> tuple[str, float]:
    subset = frame.loc[(frame["pair"] == pair) & frame[metric_col].notna()].copy()
    if subset.empty:
        return ("no_data", float("nan"))
    row = subset.sort_values(metric_col, ascending=False).iloc[0]
    return (str(row[category_col]), float(row[metric_col]))


def table_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    values = frame.fillna("")
    headers = list(values.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in values.iterrows():
        cells = []
        for value in row.tolist():
            if isinstance(value, float):
                cells.append(f"{value:.3f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def raw_save(frame: pd.DataFrame, filename: str) -> None:
    save_df(frame, RAW_DIR / filename)


def save_df(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False)


def write_json(data: dict[str, object], path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
