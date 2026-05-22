# lab_4: USDJPY 60-Minute Backtest Overfitting and Simplified PBO

Japanese: [README.ja.md](README.ja.md)

This lab demonstrates how to inspect backtest overfitting risk in the AI-assisted quant research era using real USDJPY 60-minute data.

This lab supports the Qiita article "[AI Makes Edge Discovery Easy, But Is That Backtest Real? How to Check Backtest Overfitting with PBO](https://qiita.com/tikeda123/items/fd589372f78ffa4c48fb)". The Japanese article is "[AIでエッジ探しが簡単になった時代に、そのバックテストは本物か？PBOで過学習を確認する](https://qiita.com/tikeda123/items/ab7070663e8e002e785f)".

The article's purpose is to explain that when AI and Python make it easy to test many trading rules, the best-looking backtest should not be accepted at face value. The selection process itself must be checked: does the strategy selected in-sample remain competitive out-of-sample?

This is not a production trading strategy. It is an educational experiment using 144 moving-average crossover candidates, CSCV-style splits, and a simplified PBO measure to observe how much the selection process may depend on historical data.

## Learning Log and Feedback

This lab is also part of a public learning log for learning how to question attractive backtests. The experiment artifacts are shared to make the selection process, assumptions, and limitations visible rather than to claim that a selected strategy is robust.

Corrections, reproducibility checks, objections to the simplified PBO design, and alternative ways to interpret the results are welcome when they are grounded in the shared outputs, script logic, or linked article.

## Experiment Role

The lab analyzes USDJPY 60-minute data in this order:

1. Extract the USDJPY 60-minute OHLC period from 2020 through the end of 2025.
2. Build 144 strategy candidates from short MA, long MA, ATR stop-loss, and ATR take-profit settings.
3. Generate returns assuming signal confirmation at close and execution at the next bar open.
4. Subtract a 1.0 pip round-trip transaction cost.
5. Summarize full-sample Sharpe, cumulative return, max drawdown, and trade count for each candidate.
6. Split the return matrix into 8 blocks and evaluate all 70 combinations of 4 IS blocks and 4 OOS blocks.
7. Select the best strategy by IS Sharpe in each combination and evaluate its OOS rank and OOS return.
8. Count how often the IS-best strategy falls to the median-or-worse OOS rank as simplified PBO.
9. Generate article-ready CSV, Markdown, PNG figures, Excel summary, and submission zip.

Canonical article artifacts are `candidate_summary.csv`, `pbo_results.csv`, `results_summary.json`, `experiment_report.md`, `figures/`, and `experiment_summary.xlsx`. Use `backtest_overfitting_submission.zip` for submission or redistribution.

## Input Data

Reproduction requires a headerless, tab-separated USDJPY 60-minute OHLCV file.

| File | Pair | Format |
|---|---|---|
| `USDJPY60(29).csv` | USDJPY | `timestamp, open, high, low, close, volume` |

Data-quality values recorded in the current canonical output:

| Item | Value |
|---|---:|
| Input rows | 100,000 |
| Input start | `2010-03-18 18:00` |
| Input end | `2026-04-02 12:00` |
| Experiment rows | 37,430 |
| Experiment start | `2020-01-01 22:00` |
| Experiment end | `2025-12-31 21:00` |
| Duplicate timestamps | 0 |
| Non-monotonic steps | 0 |
| Invalid OHLC rows | 0 |
| Gaps over 1 hour | 318 |

Forex weekend and holiday gaps are counted as gaps. No interpolation is applied.

The source `USDJPY60(29).csv` used for the canonical run is not stored directly under `lab_4`. To reproduce the experiment, prepare the same-format CSV and pass it with `--input`.

## Environment

The main script runs with Python 3. Required external packages are `numpy` and `matplotlib`.

| Item | Role |
|---|---|
| Python | Script execution |
| numpy | Return matrix, Sharpe, and CSCV calculations |
| matplotlib | Article PNG figure generation |
| artifact_tool | Excel summary and preview PNG generation |

Standard reproduction with `run_backtest_overfitting_experiment.py` regenerates CSV, JSON, Markdown, and PNG outputs. Regenerating the Excel summary requires the `artifact_tool` environment used for this submission.

