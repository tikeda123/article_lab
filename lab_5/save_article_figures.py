#!/usr/bin/env python3
"""Copy lab_5 article figures into a numbered figure set."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUTS_DIR = SCRIPT_DIR / "outputs"
DEFAULT_ARTICLE_DIR = DEFAULT_OUTPUTS_DIR / "article_figures"

ARTICLE_FIGURES = [
    {
        "number": 1,
        "filename": "figure01_equity_curve.png",
        "source": "trend_following_ma_cross/figures/equity_curve.png",
        "title": "Baseline MA 20/80 cumulative PnL",
        "caption": "Cumulative net pips for 60m and 240m MA cross strategies.",
    },
    {
        "number": 2,
        "filename": "figure02_drawdown_curve.png",
        "source": "trend_following_ma_cross/figures/drawdown_curve.png",
        "title": "Baseline drawdown curve",
        "caption": "Drawdown path for 60m and 240m baseline strategies.",
    },
    {
        "number": 3,
        "filename": "figure03_trade_pnl_histogram.png",
        "source": "trend_following_ma_cross/figures/trade_pnl_histogram.png",
        "title": "Trade PnL distribution",
        "caption": "Per-trade net pip distribution and right-tail dependence.",
    },
    {
        "number": 4,
        "filename": "figure04_cost_sensitivity.png",
        "source": "trend_following_ma_cross/figures/cost_sensitivity.png",
        "title": "Cost sensitivity",
        "caption": "Total net pips under different round-trip cost assumptions.",
    },
    {
        "number": 5,
        "filename": "figure05_fixed_oos_comparison.png",
        "source": "trend_following_ma_cross/figures/fixed_oos_comparison.png",
        "title": "Fixed-parameter dev vs OOS comparison",
        "caption": "Fixed MA 20/80 performance split into 2023-2024 dev and 2025 OOS.",
    },
    {
        "number": 6,
        "filename": "figure06_buy_hold_comparison.png",
        "source": "trend_following_ma_cross/figures/buy_hold_comparison.png",
        "title": "MA cross vs always-long comparison",
        "caption": "MA long/short, MA long-only, and always-long pips by period.",
    },
    {
        "number": 7,
        "filename": "figure07_direction_pnl_breakdown.png",
        "source": "trend_following_ma_cross/figures/direction_pnl_breakdown.png",
        "title": "Direction PnL breakdown",
        "caption": "Long and short contribution to baseline total PnL.",
    },
    {
        "number": 8,
        "filename": "figure08_top_trade_exclusion.png",
        "source": "trend_following_ma_cross/figures/top_trade_exclusion.png",
        "title": "Top winning trade exclusion",
        "caption": "Sensitivity to removing the largest winning trades.",
    },
    {
        "number": 9,
        "filename": "figure09_random_direction_comparison.png",
        "source": "trend_following_ma_cross/figures/random_direction_comparison.png",
        "title": "Random direction comparison",
        "caption": "Actual total PnL location inside the random direction distribution.",
    },
    {
        "number": 10,
        "filename": "figure10_parameter_heatmap_full.png",
        "source": "trend_following_ma_cross/figures/parameter_heatmap_pf_full_2023_2025.png",
        "title": "Full-period parameter PF heatmap",
        "caption": "Profit Factor surface for the full 2023-2025 period.",
    },
    {
        "number": 11,
        "filename": "figure11_parameter_heatmap_dev.png",
        "source": "trend_following_ma_cross/figures/parameter_heatmap_pf_dev_2023_2024.png",
        "title": "Dev-period parameter PF heatmap",
        "caption": "Profit Factor surface using only 2023-2024 dev data.",
    },
    {
        "number": 12,
        "filename": "figure12_parameter_heatmap_oos.png",
        "source": "trend_following_ma_cross/figures/parameter_heatmap_pf_oos_2025.png",
        "title": "OOS parameter PF heatmap",
        "caption": "Profit Factor surface using only 2025 OOS data.",
    },
    {
        "number": 13,
        "filename": "figure13_parameter_dev_vs_oos_pf.png",
        "source": "trend_following_ma_cross/figures/parameter_dev_vs_oos_pf.png",
        "title": "Dev PF vs OOS PF",
        "caption": "Whether parameter regions that look good in dev survive in OOS.",
    },
    {
        "number": 14,
        "filename": "figure14_entry_delay_sensitivity.png",
        "source": "trend_following_ma_cross/figures/entry_delay_sensitivity.png",
        "title": "Entry delay sensitivity",
        "caption": "Impact of adding extra entry-delay bars after signal confirmation.",
    },
    {
        "number": 15,
        "filename": "figure15_monthly_pnl.png",
        "source": "trend_following_ma_cross/figures/monthly_pnl.png",
        "title": "Monthly PnL",
        "caption": "Monthly net pips and the uneven waiting profile of trend following.",
    },
    {
        "number": 16,
        "filename": "figure16_direction_ablation_total_pnl.png",
        "source": "trend_following_direction_ablation/figures/variant_total_pnl.png",
        "title": "Direction ablation full-period PnL",
        "caption": "Full-period PnL for baseline, long-only, and short-suppression variants.",
    },
    {
        "number": 17,
        "filename": "figure17_direction_ablation_oos_60m.png",
        "source": "trend_following_direction_ablation/figures/variant_oos_60m.png",
        "title": "Direction ablation 60m OOS",
        "caption": "60m dev/OOS split for direction-control variants.",
    },
    {
        "number": 18,
        "filename": "figure18_direction_ablation_oos_240m.png",
        "source": "trend_following_direction_ablation/figures/variant_oos_240m.png",
        "title": "Direction ablation 240m OOS",
        "caption": "240m dev/OOS split for direction-control variants.",
    },
    {
        "number": 19,
        "filename": "figure19_short_side_pnl.png",
        "source": "trend_following_direction_ablation/figures/short_side_pnl.png",
        "title": "Short-side PnL by variant",
        "caption": "Short-side contribution after applying short-suppression diagnostics.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create numbered article figure files for lab_5.")
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS_DIR)
    parser.add_argument("--article-dir", type=Path, default=DEFAULT_ARTICLE_DIR)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Write the index even if some source figures are missing.",
    )
    return parser.parse_args()


def clean_article_dir(article_dir: Path) -> None:
    article_dir.mkdir(parents=True, exist_ok=True)
    for path in article_dir.glob("figure*.png"):
        path.unlink()
    for name in ["figure_index.csv", "figure_index.md"]:
        path = article_dir / name
        if path.exists():
            path.unlink()


def write_indexes(article_dir: Path, rows: list[dict[str, object]]) -> None:
    csv_path = article_dir / "figure_index.csv"
    fieldnames = ["figure", "filename", "source", "title", "caption", "status"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Article Figure Index",
        "",
        "| Figure | File | Source | Caption | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| Figure {figure} | [{filename}]({filename}) | `{source}` | {caption} | {status} |".format(
                **row
            )
        )
    lines.append("")
    (article_dir / "figure_index.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    outputs_dir = args.outputs_dir.resolve()
    article_dir = args.article_dir.resolve()

    clean_article_dir(article_dir)
    rows: list[dict[str, object]] = []
    missing: list[Path] = []

    for spec in ARTICLE_FIGURES:
        source = outputs_dir / str(spec["source"])
        destination = article_dir / str(spec["filename"])
        status = "copied"
        if source.exists():
            shutil.copy2(source, destination)
        else:
            status = "missing"
            missing.append(source)
        rows.append(
            {
                "figure": spec["number"],
                "filename": spec["filename"],
                "source": source.relative_to(outputs_dir).as_posix(),
                "title": spec["title"],
                "caption": spec["caption"],
                "status": status,
            }
        )

    write_indexes(article_dir, rows)

    if missing and not args.allow_missing:
        missing_list = "\n".join(f"- {path}" for path in missing)
        raise SystemExit(f"Missing source figures:\n{missing_list}")

    print(f"Article figures: {article_dir}")
    print(f"Copied figures: {sum(row['status'] == 'copied' for row in rows)}")
    if missing:
        print(f"Missing figures: {len(missing)}")


if __name__ == "__main__":
    main()
