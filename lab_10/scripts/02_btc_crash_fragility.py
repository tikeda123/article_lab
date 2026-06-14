from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
TABLE_DIR = ROOT / "outputs" / "tables"
FIGURE_DIR = ROOT / "outputs" / "figures"
REPORT_DIR = ROOT / "outputs" / "report"

BASE_SCRIPT = SCRIPT_DIR / "00_lab7_interaction_model_base.py"
HORIZONS = {"24h": 6, "48h": 12, "5d": 30}
PRIMARY_EVENT = "rolling_2sigma"
PRIMARY_RISK_ENV = "nasdaq_5d_up"
PRIMARY_FUNDING = "lower_20_or_negative"
PRIMARY_GROUPS = [
    "all_funding_covered_crashes",
    "funding_low_only",
    "risk_on_only",
    "funding_low_x_risk_on",
    "funding_high_x_risk_off",
]
COST_CASES = {
    "gross": 0.0,
    "base_cost": 10.0,
    "cost_x2": 20.0,
    "cost_x5": 50.0,
}
ENTRY_CASES = {
    "next_open": {"entry_lag_bars": 1, "adverse_entry_bps": 0.0},
    "delay_4h": {"entry_lag_bars": 2, "adverse_entry_bps": 0.0},
    "delay_8h": {"entry_lag_bars": 3, "adverse_entry_bps": 0.0},
    "adverse_10bps": {"entry_lag_bars": 1, "adverse_entry_bps": 10.0},
    "adverse_25bps": {"entry_lag_bars": 1, "adverse_entry_bps": 25.0},
}
EVENT_DEFS = [
    "rolling_1_5sigma",
    "rolling_2sigma",
    "rolling_2_5sigma",
    "full_sample_q05",
    "full_sample_q025",
]
RISK_ENVS = [
    "nasdaq_5d_up",
    "sp500_5d_up",
    "broad_3of4_5d_up",
    "nasdaq_5d_gt_1pct",
    "sp500_5d_gt_1pct",
]
FUNDING_CASES = [
    "negative",
    "lower_20_or_negative",
    "lower_20_only",
    "lower_10_or_negative",
    "high_20",
    "high_10",
]
PERIODS = {
    "all": (None, None),
    "2020_2021": ("2020-01-01", "2022-01-01"),
    "2022_stress": ("2022-01-01", "2023-01-01"),
    "2023_2024": ("2023-01-01", "2025-01-01"),
    "2025_2026": ("2025-01-01", None),
    "post_btc_etf": ("2024-01-11", None),
}
WALK_FORWARD = {
    "wf_1": {"train": ("2020-01-01", "2022-01-01"), "test": ("2022-01-01", "2023-01-01")},
    "wf_2": {"train": ("2020-01-01", "2023-01-01"), "test": ("2023-01-01", "2024-01-01")},
    "wf_3": {"train": ("2020-01-01", "2024-01-01"), "test": ("2024-01-01", "2025-01-01")},
    "wf_4": {"train": ("2020-01-01", "2025-01-01"), "test": ("2025-01-01", None)},
}
STOP_LEVELS = {"stop_3pct": -0.03, "stop_5pct": -0.05, "stop_10pct": -0.10}
LEVERAGES = [1.0, 2.0, 3.0]
MARGIN_THRESHOLDS = [30.0, 50.0, 80.0]
BOOTSTRAP_ITERATIONS = 10_000
BOOTSTRAP_SEED = 42


