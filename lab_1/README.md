# lab_1: FX 240-Minute Moment Analysis Experiment

Japanese: [README.ja.md](README.ja.md)

This lab supports the Qiita article "[Quant Intro: Stop Predicting, Read the Distribution](https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf)".

The article's purpose is to inspect the shape of FX return distributions before attempting directional prediction, and to identify which currency pairs and market conditions deserve deeper conditional-return analysis. This is an edge-exploration lab, not a final trading-strategy backtest.

## Experiment Role

The lab analyzes USDJPY, EURUSD, and AUDJPY 240-minute bars in the following order:

1. Compare close-to-close log-return moments.
2. Inspect observed maximum and minimum returns.
3. Visualize return distributions.
4. Analyze future returns after up bars and down bars.
5. Analyze mean reversion after upper-tail and lower-tail shocks.
6. Analyze future returns by 20-bar volatility quintile.
7. Check annual stability and simple next-open path risk for the AUDJPY lower-tail long candidate.

The canonical article output is `moment_analysis_outputs_2022plus/`. Older broader-period outputs are not the primary evidence for the current article.

## Input Data

Input CSV files are stored directly in this directory. They are headerless, tab-separated 240-minute OHLCV files.

| File | Pair | Format |
|---|---|---|
| `USDJPY240.csv` | USDJPY | `timestamp, open, high, low, close, volume` |
| `EURUSD240.csv` | EURUSD | `timestamp, open, high, low, close, volume` |
| `AUDJPY240.csv` | AUDJPY | `timestamp, open, high, low, close, volume` |

The 2022+ article run uses only the shared period across all three pairs.

| Item | Value |
|---|---|
| Requested start date | `2022-01-01` |
| Actual analysis start | `2022-01-02 20:00:00` |
| Actual analysis end | `2026-04-02 12:00:00` |
| Timeframe | 240-minute bars |
| Pairs | USDJPY / EURUSD / AUDJPY |
| Future-return horizons | 1, 3, 6, and 12 bars |

The actual end date is determined by the common data range across the three pairs.

## Environment

This lab runs through a standalone Python script.

| Package | Version used locally |
|---|---|
| Python | `3.11.5` |
| pandas | `2.3.2` |
| numpy | `2.3.3` |
| matplotlib | `3.10.6` |
| tabulate | `0.9.0` |

`tabulate` is used for Markdown table output. Figures are saved with matplotlib's non-GUI backend.

## Reproduction

From `lab_1`, regenerate the canonical 2022+ article outputs with:

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir moment_analysis_outputs_2022plus \
  --start-date 2022-01-01 \
  --dpi 180
```

The defaults are already aligned with the 2022+ output, so this is usually equivalent:

```bash
python run_moment_analysis_edge_experiments.py
```

For a broader legacy-style run without the start-date filter, write to a separate directory:

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir moment_analysis_outputs \
  --start-date ""
```

When experimenting, use a temporary output directory so the canonical outputs are not overwritten.

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir /tmp/lab1_moment_check \
  --start-date 2022-01-01 \
  --dpi 72
```

## Tool Usage

Check available arguments first:

```bash
python run_moment_analysis_edge_experiments.py --help
```

Key arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--data-dir` | Script directory | Directory containing `USDJPY240.csv`, `EURUSD240.csv`, and `AUDJPY240.csv` |
| `--output-dir` | `moment_analysis_outputs_2022plus` | Output path for CSV, Markdown, and PNG files |
| `--start-date` | `2022-01-01` | Analysis start date; use `""` to remove the filter |
| `--end-date` | none | Analysis end date; omitted means use the common data end |
| `--dpi` | `180` | PNG resolution |

Inspect the generated summary first:

```bash
sed -n '1,200p' moment_analysis_outputs_2022plus/article_experiment_summary.md
column -s, -t < moment_analysis_outputs_2022plus/edge_candidate_summary.csv
```

## Script Behavior