## Reproduction

From the repository root:

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir lab_4/backtest_overfitting_submission
```

From `lab_4`:

```bash
cd lab_4
python run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir ./backtest_overfitting_submission
```

When experimenting, write to a temporary directory.

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_check
```

To skip figure generation:

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_no_plots \
  --no-plots
```

Successful execution prints JSON containing the output directory, row count, number of strategies, PBO, OOS loss probability, and best full-sample strategy.

## Tool Usage

Check available arguments:

```bash
python lab_4/run_backtest_overfitting_experiment.py --help
```

Key arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--input` | `/mnt/data/USDJPY60(29).csv` | Input USDJPY 60-minute CSV |
| `--outdir` | `/mnt/data/backtest_overfitting_submission` | Output path for CSV, JSON, Markdown, and figures |
| `--start` | `2020-01-01 00:00` | Inclusive experiment start timestamp |
| `--end-exclusive` | `2026-01-01 00:00` | Exclusive experiment end timestamp |
| `--no-plots` | off | Skip PNG figure generation |

Inspect the report and JSON first:

```bash
sed -n '1,140p' lab_4/experiment_report.md
python -m json.tool lab_4/results_summary.json
```

Inspect strategy candidates and CSCV details:

```bash
column -s, -t < lab_4/candidate_summary.csv | sed -n '1,15p'
column -s, -t < lab_4/pbo_results.csv | sed -n '1,15p'
```

Read key KPIs from Python:

```bash
python - <<'PY'
import json

summary = json.load(open("lab_4/results_summary.json", encoding="utf-8"))
print("PBO:", summary["pbo_median_or_worse_rate"])
print("OOS loss probability:", summary["oos_loss_probability"])
print("Best:", summary["full_sample_best_strategy"])
PY
```

## Script Behavior

The main script:

- loads tab-separated OHLCV data and checks timestamps, OHLC consistency, gaps, and duplicates;
- uses rows with `--start <= timestamp < --end-exclusive`;
- computes ATR(14) for SL/TP and uses only ATR available before entry;
- creates long/short signals from short MAs `5, 10, 20, 30` and long MAs `50, 100, 150, 200`;
- combines SL options `none, ATR 1.0, ATR 1.5` and TP options `none, ATR 1.5, ATR 2.0`;
- confirms signals on the previous close and executes at the next open;
- subtracts half of the 1.0 pip round-trip cost on entry and exit;
- allows only one position at a time and reverses after closing the current position;
- prioritizes stop-loss if both SL and TP are touched in the same bar;
- stores each candidate's bar returns as a T x N return matrix;
- evaluates all 70 combinations of 4 IS blocks from 8 total blocks.

Simplified PBO is defined as:

```text
Simplified PBO = rate at which the IS-Sharpe-best strategy falls to median-or-worse OOS rank
```

With 144 candidates, OOS ranks 73 through 144 are counted as median-or-worse.

## Key Outputs

| File | Content |
|---|---|
| `candidate_summary.csv` | Full-sample evaluation for 144 strategy candidates |
| `pbo_results.csv` | 70 IS/OOS CSCV-style combinations |
| `pnl_matrix.csv.gz` | T x N return matrix as gzip-compressed CSV |
| `best_strategy_timeseries.csv` | Time series for the full-sample Sharpe-best strategy |
| `results_summary.json` | Conditions, data quality, and key KPIs |
| `experiment_report.md` | Short Markdown report for submission and article checking |
| `experiment_summary.xlsx` | Excel summary with KPIs, candidates, PBO results, and data quality |
| `experiment_summary_preview.png` | Preview image of the Excel summary |
| `backtest_overfitting_submission.zip` | Submission artifact bundle |
| `run_backtest_overfitting_experiment.py` | Reproduction script |
| `create_summary_workbook.py` | Excel summary generation script |
| `backtest_overfitting_experiment_outline.md` | Experiment outline for the real-data PBO article |
| `ai_edge_backtest_overfitting_outline.md` | Article outline about AI-era overfitting risk |

`figures/` contains article figures.

