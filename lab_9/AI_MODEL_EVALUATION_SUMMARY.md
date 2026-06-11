# AI Model Evaluation Summary for lab_9

Evaluation date: 2026-06-11

Experiment purpose: compare Claude Fable5, GPT 5.5 Pro, and GPT 5.5 High on a USDJPY quant-trading research prompt. The prompt asked each model to design simple, explainable strategies, run backtests and Walk Forward Optimization, account for costs, check robustness, and honestly reject the strategy if a durable OOS edge was not found.

## Final Ranking

| Rank | Model directory | Score | Verdict |
|---:|---|---:|---|
| 1 | `gpt5_5pro/` | 90 / 100 | Best overall quant research package |
| 2 | `gpt_5_5_high/` | 77 / 100 | Strong implementation, weaker final judgment |
| 3 | `fable5/` | 67 / 100 | Strong critique, weaker reproducible code |

## Short Conclusion

GPT 5.5 Pro is the best model for this task because it produced the most complete and reproducible research package while still rejecting the strategy as unsuitable for standalone live deployment.

GPT 5.5 High is useful as an implementation model and second-opinion strategy generator. Its code is strong, but it lacks a written final report and does not sufficiently benchmark the attractive 30-minute MA-cross result.

Claude Fable5 produced the sharpest skeptical narrative, especially the point that positive results are mostly USDJPY long beta, not independent strategy alpha. However, its code has practical reproducibility issues and does not fully satisfy the prompt's WFO and next-open execution requirements.

## Evaluation Criteria

| Category | Weight | What was checked |
|---|---:|---|
| Data diagnostics | 10 | Period, rows, timeframe, missing values, OHLC checks, outliers, volatility |
| Strategy breadth | 10 | Trend, breakout, mean reversion, volatility filter, regime logic |
| WFO rigor | 20 | Time ordering, train / validation / test split, OOS fold handling |
| Execution and cost realism | 15 | Next-bar execution, transaction costs, no look-ahead |
| Robustness analysis | 15 | Parameter, cost, regime, Monte Carlo, long/short diagnostics |
| Benchmark and false-positive control | 15 | Buy & Hold, flat, long/short beta, strict rejection logic |
| Artifact quality and reproducibility | 15 | CLI, structured outputs, plots, report completeness, local reusability |

## Score Matrix

| Model | Data | Strategy | WFO | Execution | Robustness | Benchmark | Artifacts | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT 5.5 Pro | 9 | 9 | 18 | 14 | 14 | 14 | 12 | 90 |
| GPT 5.5 High | 8 | 9 | 17 | 14 | 12 | 7 | 10 | 77 |
| Claude Fable5 | 8 | 8 | 10 | 7 | 13 | 13 | 8 | 67 |

## Key Evidence by Model

### GPT 5.5 Pro

Best candidate: 4H Donchian Breakout / trend-following family.

| Metric | Value |
|---|---:|
| Total return | +58.2% |
| Annual return | +3.36% |
| Sharpe | 0.403 |
| Max DD | -16.0% |
| Trades | 120 |
| Positive fold ratio | 59.3% |
| Bootstrap terminal loss probability | 9.6% |
| Bootstrap DD > 20% probability | 66.2% |

Critical benchmark:

| Benchmark | Total return | Sharpe |
|---|---:|---:|
| 4H Breakout WFO | +58.2% | 0.403 |
| USDJPY always long | +93.9% | 0.562 |

Interpretation: positive strategy, but not independent enough. Correctly rejected as live standalone strategy.

### GPT 5.5 High

Best candidate: 30m MA Cross.

| Metric | Value |
|---|---:|
| Total return | +24.7% |
| Annual return | +4.10% |
| Sharpe | 0.470 |
| Max DD | -19.6% |
| Folds | 22 |
| Positive fold ratio | 63.6% |
| Trades | 857 |
| Bootstrap terminal loss probability | 17.6% |
| Bootstrap DD > 20% probability | 32.2% |

Interpretation: technically interesting, but benchmark and written rejection/adoption logic are missing. Because the selected result comes from the shorter 30m dataset starting in 2018, it needs stronger false-positive control.

### Claude Fable5

Best candidate: H4 Donchian, but rejected.

| Metric | Value |
|---|---:|
| OOS total return | +13.7% |
| Annual return | +1.0% |
| Sharpe | 0.16 |
| Max DD | -15.3% |
| Positive fold ratio | 51.9% |
| Long contribution | +32.3% |
| Short contribution | -14.5% |
| Bootstrap terminal loss probability | 33.7% |
| Bootstrap DD > 20% probability | 70.1% |

Interpretation: best skeptical market-structure narrative, but code and WFO implementation are weaker.

## Recommended Use

Use GPT 5.5 Pro as the canonical result for the article experiment.

Use GPT 5.5 High as a source of additional implementation ideas and alternative candidate families, especially if you want to inspect shorter-timeframe MA behavior.

Use Claude Fable5 as a critique layer when writing the article's final discussion, especially for the "long beta is not independent alpha" argument.

## Overall Research Conclusion

None of the three outputs establishes a live-deployable standalone USDJPY strategy from price data alone.

The strongest common finding is negative but useful: simple price-only USDJPY strategies tend to pick up the long USDJPY regime rather than a stable, symmetric, tradeable edge. A serious next experiment should add external explanatory variables such as interest-rate differentials, swap/carry, macro event filters, intervention risk, session effects, bid/ask spreads, and slippage.
