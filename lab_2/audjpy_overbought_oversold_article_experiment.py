from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib.colors import ListedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle


# ============================================================
# AUDJPY 60分足：買われすぎ・売られすぎを数値化する記事用実験
# ============================================================
# 目的:
# - 「買われすぎ」「売られすぎ」をチャートの印象ではなく、
#   過去分布内の相対位置として数値化する。
# - その異常状態のあとに、本当に反発したかを検証する。
#
# 重要:
# - シグナル判定は60分足の終値時点
# - エントリーは次足始値
# - 同一足エントリーによる過大評価を避ける
# - これは記事用の探索実験であり、完成した売買戦略ではない
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_CSV = SCRIPT_DIR / "AUDJPY60.csv"
DEFAULT_OUT_DIR = SCRIPT_DIR / "article_outputs"
DEFAULT_HORIZONS = (1, 2, 4, 8, 12, 24)

ROLL = 500
VWAP_WIN = 24
PRIMARY_HORIZON = 4
COST_PIPS = 0.8
PIP_SIZE = 0.01

RET_BINS = [0, 5, 10, 25, 50, 75, 90, 95, 100]
RET_LABELS = ["0-5", "5-10", "10-25", "25-50", "50-75", "75-90", "90-95", "95-100"]
Z_BINS = [-np.inf, -2.5, -2.0, -1.5, -1.0, 0, 1.0, 1.5, 2.0, 2.5, np.inf]
Z_LABELS = [
    "<=-2.5",
    "-2.5~-2.0",
    "-2.0~-1.5",
    "-1.5~-1.0",
    "-1.0~0",
    "0~1.0",
    "1.0~1.5",
    "1.5~2.0",
    "2.0~2.5",
    ">=2.5",
]

CONDITIONS = [
    {
        "id": "oversold",
        "label": "売られすぎ候補: VWAP Z<=-2.0 & ret pct<=10",
        "short_label": "売られすぎ",
        "direction": "Long",
        "side": "long",
    },
    {
        "id": "strong_oversold",
        "label": "強い売られすぎ候補: VWAP Z<=-2.5 & ret pct<=5",
        "short_label": "強い売られすぎ",
        "direction": "Long",
        "side": "long",
    },
    {
        "id": "overbought",
        "label": "買われすぎ候補: VWAP Z>=2.0 & ret pct>=90",
        "short_label": "買われすぎ",
        "direction": "Short",
        "side": "short",
    },
    {
        "id": "strong_overbought",
        "label": "強い買われすぎ候補: VWAP Z>=2.5 & ret pct>=95",
        "short_label": "強い買われすぎ",
        "direction": "Short",
        "side": "short",
    },
]


def setup_font() -> None:
    jp_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if Path(jp_font_path).exists():
        jp_font = fm.FontProperties(fname=jp_font_path)
        plt.rcParams["font.family"] = jp_font.get_name()
    plt.rcParams["axes.unicode_minus"] = False


def parse_horizons(value: str) -> list[int]:
    horizons = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        horizon = int(item)
        if horizon <= 0:
            raise argparse.ArgumentTypeError("horizons must be positive integers")
        horizons.append(horizon)
    if not horizons:
        raise argparse.ArgumentTypeError("at least one horizon is required")
    return sorted(set(horizons))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate article figures and summaries for AUDJPY overbought/oversold quant analysis.",
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--roll", type=int, default=ROLL, help="rolling window for percentile/Z-score")
    parser.add_argument("--vwap-window", type=int, default=VWAP_WIN, help="rolling VWAP window in bars")
    parser.add_argument("--primary-horizon", type=int, default=PRIMARY_HORIZON, help="main rebound horizon in hours")
    parser.add_argument(
        "--horizons",
        type=parse_horizons,
        default=list(DEFAULT_HORIZONS),
        help="comma-separated rebound horizons in hours, e.g. 1,2,4,8,12,24",
    )
    parser.add_argument("--cost-pips", type=float, default=COST_PIPS)
    parser.add_argument("--pip-size", type=float, default=PIP_SIZE)
    parser.add_argument("--dpi", type=int, default=200)
    return parser.parse_args()