| Figure | Content |
|---|---|
| `fig1_sharpe_distribution.png` | Full-sample Sharpe distribution across 144 candidates |
| `fig2_is_vs_oos_sharpe.png` | IS Sharpe vs OOS Sharpe for selected strategies |
| `fig3_oos_rank_distribution.png` | OOS rank distribution of IS-best strategies |
| `fig4_simplified_pbo.png` | Simplified PBO ratio |
| `fig5_oos_loss_probability.png` | OOS loss probability |
| `fig6_best_strategy_equity_curve.png` | Equity curve of the full-sample Sharpe-best strategy |

## Key Results

The current canonical output uses 144 strategy candidates and 70 CSCV-style combinations.

| Metric | Result |
|---|---:|
| Simplified PBO | `5.71%` |
| OOS loss probability | `35.71%` |
| Mean selected IS Sharpe | `0.7474` |
| Mean selected OOS Sharpe | `0.1187` |
| Mean selected OOS rank | `32.43 / 144` |
| Median selected OOS rank | `30.0 / 144` |

Top five full-sample Sharpe strategies:

| rank | strategy_id | Sharpe | CumReturn | MaxDD | Trades | WinRate |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `ma_s20_l50_sl_none_tp_none` | `0.5717` | `35.45%` | `-10.13%` | 786 | `38.17%` |
| 2 | `ma_s20_l50_sl_atr1_5_tp_none` | `0.5396` | `31.93%` | `-10.25%` | 1659 | `30.08%` |
| 3 | `ma_s10_l50_sl_atr1_5_tp_none` | `0.5088` | `29.41%` | `-11.27%` | 1715 | `29.15%` |
| 4 | `ma_s10_l50_sl_none_tp_none` | `0.4990` | `29.87%` | `-17.23%` | 938 | `34.97%` |
| 5 | `ma_s10_l50_sl_atr1_0_tp_none` | `0.4543` | `25.32%` | `-12.27%` | 2271 | `24.39%` |

Simplified PBO is low for this candidate set, period, and split method. However, selected OOS Sharpe is much lower than selected IS Sharpe, and 35.71% of the combinations have negative selected OOS cumulative return.

## Caveats

This result does not prove that moving-average crossover strategies will remain profitable.

- Simplified PBO depends on the candidate set and split design.
- Low PBO does not remove the need to inspect OOS Sharpe decay and OOS loss probability.
- The test is limited to USDJPY 60-minute data from 2020 through the end of 2025.
- A 2026+ holdout and independent data-source check have not been performed.
- Slippage, execution rejection, liquidity stress, and gap execution are simplified.
- The result may change under a different search space.
- Optimizing directly for lower PBO can itself become another form of overfitting.

Treat this lab as a way to inspect selection risk and IS/OOS degradation, not as a method for selecting the "best" backtest.

## Article Mapping

Published articles:

- English: [AI Makes Edge Discovery Easy, But Is That Backtest Real? How to Check Backtest Overfitting with PBO](https://qiita.com/tikeda123/items/fd589372f78ffa4c48fb)
- Japanese: [AIでエッジ探しが簡単になった時代に、そのバックテストは本物か？PBOで過学習を確認する](https://qiita.com/tikeda123/items/ab7070663e8e002e785f)

Article outlines are:

- `ai_edge_backtest_overfitting_outline.md`
- `backtest_overfitting_experiment_outline.md`

Core article message:

```text
In the AI era, generating many edge candidates is easy.
But the more candidates you test, the easier it becomes to find something that only fits historical noise.

The important question is not whether the best backtest looks good.
It is how many candidates were tried, whether the IS-selected strategy survives OOS,
and what the OOS rank, OOS loss probability, and PBO say about selection risk.
```

For article numbers, verify `results_summary.json` and `experiment_report.md` first. Use `candidate_summary.csv` for candidate details, `pbo_results.csv` for CSCV combinations, and `figures/` for visual evidence.

The conclusion is not "PBO is low, therefore this strategy can be used." The accurate conclusion is: to discuss backtest overfitting, one must inspect the candidate set, IS/OOS split, selected OOS rank, and loss probability instead of quoting only the best backtest.
