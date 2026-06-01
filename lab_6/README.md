# lab_6: BTC/ETH/SOL Crypto Crash-Rebound Diagnostics

Japanese: [README.ja.md](README.ja.md)

This lab supports the Japanese Qiita article "[仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a)", the BTC/ETH/SOL crypto quant article work in `BTC_ETH_SOL_crypto_quant_article_plan.docx.md`, and the experiment plan in `crypto_crash_rebound_experiment_plan.md`. The central question is whether buying after a sharp crypto crash is actually supported by data, or whether some crashes are falling-knife conditions that should be avoided.

The lab is not trying to publish a finished trading strategy. It is an article-evidence package for separating:

- crashes that may be rebound candidates;
- crashes that require waiting;
- crashes that should not be bought without more market-structure evidence.

This is not investment advice and does not define a deployable trading system. The experiment is an educational diagnostic package for article evidence.

## Learning Log and Feedback

This lab is part of a public learning log for converting crypto market narratives into reproducible checks. The scripts, CSV outputs, Markdown reports, figures, and article-material bundle are shared so the assumptions and limits can be inspected.

Corrections, reproducibility checks, objections to the experiment design, and alternative interpretations are welcome when they are grounded in the shared scripts, outputs, or article draft files.

## Experiment Role

The lab analyzes BTCUSDT, ETHUSDT, and SOLUSDT 240-minute bars in this order:

1. Load local tab-separated BTC/ETH/SOL 4H OHLCV CSV files.
2. Audit missing timestamps, OHLCV parse failures, duplicate timestamps, invalid OHLC rows, and timestamp gaps.
3. Use the common period `2020-08-11 04:00` to `2026-05-29 12:00`.
4. Compare 4H log-return distribution moments, skewness, kurtosis, and tail events.
5. Run event studies after lower-tail crashes and upper-tail rallies across 4H, 8H, 12H, 24H, 48H, and 72H horizons.
6. Split lower-tail crash rebounds by 20-bar realized-volatility quintile.
7. Replace same-close event-study assumptions with next-4H-open long entries and fixed-time exits.
8. Measure MAE, MFE, Profit Factor, drawdown, and a simple non-overlapping event backtest.
9. Check annual stability across 2020 through partial 2026.
10. Add Binance USD-M Funding Rate regimes to separate long-overheated crashes from low-or-negative-funding crashes.
11. Add Open Interest and liquidation diagnostics where the public API data is available.
12. Package article-writing materials into `outputs/article_materials/`.

The key interpretation is that crash-rebound candidates exist in the price data, especially in high-volatility regimes, but the same candidates carry large path risk. The lab therefore treats Funding Rate, Open Interest, liquidation availability, MAE/MFE, and annual stability as necessary context rather than optional decorations.

## Main Files

| File | Content |
|---|---|
| `run_crypto_crash_rebound_experiment.py` | Main experiment runner for Phase 0 through Phase 7 |
| `BTCUSDT240.csv` | BTCUSDT 240-minute OHLCV input |
| `ETHUSDT240.csv` | ETHUSDT 240-minute OHLCV input |
| `SOLUSDT240.csv` | SOLUSDT 240-minute OHLCV input |
| `BTC_ETH_SOL_crypto_quant_article_plan.docx.md` | Article plan and narrative outline |
| `crypto_crash_rebound_experiment_plan.md` | Phase-based experiment plan |
| `outputs/crypto_crash_rebound_ohlcv/` | Canonical generated CSV, Markdown, and PNG outputs |
| `outputs/article_materials/` | Article-writing package with planning files, source data, reports, tables, event tables, and numbered figures |
| `README.md` | English lab documentation |
| `README.ja.md` | Japanese lab documentation |

## Input Data

The current lab includes the input CSV files.

| File | Symbol | Timeframe | Format |
|---|---|---|---|
| `BTCUSDT240.csv` | BTCUSDT | 240-minute | Headerless, tab-separated `timestamp, open, high, low, close, volume` |
| `ETHUSDT240.csv` | ETHUSDT | 240-minute | Headerless, tab-separated `timestamp, open, high, low, close, volume` |
| `SOLUSDT240.csv` | SOLUSDT | 240-minute | Headerless, tab-separated `timestamp, open, high, low, close, volume` |

