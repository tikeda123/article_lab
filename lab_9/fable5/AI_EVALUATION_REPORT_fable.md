# AI Evaluation Report: Claude Fable5

Evaluation date: 2026-06-11

Subject directory: `lab_9/fable5/`

Compared task: evaluate whether a generated-AI output can design and test a robust, explainable USDJPY quant trading strategy from the shared prompt in `lab_9/inputdata/prompto.md`.

## Executive Evaluation

Claude Fable5 produced the strongest critical conclusion among the three models, but its engineering artifact is weaker than its research narrative.

The report correctly rejects the strategy as a live trading candidate and gives a sharp explanation: the apparent positive performance decomposes into USDJPY long beta during yen-weakening macro regimes, while the short side does not work. That is a good quant judgment.

However, the code has material reproducibility and prompt-compliance issues. It uses hard-coded external paths, writes outputs to `/home/claude`, has no command-line data arguments, lacks the exact required function names `generate_signals()` and `plot_results()`, uses train-only WFO selection rather than train / validation / test separation, and models returns close-to-close rather than next-bar-open execution. Those issues matter because the original prompt explicitly asked for directly executable Python code with WFO, next-bar execution, and leakage control.

Overall score: 67 / 100

Recommended role: critical reviewer or narrative analyst, not the primary implementation model.

## Artifacts Reviewed

| Artifact | Assessment |
|---|---|
| `USDJPY_quant_analysis_report.md` | Strong report with a strict final conclusion and good market-structure interpretation |
| `usdjpy_wfo.py` | Compact but less reusable; hard-coded paths and weaker WFO design |
| `fold_results.csv` | Useful fold-level output for the selected H4 strategy |
| `wfo_results.png` | Useful combined plot, but only one plot file |

## Prompt Compliance

| Requirement | Result | Notes |
|---|---|---|
| Data diagnostics | Good | Period, rows, timeframe, OHLC consistency, volatility, fat tails are covered |
| Multiple strategy candidates | Good | Donchian, MA cross, mean reversion, vol filter, regime filter, plus TSMOM in narrative |
| Train / validation / test WFO | Weak | Code uses 36-month train and 6-month OOS test; no explicit validation window |
| Next-bar execution | Partial | Code shifts positions, but computes returns with `close.pct_change()` rather than open-to-open next-bar fills |
| Transaction costs | Good | Round-trip 1.0 pip cost is included |
| Required function names | Partial | Has `load_data`, `validate_data`, `create_features`, `backtest`, `walk_forward_optimization`, `evaluate_performance`, `robustness_check`; missing exact `generate_signals` and `plot_results` |
| Robustness checks | Good | Cost, parameter, regime, long/short, bootstrap are discussed |
| Benchmark comparison | Good | Buy & Hold comparison is explicitly used to reject the strategy |
| Final strict decision | Excellent | The report clearly says adoption is not justified |
| Direct repo re-execution | Weak | Paths are fixed to `/mnt/user-data/uploads` and `/home/claude` |

## Quant Research Quality

The strongest part of this output is the interpretation. Fable5 does not stop at "the best strategy has positive return." It asks whether the result is independent from the long USDJPY macro regime.

Key quantitative claims:

| Metric | Value |
|---|---:|
| Selected strategy | H4 Donchian |
| OOS total return | +13.7% |
| Annual return | +1.0% |
| OOS Sharpe | 0.16 |
| Max drawdown | -15.3% |
| Profit factor | 1.11 |
| Trades | 374 in report, 393 in `fold_results.csv` aggregation |
| Positive folds | 51.9% |
| Long PnL contribution | +32.3% |
| Short PnL contribution | -14.5% |
| Bootstrap probability of loss | 33.7% |
| Bootstrap probability of DD > 20% | 70.1% |

The conclusion that the strategy is not a robust independent edge is well supported. The report also correctly identifies that the short side is structurally poor, which is a key diagnostic for USDJPY trend-following systems.

## Engineering Quality

The script is readable and syntactically valid, but it is not a strong repo-quality deliverable.

Strengths:

- Compact implementation.
- Easy-to-read strategy registry.
- Coarse parameter grids reduce obvious overfitting.
- Includes fold output and plot generation.
- Includes long/short split and bootstrap.

Weaknesses:

- `main()` hard-codes:
  - `/mnt/user-data/uploads/USDJPY30.csv`
  - `/mnt/user-data/uploads/USDJPY60.csv`
  - `/mnt/user-data/uploads/USDJPY240.csv`
  - `/home/claude/wfo_results.png`
  - `/home/claude/fold_results.csv`
- No CLI arguments for local data paths.
- Uses close-to-close returns despite the prompt requiring next-bar execution.
- Uses train-only parameter selection, not a separate validation window.
- Does not expose exact `generate_signals()` and `plot_results()` functions.
- Saves only limited structured outputs compared with the GPT outputs.

The code can be adapted, but it is not "copy and run inside this repository" without edits.

## Methodological Risks

The largest issue is not the conclusion; the conclusion is good. The risk is that the implementation does not fully match the experimental standard requested in the prompt.

Specific risks:

- Train-only WFO can overstate robustness because parameter selection is done directly on the train period Sharpe.
- Close-to-close return modeling is less realistic than signal-at-close, fill-at-next-open, open-to-open PnL.
- The lack of CLI inputs makes independent reproduction harder.
- Some additional claims in the report, such as TSMOM and deflated Sharpe commentary, are not fully represented as saved structured artifacts in this directory.

## Strengths

- Best qualitative rejection of false positive strategy performance.
- Strong explanation of USDJPY long-beta dependence.
- Correctly highlights that Buy & Hold comparison weakens the strategy case.
- Correctly treats "no strategy found" as a valid quant outcome.
- Good discussion of what additional information would be needed, such as carry, swap, session effects, intervention filters, and tick-volume hypotheses.

## Weaknesses

- Lower reproducibility than the other two outputs.
- Does not fully satisfy the exact function and execution requirements.
- WFO separation is less rigorous.
- Artifacts are sparse.
- Output paths are not repository-relative.

## Score Breakdown

| Category | Score |
|---|---:|
| Data diagnostics | 8 / 10 |
| Strategy breadth | 8 / 10 |
| WFO rigor | 10 / 20 |
| Execution and cost realism | 7 / 15 |
| Robustness analysis | 13 / 15 |
| Benchmark and false-positive control | 13 / 15 |
| Artifact quality and reproducibility | 8 / 15 |
| Total | 67 / 100 |

## Final Assessment

Claude Fable5 is valuable as a skeptical quant reviewer. It produced the most concise and conceptually sharp rejection of the strategy. For article writing, it gives useful language: "the positive component is long beta, not an independent price-pattern edge."

For production-quality experiment generation, it ranks below the GPT outputs because the code is less reproducible and the WFO implementation does not fully follow the prompt constraints.

Use Fable5's output as a critique layer, not as the primary canonical experiment.
