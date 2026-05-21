# lab_2: Quantifying AUDJPY Overbought and Oversold Conditions

Japanese: [README.ja.md](README.ja.md)

This lab supports the Qiita article "[How Quant Traders Judge Overbought and Oversold Conditions](https://qiita.com/tikeda123/items/8dfcc1c09e34d5304d49)".

The article's purpose is to convert subjective market language such as "too low" or "too high" into measurable conditions: a 24-hour VWAP deviation Z-score and a rolling percentile of the latest 1-hour return. The lab then checks whether price actually rebounded after those conditions.

This is not a finished strategy backtest. It is an exploration phase for turning overbought and oversold ideas into testable hypotheses.

## Experiment Role

The lab uses AUDJPY 60-minute data and analyzes it in this order:

1. Compute a rolling 24-hour VWAP.
2. Measure the close's deviation from the 24-hour VWAP.
3. Convert VWAP deviation into a rolling Z-score using the past 500 bars.
4. Convert the latest 1-hour return into a rolling percentile using the past 500 bars.
5. Define oversold and overbought candidate zones from VWAP Z-score and return percentile.
6. Assume next-open entry after signal confirmation and evaluate 4-hour rebound returns.
7. Compare against unconditional long/short baselines, horizon sensitivity, annual stability, and return distributions.

The canonical article output is `article_outputs/`.

## Input Data

Input CSV is stored directly in this directory. It is a headerless, tab-separated 60-minute OHLCV file.

| File | Pair | Format |
|---|---|---|
| `AUDJPY60.csv` | AUDJPY | `timestamp, open, high, low, close, volume` |

Canonical output statistics:

| Item | Value |
|---|---:|
| Input rows | 100,000 |
| Usable rows after indicator warmup | 99,473 |
| Data start | `2010-04-12 23:00:00` |
| Data end | `2026-04-24 20:00:00` |
| Actual analysis start | `2010-05-12 17:00:00` |
| Actual analysis end | `2026-04-24 15:00:00` |
| Timeframe | 60-minute bars |
| Pair | AUDJPY |

The analysis starts later than the input because the rolling 500-bar percentile/Z-score and 24-hour VWAP need warmup. It ends earlier because next-open entry and 4-hour forward evaluation need future bars.

## Environment

This lab runs through a standalone Python script.

| Package | Version used locally |
|---|---|
| Python | `3.11.5` |
| pandas | `2.3.2` |
| numpy | `2.3.3` |
| matplotlib | `3.10.6` |
| tabulate | `0.9.0` |

`tabulate` is used for Markdown summary output. Figures are saved as PNG files.

## Reproduction

From the repository root:

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py
```

From `lab_2`:

```bash
cd lab_2
python audjpy_overbought_oversold_article_experiment.py
```

Successful execution prints the analysis period and output path.

```text
Analysis period: 2010-05-12 17:00:00 to 2026-04-24 15:00:00
Saved files to: .../lab_2/article_outputs
```

When experimenting, write to a separate output directory.

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py \
  --output-dir /tmp/lab2_overbought_oversold_check \
  --dpi 80
```

## Tool Usage

Check available arguments first:

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py --help
```

Key arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--input-csv` | `lab_2/AUDJPY60.csv` | Input AUDJPY 60-minute CSV |
| `--output-dir` | `lab_2/article_outputs` | Output path for CSV, Markdown, and PNG files |
| `--roll` | `500` | Rolling window for return percentile and VWAP Z-score |
| `--vwap-window` | `24` | Rolling window for 24-hour VWAP |
| `--primary-horizon` | `4` | Main rebound-evaluation horizon |
| `--horizons` | `1,2,4,8,12,24` | Horizons for sensitivity checks |
| `--cost-pips` | `0.8` | Round-trip cost in pips |
| `--pip-size` | `0.01` | One pip for JPY pairs |
| `--dpi` | `200` | PNG resolution |

Inspect the article summary and condition table first:

```bash
sed -n '1,180p' lab_2/article_outputs/14_article_experiment_summary.md
column -s, -t < lab_2/article_outputs/03_article_condition_summary.csv
```

## Script Behavior

The main script:

- loads `AUDJPY60.csv`, sorts timestamps, and converts OHLCV fields to numeric values;
- computes the latest 1-hour return with `close.pct_change()`;
- computes the rolling percentile of the latest return over the past 500 bars;
- computes 24-hour VWAP from typical price and volume;
- converts VWAP deviation into a rolling Z-score over the past 500 bars;
- evaluates next-open entry and specified-horizon exit;
- subtracts 0.8 pips of round-trip cost;
- evaluates oversold conditions as long rebound candidates and overbought conditions as short reversal candidates;
- writes baseline summaries, condition summaries, heatmaps, horizon sensitivity, annual stability, and return-distribution figures.

## Condition Definitions

| Condition | Direction | Definition |
|---|---|---|
| Oversold candidate | Long | `VWAP Z <= -2.0` and `return percentile <= 10` |
| Strong oversold candidate | Long | `VWAP Z <= -2.5` and `return percentile <= 5` |
| Overbought candidate | Short | `VWAP Z >= 2.0` and `return percentile >= 90` |
| Strong overbought candidate | Short | `VWAP Z >= 2.5` and `return percentile >= 95` |

These are candidate zones, not immediate production trading signals.

## Key Outputs

Canonical outputs are under `article_outputs/`.

| File | Content |
|---|---|
| `00_article_judgement_map_overbought_oversold.png` | Conceptual map of overbought and oversold definitions |
| `01_article_heatmap_contrarian_mean_bps.png` | Contrarian 4-hour mean-return heatmap |
| `02_article_heatmap_rebound_probability.png` | Rebound-probability heatmap |
| `03_article_condition_summary.csv` | Main article condition summary |
| `04_heatmap_mean_bps_matrix.csv` | Heatmap mean-return matrix |
| `05_heatmap_probability_matrix.csv` | Heatmap probability matrix |
| `06_heatmap_sample_count_matrix.csv` | Heatmap sample-count matrix |
| `07_article_condition_summary_bars.png` | Condition summary bar chart |
| `08_article_horizon_sensitivity.png` | 1/2/4/8/12/24-hour horizon comparison |
| `09_article_annual_stability.png` | Annual stability for strong conditions |
| `10_article_return_distribution_boxplot.png` | 4-hour return distribution by condition |
| `11_horizon_sensitivity_summary.csv` | Horizon sensitivity table |
| `12_annual_condition_summary.csv` | Annual condition summary |
| `13_baseline_summary.csv` | Unconditional long/short baseline |
| `14_article_experiment_summary.md` | Article-ready tabular summary |

Use `14_article_experiment_summary.md` first, then verify article numbers against `03_article_condition_summary.csv` and `13_baseline_summary.csv`.

## Key Results

The primary horizon is 4 hours after next-open entry, net of 0.8 pips round-trip cost.

| Condition | Direction | Count | Rebound Probability | Mean Return | Excess vs Baseline |
|---|---|---:|---:|---:|---:|
| Oversold candidate | Long | 1,549 | 53.32% | +1.56 bps | +2.31 bps |
| Strong oversold candidate | Long | 670 | 53.28% | +5.09 bps | +5.84 bps |
| Overbought candidate | Short | 889 | 51.74% | +3.31 bps | +4.41 bps |
| Strong overbought candidate | Short | 326 | 53.37% | +5.95 bps | +7.05 bps |

The unconditional 4-hour baselines are -0.75 bps for long and -1.10 bps for short. Both strong oversold and strong overbought conditions improve on those baselines.

## Caveats

This result does not mean the conditions are ready for live trading.

- Rebound probabilities are only slightly above 50%.
- Mean returns are positive, but left-tail losses remain meaningful.
- Some years are negative.
- Stop-loss, take-profit, maximum adverse excursion, slippage, time-of-day, and regime filters are not finalized.
- Walk-forward validation, holdout validation, and dry-run checks have not been performed.

Treat this lab as a way to quantify and observe candidate zones, not as a completed trading system.

## Article Mapping

The article's core conversion is:

```text
"Looks too low"
=> The latest return is in the bottom 10% of the past 500 bars
   and close is more than 2 standard deviations below 24-hour VWAP.
```

The same idea is used for overbought conditions. The important question is not just whether the current state is extreme, but how the return distribution changes after that state.