Current data audit values from `outputs/crypto_crash_rebound_ohlcv/data_profile.csv`:

| Symbol | Raw rows | Clean rows | First timestamp | Last timestamp | Common rows | Common missing rows | Gap breaks | Status |
|---|---:|---:|---|---|---:|---:|---:|---|
| BTCUSDT | 19,227 | 19,227 | `2017-08-17 04:00` | `2026-05-29 12:00` | 12,704 | 1 | 10 | WARN |
| ETHUSDT | 19,227 | 19,227 | `2017-08-17 04:00` | `2026-05-29 12:00` | 12,704 | 1 | 10 | WARN |
| SOLUSDT | 12,704 | 12,704 | `2020-08-11 04:00` | `2026-05-29 12:00` | 12,704 | 1 | 1 | WARN |

The common cross-symbol analysis period is `2020-08-11 04:00` to `2026-05-29 12:00`. Returns crossing non-4H timestamp gaps are excluded from return statistics and forward-return calculations.

## Environment

The main script runs with Python 3 and uses these external packages:

| Package | Role |
|---|---|
| pandas | CSV loading, event tables, summaries |
| numpy | Return calculations and metrics |
| matplotlib | PNG figure generation |

The script also uses Python standard-library HTTP tools to fetch Binance Funding Rate, Open Interest, and liquidation endpoint data when refresh flags are used.

## Reproduction

From the repository root, regenerate the full current Phase 0 through Phase 7 output:

```bash
python lab_6/run_crypto_crash_rebound_experiment.py
```

To avoid overwriting the canonical output, write to a temporary directory:

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --output-dir /tmp/lab6_crypto_crash_rebound_check
```

Run only through a specific phase:

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --phase phase5 \
  --output-dir /tmp/lab6_phase5_check
```

Refresh cached Funding Rate or Open Interest source data when needed:

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --refresh-funding \
  --refresh-open-interest \
  --output-dir /tmp/lab6_refresh_check
```

## Tool Usage

Check available arguments:

```bash
python lab_6/run_crypto_crash_rebound_experiment.py --help
```

Important arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--data-dir` | `lab_6/` | Directory containing `BTCUSDT240.csv`, `ETHUSDT240.csv`, and `SOLUSDT240.csv` |
| `--output-dir` | `lab_6/outputs/crypto_crash_rebound_ohlcv` | Generated CSV, Markdown, and PNG output directory |
| `--phase` | `phase7` | Run `phase0` through `phase7`; later phases refresh earlier outputs |
| `--refresh-funding` | off | Fetch Binance Funding Rate history even when a cached CSV exists |
| `--refresh-open-interest` | off | Fetch Binance Open Interest history even when a cached CSV exists |
| `--dpi` | `180` | Figure DPI |

## Script Behavior

The main script:

- reads headerless tab-separated OHLCV files and sorts by timestamp;
- drops rows with missing timestamp or OHLC values;
- removes duplicate timestamps, keeping the last row;
- checks invalid OHLC rows and timestamp gaps;
- uses log returns, `log(close_t / close_{t-1}) * 100`;
- excludes returns and future returns that cross non-4H timestamp gaps;
- defines shock thresholds from each symbol's own full-period return distribution;
- evaluates lower and upper tail events at 5%, 2.5%, and 1% levels;
- evaluates 4H, 8H, 12H, 24H, 48H, and 72H horizons;
- uses 20-bar realized volatility quintiles for volatility-regime analysis;
- checks next-4H-open entries after crash signals, fixed-time exits, MAE, MFE, Profit Factor, and drawdown;
- builds annual stability summaries for 2020 through partial 2026;
- fetches or reuses Binance USD-M Funding Rate and Open Interest histories for Phase 6 and Phase 7;
- records liquidation endpoint unavailability as a data limitation instead of fabricating missing results.

## Key Outputs

Main outputs under `outputs/crypto_crash_rebound_ohlcv/`:

