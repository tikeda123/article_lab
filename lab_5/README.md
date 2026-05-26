# lab_5: USDJPY Trend-Following Edge Diagnostics

Japanese: [README.ja.md](README.ja.md)

This lab supports the Qiita article "[トレンドフォローにエッジはあるのか――「遅れて入る」戦略がなぜ生き残るのか](https://qiita.com/tikeda123/items/e599112d88c912a86125)" and its [English version](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2). The purpose is to test whether a simple moving-average crossover has a trend-following PnL structure after costs, and whether that structure survives fixed out-of-sample inspection.

The main question is not whether MA 20/80 is a production trading strategy. The lab treats it as a small, inspectable case study for asking whether trend following is supported by right-tail profits, cost tolerance, parameter-neighborhood behavior, random-direction comparison, and a fixed 2025 OOS check.

This is not investment advice and does not define a deployable trading system. The experiment is an educational diagnostic package for article evidence.

## Learning Log and Feedback

This lab is also part of a public learning log for converting trend-following ideas into reproducible checks. The code, CSV outputs, figures, and article notes are shared so that the assumptions and limitations can be inspected.

Corrections, reproducibility checks, objections to the experiment design, and alternative interpretations are welcome when they are grounded in the shared scripts, outputs, or article draft files.

## Experiment Role

The lab analyzes USDJPY 60-minute and 240-minute bars in this order:

1. Load local tab-separated USDJPY 60m and 240m OHLCV CSV files.
2. Audit missing timestamps, missing OHLC rows, duplicate timestamps, invalid OHLC rows, and market gaps.
3. Use the period `2023-01-01 <= timestamp < 2026-01-01`.
4. Treat `2023-2024` as the development and analysis period, and `2025` as the fixed OOS period.
5. Run a simple MA 20/80 crossover strategy on both timeframes.
6. Confirm the signal on the close and execute at the next bar open.
7. Use round-trip cost assumptions, with `1.0` pips as the main case.
8. Compare full-period, dev, and OOS performance.
9. Diagnose cost sensitivity, top-winning-trade dependence, random-direction comparison, parameter surfaces, entry-delay sensitivity, monthly PnL, and direction contribution.
10. Run separate direction ablations for long-only and short-suppression variants.
11. Copy the generated article figures into a numbered `article_figures/` bundle.

The key interpretation is that the 240m baseline looked strong in the full sample and in 2023-2024, but broke in the fixed 2025 OOS period. That makes the lab useful as a trend-following and backtest-skepticism exercise rather than a parameter-selection result.

## Main Files

| File | Content |
|---|---|
| `run_trend_following_experiment.py` | Main MA-cross experiment, diagnostics, CSV outputs, and figures |
| `run_trend_following_direction_ablation.py` | Long-only and short-suppression ablations |
| `save_article_figures.py` | Copies selected figures into numbered article-ready files |
| `USDJPY60.csv` | Local USDJPY 60-minute OHLCV input |
| `USDJPY240.csv` | Local USDJPY 240-minute OHLCV input |
| `trend_following_edge_article_outline_improved.md` | Improved article outline |
| `trend_following_experiment_analysis_and_discussion.md` | Japanese analysis and discussion memo |
| `trend_following_experiment_implementation_plan.md` | Implementation plan |
| `trend_following_experiment_outline_no_wfo.md` | No-WFO experiment outline |
| `README.md` | English lab documentation |
| `README.ja.md` | Japanese lab documentation |

## Input Data

The current lab includes the input CSV files.

| File | Timeframe | Format |
|---|---|---|
| `USDJPY60.csv` | 60-minute | Headerless, tab-separated `datetime, open, high, low, close, volume` |
| `USDJPY240.csv` | 240-minute | Headerless, tab-separated `datetime, open, high, low, close, volume` |

Current data audit values from `outputs/trend_following_ma_cross/data_audit.csv`:

