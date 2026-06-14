# lab_7: BTC Crash Rebound Interaction Model

Japanese: [README.ja.md](README.ja.md)

This lab supports the Japanese Qiita article "[BTC急落は買いなのか？](https://qiita.com/tikeda123/items/c38b1dbc85d02f99c32c)", its English version "[Is a BTC Crash a "Buy"?](https://qiita.com/tikeda123/items/ef9000ba3d9fd349fadb)", the article draft in `BTC急落実験.pdf`, and the interaction-model experiment in `run_interaction_model_experiment.py`. The central question is whether BTC crashes should be treated as one uniform "buy the dip" category, or whether Funding Rate and the external risk environment can separate buyable crashes from crashes that should be avoided.

The lab does not claim that Nasdaq directly predicts BTC. Nasdaq, S&P 500, Dow, and DAX are used as context variables for judging whether a BTC crash is happening in a broader risk-on or risk-off environment.

This is not investment advice and does not define a deployable trading system. The experiment is an educational diagnostic package for article evidence.

## Learning Log and Feedback

This lab is part of a public learning log for converting crypto market narratives into reproducible checks. The scripts, CSV outputs, Markdown report, and PNG figures are shared so the assumptions and limits can be inspected.

Corrections, reproducibility checks, objections to the experiment design, and alternative interpretations are welcome when they are grounded in the shared script, outputs, or article draft.

## Experiment Role

The lab analyzes BTC 4-hour crash events in this order:

1. Load BTC, Nasdaq, S&P 500, Dow, and DAX 4H OHLCV CSV files from `data/`.
2. Build a common timestamp panel across the five markets.
3. Calculate BTC and equity-index 4H returns and 5-day returns.
4. Define BTC crash events using a rolling 180-bar sigma score.
5. Add robustness crash definitions using rolling 1.5 sigma and full-sample lower 5%.
6. Apply a 24-hour event cooldown so one crash wave is not counted repeatedly.
7. Merge BTCUSDT Funding Rate using only funding information known at the signal time.
8. Classify Funding as low, negative, low-20%, high, or unavailable.
9. Classify external risk-on by Nasdaq 5-day return, S&P 500 5-day return, and broad 3-of-4 risk-on across Nasdaq/S&P 500/Dow/DAX.
10. Evaluate next-4H-open BTC entries with 24H, 48H, and 5-day fixed exits.
11. Measure return, win rate, Profit Factor, MAE, MFE, drawdown, regression coefficients, robustness contrasts, and period stability.
12. Write the generated CSV tables, Markdown report, and figures to `outputs/interaction_model/`.

The key interpretation is that Funding Rate and external risk context can help classify BTC crashes, but the strongest article claim should be conditional filtering rather than a stable linear interaction coefficient.

## Main Files

