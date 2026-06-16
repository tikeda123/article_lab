# lab_11: FX 2Y Yield-Spread Trend Filter

日本語: [README.ja.md](README.ja.md)

This lab supports the Japanese Qiita article "[FXは2年金利差でどこまで説明できるのか？ ― 水準ではなく「変化の向き」で見るトレンドフィルター](https://qiita.com/tikeda123/items/2bf3c18cbec6b4f3527a)".

It tests whether 2-year sovereign yield spreads can help explain FX price trends for EURUSD and USDJPY. The central question is not whether the spread is a standalone trading signal, but whether it can separate price trends that are supported by rate markets from price moves that deserve caution.

This is an educational quant-article experiment. It is not investment advice, not a live trading signal, and not a production trading system.

## Layout

The lab_11 outputs are stored under this directory, but regeneration depends on the local FX Nexus DuckDB database and the Ministry of Finance historical JGB CSV.

| Type | Path |
|---|---|
| Published article | [FXは2年金利差でどこまで説明できるのか？ ― 水準ではなく「変化の向き」で見るトレンドフィルター](https://qiita.com/tikeda123/items/2bf3c18cbec6b4f3527a) |
| Article base note | `article_base.md` |
| Experiment design note | `lab_base.md` |
| Experiment script | `run_yield_spread_experiment.py` |
| Canonical outputs | `outputs/yield_spread_filter/` |
| Main report | `outputs/yield_spread_filter/report/analysis_report.ja.md` |

## Data Dependencies

| Source | Use |
|---|---|
| FX Nexus `ohlcv` | EURUSD and USDJPY daily close data |
| FX Nexus `sovereign_yields` | USD and EUR 2Y sovereign yields |
| Japan Ministry of Finance historical JGB CSV | JPY 2Y yield history |
| FX Nexus `regime_features` | Trend, range, volatility, and carry-regime context |
| FX Nexus `market_distortion_features` | Pair residual and distortion context |
| FX Nexus `inefficiency_features` | Cost and candidate-status context |

The script applies a leakage guard: T-day yield features are only available from T+1 when merged with price data.

## Experiments

| Experiment | File | Question |
|---|---|---|
| Data coverage | `tables/data_coverage.csv` | Which pairs, currencies, and date ranges are usable? |
| Yield-level bucket | `tables/experiment1_yield_level_bucket.csv` | Is simply buying the higher-yielding currency enough? |
| Spread-change bucket | `tables/experiment2_spread_change_bucket.csv` | Does the direction of 2Y spread change matter more than level? |
| Price/rate alignment | `tables/experiment3_alignment_trend_follow.csv` | Does trend following improve when price and rates point the same way? |
| Divergence | `tables/experiment4_divergence_mean_reversion.csv` | Is price/rate divergence a mean-reversion or warning signal? |
| Regime robustness | `tables/experiment5_regime_robustness.csv` | Does the filter behave differently by volatility and macro regime? |
| Latest snapshot | `tables/latest_snapshot.csv` | What does the latest pair state look like? |

## Environment

Required packages:

```text
duckdb
numpy
pandas
requests
```

## Reproduce

From the repository root:

```bash
python3 lab_11/run_yield_spread_experiment.py
```

If the FX Nexus database is not in the default location, set the environment variables explicitly:

```bash
FX_NEXUS_ROOT=/path/to/fx_nexus \
FX_NEXUS_DB=/path/to/fx_nexus/var/fx_nexus.duckdb \
python3 lab_11/run_yield_spread_experiment.py
```

The current script writes directly to `lab_11/outputs/yield_spread_filter/`.

## Main Outputs

| File | Description |
|---|---|
| `outputs/yield_spread_filter/data/master_daily.csv` | Daily pair-level master table after T+1 yield-feature shift |
| `outputs/yield_spread_filter/data/experiment_sample_daily.csv` | Test sample with 5d, 10d, and 20d forward returns |
| `outputs/yield_spread_filter/data/raw/*.csv` | Raw or combined yield-spread source data saved for inspection |
| `outputs/yield_spread_filter/tables/data_coverage.csv` | Data range and row-count checks |
| `outputs/yield_spread_filter/tables/experiment1_yield_level_bucket.csv` | Yield-level bucket results |
| `outputs/yield_spread_filter/tables/experiment2_spread_change_bucket.csv` | Spread-change bucket results |
| `outputs/yield_spread_filter/tables/experiment3_alignment_trend_follow.csv` | Price/rate alignment trend-follow results |
| `outputs/yield_spread_filter/tables/experiment4_divergence_mean_reversion.csv` | Divergence and mean-reversion diagnostics |
| `outputs/yield_spread_filter/tables/experiment5_regime_robustness.csv` | Regime and volatility breakdown |
| `outputs/yield_spread_filter/figures/*.svg` | Article-facing explanatory charts |
| `outputs/yield_spread_filter/report/analysis_report.ja.md` | Japanese analysis report used as the main article evidence |
| `outputs/yield_spread_filter/experiment_metadata.json` | Data-source, period, leakage-rule, and row-count metadata |

## Key Result

The experiment supports the article's practical framing: 2Y yield spread is better treated as an environment filter than as a direct entry signal.

In the current output, spread expansion is the strongest 10-day cost-adjusted spread-change bucket for both pairs: EURUSD `spread_expanding` is +28.09 bp and USDJPY `spread_expanding` is +56.98 bp. Simple yield level is less stable: EURUSD looks best in the high-spread bucket, while USDJPY is stronger in lower and mid-low spread buckets than in the highest bucket.

For alignment, USDJPY is the clearest case. `aligned_long_base` shows +42.83 bp over 10 days and +74.09 bp over 20 days, while EURUSD shows weaker and more mixed alignment effects. Divergence should therefore be read mainly as a warning that price is harder to explain with rates, not as an automatic reversal signal.

## Interpretation Notes

- The sample starts in June 2021, so results are tied to a limited post-pandemic and rate-hiking regime.
- JPY 2Y history is supplemented from the Ministry of Finance CSV because the local FX Nexus JPY adapter did not provide the full historical range.
- The reported drawdowns are diagnostic cumulative event-return drawdowns, not live portfolio drawdowns.
- Rate/price alignment is a filter for whether a trend is easier to trust. It is not an entry rule by itself.
- Pair structure matters: USDJPY responds more cleanly to the 2Y spread filter than EURUSD in this sample.