| Timeframe | Raw rows | Clean rows | First timestamp | Last timestamp | Selected rows | Dev rows | OOS rows | Gaps |
|---|---:|---:|---|---|---:|---:|---:|---:|
| 60m | 100,000 | 100,000 | `2010-03-18 18:00` | `2026-04-02 12:00` | 18,700 | 12,474 | 6,226 | 859 |
| 240m | 25,855 | 25,855 | `2010-03-18 08:00` | `2026-04-02 12:00` | 4,835 | 3,225 | 1,610 | 854 |

Weekend and holiday market closures are counted as gaps. No interpolation is applied.

## Environment

The main scripts run with Python 3 and use these external packages:

| Package | Role |
|---|---|
| pandas | CSV loading, trade logs, summary tables |
| numpy | Metrics, random-direction comparison, array calculations |
| matplotlib | PNG figure generation |

## Reproduction

From the repository root, regenerate the main experiment outputs:

```bash
python lab_5/run_trend_following_experiment.py
```

To avoid overwriting the canonical output, write to a temporary directory:

```bash
python lab_5/run_trend_following_experiment.py \
  --output-dir /tmp/lab5_trend_following_check
```

Regenerate the direction ablation outputs:

```bash
python lab_5/run_trend_following_direction_ablation.py
```

Use a temporary output directory for checks:

```bash
python lab_5/run_trend_following_direction_ablation.py \
  --output-dir /tmp/lab5_direction_ablation_check
```

Copy generated figures into the numbered article bundle:

```bash
python lab_5/save_article_figures.py
```

## Tool Usage

Check available arguments:

```bash
python lab_5/run_trend_following_experiment.py --help
python lab_5/run_trend_following_direction_ablation.py --help
python lab_5/save_article_figures.py --help
```

Important main-experiment arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--input-60m` | `lab_5/USDJPY60.csv` | USDJPY 60-minute input CSV |
| `--input-240m` | `lab_5/USDJPY240.csv` | USDJPY 240-minute input CSV |
| `--output-dir` | `lab_5/outputs/trend_following_ma_cross` | Main output directory |
| `--start` | `2023-01-01` | Inclusive experiment start |
| `--end` | `2026-01-01` | Exclusive experiment end |
| `--dev-end` | `2025-01-01` | Dev/OOS split boundary |
| `--short-window` | `20` | Short MA window |
| `--long-window` | `80` | Long MA window |
| `--costs` | `0.0 0.8 1.0 2.0` | Round-trip cost assumptions in pips |
| `--random-runs` | `1000` | Random-direction simulations |
| `--seed` | `12345` | Random seed |
| `--stage` | `all` | Run `audit`, `baseline`, `robustness`, `oos`, or `all` |

Important direction-ablation arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--output-dir` | `lab_5/outputs/trend_following_direction_ablation` | Ablation output directory |
| `--round-trip-cost-pips` | `1.0` | Main cost assumption |
| `--slope-lookback-bars` | `20` | Lookback for falling-MA filters |
| `--regime-ma-window` | `200` | Regime MA for the MA200 short filter |

## Script Behavior

The main script:

- reads tab-separated OHLCV files and sorts by timestamp;
- drops rows with missing timestamp or OHLC values;
- removes duplicate timestamps, keeping the last row;
- checks invalid OHLC rows and market gaps;
- uses `--start <= timestamp < --end`;
- computes moving-average signals with the configured short and long windows;
- confirms the previous-bar close signal and trades at the next open;
- reverses when the target direction changes;
- subtracts the full round-trip cost from each completed trade;
- evaluates 60m and 240m using the same fixed MA 20/80 logic;
- splits results into full `2023-2025`, dev `2023-2024`, and OOS `2025`;
- creates robustness diagnostics and article figures.

The direction-ablation script keeps the same MA 20/80 base rule and changes only short exposure:

| Variant | Meaning |
|---|---|
| `baseline_long_short` | Original long/short reversal logic |
| `long_only` | Short signals become flat exits |
| `short_filter_ma80_slope` | Short entries only when MA80 is falling over 20 bars |
| `short_filter_ma200_down` | Short entries only when close is below a falling MA200 |