| File | Content |
|---|---|
| `run_interaction_model_experiment.py` | Main experiment runner for the interaction-model analysis |
| [BTC急落は買いなのか？](https://qiita.com/tikeda123/items/c38b1dbc85d02f99c32c) | Published Japanese Qiita article |
| [Is a BTC Crash a "Buy"?](https://qiita.com/tikeda123/items/ef9000ba3d9fd349fadb) | Published English Qiita article |
| `BTC急落実験.pdf` | Japanese article draft and experiment outline |
| `data/BTCUSD240.csv` | BTC 240-minute OHLCV input |
| `data/USATECHIDXUSD240.csv` | Nasdaq 240-minute OHLCV input |
| `data/USA500IDXUSD240.csv` | S&P 500 240-minute OHLCV input |
| `data/USA30IDXUSD240.csv` | Dow 240-minute OHLCV input |
| `data/DEUIDXEUR240.csv` | DAX 240-minute OHLCV input |
| `data/funding_rate_history.csv` | Funding Rate history; the script filters BTCUSDT |
| `outputs/interaction_model/` | Canonical generated CSV, Markdown, and PNG outputs |
| `README.md` | English lab documentation |
| `README.ja.md` | Japanese lab documentation |

## Input Data

The current lab includes the input CSV files.

| File | Rows | First timestamp | Last timestamp | Format |
|---|---:|---|---|---|
| `data/BTCUSD240.csv` | 17,775 | `2017-05-23 00:00:00` | `2026-06-05 20:00:00` | Headerless, tab-separated `timestamp, open, high, low, close, volume` |
| `data/USATECHIDXUSD240.csv` | 19,175 | `2013-05-22 12:00:00` | `2026-06-05 20:00:00` | Headerless, tab-separated OHLCV |
| `data/USA500IDXUSD240.csv` | 19,102 | `2013-05-23 00:00:00` | `2026-06-05 20:00:00` | Headerless, tab-separated OHLCV |
| `data/USA30IDXUSD240.csv` | 19,652 | `2013-05-23 00:00:00` | `2026-06-05 20:00:00` | Headerless, tab-separated OHLCV |
| `data/DEUIDXEUR240.csv` | 19,400 | `2013-05-21 12:00:00` | `2026-06-05 16:00:00` | Headerless, tab-separated OHLCV |
| `data/funding_rate_history.csv` | 19,036 | `2020-08-11 00:00:00` | `2026-05-29 16:00:00` | CSV Funding Rate history |

Current data coverage from `outputs/interaction_model/interaction_model_report.md`:

| Item | Value |
|---|---:|
| Common 4H panel rows | 13,515 |
| Common panel first timestamp | `2017-05-23 04:00:00` |
| Common panel last timestamp | `2026-06-05 16:00:00` |
| Full-sample lower 5% BTC 4H threshold | `-2.3918%` |

Funding Rate is merged with `merge_asof` using the latest prior value within a 12-hour tolerance. Funding low/high percentile states use an expanding percentile so the current event does not use future Funding Rate distribution information.

## Environment

The main script runs with Python 3 and uses these external packages:

| Package | Role |
|---|---|
| pandas | CSV loading, panel construction, tables |
| numpy | Return calculations and metrics |
| scipy | t-tests and regression p-values |
| matplotlib | PNG figure generation |

## Reproduction

From the repository root, regenerate the current output:

```bash
python lab_7/run_interaction_model_experiment.py
```

The current script does not expose command-line arguments. It writes directly to:

```text
lab_7/outputs/interaction_model/
```

Running it overwrites the canonical generated CSV, Markdown, and PNG outputs in that directory.

## Script Behavior

The main script:

- reads headerless tab-separated OHLCV files and sorts by timestamp;
- builds an inner-joined multi-market 4H panel;
- calculates log returns for BTC and each equity index;
- defines the primary BTC crash event as `btc_sigma_score_180 <= -2.0`;
- defines robustness crash events as rolling 1.5 sigma and full-sample lower 5%;
- evaluates horizons of 24H, 48H, and 5 days using next-4H-open entry and fixed open-to-open exits;
- calculates MAE and MFE over the future holding path;
- defines primary risk-on as `Nasdaq 5-day return > 0`;
- checks robustness risk-on states using S&P 500 and broad 3-of-4 equity-index confirmation;
- defines Funding low as expanding lower 20% or negative Funding Rate;
- defines Funding high as expanding upper 20%;
- runs group statistics, simple OLS coefficients with classic standard errors, robustness contrasts, and period stability checks;
- saves the feature panel, summary tables, generated report, and figures.

## Key Outputs

Main outputs under `outputs/interaction_model/`:

| File | Content |
|---|---|
| `interaction_model_report.md` | Overall generated experiment summary |
| `interaction_feature_panel.csv` | Common multi-market feature panel with crash, risk, Funding, and future-return fields |
| `interaction_group_stats.csv` | Return, win rate, PF, MAE, MFE, and drawdown by condition group |
| `interaction_regression_coefficients.csv` | OLS coefficients for Funding, risk-on, and interaction terms |
| `interaction_contrasts.csv` | Difference-style robustness contrasts across crash definitions and risk proxies |
| `interaction_period_stability.csv` | Period stability checks for primary conditions |
| `figures/` | Generated article figures |

## Figures

`outputs/interaction_model/figures/` contains five generated figures:

| Figure | Content |
|---|---|
| `figure02_primary_48h_mean_return.png` | Primary 48H mean return by condition group |
| `figure03_four_cell_24h_mean_return.png` | Four-cell 24H mean return for Funding low/not-low and risk-on/off |
| `figure04_four_cell_48h_mean_return.png` | Four-cell 48H mean return |
| `figure05_risk_proxy_low_funding_risk_on.png` | Funding-low x risk-on mean return by risk proxy |
| `figure06_interaction_coefficients.png` | Interaction coefficients with classic standard errors |

## Key Results

Primary rolling-2-sigma BTC crash results using Nasdaq 5-day risk-on:

| Group | Horizon | Events | Mean return | Win rate | PF | Mean MAE | Worst MAE | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| all funding-covered crashes | 24H | 201 | `+0.341%` | `53.234%` | `1.260` | `-3.727%` | `-36.617%` | `-30.823%` |
| funding low only | 24H | 44 | `+1.258%` | `63.636%` | `2.528` | `-3.051%` | `-20.252%` | `-19.097%` |
| risk-on only | 24H | 88 | `+0.423%` | `54.545%` | `1.406` | `-3.418%` | `-36.617%` | `-27.800%` |
| funding low x risk-on | 24H | 15 | `+1.297%` | `66.667%` | `3.122` | `-2.651%` | `-9.426%` | `-3.470%` |
| funding high x risk-off | 24H | 26 | `-0.242%` | `42.308%` | `0.837` | `-4.330%` | `-12.258%` | `-19.250%` |
| all funding-covered crashes | 48H | 201 | `+0.603%` | `61.194%` | `1.368` | `-4.716%` | `-36.617%` | `-42.441%` |
| funding low x risk-on | 48H | 15 | `+1.115%` | `73.333%` | `2.073` | `-3.249%` | `-9.426%` | `-6.181%` |
| funding high x risk-off | 48H | 26 | `-0.100%` | `53.846%` | `0.935` | `-5.347%` | `-13.622%` | `-18.777%` |

Generated verdict from `interaction_model_report.md`:

| Question | Answer | Interpretation |
|---|---|---|
| Is the primary condition better than all crashes? | yes | In rolling-2-sigma x Nasdaq 5-day-up cases, Funding-low x risk-on beats all crashes at 24H and 48H. |
| Is it better than Funding alone? | mixed | The improvement exists but is not large. |
| Is it better than risk-on alone? | mixed | It improves 24H, but 48H risk-on alone is stronger. |
| Can avoidable crashes be seen? | directionally yes | Funding-high x risk-off is weaker at 24H and 48H. |

## Interpretation Limits

- The sample for `funding_low_x_risk_on` is small in the primary setup: 15 events.
- Metrics are gross of fees, spread, and slippage.
- P-values are naive and do not fully correct for time-series dependence.
- The interaction coefficient is not stable enough to claim a robust linear interaction effect.
- The cleaner article claim is that Funding and external risk conditions help classify BTC crashes, not that Nasdaq directly predicts BTC.
- This lab is an article-evidence package, not a production trading strategy.
