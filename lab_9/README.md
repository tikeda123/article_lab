# lab_9: AI Model Evaluation for USDJPY Quant Research

日本語: [README.ja.md](README.ja.md)

This lab supports the Japanese Qiita article "[クオンツトレードに最適な生成AIはどれか？ ― Claude Fable5 / GPT 5.5 Pro / GPT 5.5 High をUSDJPY戦略開発で比較した](https://qiita.com/tikeda123/items/63e6882cacadbdce1bc4)".

It compares three generated-AI outputs on the same USDJPY quant-trading research prompt. Each model was asked to diagnose the data, design simple explainable strategy candidates, run backtests and Walk Forward Optimization, account for costs, check robustness, compare against benchmarks, and honestly reject the strategy if a durable OOS edge was not found.

This is an educational model-evaluation and quant-research experiment. It is not investment advice, not a live trading signal, and not a production trading system.

## Self-Contained Layout

The lab_9 experiment is self-contained in this directory.

| Type | Path |
|---|---|
| Published article | [クオンツトレードに最適な生成AIはどれか？ ― Claude Fable5 / GPT 5.5 Pro / GPT 5.5 High をUSDJPY戦略開発で比較した](https://qiita.com/tikeda123/items/63e6882cacadbdce1bc4) |
| Shared prompt | `inputdata/prompto.md` |
| Input data | `inputdata/USDJPY30.csv`, `inputdata/USDJPY60.csv`, `inputdata/USDJPY240.csv` |
| Evaluation summary | `AI_MODEL_EVALUATION_SUMMARY.md` |
| Canonical model output | `gpt5_5pro/` |
| Second-opinion implementation output | `gpt_5_5_high/` |
| Critique-layer output | `fable5/` |

Unlike some earlier labs, `lab_9` does not have one top-level experiment runner. It is a comparison package that stores the shared prompt, shared input data, each model's output, and the final evaluation summary.

## Evaluation Target

All three models were evaluated against the same task:

| Requirement | Meaning |
|---|---|
| Data diagnostics | Check period, row count, timeframe, missing values, duplicates, OHLC validity, outliers, volatility, and trend/range behavior |
| Strategy breadth | Compare simple families such as trend following, breakout, mean reversion, volatility filters, and regime logic |
| WFO rigor | Preserve time order and separate train / validation / test periods |
| Execution realism | Use past-only signals, next-bar execution, and transaction costs |
| Robustness | Test parameters, costs, regimes, Monte Carlo / bootstrap, and long/short dependence |
| Benchmark control | Compare against Buy & Hold, always long, always short, and flat exposure where available |
| Final judgment | Accept "no valid standalone strategy found" as a correct outcome |

## Model Outputs

| Directory | Role | Main artifacts |
|---|---|---|
| `gpt5_5pro/` | Canonical result for the article experiment | `USDJPY_report.md`, `AI_EVALUATION_REPORT_gpt55_pro.md`, `usdjpy_wfo_quant_research.py`, `outputs/*.csv`, `outputs/*.png` |
| `gpt_5_5_high/` | Strong implementation and alternative candidate generator | `AI_EVALUATION_REPORT_gpt55_high.md`, `usdjpy_wfo_strategy.py`, `output_csv/*.csv`, `*.png` |
| `fable5/` | Skeptical critique and narrative comparison layer | `USDJPY_quant_analysis_report.md`, `AI_EVALUATION_REPORT_fable.md`, `usdjpy_wfo.py`, `fold_results.csv`, `wfo_results.png` |

## Final Ranking

| Rank | Model directory | Score | Verdict |
|---:|---|---:|---|
| 1 | `gpt5_5pro/` | 90 / 100 | Best overall quant research package |
| 2 | `gpt_5_5_high/` | 77 / 100 | Strong implementation, weaker final judgment |
| 3 | `fable5/` | 67 / 100 | Strong critique, weaker reproducible code |

## Score Matrix

| Model | Data | Strategy | WFO | Execution | Robustness | Benchmark | Artifacts | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT 5.5 Pro | 9 | 9 | 18 | 14 | 14 | 14 | 12 | 90 |
| GPT 5.5 High | 8 | 9 | 17 | 14 | 12 | 7 | 10 | 77 |
| Claude Fable5 | 8 | 8 | 10 | 7 | 13 | 13 | 8 | 67 |

## Key Result

GPT 5.5 Pro is the canonical result because it produced the most complete and reproducible research package while still rejecting the selected strategy as unsuitable for standalone live deployment.

The selected GPT 5.5 Pro candidate, a 4H Donchian breakout / trend-following family, had positive OOS performance, but it underperformed simple USDJPY always-long exposure:

| Candidate | Total return | Annual return | Sharpe | Calmar | Max DD |
|---|---:|---:|---:|---:|---:|
| 4H Breakout WFO | +58.2% | +3.36% | 0.403 | 0.210 | -16.0% |
| USDJPY always long | +93.9% | +4.88% | 0.562 | 0.238 | -20.5% |

The research conclusion is therefore negative but useful: the apparent positive result is closer to risk-managed USDJPY long beta than a durable standalone strategy alpha.

## Environment

The generated scripts primarily use:

```text
numpy
pandas
matplotlib
```

The prompt allowed `scipy` and `scikit-learn`, but the reviewed scripts do not rely on difficult-to-install TA-Lib-style dependencies.

## Reproduce or Inspect

Start with the evaluation summary:

```bash
sed -n '1,220p' lab_9/AI_MODEL_EVALUATION_SUMMARY.md
```

Re-run the GPT 5.5 Pro implementation to a temporary output directory:

```bash
python3 lab_9/gpt5_5pro/usdjpy_wfo_quant_research.py \
  --files lab_9/inputdata/USDJPY30.csv lab_9/inputdata/USDJPY60.csv lab_9/inputdata/USDJPY240.csv \
  --outdir /tmp/lab9_gpt55pro_check \
  --strategy-filter breakout \
  --bootstrap-sims 500
```

Re-run the GPT 5.5 High implementation to a temporary output directory:

```bash
python3 lab_9/gpt_5_5_high/usdjpy_wfo_strategy.py \
  --data lab_9/inputdata/USDJPY30.csv lab_9/inputdata/USDJPY60.csv lab_9/inputdata/USDJPY240.csv \
  --outdir /tmp/lab9_gpt55high_check
```

The Fable5 script is useful as reviewed evidence, but its `main()` contains hard-coded external paths. Treat `fable5/USDJPY_quant_analysis_report.md`, `fable5/fold_results.csv`, and `fable5/wfo_results.png` as the reviewed artifacts unless the script is adapted to repository-relative input paths.

## Main Artifacts

| File | Description |
|---|---|
| `AI_MODEL_EVALUATION_SUMMARY.md` | Final cross-model evaluation and article-facing result summary |
| `inputdata/prompto.md` | Shared prompt given to each model |
| `inputdata/USDJPY30.csv` | USDJPY 30-minute OHLCV input |
| `inputdata/USDJPY60.csv` | USDJPY 60-minute OHLCV input |
| `inputdata/USDJPY240.csv` | USDJPY 240-minute OHLCV input |
| `gpt5_5pro/USDJPY_report.md` | GPT 5.5 Pro research report |
| `gpt5_5pro/AI_EVALUATION_REPORT_gpt55_pro.md` | Evaluation report for GPT 5.5 Pro |
| `gpt5_5pro/outputs/benchmark_comparison.csv` | Critical always-long / always-short / flat benchmark comparison |
| `gpt5_5pro/outputs/selected_4h_breakout_monte_carlo_summary.csv` | Bootstrap and drawdown risk summary |
| `gpt_5_5_high/AI_EVALUATION_REPORT_gpt55_high.md` | Evaluation report for GPT 5.5 High |
| `gpt_5_5_high/output_csv/usdjpy_wfo_summary.csv` | GPT 5.5 High family-level WFO comparison |
| `fable5/AI_EVALUATION_REPORT_fable.md` | Evaluation report for Claude Fable5 |
| `fable5/USDJPY_quant_analysis_report.md` | Fable5 research narrative and rejection logic |

## Interpretation Notes

- The score matrix is based on the author's evaluation criteria, not an absolute benchmark of model quality.
- Each model output is a single run, so the result is not a statistically stable model leaderboard.
- GPT 5.5 Pro ranks first because it combines implementation quality with strict false-positive rejection, not because it found a tradeable strategy.
- GPT 5.5 High is useful for candidate generation, but the attractive 30-minute MA-cross result needs stronger benchmark and long-beta controls.
- Claude Fable5 is useful as a skeptical critique layer, especially for the point that positive USDJPY results can be long beta rather than independent alpha.
- None of the three outputs establishes a live-deployable standalone USDJPY strategy from price data alone.