def read_price_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["datetime", "open", "high", "low", "close", "volume"],
    )
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["datetime", "open", "high", "low", "close"]).reset_index(drop=True)
    return df


def last_percentile_rank(values: pd.Series) -> float:
    return values.rank(pct=True).iloc[-1] * 100


def add_indicators(df: pd.DataFrame, roll: int, vwap_window: int) -> pd.DataFrame:
    df = df.copy()
    df["ret_1h"] = df["close"].pct_change()
    df["ret_pct_rank_500"] = (
        df["ret_1h"].rolling(roll, min_periods=roll).apply(last_percentile_rank, raw=False)
    )

    typical = (df["high"] + df["low"] + df["close"]) / 3
    pv = typical * df["volume"]
    vol_sum = df["volume"].rolling(vwap_window, min_periods=vwap_window).sum()
    df["vwap_24h"] = pv.rolling(vwap_window, min_periods=vwap_window).sum() / vol_sum
    df["vwap_dev"] = df["close"] / df["vwap_24h"] - 1
    df["vwap_dev_mean_500"] = df["vwap_dev"].rolling(roll, min_periods=roll).mean()
    df["vwap_dev_std_500"] = df["vwap_dev"].rolling(roll, min_periods=roll).std()
    df["vwap_z_500"] = (df["vwap_dev"] - df["vwap_dev_mean_500"]) / df["vwap_dev_std_500"]
    return df


def add_trade_returns(
    df: pd.DataFrame,
    horizons: list[int],
    cost_pips: float,
    pip_size: float,
) -> pd.DataFrame:
    df = df.copy()
    entry = df["open"].shift(-1)
    cost_ret = (cost_pips * pip_size) / entry
    df["entry_open_next"] = entry

    for horizon in horizons:
        exit_open = df["open"].shift(-(1 + horizon))
        df[f"exit_open_{horizon}h"] = exit_open
        df[f"long_net_ret_{horizon}h"] = ((exit_open - entry) / entry) - cost_ret
        df[f"short_net_ret_{horizon}h"] = ((entry - exit_open) / entry) - cost_ret

    return df


def condition_mask(work: pd.DataFrame, condition_id: str) -> pd.Series:
    if condition_id == "oversold":
        return (work["vwap_z_500"] <= -2.0) & (work["ret_pct_rank_500"] <= 10)
    if condition_id == "strong_oversold":
        return (work["vwap_z_500"] <= -2.5) & (work["ret_pct_rank_500"] <= 5)
    if condition_id == "overbought":
        return (work["vwap_z_500"] >= 2.0) & (work["ret_pct_rank_500"] >= 90)
    if condition_id == "strong_overbought":
        return (work["vwap_z_500"] >= 2.5) & (work["ret_pct_rank_500"] >= 95)
    raise ValueError(f"unknown condition_id: {condition_id}")


def ret_col(side: str, horizon: int) -> str:
    return f"{side}_net_ret_{horizon}h"


def return_stats(ret: pd.Series) -> dict[str, float]:
    ret = ret.dropna()
    if ret.empty:
        return {
            "n": 0,
            "rebound_probability_%": np.nan,
            "mean_net_return_bps": np.nan,
            "median_net_return_bps": np.nan,
            "p5_net_return_bps": np.nan,
            "p95_net_return_bps": np.nan,
            "std_net_return_bps": np.nan,
            "t_stat": np.nan,
        }

    std = ret.std(ddof=1)
    t_stat = ret.mean() / (std / np.sqrt(len(ret))) if len(ret) > 1 and std > 0 else np.nan
    return {
        "n": int(len(ret)),
        "rebound_probability_%": (ret > 0).mean() * 100,
        "mean_net_return_bps": ret.mean() * 10000,
        "median_net_return_bps": ret.median() * 10000,
        "p5_net_return_bps": ret.quantile(0.05) * 10000,
        "p95_net_return_bps": ret.quantile(0.95) * 10000,
        "std_net_return_bps": std * 10000,
        "t_stat": t_stat,
    }