| File | Content |
|---|---|
| `article_experiment_summary.md` | Overall generated experiment summary |
| `data_profile.csv` | Input data quality and common-period audit |
| `timestamp_gap_events.csv` | Timestamp gap evidence |
| `moment_summary.csv` | 4H return moments by symbol |
| `direction_return_summary.csv` | Future returns after up and down bars |
| `shock_mean_reversion_summary.csv` | Tail-shock mean-reversion event study |
| `phase2_candidate_summary.csv` | Phase 2 article candidate conditions |
| `vol_regime_summary.csv` | Volatility-regime profile |
| `shock_mean_reversion_by_vol_summary.csv` | Tail-shock results by volatility regime |
| `phase3_lower5_by_vol_candidate_summary.csv` | Phase 3 Q5 crash-rebound candidates |
| `phase4_candidate_table.csv` | Next-open entry candidate definitions |
| `path_risk_summary.csv` | MAE, MFE, and path-risk summary |
| `simple_backtest_summary.csv` | Non-overlapping event-backtest summary |
| `annual_condition_summary.csv` | Annual condition-level summary |
| `annual_stability_summary.csv` | Annual stability metrics |
| `funding_profile.csv` | Funding Rate coverage and distribution |
| `shock_mr_by_funding_summary.csv` | Crash rebound by Funding regime |
| `oi_profile.csv` | Open Interest coverage and limitations |
| `shock_mr_by_oi_summary.csv` | Crash rebound by OI regime |
| `liquidation_profile.csv` | Liquidation endpoint availability |

Article material bundle:

| Path | Content |
|---|---|
| `outputs/article_materials/README.md` | Article-material package guide |
| `outputs/article_materials/planning/` | Plans and reproduction script |
| `outputs/article_materials/source_data/` | OHLCV, Funding Rate, and Open Interest source data |
| `outputs/article_materials/reports/` | Phase 1 through Phase 7 reports |
| `outputs/article_materials/tables/` | Article-facing summary CSVs |
| `outputs/article_materials/event_tables/` | Event-level CSVs |
| `outputs/article_materials/figures/` | Numbered article figures |
| `outputs/article_materials/figure_index.csv` | Numbered figure metadata |
| `outputs/article_materials/table_index.csv` | Table metadata |
| `outputs/article_materials/report_index.csv` | Report metadata |
| `outputs/article_materials/source_data_index.csv` | Source-data metadata |

## Article Figures

`outputs/article_materials/figures/` contains 15 numbered figures:

| Figure | Content |
|---|---|
| 1-4 | Moment, extreme return, distribution histogram, and QQ diagnostics |
| 5-6 | Directional future returns and shock mean reversion by horizon |
| 7-8 | Volatility-regime context and lower-5% crash rebound by volatility |
| 9-11 | Next-open path risk, simple equity curve, and drawdown curve |
| 12 | Annual condition summary |
| 13 | Funding-regime crash rebound |
| 14 | Open Interest-regime crash rebound |
| 15 | Liquidation-data availability and limitation summary |

## Key Results

Lower 5% crash long candidates from the close-based Phase 2 event study:

| Symbol | Lower 5% threshold | Best horizon | Count | Mean MR | Median MR | Win rate | t-stat |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | `-1.8988%` | 48H | 636 | `+0.4943%` | `+0.4808%` | `55.66%` | `2.23` |
| ETHUSDT | `-2.5347%` | 24H | 636 | `+0.3453%` | `+0.5708%` | `55.66%` | `1.51` |
| SOLUSDT | `-3.7213%` | 72H | 636 | `+2.5185%` | `+2.7538%` | `61.48%` | `4.32` |

Q5 high-volatility lower-5% crash long candidates from Phase 3:

| Symbol | Q5 best horizon | Count | Mean MR | Median MR | Win rate | t-stat |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 48H | 324 | `+1.0495%` | `+0.9602%` | `57.72%` | `2.98` |
| ETHUSDT | 72H | 340 | `+0.9078%` | `+1.5715%` | `58.24%` | `1.63` |
| SOLUSDT | 72H | 336 | `+4.3539%` | `+4.0895%` | `66.67%` | `4.91` |

Next-open entry and path-risk results from Phase 4:

