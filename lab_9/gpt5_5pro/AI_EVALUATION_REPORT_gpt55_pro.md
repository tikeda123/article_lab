# AI Evaluation Report: GPT 5.5 Pro

Evaluation date: 2026-06-11

Subject directory: `lab_9/gpt5_5pro/`

Compared task: evaluate whether a generated-AI output can design and test a robust, explainable USDJPY quant trading strategy from the shared prompt in `lab_9/inputdata/prompto.md`.

## Executive Evaluation

GPT 5.5 Pro produced the best overall output in this experiment.

It best matches the original prompt because it combines:

- broad but still simple strategy-family comparison,
- explicit data diagnostics,
- train / validation / OOS test separation,
- next-bar-open execution,
- transaction costs,
- benchmark comparison,
- parameter sensitivity,
- Monte Carlo / block bootstrap,
- monthly and regime outputs,
- and a strict final "not suitable for live standalone deployment" conclusion.

Most importantly, GPT 5.5 Pro does not over-sell its best-performing strategy. It identifies a positive 4H trend / breakout candidate, then rejects it as an independent trading edge because it underperforms USDJPY always-long exposure and depends too much on the long side.

Overall score: 90 / 100

Recommended role: primary quant research and canonical experiment generation model.

## Artifacts Reviewed

| Artifact | Assessment |
|---|---|
| `USDJPY_report.md` | Detailed, structured, and aligned with the requested output format |
| `usdjpy_wfo_quant_research.py` | Strongest implementation; CLI, required functions, WFO, robustness, plots |
| `outputs/data_diagnostics_usdjpy.csv` | Good diagnostics across 30m, 60m, and 240m data |
| `outputs/family_wfo_comparison_cost1pip.csv` | Clear strategy-family comparison |
| `outputs/benchmark_comparison.csv` | Critical benchmark evidence |
| `outputs/selected_4h_breakout_fold_oos_results.csv` | Detailed OOS fold evidence |
| `outputs/selected_4h_breakout_parameter_sensitivity.csv` | Important overfitting diagnostic |
| `outputs/selected_4h_breakout_monte_carlo_summary.csv` | Good distributional risk diagnostic |
| `outputs/selected_4h_breakout_regime_performance.csv` | Good regime-level explanation |
| `outputs/*.png` | Equity and drawdown plots are generated |
| `usdjpy_quant_package.zip` | Packaged outputs for distribution |

## Prompt Compliance

| Requirement | Result | Notes |
|---|---|---|
| Data diagnostics | Excellent | Period, rows, timeframe, gaps, missing values, OHLC, outliers, volatility, ER |
| Multiple strategy candidates | Excellent | MA trend, breakout, mean reversion, regime trend, meta comparison |
| Train / validation / test WFO | Excellent | 24 months train, 6 months validation, 3 months OOS test |
| Next-bar execution | Excellent | Code documents signal after close and fill at next open |
| Transaction costs | Excellent | Round-trip pips, half charged per side |
| Required function names | Excellent | All required functions are present |
| Robustness checks | Excellent | Cost sensitivity, parameter sensitivity, Monte Carlo, monthly CVaR, regime checks |
| Benchmark comparison | Excellent | Always long, always short, flat; used directly in final judgment |
| Final strict decision | Excellent | Positive strategy is still rejected as live standalone strategy |
| Direct repo re-execution | Good | CLI supports paths and outdir; report examples use `/mnt/data`, but script itself is reusable |

## Quant Research Quality

GPT 5.5 Pro's strongest research contribution is that it separates "positive OOS strategy return" from "tradable independent edge."

The selected research candidate is 4H Donchian Breakout. It has decent-looking OOS performance, but the report correctly treats it as insufficient.

Key quantitative evidence:

| Metric | 4H Breakout WFO |
|---|---:|
| Total return | +58.18% |
| Annual return | +3.36% |
| Sharpe | 0.403 |
| Sortino | 0.514 |
| Calmar | 0.210 |
| Max drawdown | -15.97% |
| Profit factor | 1.476 |
| Trades | 120 |
| Positive fold ratio | 59.3% |
| OOS period | 2012-11-26 to 2026-05-26 |

The benchmark comparison is the decisive part:

| Candidate | Total return | Annual return | Sharpe | Calmar | Max DD |
|---|---:|---:|---:|---:|---:|
| 4H Breakout WFO | +58.2% | +3.36% | 0.403 | 0.210 | -16.0% |
| USDJPY always long | +93.9% | +4.88% | 0.562 | 0.238 | -20.5% |
| USDJPY always short | -54.2% | -5.47% | -0.562 | -0.100 | -54.7% |
| Flat | 0.0% | 0.0% | n/a | n/a | 0.0% |

This comparison prevents a false positive. The model correctly concludes that the strategy is closer to a risk-managed expression of USDJPY long beta than a standalone symmetric trend-following edge.

## Robustness Evaluation

The robustness package is broad and useful.

Cost sensitivity is stable:

| Round-trip cost | Total return | Sharpe | Max DD |
|---:|---:|---:|---:|
| 0.5 pips | +59.13% | 0.408 | -15.95% |
| 1.0 pips | +58.18% | 0.403 | -15.97% |
| 2.0 pips | +56.30% | 0.394 | -16.00% |

This shows the 4H candidate is low-turnover enough to survive cost changes. The report does not over-interpret this; it notes that cost tolerance can simply mean low turnover.

Monte Carlo / block bootstrap:

| Metric | Value |
|---|---:|
| Terminal return median | +57.2% |
| Terminal return 5% | -10.4% |
| Max DD median | -22.6% |
| Max DD 5% | -39.0% |
| Probability of terminal loss | 9.6% |
| Probability of DD > 20% | 66.2% |
| Probability of DD > 30% | 19.2% |
| Monthly CVaR 5% | -5.72% |

This is exactly the kind of result a robust quant report should surface: the strategy can look positive on terminal return while still carrying an uncomfortable drawdown distribution.

## Engineering Quality

The script is the strongest implementation among the three.

Strengths:

- Provides all requested core functions:
  - `load_data()`
  - `validate_data()`
  - `create_features()`
  - `generate_signals()`
  - `backtest()`
  - `walk_forward_optimization()`
  - `evaluate_performance()`
  - `robustness_check()`
  - `plot_results()`
- Uses CLI arguments for input files, output directory, strategy filter, costs, and bootstrap count.
- Supports multiple file formats and headerless data.
- Implements open-to-open execution with signal delay.
- Saves structured CSV outputs.
- Saves plots.
- Avoids hard-to-install TA-Lib dependency.

Minor weaknesses:

- The report examples use `/mnt/data/...` paths rather than repository-relative paths.
- The selected result emphasizes 4H Breakout, while the family comparison shows 4H MA Trend has slightly higher Sharpe but worse drawdown. The report explains why Breakout is easier to defend, but this choice should be documented as a research judgment.
- Benchmark comparison is excellent, but deflated Sharpe / White's Reality Check / PBO are recommended rather than implemented.

## Strengths

- Best balance of research rigor and implementation.
- Best artifact coverage.
- Strong false-positive control through benchmark comparison.
- Good recognition of long-side dependence.
- Uses strict adoption threshold.
- Produces reusable experiment package.

## Weaknesses

- Still not enough for live trading, by its own conclusion.
- Does not fully implement multi-test correction.
- Does not include actual bid/ask, slippage, swap, intervention filters, or macro rate differential data.
- Some results are still consistent with USDJPY long beta rather than a standalone edge.

## Score Breakdown

| Category | Score |
|---|---:|
| Data diagnostics | 9 / 10 |
| Strategy breadth | 9 / 10 |
| WFO rigor | 18 / 20 |
| Execution and cost realism | 14 / 15 |
| Robustness analysis | 14 / 15 |
| Benchmark and false-positive control | 14 / 15 |
| Artifact quality and reproducibility | 12 / 15 |
| Total | 90 / 100 |

## Final Assessment

GPT 5.5 Pro is the strongest model for this quant-trading evaluation task.

It should be treated as the canonical output for `lab_9` because it produces the most complete and reproducible research package and because its final decision is appropriately conservative. The best use of this result is not to trade the proposed 4H breakout strategy, but to use it as evidence that price-only USDJPY strategies need stronger external explanatory variables before they can be considered live candidates.