def build_work(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    needed = ["ret_pct_rank_500", "vwap_z_500", ret_col("long", horizon), ret_col("short", horizon)]
    work = df.dropna(subset=needed).copy()
    work["ret_bin"] = pd.cut(work["ret_pct_rank_500"], bins=RET_BINS, labels=RET_LABELS, include_lowest=True)
    work["z_bin"] = pd.cut(work["vwap_z_500"], bins=Z_BINS, labels=Z_LABELS, include_lowest=True)
    return work.dropna(subset=["ret_bin", "z_bin"]).copy()


def build_baseline_summary(work: pd.DataFrame, horizon: int) -> pd.DataFrame:
    rows = []
    for direction, side in [("Long", "long"), ("Short", "short")]:
        stats = return_stats(work[ret_col(side, horizon)])
        rows.append(
            {
                "horizon_hours": horizon,
                "direction": direction,
                **stats,
            }
        )
    return pd.DataFrame(rows)


def build_condition_summary(work: pd.DataFrame, horizon: int, baseline: pd.DataFrame) -> pd.DataFrame:
    baseline_by_direction = baseline.set_index("direction")["mean_net_return_bps"].to_dict()
    rows = []

    for spec in CONDITIONS:
        mask = condition_mask(work, spec["id"])
        stats = return_stats(work.loc[mask, ret_col(spec["side"], horizon)])
        baseline_mean = baseline_by_direction[spec["direction"]]
        rows.append(
            {
                "condition_id": spec["id"],
                "condition": spec["label"],
                "short_label": spec["short_label"],
                "direction": spec["direction"],
                "horizon_hours": horizon,
                **stats,
                "baseline_mean_net_return_bps": baseline_mean,
                "excess_vs_baseline_bps": stats["mean_net_return_bps"] - baseline_mean,
            }
        )

    return pd.DataFrame(rows)


def build_horizon_summary(df: pd.DataFrame, horizons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    condition_rows = []
    baseline_rows = []
    for horizon in horizons:
        work = build_work(df, horizon)
        baseline = build_baseline_summary(work, horizon)
        condition_summary = build_condition_summary(work, horizon, baseline)
        condition_rows.append(condition_summary)
        baseline_rows.append(baseline)
    return pd.concat(condition_rows, ignore_index=True), pd.concat(baseline_rows, ignore_index=True)


def add_contrarian_columns(work: pd.DataFrame, horizon: int) -> pd.DataFrame:
    work = work.copy()
    long_zone = (work["vwap_z_500"] < 0) & (work["ret_pct_rank_500"] <= 50)
    short_zone = (work["vwap_z_500"] > 0) & (work["ret_pct_rank_500"] > 50)

    work[f"contrarian_net_ret_{horizon}h"] = np.nan
    work.loc[long_zone, f"contrarian_net_ret_{horizon}h"] = work.loc[long_zone, ret_col("long", horizon)]
    work.loc[short_zone, f"contrarian_net_ret_{horizon}h"] = work.loc[short_zone, ret_col("short", horizon)]

    ret = work[f"contrarian_net_ret_{horizon}h"]
    work[f"contrarian_net_bps_{horizon}h"] = ret * 10000
    work[f"contrarian_win_pct_{horizon}h"] = np.where(ret.notna(), (ret > 0).astype(float) * 100, np.nan)
    return work


def build_heatmap_tables(work: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    work = add_contrarian_columns(work, horizon)
    mean_bps = (
        work.pivot_table(
            index="z_bin",
            columns="ret_bin",
            values=f"contrarian_net_bps_{horizon}h",
            aggfunc="mean",
            observed=False,
        )
        .reindex(index=Z_LABELS, columns=RET_LABELS)
        .astype(float)
    )
    probability = (
        work.pivot_table(
            index="z_bin",
            columns="ret_bin",
            values=f"contrarian_win_pct_{horizon}h",
            aggfunc="mean",
            observed=False,
        )
        .reindex(index=Z_LABELS, columns=RET_LABELS)
        .astype(float)
    )
    count = (
        work.pivot_table(
            index="z_bin",
            columns="ret_bin",
            values=f"contrarian_net_ret_{horizon}h",
            aggfunc="count",
            observed=False,
        )
        .reindex(index=Z_LABELS, columns=RET_LABELS)
        .astype(float)
    )
    count = count.where(count > 0)
    return mean_bps, probability, count


def annotate_candidate_areas(ax: plt.Axes) -> None:
    blue = "#1769aa"
    red = "#b23a48"
    ax.add_patch(Rectangle((-0.5, -0.5), 2, 2, fill=False, edgecolor=blue, linewidth=2.2))
    ax.add_patch(Rectangle((-0.5, -0.5), 1, 1, fill=False, edgecolor=blue, linewidth=3.4))
    ax.add_patch(Rectangle((5.5, 7.5), 2, 2, fill=False, edgecolor=red, linewidth=2.2))
    ax.add_patch(Rectangle((6.5, 8.5), 1, 1, fill=False, edgecolor=red, linewidth=3.4))


def plot_judgement_map(output_dir: Path, dpi: int) -> None:
    grid = np.zeros((len(Z_LABELS), len(RET_LABELS)))
    grid[0:2, 0:2] = -1
    grid[0, 0] = -2
    grid[8:10, 6:8] = 1
    grid[9, 7] = 2

    cmap = ListedColormap(["#2f6f9f", "#9cc9e2", "#f3f4f6", "#f1b481", "#c94c4c"])
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.imshow(grid, aspect="auto", cmap=cmap, vmin=-2, vmax=2)

    ax.set_xticks(np.arange(len(RET_LABELS)))
    ax.set_xticklabels(RET_LABELS, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(Z_LABELS)))
    ax.set_yticklabels(Z_LABELS)
    ax.set_xlabel("直近1時間リターンの過去500本内パーセンタイル")
    ax.set_ylabel("24時間VWAP乖離Zスコア")
    ax.set_title("AUDJPY 60分足：買われすぎ・売られすぎの定義マップ")

    for i in range(len(Z_LABELS)):
        for j in range(len(RET_LABELS)):
            label = ""
            color = "black"
            if i == 0 and j == 0:
                label = "強い\n売られすぎ"
                color = "white"
            elif i in (0, 1) and j in (0, 1):
                label = "売られ\nすぎ候補"
            elif i == 9 and j == 7:
                label = "強い\n買われすぎ"
                color = "white"
            elif i in (8, 9) and j in (6, 7):
                label = "買われ\nすぎ候補"
            elif i == 4 and j == 3:
                label = "中立"
            if label:
                ax.text(j, i, label, ha="center", va="center", fontsize=10, color=color)

    ax.set_xticks(np.arange(-0.5, len(RET_LABELS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(Z_LABELS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    annotate_candidate_areas(ax)
    fig.tight_layout()
    fig.savefig(output_dir / "00_article_judgement_map_overbought_oversold.png", dpi=dpi)
    plt.close(fig)


def finite_clip_abs(data: pd.DataFrame, quantile: float, minimum: float) -> float:
    values = np.abs(data.to_numpy(dtype=float))
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return minimum
    return max(minimum, float(np.nanquantile(finite, quantile)))


def plot_heatmap(
    data: pd.DataFrame,
    count: pd.DataFrame,
    title: str,
    value_label: str,
    filename: str,
    output_dir: Path,
    dpi: int,
    mode: str,
) -> None:
    fig, ax = plt.subplots(figsize=(13, 7.5))
    values = data.astype(float)

    if mode == "mean":
        clip_abs = finite_clip_abs(values, quantile=0.95, minimum=5.0)
        plot_values = values.clip(lower=-clip_abs, upper=clip_abs)
        norm = TwoSlopeNorm(vmin=-clip_abs, vcenter=0, vmax=clip_abs)
        cmap = plt.get_cmap("RdBu_r").copy()
    elif mode == "probability":
        deviations = (values - 50).abs()
        clip_dev = finite_clip_abs(deviations, quantile=0.95, minimum=5.0)
        lower = 50 - clip_dev
        upper = 50 + clip_dev
        plot_values = values.clip(lower=lower, upper=upper)
        norm = TwoSlopeNorm(vmin=lower, vcenter=50, vmax=upper)
        cmap = plt.get_cmap("RdYlGn").copy()
    else:
        raise ValueError(f"unknown heatmap mode: {mode}")

    cmap.set_bad("#f3f4f6")
    arr = np.ma.masked_invalid(plot_values.to_numpy(dtype=float))
    im = ax.imshow(arr, aspect="auto", cmap=cmap, norm=norm)

    ax.set_xticks(np.arange(len(values.columns)))
    ax.set_xticklabels(values.columns, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(values.index)))
    ax.set_yticklabels(values.index)
    ax.set_xlabel("直近1時間リターンの過去500本内パーセンタイル")
    ax.set_ylabel("24時間VWAP乖離Zスコア")
    ax.set_title(title)
    ax.set_xticks(np.arange(-0.5, len(values.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(values.index), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.7)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            val = values.iloc[i, j]
            n = count.iloc[i, j]
            if np.isfinite(val) and pd.notna(n):
                suffix = "%" if mode == "probability" else "bps"
                ax.text(j, i, f"{val:.1f}{suffix}\nN={int(n)}", ha="center", va="center", fontsize=8)

    annotate_candidate_areas(ax)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(value_label)
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=dpi)
    plt.close(fig)


def plot_condition_bars(summary: pd.DataFrame, baseline: pd.DataFrame, output_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    labels = summary["short_label"].tolist()
    colors = ["#2f6f9f" if direction == "Long" else "#c94c4c" for direction in summary["direction"]]
    x = np.arange(len(summary))

    axes[0].bar(x, summary["mean_net_return_bps"], color=colors, alpha=0.85)
    axes[0].scatter(x, summary["baseline_mean_net_return_bps"], color="black", marker="_", s=220, label="無条件平均")
    axes[0].axhline(0, color="#333333", linewidth=1)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=20, ha="right")
    axes[0].set_ylabel("平均ネットリターン (bps)")
    axes[0].set_title("条件を付けた後の平均リターン")
    axes[0].legend(loc="upper left")
    for idx, row in summary.iterrows():
        y = row["mean_net_return_bps"]
        va = "bottom" if y >= 0 else "top"
        axes[0].text(idx, y, f"{y:.1f}\nN={int(row['n'])}", ha="center", va=va, fontsize=9)

    axes[1].bar(x, summary["rebound_probability_%"], color=colors, alpha=0.85)
    axes[1].axhline(50, color="#333333", linewidth=1, linestyle="--")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=20, ha="right")
    axes[1].set_ylabel("反発確率 (%)")
    axes[1].set_title("反発確率は50%をどれだけ上回るか")
    axes[1].set_ylim(45, max(58, summary["rebound_probability_%"].max() + 2))
    for idx, row in summary.iterrows():
        y = row["rebound_probability_%"]
        axes[1].text(idx, y, f"{y:.1f}%", ha="center", va="bottom", fontsize=9)

    fig.suptitle("AUDJPY 60分足：買われすぎ・売られすぎ候補の条件別サマリー")
    fig.tight_layout()
    fig.savefig(output_dir / "07_article_condition_summary_bars.png", dpi=dpi)
    plt.close(fig)


def plot_horizon_sensitivity(horizon_summary: pd.DataFrame, output_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6))
    colors = {
        "oversold": "#5aa6d1",
        "strong_oversold": "#1769aa",
        "overbought": "#e58f65",
        "strong_overbought": "#b23a48",
    }
    for spec in CONDITIONS:
        sub = horizon_summary[horizon_summary["condition_id"] == spec["id"]].sort_values("horizon_hours")
        ax.plot(
            sub["horizon_hours"],
            sub["mean_net_return_bps"],
            marker="o",
            linewidth=2,
            label=spec["short_label"],
            color=colors[spec["id"]],
        )
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_xlabel("評価ホライズン (時間後)")
    ax.set_ylabel("平均ネットリターン (bps)")
    ax.set_title("ホライズンを変えると反発傾向はどう見えるか")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "08_article_horizon_sensitivity.png", dpi=dpi)
    plt.close(fig)


def build_annual_summary(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    work = build_work(df, horizon)
    work["year"] = work["datetime"].dt.year
    rows = []
    for spec in CONDITIONS:
        mask = condition_mask(work, spec["id"])
        target = work.loc[mask].copy()
        for year, group in target.groupby("year"):
            stats = return_stats(group[ret_col(spec["side"], horizon)])
            rows.append(
                {
                    "year": int(year),
                    "condition_id": spec["id"],
                    "condition": spec["label"],
                    "short_label": spec["short_label"],
                    "direction": spec["direction"],
                    "horizon_hours": horizon,
                    **stats,
                }
            )
    return pd.DataFrame(rows)


def plot_annual_stability(annual: pd.DataFrame, output_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.2), sharex=True)
    plot_specs = [
        ("strong_oversold", "強い売られすぎ: Long"),
        ("strong_overbought", "強い買われすぎ: Short"),
    ]
    colors = {"strong_oversold": "#1769aa", "strong_overbought": "#b23a48"}
    for ax, (condition_id, title) in zip(axes, plot_specs):
        sub = annual[annual["condition_id"] == condition_id].sort_values("year")
        ax.bar(sub["year"].astype(str), sub["mean_net_return_bps"], color=colors[condition_id], alpha=0.85)
        ax.axhline(0, color="#333333", linewidth=1)
        ax.set_ylabel("平均bps")
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.25)
        for idx, row in enumerate(sub.itertuples(index=False)):
            y = row.mean_net_return_bps
            if row.n >= 10:
                va = "bottom" if y >= 0 else "top"
                ax.text(idx, y, f"N={int(row.n)}", ha="center", va=va, fontsize=8, rotation=90)
    axes[-1].set_xlabel("年")
    fig.suptitle("年別に見ると、プラス傾向は一定ではない")
    fig.tight_layout()
    fig.savefig(output_dir / "09_article_annual_stability.png", dpi=dpi)
    plt.close(fig)


def plot_return_distribution(work: pd.DataFrame, horizon: int, output_dir: Path, dpi: int) -> None:
    labels = []
    data = []
    colors = []
    for spec in CONDITIONS:
        mask = condition_mask(work, spec["id"])
        series = work.loc[mask, ret_col(spec["side"], horizon)].dropna() * 10000
        labels.append(spec["short_label"])
        data.append(series)
        colors.append("#2f6f9f" if spec["direction"] == "Long" else "#c94c4c")

    fig, ax = plt.subplots(figsize=(10.5, 6))
    box = ax.boxplot(
        data,
        tick_labels=labels,
        whis=[5, 95],
        patch_artist=True,
        showmeans=True,
        showfliers=False,
    )
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
    for median in box["medians"]:
        median.set_color("#111111")
        median.set_linewidth(1.5)
    for mean in box["means"]:
        mean.set_marker("o")
        mean.set_markerfacecolor("white")
        mean.set_markeredgecolor("#111111")

    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_ylabel("4時間後ネットリターン (bps)")
    ax.set_title("平均だけでなく、損益分布の幅も確認する")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "10_article_return_distribution_boxplot.png", dpi=dpi)
    plt.close(fig)


def rounded_for_article(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df[columns].copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].round(2)
    return out


def write_article_summary(
    output_dir: Path,
    input_csv: Path,
    df: pd.DataFrame,
    work: pd.DataFrame,
    primary_horizon: int,
    roll: int,
    vwap_window: int,
    cost_pips: float,
    condition_summary: pd.DataFrame,
    baseline_summary: pd.DataFrame,
    horizon_summary: pd.DataFrame,
    annual_summary: pd.DataFrame,
) -> None:
    condition_table = rounded_for_article(
        condition_summary,
        [
            "condition",
            "direction",
            "n",
            "rebound_probability_%",
            "mean_net_return_bps",
            "median_net_return_bps",
            "p5_net_return_bps",
            "p95_net_return_bps",
            "baseline_mean_net_return_bps",
            "excess_vs_baseline_bps",
            "t_stat",
        ],
    )
    baseline_table = rounded_for_article(
        baseline_summary,
        ["direction", "n", "rebound_probability_%", "mean_net_return_bps", "median_net_return_bps"],
    )
    horizon_pivot = horizon_summary.pivot_table(
        index="short_label",
        columns="horizon_hours",
        values="mean_net_return_bps",
        aggfunc="first",
    )
    horizon_pivot = horizon_pivot.reindex([spec["short_label"] for spec in CONDITIONS]).round(2)

    annual_notes = []
    for condition_id in ["strong_oversold", "strong_overbought"]:
        sub = annual_summary[annual_summary["condition_id"] == condition_id]
        label = sub["short_label"].iloc[0]
        positive_years = int((sub["mean_net_return_bps"] > 0).sum())
        annual_notes.append(
            f"- {label}: {positive_years}/{len(sub)} 年が平均プラス、"
            f"最小 {sub['mean_net_return_bps'].min():.2f} bps、最大 {sub['mean_net_return_bps'].max():.2f} bps"
        )

    text = f"""# AUDJPY 買われすぎ・売られすぎ記事用 実験サマリ

## 目的

この記事用の実験は、「買われすぎ・売られすぎ」をチャートの印象ではなく、24時間VWAP乖離Zスコアと直近1時間リターンの過去{roll}本内パーセンタイルで定義し、その後の反発リターンを検証するためのものである。

## 再現コマンド

```bash
python audjpy_overbought_oversold_article_experiment.py
```

入力CSVは `{input_csv.name}`、出力先は `article_outputs/` ディレクトリである。

## データと設定

| 項目 | 値 |
|---|---:|
| 入力行数 | {len(df):,} |
| 指標計算後の利用可能行数 | {len(work):,} |
| データ開始 | {df['datetime'].min()} |
| データ終了 | {df['datetime'].max()} |
| パーセンタイル/Zスコア窓 | {roll} 本 |
| VWAP窓 | {vwap_window} 本 |
| 主評価ホライズン | {primary_horizon} 時間後 |
| エントリー | シグナル判定後の次足始値 |
| コスト | 往復 {cost_pips} pips |

## 無条件ベースライン

{baseline_table.to_markdown(index=False)}

## 条件別サマリー

{condition_table.to_markdown(index=False)}

## ホライズン感度: 平均ネットリターン bps

{horizon_pivot.to_markdown()}

## 年別安定性メモ

{chr(10).join(annual_notes)}

年別に見ると、全期間平均がプラスでも負ける年がある。記事では、この結果を「完成した売買戦略」ではなく、「反発しやすい候補領域の探索」として扱う。

## 生成ファイル

| ファイル | 用途 |
|---|---|
| `00_article_judgement_map_overbought_oversold.png` | 買われすぎ・売られすぎの定義を説明する概念図 |
| `01_article_heatmap_contrarian_mean_bps.png` | 逆張り4時間リターンの期待値ヒートマップ |
| `02_article_heatmap_rebound_probability.png` | 反発確率ヒートマップ |
| `03_article_condition_summary.csv` | 記事本文に使う条件別サマリー |
| `04_heatmap_mean_bps_matrix.csv` | ヒートマップ期待値の数値表 |
| `05_heatmap_probability_matrix.csv` | ヒートマップ反発確率の数値表 |
| `06_heatmap_sample_count_matrix.csv` | ヒートマップの評価対象サンプル数 |
| `07_article_condition_summary_bars.png` | 条件別サマリー棒グラフ |
| `08_article_horizon_sensitivity.png` | 1/2/4/8/12/24時間後の感度比較 |
| `09_article_annual_stability.png` | 強い候補条件の年別安定性 |
| `10_article_return_distribution_boxplot.png` | 条件別4時間後リターン分布 |
| `11_horizon_sensitivity_summary.csv` | ホライズン感度の数値表 |
| `12_annual_condition_summary.csv` | 年別条件別サマリー |
| `13_baseline_summary.csv` | 無条件Long/Shortベースライン |
"""
    (output_dir / "14_article_experiment_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    setup_font()
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    horizons = sorted(set(args.horizons + [args.primary_horizon]))
    df = read_price_csv(args.input_csv)
    df = add_indicators(df, args.roll, args.vwap_window)
    df = add_trade_returns(df, horizons, args.cost_pips, args.pip_size)

    work = build_work(df, args.primary_horizon)
    baseline_summary = build_baseline_summary(work, args.primary_horizon)
    condition_summary = build_condition_summary(work, args.primary_horizon, baseline_summary)
    horizon_summary, all_baselines = build_horizon_summary(df, horizons)
    annual_summary = build_annual_summary(df, args.primary_horizon)
    mean_bps, probability, count = build_heatmap_tables(work, args.primary_horizon)

    condition_summary.to_csv(output_dir / "03_article_condition_summary.csv", index=False, encoding="utf-8-sig")
    mean_bps.to_csv(output_dir / "04_heatmap_mean_bps_matrix.csv", encoding="utf-8-sig")
    probability.to_csv(output_dir / "05_heatmap_probability_matrix.csv", encoding="utf-8-sig")
    count.to_csv(output_dir / "06_heatmap_sample_count_matrix.csv", encoding="utf-8-sig")
    horizon_summary.to_csv(output_dir / "11_horizon_sensitivity_summary.csv", index=False, encoding="utf-8-sig")
    annual_summary.to_csv(output_dir / "12_annual_condition_summary.csv", index=False, encoding="utf-8-sig")
    all_baselines.to_csv(output_dir / "13_baseline_summary.csv", index=False, encoding="utf-8-sig")

    plot_judgement_map(output_dir, args.dpi)
    plot_heatmap(
        mean_bps,
        count,
        f"AUDJPY 60分足：逆張り{args.primary_horizon}時間リターン期待値（コスト控除後）",
        "平均ネットリターン (bps、表示色は外れ値をクリップ)",
        "01_article_heatmap_contrarian_mean_bps.png",
        output_dir,
        args.dpi,
        mode="mean",
    )
    plot_heatmap(
        probability,
        count,
        f"AUDJPY 60分足：逆張り{args.primary_horizon}時間後の反発確率（コスト控除後）",
        "反発確率 (%)",
        "02_article_heatmap_rebound_probability.png",
        output_dir,
        args.dpi,
        mode="probability",
    )
    plot_condition_bars(condition_summary, baseline_summary, output_dir, args.dpi)
    plot_horizon_sensitivity(horizon_summary, output_dir, args.dpi)
    plot_annual_stability(annual_summary, output_dir, args.dpi)
    plot_return_distribution(work, args.primary_horizon, output_dir, args.dpi)
    write_article_summary(
        output_dir=output_dir,
        input_csv=args.input_csv,
        df=df,
        work=work,
        primary_horizon=args.primary_horizon,
        roll=args.roll,
        vwap_window=args.vwap_window,
        cost_pips=args.cost_pips,
        condition_summary=condition_summary,
        baseline_summary=baseline_summary,
        horizon_summary=horizon_summary,
        annual_summary=annual_summary,
    )

    print(condition_summary[["condition", "direction", "n", "rebound_probability_%", "mean_net_return_bps"]])
    print(f"Analysis period: {work['datetime'].min()} to {work['datetime'].max()}")
    print(f"Saved files to: {output_dir}")


if __name__ == "__main__":
    main()