| Candidate | Events | Exit | Mean return | Win rate | PF | Mean MAE | Worst MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTC all 48H | 636 | 48H | `+0.4964%` | `55.97%` | `1.27` | `-5.1126%` | `-36.8271%` |
| ETH all 24H | 636 | 24H | `+0.3431%` | `55.66%` | `1.18` | `-5.5627%` | `-57.2095%` |
| SOL all 72H | 636 | 72H | `+2.5201%` | `61.48%` | `1.62` | `-11.6441%` | `-96.9345%` |
| BTC Q5 48H | 324 | 48H | `+1.0497%` | `58.02%` | `1.54` | `-6.0026%` | `-36.8271%` |
| ETH Q5 72H | 340 | 72H | `+0.9026%` | `58.24%` | `1.26` | `-10.5276%` | `-65.4687%` |
| SOL Q5 72H | 336 | 72H | `+4.3491%` | `66.37%` | `2.07` | `-13.6506%` | `-87.3176%` |

Non-overlapping Phase 4 event-backtest highlights:

| Candidate | Accepted events | Mean return | Win rate | PF | Mean MAE | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| BTC Q5 48H | 149 | `+0.7693%` | `56.38%` | `1.39` | `-5.3196%` | `-39.2781%` |
| ETH Q5 72H | 120 | `+0.3897%` | `52.50%` | `1.12` | `-8.6000%` | `-65.7119%` |
| SOL Q5 72H | 113 | `+4.5583%` | `69.03%` | `2.40` | `-12.2134%` | `-59.9710%` |

Funding Rate extension highlights:

| Symbol | Best funding regime | Horizon | Count | Gross MR | Funding-adjusted MR | Adjusted win rate | Adjusted t-stat |
|---|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | `funding_low_or_negative` | 24H | 112 | `+1.3283%` | `+1.3361%` | `64.29%` | `3.13` |
| ETHUSDT | `funding_low_or_negative` | 24H | 146 | `+0.8810%` | `+0.8962%` | `56.85%` | `1.88` |
| SOLUSDT | `funding_low_or_negative` | 72H | 159 | `+2.9243%` | `+4.4465%` | `67.30%` | `4.04` |

## Interpretation Boundary

The lab does not prove that all crypto crashes should be bought.

- Phase 2 shows close-based crash-rebound candidates, but it uses full-period exploratory thresholds.
- Phase 3 shows that the strongest rebound candidates are concentrated in high-volatility regimes.
- Phase 4 shows that next-open entries can preserve some average rebound, but MAE and drawdown are large.
- SOL Q5 72H is the strongest candidate numerically, but it also has severe path risk.
- ETH is weaker once overlapping signals are removed.
- BTC Q5 48H is less spectacular than SOL but has a more moderate risk profile in this sample.
- Phase 5 shows annual variation; partial 2020 and partial 2026 should not be overused.
- Phase 6 Funding Rate results use Binance USD-M futures data; if OHLCV is spot-derived, the market-source mismatch must be disclosed.
- Phase 7 Open Interest covers only a recent rolling window from the API, so it is a limitation and next-step section, not a full-period conclusion.
- Liquidation history was unavailable from the attempted public endpoint, and the lab records that limitation directly.

For article writing, the safest conclusion is:

```text
Price data alone shows crash-rebound candidates in BTC, ETH, and SOL,
especially after high-volatility lower-tail crashes. But the candidates are
not safe dip-buying rules. They come with large MAE, drawdown, annual variation,
and market-structure ambiguity. Funding Rate, Open Interest, liquidation data,
and execution-aware risk controls are needed before separating buyable crashes
from falling-knife crashes.
```

## Article Mapping

Current article and planning files:

| File | Role |
|---|---|
| [仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a) | Published Japanese Qiita article |
| `BTC_ETH_SOL_crypto_quant_article_plan.docx.md` | Article plan and narrative outline |
| `crypto_crash_rebound_experiment_plan.md` | Phase-based experiment plan |
| `outputs/article_materials/README.md` | Guide to the article-writing material bundle |
| `outputs/article_materials/report_index.csv` | Report index |
| `outputs/article_materials/table_index.csv` | Table index |
| `outputs/article_materials/figure_index.csv` | Figure index |

The article's core message should stay close to this boundary:

```text
Crypto crash rebounds can be measured, and some high-volatility crash regimes
show positive mean reversion. But "it crashed, therefore buy" is too crude.
The useful question is which crashes are likely post-liquidation rebounds and
which are still part of leverage unwinds.
```