## Key Outputs

Main outputs under `outputs/trend_following_ma_cross/`:

| File | Content |
|---|---|
| `article_result_summary.md` | Main article-result summary |
| `data_audit.csv` | Input data quality and selected-row audit |
| `summary_metrics.csv` | Full-period metrics by timeframe and cost |
| `fixed_oos_summary.csv` | Dev/OOS split metrics by timeframe and cost |
| `direction_breakdown.csv` | Long and short contribution |
| `buy_hold_comparison.csv` | MA long/short, long-only, and always-long comparison |
| `cost_sensitivity.csv` | Cost sensitivity table |
| `top_trade_exclusion.csv` | Results after removing top winning trades |
| `top_trade_contribution.csv` | Concentration in the largest winning trades |
| `random_direction_comparison.csv` | Actual PnL location inside random-direction simulations |
| `parameter_heatmap.csv` | Parameter-surface summary |
| `parameter_heatmap_dev_oos_comparison.csv` | Dev-vs-OOS parameter comparison |
| `entry_delay_sensitivity.csv` | Extra entry-delay sensitivity |
| `monthly_pnl.csv` | Monthly PnL |
| `run_risk_summary.csv` | Losing streak and time-under-water diagnostics |
| `trade_log_60m.csv` | 60m trade log |
| `trade_log_240m.csv` | 240m trade log |

Direction-ablation outputs under `outputs/trend_following_direction_ablation/`:

| File | Content |
|---|---|
| `direction_ablation_result_summary.md` | Ablation summary |
| `direction_ablation_summary.csv` | Full-period metrics by variant |
| `direction_ablation_breakdown.csv` | Direction contribution by variant |
| `direction_ablation_trade_log.csv` | Ablation trade log |

Article figure bundle:

| File | Content |
|---|---|
| `outputs/article_figures/figure_index.md` | Numbered figure index |
| `outputs/article_figures/figure_index.csv` | Figure metadata CSV |
| `outputs/article_figures/figure01_*.png` through `figure19_*.png` | Article-ready PNG files |

## Article Figures

`outputs/article_figures/` contains 19 numbered figures:

| Figure | Content |
|---|---|
| 1 | Baseline cumulative PnL |
| 2 | Baseline drawdown curve |
| 3 | Trade PnL distribution |
| 4 | Cost sensitivity |
| 5 | Fixed-parameter dev vs OOS comparison |
| 6 | MA cross vs long-only vs always-long comparison |
| 7 | Long and short PnL contribution |
| 8 | Top winning trade exclusion |
| 9 | Random-direction comparison |
| 10-12 | Full, dev, and OOS parameter PF heatmaps |
| 13 | Dev PF vs OOS PF |
| 14 | Entry-delay sensitivity |
| 15 | Monthly PnL |
| 16-19 | Direction-ablation diagnostics |

## Key Results

Baseline MA 20/80 with 1.0 pip round-trip cost:

| Timeframe | Trades | Total PnL | Win rate | Profit Factor | MaxDD |
|---|---:|---:|---:|---:|---:|
| 60m | 292 | `-140.1 pips` | `35.27%` | `0.990` | `2067.1 pips` |
| 240m | 70 | `+1746.6 pips` | `41.43%` | `1.304` | `2120.2 pips` |

Fixed dev/OOS split with 1.0 pip cost:

| Timeframe | Dev 2023-2024 PnL | Dev PF | OOS 2025 PnL | OOS PF |
|---|---:|---:|---:|---:|
| 60m | `-235.9 pips` | `0.976` | `+75.5 pips` | `1.021` |
| 240m | `+2569.3 pips` | `1.787` | `-808.0 pips` | `0.686` |

Direction contribution with 1.0 pip cost:

| Timeframe | Period | Long PnL | Short PnL |
|---|---|---:|---:|
| 60m | full 2023-2025 | `+1215.3 pips` | `-1355.4 pips` |
| 240m | full 2023-2025 | `+2164.6 pips` | `-418.0 pips` |
| 60m | OOS 2025 | `+11.8 pips` | `+63.7 pips` |
| 240m | OOS 2025 | `-424.5 pips` | `-383.5 pips` |