def load_base_module():
    spec = importlib.util.spec_from_file_location("lab10_lab7_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base_module()


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def add_extra_features(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    out = panel.copy()
    q025 = float(out["btc_ret_4h"].quantile(0.025))
    out["crash_rolling_2_5sigma"] = out["btc_sigma_score_180"] <= -2.5
    out["crash_full_sample_q025"] = out["btc_ret_4h"] <= q025
    out["risk_on_nasdaq_gt_1pct"] = out["nasdaq_ret_5d"] > math.log(1.01)
    out["risk_on_sp500_gt_1pct"] = out["sp500_ret_5d"] > math.log(1.01)
    out["funding_low10"] = out["funding_percentile_expanding"] <= 0.10
    out["funding_high10"] = out["funding_percentile_expanding"] >= 0.90
    return out, {"btc_q025_pct": q025 * 100}


def risk_series(panel: pd.DataFrame, risk_env: str) -> pd.Series:
    mapping = {
        "nasdaq_5d_up": "risk_on_nasdaq",
        "sp500_5d_up": "risk_on_sp500",
        "broad_3of4_5d_up": "risk_on_broad_3of4",
        "nasdaq_5d_gt_1pct": "risk_on_nasdaq_gt_1pct",
        "sp500_5d_gt_1pct": "risk_on_sp500_gt_1pct",
    }
    return panel[mapping[risk_env]].fillna(False).astype(bool)


def funding_pair(panel: pd.DataFrame, funding_case: str) -> tuple[pd.Series, pd.Series]:
    if funding_case == "negative":
        low = panel["funding_negative"]
        high = panel["funding_high"]
    elif funding_case == "lower_20_or_negative":
        low = panel["funding_low"]
        high = panel["funding_high"]
    elif funding_case == "lower_20_only":
        low = panel["funding_low20"]
        high = panel["funding_high"]
    elif funding_case == "lower_10_or_negative":
        low = panel["funding_low10"] | panel["funding_negative"]
        high = panel["funding_high"]
    elif funding_case == "high_20":
        low = panel["funding_low"]
        high = panel["funding_high"]
    elif funding_case == "high_10":
        low = panel["funding_low"]
        high = panel["funding_high10"]
    else:
        raise ValueError(f"Unknown funding case: {funding_case}")
    return low.fillna(False).astype(bool), high.fillna(False).astype(bool)


def event_mask(panel: pd.DataFrame, event_def: str) -> pd.Series:
    mapping = {
        "rolling_1_5sigma": "crash_rolling_1_5sigma",
        "rolling_2sigma": "crash_rolling_2sigma",
        "rolling_2_5sigma": "crash_rolling_2_5sigma",
        "full_sample_q05": "crash_full_sample_q05",
        "full_sample_q025": "crash_full_sample_q025",
    }
    return panel[mapping[event_def]].fillna(False).astype(bool)


def apply_cooldown(panel: pd.DataFrame, event_def: str) -> pd.DataFrame:
    return BASE.apply_cooldown(panel[event_mask(panel, event_def)].copy())


def select_period(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    selected = df
    if start is not None:
        selected = selected[selected.index >= start]
    if end is not None:
        selected = selected[selected.index < end]
    return selected


def compute_path_metrics(
    panel: pd.DataFrame,
    horizon_bars: int,
    entry_lag_bars: int = 1,
    adverse_entry_bps: float = 0.0,
) -> pd.DataFrame:
    open_prices = panel["btc_open"].to_numpy(dtype=float)
    highs = panel["btc_high"].to_numpy(dtype=float)
    lows = panel["btc_low"].to_numpy(dtype=float)
    future_ret = np.full(len(panel), np.nan)
    mae = np.full(len(panel), np.nan)
    mfe = np.full(len(panel), np.nan)
    entry_shift = 1.0 + adverse_entry_bps / 10000.0

    for i in range(len(panel)):
        entry_i = i + entry_lag_bars
        exit_i = entry_i + horizon_bars
        if entry_i >= len(panel) or exit_i >= len(panel):
            continue
        entry = open_prices[entry_i] * entry_shift
        exit_price = open_prices[exit_i]
        if not math.isfinite(entry) or entry <= 0 or not math.isfinite(exit_price):
            continue
        path_high = np.nanmax(highs[entry_i : exit_i + 1])
        path_low = np.nanmin(lows[entry_i : exit_i + 1])
        future_ret[i] = math.log(exit_price / entry)
        mae[i] = math.log(path_low / entry) if path_low > 0 else np.nan
        mfe[i] = math.log(path_high / entry) if path_high > 0 else np.nan

    return pd.DataFrame(
        {
            "gross_return": future_ret,
            "mae": mae,
            "mfe": mfe,
        },
        index=panel.index,
    )


def max_drawdown_pct(log_returns: pd.Series) -> float:
    ret = log_returns.dropna().astype(float)
    if ret.empty:
        return np.nan
    equity = np.exp(ret.cumsum())
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min() * 100)


def profit_factor(ret: pd.Series) -> float:
    values = ret.dropna().astype(float)
    if values.empty:
        return np.nan
    gains = values[values > 0].sum()
    losses = values[values < 0].sum()
    if losses < 0:
        return float(gains / abs(losses))
    return np.inf if gains > 0 else np.nan


def var_es(ret: pd.Series, q: float) -> tuple[float, float]:
    values = ret.dropna().astype(float)
    if values.empty:
        return np.nan, np.nan
    var = float(values.quantile(q))
    tail = values[values <= var]
    es = float(tail.mean()) if len(tail) else np.nan
    return var * 100, es * 100


def metrics_from_returns(ret: pd.Series, mae: pd.Series | None = None, mfe: pd.Series | None = None) -> dict[str, float]:
    values = ret.dropna().astype(float)
    n = len(values)
    var_95, es_95 = var_es(values, 0.05)
    var_99, es_99 = var_es(values, 0.01)
    if n >= 2 and values.std(ddof=1) > 0:
        t_stat = float(stats.ttest_1samp(values, 0.0, nan_policy="omit").statistic)
    else:
        t_stat = np.nan
    aligned_mae = mae.loc[values.index].dropna().astype(float) if mae is not None else pd.Series(dtype=float)
    aligned_mfe = mfe.loc[values.index].dropna().astype(float) if mfe is not None else pd.Series(dtype=float)
    return {
        "n": int(n),
        "mean_ret_pct": values.mean() * 100 if n else np.nan,
        "median_ret_pct": values.median() * 100 if n else np.nan,
        "win_rate_pct": (values > 0).mean() * 100 if n else np.nan,
        "profit_factor": profit_factor(values),
        "t_stat": t_stat,
        "var_95_pct": var_95,
        "es_95_pct": es_95,
        "var_99_pct": var_99,
        "es_99_pct": es_99,
        "mean_mae_pct": aligned_mae.mean() * 100 if len(aligned_mae) else np.nan,
        "worst_mae_pct": aligned_mae.min() * 100 if len(aligned_mae) else np.nan,
        "mean_mfe_pct": aligned_mfe.mean() * 100 if len(aligned_mfe) else np.nan,
        "best_mfe_pct": aligned_mfe.max() * 100 if len(aligned_mfe) else np.nan,
        "maxdd_pct": max_drawdown_pct(values),
    }


def group_masks(events: pd.DataFrame, risk_on: pd.Series, funding_low: pd.Series, funding_high: pd.Series) -> dict[str, pd.Series]:
    risk = risk_on.reindex(events.index).fillna(False).astype(bool)
    low = funding_low.reindex(events.index).fillna(False).astype(bool)
    high = funding_high.reindex(events.index).fillna(False).astype(bool)
    return {
        "all_funding_covered_crashes": pd.Series(True, index=events.index),
        "funding_low_only": low,
        "risk_on_only": risk,
        "funding_low_x_risk_on": low & risk,
        "funding_low_x_risk_off": low & (~risk),
        "funding_not_low_x_risk_on": (~low) & risk,
        "funding_not_low_x_risk_off": (~low) & (~risk),
        "funding_high_x_risk_off": high & (~risk),
        "funding_high_x_risk_on": high & risk,
    }


def add_fragility_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["is_small_sample"] = out["n"] < 30
    out["is_very_small_sample"] = out["n"] < 20
    out["is_mean_broken"] = out["mean_ret_pct"] <= 0
    out["is_pf_broken"] = out["profit_factor"] <= 1
    out["is_drawdown_severe"] = out["maxdd_pct"] <= -20

    def status(row: pd.Series) -> str:
        if bool(row["is_mean_broken"]) or bool(row["is_pf_broken"]):
            return "broken"
        if bool(row["is_very_small_sample"]):
            return "fragile"
        if bool(row["is_small_sample"]) or bool(row["is_drawdown_severe"]):
            return "watch"
        return "survives_this_test"

    out["fragility_status"] = out.apply(status, axis=1)
    return out


def evaluate_groups(
    panel: pd.DataFrame,
    path: pd.DataFrame,
    event_def: str,
    horizon: str,
    risk_env: str,
    funding_case: str,
    cost_bps: float = 0.0,
    groups: list[str] | None = None,
    period: tuple[str | None, str | None] = (None, None),
) -> pd.DataFrame:
    events = apply_cooldown(panel, event_def)
    events = select_period(events, period[0], period[1])
    events = events[events["has_funding_regime"]].copy()
    risk = risk_series(panel, risk_env)
    funding_low, funding_high = funding_pair(panel, funding_case)
    masks = group_masks(events, risk, funding_low, funding_high)
    ret = path["gross_return"] - cost_bps / 10000.0
    mae = path["mae"]
    mfe = path["mfe"]
    selected_groups = groups or list(masks)
    rows: list[dict[str, object]] = []
    for group in selected_groups:
        group_index = events.index[masks[group].fillna(False)]
        row = {
            "event_def": event_def,
            "horizon": horizon,
            "risk_env": risk_env,
            "funding_case": funding_case,
            "group": group,
            "cost_bps": cost_bps,
        }
        row.update(metrics_from_returns(ret.loc[group_index], mae.loc[group_index], mfe.loc[group_index]))
        rows.append(row)
    return add_fragility_flags(pd.DataFrame(rows))


def bootstrap_metrics(ret: pd.Series, iterations: int = BOOTSTRAP_ITERATIONS, seed: int = BOOTSTRAP_SEED) -> dict[str, float]:
    values = ret.dropna().astype(float).to_numpy()
    n = len(values)
    if n == 0:
        return {
            "bootstrap_iterations": iterations,
            "mean_p05_pct": np.nan,
            "mean_p50_pct": np.nan,
            "mean_p95_pct": np.nan,
            "pf_p05": np.nan,
            "pf_p50": np.nan,
            "pf_p95": np.nan,
            "win_rate_p05_pct": np.nan,
            "win_rate_p50_pct": np.nan,
            "win_rate_p95_pct": np.nan,
        }
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(iterations, n), replace=True)
    means = samples.mean(axis=1) * 100
    wins = (samples > 0).mean(axis=1) * 100
    gains = np.where(samples > 0, samples, 0).sum(axis=1)
    losses = np.where(samples < 0, samples, 0).sum(axis=1)
    pf = np.divide(gains, np.abs(losses), out=np.full(iterations, np.nan), where=losses < 0)
    pf = np.where(np.isfinite(pf), pf, np.nan)
    return {
        "bootstrap_iterations": iterations,
        "mean_p05_pct": float(np.nanquantile(means, 0.05)),
        "mean_p50_pct": float(np.nanquantile(means, 0.50)),
        "mean_p95_pct": float(np.nanquantile(means, 0.95)),
        "pf_p05": float(np.nanquantile(pf, 0.05)),
        "pf_p50": float(np.nanquantile(pf, 0.50)),
        "pf_p95": float(np.nanquantile(pf, 0.95)),
        "win_rate_p05_pct": float(np.nanquantile(wins, 0.05)),
        "win_rate_p50_pct": float(np.nanquantile(wins, 0.50)),
        "win_rate_p95_pct": float(np.nanquantile(wins, 0.95)),
    }


def build_paths(panel: pd.DataFrame) -> dict[tuple[str, str], pd.DataFrame]:
    paths: dict[tuple[str, str], pd.DataFrame] = {}
    for horizon, bars in HORIZONS.items():
        for case, params in ENTRY_CASES.items():
            paths[(horizon, case)] = compute_path_metrics(panel, bars, **params)
    return paths


def build_baseline(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for horizon in HORIZONS:
        rows.append(
            evaluate_groups(
                panel,
                paths[(horizon, "next_open")],
                PRIMARY_EVENT,
                horizon,
                PRIMARY_RISK_ENV,
                PRIMARY_FUNDING,
                groups=PRIMARY_GROUPS,
            )
        )
    return pd.concat(rows, ignore_index=True)


def build_cost_stress(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for horizon in HORIZONS:
        for cost_case, cost_bps in COST_CASES.items():
            result = evaluate_groups(
                panel,
                paths[(horizon, "next_open")],
                PRIMARY_EVENT,
                horizon,
                PRIMARY_RISK_ENV,
                PRIMARY_FUNDING,
                cost_bps=cost_bps,
                groups=groups,
            )
            result.insert(0, "cost_case", cost_case)
            rows.append(result)
    return pd.concat(rows, ignore_index=True)


def build_entry_stress(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for horizon in ["24h", "48h", "5d"]:
        for case, params in ENTRY_CASES.items():
            result = evaluate_groups(
                panel,
                paths[(horizon, case)],
                PRIMARY_EVENT,
                horizon,
                PRIMARY_RISK_ENV,
                PRIMARY_FUNDING,
                groups=groups,
            )
            result.insert(0, "entry_case", case)
            result.insert(1, "entry_lag_bars", params["entry_lag_bars"])
            result.insert(2, "adverse_entry_bps", params["adverse_entry_bps"])
            rows.append(result)
    return pd.concat(rows, ignore_index=True)


def build_definition_robustness(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for event_def in EVENT_DEFS:
        for horizon in HORIZONS:
            rows.append(
                evaluate_groups(
                    panel,
                    paths[(horizon, "next_open")],
                    event_def,
                    horizon,
                    PRIMARY_RISK_ENV,
                    PRIMARY_FUNDING,
                    groups=groups,
                )
            )
    return pd.concat(rows, ignore_index=True)


def build_risk_env_robustness(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for risk_env in RISK_ENVS:
        for horizon in HORIZONS:
            rows.append(
                evaluate_groups(
                    panel,
                    paths[(horizon, "next_open")],
                    PRIMARY_EVENT,
                    horizon,
                    risk_env,
                    PRIMARY_FUNDING,
                    groups=groups,
                )
            )
    return pd.concat(rows, ignore_index=True)


def build_funding_robustness(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for funding_case in FUNDING_CASES:
        for horizon in HORIZONS:
            rows.append(
                evaluate_groups(
                    panel,
                    paths[(horizon, "next_open")],
                    PRIMARY_EVENT,
                    horizon,
                    PRIMARY_RISK_ENV,
                    funding_case,
                    groups=groups,
                )
            )
    return pd.concat(rows, ignore_index=True)


def build_subperiod_results(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for period_name, period in PERIODS.items():
        for horizon in HORIZONS:
            result = evaluate_groups(
                panel,
                paths[(horizon, "next_open")],
                PRIMARY_EVENT,
                horizon,
                PRIMARY_RISK_ENV,
                PRIMARY_FUNDING,
                groups=groups,
                period=period,
            )
            result.insert(0, "period", period_name)
            rows.append(result)
    return pd.concat(rows, ignore_index=True)


def build_walk_forward(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    for fold, cfg in WALK_FORWARD.items():
        for stage in ["train", "test"]:
            for horizon in ["24h", "48h"]:
                result = evaluate_groups(
                    panel,
                    paths[(horizon, "next_open")],
                    PRIMARY_EVENT,
                    horizon,
                    PRIMARY_RISK_ENV,
                    PRIMARY_FUNDING,
                    groups=groups,
                    period=cfg[stage],
                )
                result.insert(0, "fold", fold)
                result.insert(1, "stage", stage)
                result.insert(2, "period_start", cfg[stage][0] or "")
                result.insert(3, "period_end", cfg[stage][1] or "")
                rows.append(result)
    return pd.concat(rows, ignore_index=True)


def build_mae_dd_stress(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    stress_rows = []
    leverage_rows = []
    groups = ["funding_low_x_risk_on", "funding_high_x_risk_off"]
    events = apply_cooldown(panel, PRIMARY_EVENT)
    events = events[events["has_funding_regime"]].copy()
    risk = risk_series(panel, PRIMARY_RISK_ENV)
    funding_low, funding_high = funding_pair(panel, PRIMARY_FUNDING)
    masks = group_masks(events, risk, funding_low, funding_high)

    for horizon in HORIZONS:
        path = paths[(horizon, "next_open")]
        base_ret = path["gross_return"]
        mae = path["mae"]
        mfe = path["mfe"]
        for group in groups:
            idx = events.index[masks[group].fillna(False)]
            for stop_case, stop_level in STOP_LEVELS.items():
                selected_ret = base_ret.loc[idx]
                selected_mae = mae.loc[idx]
                stop_log = math.log(1.0 + stop_level)
                stopped = selected_ret.where(selected_mae > stop_log, stop_log)
                row = {
                    "horizon": horizon,
                    "group": group,
                    "stop_case": stop_case,
                    "stop_level_pct": stop_level * 100,
                }
                row.update(metrics_from_returns(stopped, selected_mae, mfe.loc[idx]))
                stress_rows.append(row)

            for leverage in LEVERAGES:
                levered_ret = base_ret.loc[idx] * leverage
                levered_mae = mae.loc[idx] * leverage
                row = {
                    "horizon": horizon,
                    "group": group,
                    "leverage": leverage,
                }
                row.update(metrics_from_returns(levered_ret, levered_mae, mfe.loc[idx] * leverage))
                for threshold in MARGIN_THRESHOLDS:
                    row[f"margin_breach_{int(threshold)}pct_count"] = int((levered_mae * 100 <= -threshold).sum())
                    row[f"margin_breach_{int(threshold)}pct_rate"] = (
                        (levered_mae * 100 <= -threshold).mean() * 100 if len(levered_mae.dropna()) else np.nan
                    )
                leverage_rows.append(row)

    return add_fragility_flags(pd.DataFrame(stress_rows)), add_fragility_flags(pd.DataFrame(leverage_rows))


def build_bootstrap(panel: pd.DataFrame, paths: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    groups = ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
    events = apply_cooldown(panel, PRIMARY_EVENT)
    events = events[events["has_funding_regime"]].copy()
    risk = risk_series(panel, PRIMARY_RISK_ENV)
    funding_low, funding_high = funding_pair(panel, PRIMARY_FUNDING)
    masks = group_masks(events, risk, funding_low, funding_high)
    for horizon in ["24h", "48h"]:
        path = paths[(horizon, "next_open")]
        for group in groups:
            idx = events.index[masks[group].fillna(False)]
            ret = path["gross_return"].loc[idx]
            row = {
                "event_def": PRIMARY_EVENT,
                "horizon": horizon,
                "risk_env": PRIMARY_RISK_ENV,
                "funding_case": PRIMARY_FUNDING,
                "group": group,
                "n": int(ret.dropna().shape[0]),
            }
            row.update(bootstrap_metrics(ret))
            row["is_ci_fragile"] = row["mean_p05_pct"] <= 0 if math.isfinite(row["mean_p05_pct"]) else True
            rows.append(row)
    return pd.DataFrame(rows)


def save_heatmap(path: Path, data: pd.DataFrame, row_col: str, col_col: str, value_col: str, title: str) -> None:
    pivot = data.pivot_table(index=row_col, columns=col_col, values=value_col, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.2), max(4, len(pivot.index) * 0.5)))
    image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="RdYlGn")
    ax.set_title(title)
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.iloc[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label=value_col)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_bar(path: Path, data: pd.DataFrame, x_col: str, y_col: str, title: str, ylabel: str) -> None:
    plot = data.copy()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(np.arange(len(plot)), plot[y_col].astype(float), color="#3F6F8F", alpha=0.86)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(np.arange(len(plot)))
    ax.set_xticklabels(plot[x_col].astype(str), rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def generate_figures(
    cost: pd.DataFrame,
    entry: pd.DataFrame,
    definition: pd.DataFrame,
    risk_env: pd.DataFrame,
    funding: pd.DataFrame,
    leverage: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> None:
    low_on_cost = cost[
        (cost["group"].eq("funding_low_x_risk_on")) & (cost["horizon"].isin(["24h", "48h"]))
    ].copy()
    low_on_cost["case"] = low_on_cost["horizon"] + "/" + low_on_cost["cost_case"]
    save_heatmap(
        FIGURE_DIR / "btc_cost_stress_heatmap.png",
        low_on_cost,
        "group",
        "case",
        "mean_ret_pct",
        "BTC Funding low x risk-on cost stress",
    )

    low_on_entry = entry[
        (entry["group"].eq("funding_low_x_risk_on")) & (entry["horizon"].isin(["24h", "48h"]))
    ].copy()
    low_on_entry["case"] = low_on_entry["horizon"] + "/" + low_on_entry["entry_case"]
    save_bar(
        FIGURE_DIR / "btc_entry_execution_stress.png",
        low_on_entry.sort_values(["horizon", "entry_case"]),
        "case",
        "mean_ret_pct",
        "BTC entry and execution stress",
        "Mean return (%)",
    )

    low_on_def = definition[
        (definition["group"].eq("funding_low_x_risk_on")) & (definition["horizon"].isin(["24h", "48h"]))
    ].copy()
    low_on_def["case"] = low_on_def["horizon"] + "/" + low_on_def["event_def"]
    save_heatmap(
        FIGURE_DIR / "btc_definition_robustness_heatmap.png",
        low_on_def,
        "horizon",
        "event_def",
        "mean_ret_pct",
        "BTC crash definition robustness",
    )

    low_on_risk = risk_env[
        (risk_env["group"].eq("funding_low_x_risk_on")) & (risk_env["horizon"].eq("48h"))
    ].copy()
    save_bar(
        FIGURE_DIR / "btc_risk_env_robustness.png",
        low_on_risk.sort_values("risk_env"),
        "risk_env",
        "mean_ret_pct",
        "BTC risk-on proxy robustness (48h)",
        "Mean return (%)",
    )

    low_on_funding = funding[
        (funding["group"].eq("funding_low_x_risk_on"))
        & (funding["horizon"].eq("48h"))
        & (funding["funding_case"].isin(
            ["negative", "lower_10_or_negative", "lower_20_only", "lower_20_or_negative"]
        ))
    ].copy()
    save_bar(
        FIGURE_DIR / "btc_funding_definition_robustness.png",
        low_on_funding.sort_values("funding_case"),
        "funding_case",
        "mean_ret_pct",
        "BTC funding definition robustness (48h)",
        "Mean return (%)",
    )

    lev = leverage[
        (leverage["group"].eq("funding_low_x_risk_on")) & (leverage["horizon"].eq("48h"))
    ].copy()
    save_bar(
        FIGURE_DIR / "btc_leverage_tolerance.png",
        lev.sort_values("leverage"),
        "leverage",
        "worst_mae_pct",
        "BTC leverage stress: worst MAE (48h)",
        "Worst MAE (%)",
    )

    boot = bootstrap[
        (bootstrap["group"].eq("funding_low_x_risk_on")) & (bootstrap["horizon"].isin(["24h", "48h"]))
    ].copy()
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(boot))
    med = boot["mean_p50_pct"].to_numpy(dtype=float)
    low = boot["mean_p05_pct"].to_numpy(dtype=float)
    high = boot["mean_p95_pct"].to_numpy(dtype=float)
    ax.errorbar(x, med, yerr=[med - low, high - med], fmt="o", color="#8B4A63", capsize=5)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(boot["horizon"])
    ax.set_title("Bootstrap mean return uncertainty")
    ax.set_ylabel("Mean return (%)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "btc_bootstrap_mean_return.png", dpi=180)
    plt.close(fig)


def fmt(value: object, digits: int = 3) -> str:
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return "-"
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(df: pd.DataFrame, cols: list[str], digits: int = 3) -> str:
    if df.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(fmt(row[col], digits) for col in cols) + " |")
    return "\n".join(lines)


def make_report(
    metadata: dict[str, str],
    extra_metadata: dict[str, float],
    baseline: pd.DataFrame,
    cost: pd.DataFrame,
    entry: pd.DataFrame,
    definition: pd.DataFrame,
    risk_env: pd.DataFrame,
    funding: pd.DataFrame,
    subperiod: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> str:
    primary_cols = [
        "horizon",
        "group",
        "n",
        "mean_ret_pct",
        "win_rate_pct",
        "profit_factor",
        "mean_mae_pct",
        "worst_mae_pct",
        "maxdd_pct",
        "fragility_status",
    ]
    baseline_focus = baseline[
        baseline["group"].isin(
            ["all_funding_covered_crashes", "funding_low_x_risk_on", "funding_high_x_risk_off"]
        )
    ]
    cost_focus = cost[
        (cost["group"].eq("funding_low_x_risk_on")) & (cost["horizon"].isin(["24h", "48h"]))
    ].sort_values(["horizon", "cost_bps"])
    entry_focus = entry[
        (entry["group"].eq("funding_low_x_risk_on")) & (entry["horizon"].isin(["24h", "48h"]))
    ].sort_values(["horizon", "entry_lag_bars", "adverse_entry_bps"])
    def_focus = definition[
        (definition["group"].eq("funding_low_x_risk_on")) & (definition["horizon"].eq("48h"))
    ].sort_values("event_def")
    risk_focus = risk_env[
        (risk_env["group"].eq("funding_low_x_risk_on")) & (risk_env["horizon"].eq("48h"))
    ].sort_values("risk_env")
    funding_focus = funding[
        (funding["group"].eq("funding_low_x_risk_on"))
        & (funding["horizon"].eq("48h"))
        & (funding["funding_case"].isin(
            ["negative", "lower_10_or_negative", "lower_20_only", "lower_20_or_negative"]
        ))
    ].sort_values("funding_case")
    period_focus = subperiod[
        (subperiod["group"].eq("funding_low_x_risk_on")) & (subperiod["horizon"].eq("48h"))
    ].sort_values("period")
    boot_focus = bootstrap[bootstrap["group"].eq("funding_low_x_risk_on")].sort_values("horizon")

    return f"""# BTC crash fragility experiment

## Purpose

This experiment reuses the `lab_7` BTC crash, Funding Rate, and external risk-on setup, but does not try to prove a tradable edge. It asks where the candidate breaks.

## Data

- Common 4H panel: {metadata["rows"]} rows
- Range: {metadata["start"]} to {metadata["end"]}
- Full-sample lower 5% BTC 4H threshold: {metadata["btc_q05_pct"]}%
- Full-sample lower 2.5% BTC 4H threshold: {extra_metadata["btc_q025_pct"]:.4f}%
- Primary condition: `rolling_2sigma x nasdaq_5d_up x lower_20_or_negative`

## Baseline Candidate

{markdown_table(baseline_focus, primary_cols, digits=3)}

## Cost Stress: Funding low x risk-on

{markdown_table(cost_focus, ["horizon", "cost_case", "cost_bps", "n", "mean_ret_pct", "profit_factor", "maxdd_pct", "fragility_status"], digits=3)}

## Entry and Execution Stress: Funding low x risk-on

{markdown_table(entry_focus, ["horizon", "entry_case", "entry_lag_bars", "adverse_entry_bps", "n", "mean_ret_pct", "profit_factor", "fragility_status"], digits=3)}

## Crash Definition Robustness: Funding low x risk-on, 48h

{markdown_table(def_focus, ["event_def", "n", "mean_ret_pct", "profit_factor", "mean_mae_pct", "maxdd_pct", "fragility_status"], digits=3)}

## Risk-on Proxy Robustness: Funding low x risk-on, 48h

{markdown_table(risk_focus, ["risk_env", "n", "mean_ret_pct", "profit_factor", "mean_mae_pct", "maxdd_pct", "fragility_status"], digits=3)}

## Funding Definition Robustness: Funding low x risk-on, 48h

{markdown_table(funding_focus, ["funding_case", "n", "mean_ret_pct", "profit_factor", "mean_mae_pct", "maxdd_pct", "fragility_status"], digits=3)}

## Subperiod Stability: Funding low x risk-on, 48h

{markdown_table(period_focus, ["period", "n", "mean_ret_pct", "profit_factor", "mean_mae_pct", "maxdd_pct", "fragility_status"], digits=3)}

## Bootstrap Uncertainty

{markdown_table(boot_focus, ["horizon", "n", "mean_p05_pct", "mean_p50_pct", "mean_p95_pct", "pf_p05", "pf_p50", "pf_p95", "is_ci_fragile"], digits=3)}

## Figures

- `outputs/figures/btc_cost_stress_heatmap.png`
- `outputs/figures/btc_entry_execution_stress.png`
- `outputs/figures/btc_definition_robustness_heatmap.png`
- `outputs/figures/btc_risk_env_robustness.png`
- `outputs/figures/btc_funding_definition_robustness.png`
- `outputs/figures/btc_leverage_tolerance.png`
- `outputs/figures/btc_bootstrap_mean_return.png`

## Article Interpretation

- `Funding low x risk-on` remains an interesting candidate, but the primary 24h/48h condition has very small `n`.
- The candidate must be discussed through sample size, cost, entry assumptions, definition changes, period dependence, and left-tail path risk.
- The clean article claim is not "buy BTC crashes"; it is "an edge-looking subgroup still needs error-on-error diagnostics."
"""


def main() -> None:
    ensure_dirs()
    panel, metadata = BASE.build_panel()
    panel, extra_metadata = add_extra_features(panel)
    paths = build_paths(panel)

    baseline = build_baseline(panel, paths)
    cost = build_cost_stress(panel, paths)
    entry = build_entry_stress(panel, paths)
    definition = build_definition_robustness(panel, paths)
    risk_env = build_risk_env_robustness(panel, paths)
    funding = build_funding_robustness(panel, paths)
    subperiod = build_subperiod_results(panel, paths)
    walk_forward = build_walk_forward(panel, paths)
    mae_dd, leverage = build_mae_dd_stress(panel, paths)
    bootstrap = build_bootstrap(panel, paths)

    baseline.to_csv(TABLE_DIR / "btc_crash_baseline.csv", index=False)
    cost.to_csv(TABLE_DIR / "btc_cost_stress.csv", index=False)
    entry.to_csv(TABLE_DIR / "btc_entry_execution_stress.csv", index=False)
    definition.to_csv(TABLE_DIR / "btc_definition_robustness.csv", index=False)
    risk_env.to_csv(TABLE_DIR / "btc_risk_env_robustness.csv", index=False)
    funding.to_csv(TABLE_DIR / "btc_funding_definition_robustness.csv", index=False)
    subperiod.to_csv(TABLE_DIR / "btc_subperiod_results.csv", index=False)
    walk_forward.to_csv(TABLE_DIR / "btc_walk_forward.csv", index=False)
    mae_dd.to_csv(TABLE_DIR / "btc_mae_dd_stress.csv", index=False)
    leverage.to_csv(TABLE_DIR / "btc_leverage_tolerance.csv", index=False)
    bootstrap.to_csv(TABLE_DIR / "btc_bootstrap_uncertainty.csv", index=False)

    generate_figures(cost, entry, definition, risk_env, funding, leverage, bootstrap)
    (REPORT_DIR / "btc_crash_fragility.md").write_text(
        make_report(metadata, extra_metadata, baseline, cost, entry, definition, risk_env, funding, subperiod, bootstrap),
        encoding="utf-8",
    )

    for name in [
        "btc_crash_baseline.csv",
        "btc_cost_stress.csv",
        "btc_entry_execution_stress.csv",
        "btc_definition_robustness.csv",
        "btc_risk_env_robustness.csv",
        "btc_funding_definition_robustness.csv",
        "btc_subperiod_results.csv",
        "btc_walk_forward.csv",
        "btc_mae_dd_stress.csv",
        "btc_leverage_tolerance.csv",
        "btc_bootstrap_uncertainty.csv",
    ]:
        print(f"Wrote {TABLE_DIR / name}")
    print(f"Wrote {REPORT_DIR / 'btc_crash_fragility.md'}")


if __name__ == "__main__":
    main()