The main script:

- loads and cleans the three CSV files;
- aligns all pairs to their common time range;
- computes close-based log returns as `log(close_t / close_{t-1}) * 100`;
- computes future returns for 1, 3, 6, and 12 bars;
- classifies 20-bar volatility into five quintiles;
- summarizes mean reversion after 5%, 2.5%, and 1% upper/lower tail shocks;
- checks simple next-open path risk for AUDJPY lower-tail long candidates;
- writes CSV tables, Markdown summaries, and article figures.

Mean-reversion returns use this sign convention:

```text
Upper-tail shock short mean reversion = -future_return
Lower-tail shock long mean reversion = +future_return
```

## Key Outputs

Canonical outputs are under `moment_analysis_outputs_2022plus/`.

| File | Content |
|---|---|
| `article_experiment_summary.md` | Article-ready tabular summary |
| `experiment_conclusion_report.md` | 2022+ conclusion report |
| `data_profile.csv` | Input data range, row counts, missing and duplicate checks |
| `moment_summary.csv` | Mean, median, variance, standard deviation, skewness, excess kurtosis, min, max |
| `direction_return_summary.csv` | Future returns after up and down bars |
| `shock_mean_reversion_summary.csv` | Tail-shock mean-reversion summary |
| `shock_mean_reversion_by_vol_summary.csv` | Tail-shock mean reversion by volatility regime |
| `vol_regime_summary.csv` | Future absolute returns by volatility regime |
| `edge_candidate_summary.csv` | Article candidate summary |
| `annual_audjpy_q5_lower5_h6.csv` | Annual check for AUDJPY Q5 lower-tail long |
| `audjpy_path_risk_summary.csv` | Next-open return, MAE, and MFE summary |
| `audjpy_path_risk_events.csv` | Event-level AUDJPY path-risk rows |

`moment_analysis_outputs_2022plus/figures/` contains article figures.

## Key Results

The clearest 2022+ candidate is AUDJPY lower-tail long mean reversion.

| Candidate | Condition | Horizon | Count | Mean MR Return | Win Rate | t-stat |
|---|---|---:|---:|---:|---:|---:|
| USDJPY lower-tail long MR | lower 5% shock long | 48h | 343 | `+0.0484%` | `54.52%` | `0.85` |
| EURUSD extreme-up short MR | upper 1% shock short | 12h | 69 | `-0.0059%` | `56.52%` | `-0.12` |
| AUDJPY lower-tail long MR | lower 5% shock long | 48h | 343 | `+0.2024%` | `60.06%` | `3.18` |
| AUDJPY extreme-down long MR | lower 1% shock long | 48h | 69 | `+0.3856%` | `62.32%` | `2.25` |
| AUDJPY Q5 lower-tail long MR | Q5 volatility, lower 5% shock long | 24h | 168 | `+0.1446%` | `54.76%` | `1.66` |

The article should frame the finding as broader AUDJPY lower-tail mean reversion, not only the high-volatility subset.

## Caveats

This lab finds edge candidates; it does not define a production strategy.

- Transaction costs, slippage, and delayed execution require separate evaluation.
- Stop-loss, take-profit, time-stop, and MAE-based sizing are not finalized.
- Annual and regime stability must be checked before strategy use.
- Walk-forward optimization, holdout validation, and dry-run confirmation are still required.

## Article Mapping

Use the 2022+ output files when citing numbers in the article.

- Data and period: `data_profile.csv`
- Moment comparison: `moment_summary.csv` and `fig_01_moment_std_skew_kurtosis.png`
- Extreme returns: `moment_summary.csv` and `fig_02_extreme_returns.png`
- Return distributions: `fig_03_return_distribution_histograms.png`
- Directional returns: `direction_return_summary.csv` and `fig_04_direction_future_returns.png`
- Candidate evidence: `edge_candidate_summary.csv`, `audjpy_path_risk_summary.csv`, and `experiment_conclusion_report.md`