Robustness diagnostics:

| Check | 60m | 240m | Reading |
|---|---:|---:|---|
| Cost 2.0 pips total PnL | `-432.1` | `+1676.6` | 240m was more cost tolerant in the full sample |
| Remove top 5% winning trades | `-3001.4` | `-352.9` | Right-tail dependence is large |
| Random-direction PnL percentile | `50.3` | `77.5` | 60m was near random; 240m was better but not decisive |
| Max time under water | `866.6 days` | `344.3 days` | Both variants require long waiting periods |

## Direction Ablation Results

Full-period direction ablations:

| Variant | 60m PnL | 60m PF | 240m PnL | 240m PF |
|---|---:|---:|---:|---:|
| `baseline_long_short` | `-140.1` | `0.990` | `+1746.6` | `1.304` |
| `long_only` | `+1215.3` | `1.181` | `+2164.6` | `2.127` |
| `short_filter_ma80_slope` | `-657.7` | `0.947` | `+2536.6` | `1.615` |
| `short_filter_ma200_down` | `+863.0` | `1.079` | `+1915.4` | `1.465` |

Fixed 2025 OOS direction ablations:

| Variant | 60m OOS PnL | 60m OOS PF | 240m OOS PnL | 240m OOS PF |
|---|---:|---:|---:|---:|
| `baseline_long_short` | `+75.5` | `1.021` | `-808.0` | `0.686` |
| `long_only` | `+11.8` | `1.006` | `-424.5` | `0.508` |
| `short_filter_ma80_slope` | `-345.1` | `0.906` | `-847.8` | `0.595` |
| `short_filter_ma200_down` | `-512.2` | `0.855` | `-245.9` | `0.827` |

These ablations diagnose whether short exposure damaged the baseline. They are not final selected strategies. Because the 2025 OOS period has already been inspected, any additional filter that improves it should be treated as post-hoc exploration until validated on a fresh holdout.

## Interpretation Boundary

The lab does not prove a permanent USDJPY trend-following edge.

- 240m looked better than 60m in the full sample, but fixed 2025 OOS failed.
- The profitable full-period 240m result depends heavily on large winning trades.
- The 60m signal was close to the random-direction baseline.
- Long-side performance was stronger than short-side performance in this sample, but that may reflect the USDJPY regime during the selected period.
- Direction filters and long-only variants are diagnostic ablations, not validated production rules.
- No WFO and no OOS re-optimization are performed in the main article experiment.
- Slippage, execution rejection, liquidity stress, and stop mechanics are simplified.

For article writing, the safest conclusion is:

```text
Trend following can show a low-win-rate, right-tail-dependent PnL structure,
especially on the 240m sample, but this lab does not establish a stable
production edge because the fixed 2025 OOS check broke the main 240m result.
```

## Article Mapping

Published articles:

| Language | Article |
|---|---|
| Japanese | [トレンドフォローにエッジはあるのか――「遅れて入る」戦略がなぜ生き残るのか](https://qiita.com/tikeda123/items/e599112d88c912a86125) |
| English | [Qiita English article](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2) |

The article draft and supporting notes are:

| File | Role |
|---|---|
| `trend_following_edge_article_outline_improved.md` | Main improved article outline |
| `trend_following_experiment_analysis_and_discussion.md` | Analysis and discussion memo |
| `trend_following_experiment_outline_no_wfo.md` | No-WFO experiment outline |
| `trend_following_experiment_implementation_plan.md` | Implementation plan |

The article's core message should stay close to this boundary:

```text
Trend following is not a high-win-rate prediction method.
It is a structure that tries to capture continuation and right-tail payoffs.
In this USDJPY experiment, the 240m sample showed that structure in development,
but the fixed 2025 OOS result failed, so the result is diagnostic rather than
proof of a durable edge.
```
