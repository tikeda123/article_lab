# AI Evaluation Report: GPT 5.5 High

Evaluation date: 2026-06-11

Subject directory: `lab_9/gpt_5_5_high/`

Compared task: evaluate whether a generated-AI output can design and test a robust, explainable USDJPY quant trading strategy from the shared prompt in `lab_9/inputdata/prompto.md`.

## Executive Evaluation

GPT 5.5 High produced a strong implementation and the best-looking raw candidate result, but it is weaker than GPT 5.5 Pro as a quant research output because it lacks a written final report and does not sufficiently challenge the selected 30-minute MA-cross result against simple USDJPY long exposure.

The code is generally well structured. It includes the required functions, supports CLI execution, uses train / validation / test WFO, models next-bar open-to-open returns, includes transaction costs, outputs fold-level CSVs, generates plots, and runs Monte Carlo / regime checks.

The concern is research judgment. The top result is a 30-minute MA cross with Sharpe around 0.47, but the 30-minute dataset only starts in 2018, a period dominated by a large USDJPY upward regime from 2021 onward. Without a benchmark comparison and a written critique, this result is easier to overread as strategy alpha.

Overall score: 77 / 100

Recommended role: strong implementation model and second-opinion candidate generator, but not the final research judge.

## Artifacts Reviewed

| Artifact | Assessment |
|---|---|
| `usdjpy_wfo_strategy.py` | Strong code structure with required functions and CLI |
| `usdjpy_wfo_summary.csv` | Main family-level WFO comparison |
| `usdjpy_best_30m_ma_cross_folds.csv` | Fold detail for selected 30m MA cross |
| `usdjpy_cost_sensitivity_30m_ma_cross.csv` | Cost sensitivity for selected strategy |
| `usdjpy_monte_carlo_30m_ma_cross.csv` | Block bootstrap / Monte Carlo output |
| `usdjpy_regime_check_30m_ma_cross.csv` | ADX and ATR regime checks |
| `usdjpy_param_sensitivity_30m_ma_cross.csv` | Parameter sensitivity output |
| `usdjpy_data_diagnostics.csv` | Diagnostics for 30m, 60m, and 240m data |
| `usdjpy_30m_ma_cross_wfo_equity.png` | Equity curve |
| `usdjpy_30m_ma_cross_wfo_drawdown.png` | Drawdown curve |

There is no equivalent of `USDJPY_report.md` in this directory. That is the largest artifact gap.

## Prompt Compliance

| Requirement | Result | Notes |
|---|---|---|
| Data diagnostics | Good | Data diagnostics CSV exists for all three timeframes |
| Multiple strategy candidates | Excellent | MA, Donchian, ADX, vol-filter, mean reversion variants |
| Train / validation / test WFO | Excellent | 24 months train, 6 months validation, 3 months OOS |
| Next-bar execution | Excellent | Code uses signal delay and open-to-open forward return |
| Transaction costs | Excellent | 1.0 pip round-trip cost and sensitivity outputs |
| Required function names | Excellent | All required functions are present |
| Robustness checks | Good | Cost, parameter, Monte Carlo, ADX/ATR regime checks |
| Benchmark comparison | Weak | No saved Buy & Hold / flat benchmark comparison |
| Final strict decision | Weak | No written report, no explicit adoption / rejection conclusion |
| Direct repo re-execution | Good | CLI supports input data paths and outdir |

## Quant Research Quality

The strongest numeric result in this directory is the 30-minute MA cross.

Key result:

| Metric | 30m MA Cross |
|---|---:|
| Total return | +24.70% |
| Annual return | +4.10% |
| Sharpe | 0.470 |
| Calmar | 0.209 |
| Max drawdown | -19.58% |
| Folds | 22 |
| Positive folds | 63.6% |
| Total trades | 857 |
| OOS period | 2020-12-01 to 2026-06-01 |

This is the highest Sharpe among the saved selected candidates across the three directories. But it needs careful interpretation.

Main concern:

The 30-minute data begins in 2018 and the OOS starts in late 2020. This makes the candidate heavily exposed to the 2021-2024 USDJPY upward regime. Without explicit always-long comparison, long/short decomposition, and a written final rejection / adoption analysis, the result is not sufficiently defended.

The 4H results in the same summary are much weaker:

| Data | Family | Total return | Sharpe | Max DD |
|---|---|---:|---:|---:|
| USDJPY30 | MA cross | +24.7% | 0.470 | -19.6% |
| USDJPY240 | Donchian | +16.8% | 0.170 | -20.4% |
| USDJPY60 | Donchian ADX | +9.2% | 0.125 | -15.6% |
| USDJPY240 | MA cross | +5.8% | 0.091 | -42.0% |

The fact that the strongest result is on the shortest and most truncated dataset is a warning sign.

## Robustness Evaluation

Cost sensitivity is reasonably stable:

| Round-trip cost | Total return | Annual return | Sharpe | Max DD |
|---:|---:|---:|---:|---:|
| 0.5 pips | +28.68% | +4.69% | 0.530 | -19.18% |
| 1.0 pips | +24.70% | +4.10% | 0.470 | -19.58% |
| 2.0 pips | +22.61% | +3.78% | 0.438 | -20.36% |

Monte Carlo / block bootstrap:

| Metric | Value |
|---|---:|
| Terminal return median | +24.0% |
| Terminal return 5% | -14.2% |
| Terminal return 95% | +79.2% |
| Max DD median | -16.7% |
| Max DD 5% worst | -29.7% |
| Max DD 1% worst | -36.7% |
| Probability of terminal loss | 17.6% |
| Probability of DD > 20% | 32.2% |
| Probability of DD > 30% | 4.8% |

Regime check:

| Regime | Total return | Sharpe | Max DD |
|---|---:|---:|---:|
| ADX >= 20 trend-like | +34.7% | 0.705 | -14.5% |
| ADX < 20 range-like | -7.5% | -0.266 | -16.4% |
| ATR >= rolling median | +5.5% | 0.159 | -18.3% |
| ATR < rolling median | +18.2% | 0.676 | -6.5% |

This is useful: the model identifies that the MA cross mostly works in trend-like regimes and struggles in range-like regimes. However, the report should have connected this to USDJPY macro regimes and benchmark exposure.

## Engineering Quality

The code quality is strong.

Strengths:

- Provides all required functions:
  - `load_data()`
  - `validate_data()`
  - `create_features()`
  - `generate_signals()`
  - `backtest()`
  - `walk_forward_optimization()`
  - `evaluate_performance()`
  - `robustness_check()`
  - `plot_results()`
- Uses CLI arguments:
  - `--data`
  - `--outdir`
  - `--cost-pips`
- Uses open-to-open next-bar execution.
- Uses train / validation / test windows.
- Saves multiple structured CSVs.
- Saves equity and drawdown plots.

Weaknesses:

- No generated Markdown report explaining the result.
- No saved benchmark comparison.
- No explicit long/short contribution output in the visible CSV set.
- File names in generated outputs include uploaded names like `USDJPY30(13).csv`, while repo input files are named `USDJPY30.csv`, `USDJPY60.csv`, and `USDJPY240.csv`. This is not fatal, but it weakens traceability.
- The selected 30m strategy is plausible, but its historical coverage is shorter than the 60m and 240m data.

## Strengths

- Strong implementation.
- Good WFO structure.
- Good output granularity.
- Good cost and regime checks.
- Strong candidate search over simple strategy families.
- Highest selected candidate Sharpe among the three outputs.

## Weaknesses

- Missing final research report.
- Too easy to overstate the 30m MA cross result.
- Weak false-positive control because benchmark comparison is missing.
- Does not clearly say whether the strategy is live-adoptable.
- Less skeptical than GPT 5.5 Pro and Fable5.

## Score Breakdown

| Category | Score |
|---|---:|
| Data diagnostics | 8 / 10 |
| Strategy breadth | 9 / 10 |
| WFO rigor | 17 / 20 |
| Execution and cost realism | 14 / 15 |
| Robustness analysis | 12 / 15 |
| Benchmark and false-positive control | 7 / 15 |
| Artifact quality and reproducibility | 10 / 15 |
| Total | 77 / 100 |

## Final Assessment

GPT 5.5 High is the best "implementation and candidate generation" output after GPT 5.5 Pro. It is technically capable and produced a coherent WFO pipeline.

The output should not be accepted as a final quant conclusion until it adds:

- an always-long / always-short / flat benchmark comparison,
- long/short contribution decomposition,
- a written conclusion that explicitly says adopt or reject,
- and a discussion of whether the 30m MA cross survives outside the 2021-2024 USDJPY long regime.

Use this output as a useful second candidate set, but not as the final research answer.
