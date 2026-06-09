# lab_8: Monte Carlo Test for BTC Crash-Filter Candidates

日本語: [README.ja.md](README.ja.md)

This lab implements the experiment described in `実験設計ドキュメント.pdf`. It stress-tests the BTC crash-filter candidate from lab_7, especially the `BTC crash x low Funding x external risk-on` condition, with Monte Carlo drawdown, survival, leverage, and cost diagnostics.

This is an educational article experiment, not investment advice or a production trading system.

## Self-Contained Layout

The lab_8 experiment is self-contained in this directory.

| Type | Path |
|---|---|
| Experiment design | `実験設計ドキュメント.pdf` |
| Input data | `data/` |
| Experiment script | `run_monte_carlo_experiment.py` |
| Dependency note | `requirements.txt` |
| Canonical outputs | `outputs/monte_carlo/` |

The script does not import code from other `lab_xxx` directories and reads only `lab_8/data/`.

## Groups

| ID | Group | Condition |
|---|---|---|
| G0 | `G0_all_crashes` | All BTC crash events with Funding data |
| G1 | `G1_funding_low` | Low or negative Funding |
| G2 | `G2_risk_on` | Nasdaq 5-day return is positive |
| G3 | `G3_funding_low_x_risk_on` | Low Funding x risk-on |
| G4 | `G4_avoid_high_funding_risk_off` | All crashes excluding high-Funding x risk-off |
| G5 | `G5_high_funding_x_risk_off` | High Funding x risk-off |

## Monte Carlo Methods

| Method | Meaning |
|---|---|
| `original_order` | Historical order equity curve |
| `shuffle` | Same trades, shuffled without replacement |
| `iid_bootstrap` | Trades sampled with replacement |
| `block_bootstrap` | Fixed-length block resampling |
| `stationary_bootstrap` | Random-length block resampling |
| `regime_aware_bootstrap` | Resampling within year/risk/Funding regime labels |

## Inputs

| File | Description |
|---|---|
| `data/BTCUSD240.csv` | BTC 240-minute OHLCV |
| `data/USATECHIDXUSD240.csv` | Nasdaq 240-minute OHLCV |
| `data/USA500IDXUSD240.csv` | S&P 500 240-minute OHLCV |
| `data/USA30IDXUSD240.csv` | Dow 240-minute OHLCV |
| `data/DEUIDXEUR240.csv` | DAX 240-minute OHLCV |
| `data/funding_rate_history.csv` | Funding Rate history. The script uses BTCUSDT only |

## Environment

Required packages:

```text
numpy
pandas
```

This implementation does not generate PNG charts, so `matplotlib` is not required.

## Reproduce

From the repository root:

```bash
python3 lab_8/run_monte_carlo_experiment.py
```

With a custom simulation count:

```bash
python3 lab_8/run_monte_carlo_experiment.py --n-sims 10000 --seed 20260609
```

## Outputs

| File | Description |
|---|---|
| `outputs/monte_carlo/data_profile.csv` | Input data profile |
| `outputs/monte_carlo/feature_panel.csv` | Full panel with crash, Funding, risk-on, and future-return fields |
| `outputs/monte_carlo/trade_events.csv` | Cooldown-filtered crash events with Funding coverage |
| `outputs/monte_carlo/original_trade_metrics.csv` | Historical-order trade metrics |
| `outputs/monte_carlo/monte_carlo_summary.csv` | Main Monte Carlo summaries |
| `outputs/monte_carlo/experiment1_group_comparison.csv` | All crashes vs conditional filters |
| `outputs/monte_carlo/experiment2_small_sample_iid.csv` | Small-sample stress for G3 |
| `outputs/monte_carlo/experiment3_horizon_tradeoff.csv` | 24h candidate vs 48h risk-on |
| `outputs/monte_carlo/experiment4_avoid_filter_effect.csv` | Effect of avoiding high-Funding x risk-off crashes |
| `outputs/monte_carlo/experiment5_leverage_sensitivity.csv` | Leverage sensitivity |
| `outputs/monte_carlo/experiment6_cost_sensitivity.csv` | One-way cost sensitivity |
| `outputs/monte_carlo/figure_index.csv` | Generated SVG figure inventory |
| `outputs/monte_carlo/figures/*.svg` | Explanatory SVG charts for article use |
| `outputs/monte_carlo/monte_carlo_experiment_report.md` | Generated article report |
| `outputs/monte_carlo/analysis_report.ja.md` | Japanese analysis report aligned with the experiment objective |

## Figures

The generated report embeds these SVG figures to make the results easier to explain.

| Figure | Description |
|---|---|
| `figure01_iid_24h_final_return_q05.svg` | 24h i.i.d. bootstrap final-return 5th percentile |
| `figure02_iid_24h_mdd_q05.svg` | 24h i.i.d. bootstrap max-drawdown 5th percentile |
| `figure03_g3_method_mdd_q05.svg` | G3 drawdown stress by Monte Carlo method |
| `figure04_horizon_tradeoff_final_return_q05.svg` | 24h candidate vs 48h risk-on comparison |
| `figure05_leverage_prob_dd30.svg` | 30% drawdown hit probability by leverage |
| `figure06_cost_prob_dd30.svg` | 30% drawdown hit probability by transaction cost |

## Interpretation Notes

- `G3_funding_low_x_risk_on` has only 15 trades, so good results are not enough to claim deployability.
- Costs are one-way bps. Each trade subtracts a round-trip cost of `2 x one_way_cost_bps`.
- Leverage is applied to simple returns after cost. A single-trade loss of 100% or worse is treated as ruin.
- The Monte Carlo layer asks whether a candidate edge can survive being traded, not only whether it looked good in one historical order.
