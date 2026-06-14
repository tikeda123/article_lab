# lab_10: BTC Fragility Diagnostics for Fat-Tail Risk Practice

This lab supports the Japanese Qiita article "[ファットテールを織り込んだ\"つもり\"になっていないか](https://qiita.com/tikeda123/items/091519af64bd22367c2d)".

The experiment reuses the `lab_7` BTC crash, Funding Rate, and external risk-environment setup, but the goal is different. It does not try to prove that BTC crashes are buyable, and it does not promote `Funding low x risk-on` as a live trading strategy. Instead, it asks a narrower risk-management question:

> When an edge candidate looks attractive, which assumptions make it break?

This is an educational quant-risk and article-support package. It is not investment advice, not a live trading signal, and not a production trading system.

## Self-Contained Layout

The lab_10 experiment is self-contained in this directory.

| Type | Path |
|---|---|
| Published article | [ファットテールを織り込んだ"つもり"になっていないか](https://qiita.com/tikeda123/items/091519af64bd22367c2d) |
| Experiment plan | `EXPERIMENT_PLAN.ja.md` |
| Implementation spec | `IMPLEMENTATION_SPEC.ja.md` |
| Main scripts | `scripts/00_lab7_interaction_model_base.py`, `scripts/02_btc_crash_fragility.py`, `scripts/03_fragility_matrix.py` |
| Input data copied from lab_7 | `data/lab_7/` |
| Generated reports | `outputs/report/` |
| Generated tables | `outputs/tables/` |
| Generated figures | `outputs/figures/` |
| Minimal AI-review package | `article_materials_btc_minimal_ai/` |
| Full article-material package | `article_materials_btc_only/` |

## Experiment Target

The target candidate is the BTC crash subgroup:

```text
Funding low x risk-on
```

Baseline setup:

| Item | Definition |
|---|---|
| Market | BTC 4H bars |
| Baseline crash | Rolling 180-bar sigma score `<= -2.0` |
| Baseline risk-on proxy | Nasdaq 5-day return > 0 |
| Baseline Funding-low condition | Lower 20% or negative Funding Rate |
| Entry | Next 4H open after crash signal |
| Exit horizons | 24h, 48h, 5d |
| Evaluation | Open-to-open log return, MAE, MaxDD, PF, bootstrap, robustness checks |

External equity indexes are used only as risk-environment proxies. They are not treated as direct BTC predictors.

## Key Result

The 48h `Funding low x risk-on` point estimate looks interesting:

| Candidate | n | Mean return | Profit factor |
|---|---:|---:|---:|
| 48h `Funding low x risk-on` | 15 | +1.115% | 2.073 |
| 24h `Funding low x risk-on` | 15 | +1.297% | 3.122 |

The article-relevant conclusion is weaker and more important:

| Fragility check | Result | Interpretation |
|---|---:|---|
| 48h bootstrap mean 5% lower bound | -0.380% | Positive expectation cannot be stated strongly with `n=15` |
| 24h bootstrap mean 5% lower bound | -0.057% | 24h also touches the zero line |
| `full_sample_q025` crash definition, 48h | mean -1.082%, PF 0.666 | A stricter crash definition breaks the candidate |
| 2022 stress period, 48h | n=4, mean -0.789%, PF 0.505 | The candidate is regime-dependent |
| 48h `cost_x5` | PF 2.073 -> 1.524 | Cost stress compresses the edge |
| 48h 4H delayed entry | PF 2.073 -> 1.324 | Execution assumptions matter |
| 48h 3x leverage | worst MAE -28.277% | Mean return must be read with path risk |

The clean conclusion is:

> `Funding low x risk-on` is a useful test subject, not a proven strategy. The experiment supports the article's claim that fat-tail-aware practice means finding where a good-looking estimate breaks and translating that into operating rules.

## Experiment Phases

| Phase | Script | Purpose |
|---|---|---|
| 0 | `scripts/00_lab7_interaction_model_base.py` | Reproduce the `lab_7` BTC crash interaction baseline inside `lab_10` |
| 1 | `scripts/02_btc_crash_fragility.py` | Generate BTC fragility diagnostics: bootstrap, crash definition, period, cost, execution, risk proxy, Funding threshold, leverage |
| 2 | `scripts/03_fragility_matrix.py` | Convert the diagnostics into article-facing key metrics, reports, and a Fragility Matrix |

## Reproduce

Use the local Python environment with `pandas`, `numpy`, `scipy`, and `matplotlib`.

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

Syntax-check the scripts:

```bash
/Users/toikeda/miniconda3/bin/python -m py_compile \
  lab_10/scripts/00_lab7_interaction_model_base.py \
  lab_10/scripts/02_btc_crash_fragility.py \
  lab_10/scripts/03_fragility_matrix.py
```

## Main Artifacts

| File | Description |
|---|---|
| `outputs/report/lab_10_experiment_report.md` | Article-support experiment report |
| `outputs/report/article_outline_alignment.md` | Mapping from the published article sections to experiment evidence |
| `outputs/report/fragility_matrix.md` | Fragility Matrix explanation |
| `outputs/report/article_figure_selection.md` | Figure selection for article and appendix use |
| `outputs/report/btc_crash_fragility.md` | Detailed BTC fragility diagnostics report |
| `outputs/tables/article_key_metrics.csv` | Small table of article-critical metrics |
| `outputs/tables/fragility_matrix.csv` | Article-facing break-condition matrix |
| `outputs/tables/btc_bootstrap_uncertainty.csv` | Bootstrap uncertainty for the candidate |
| `outputs/tables/btc_definition_robustness.csv` | Crash-definition robustness |
| `outputs/tables/btc_subperiod_results.csv` | Period and regime split results |
| `outputs/tables/btc_cost_stress.csv` | Transaction-cost stress |
| `outputs/tables/btc_entry_execution_stress.csv` | Entry delay and adverse execution stress |
| `outputs/tables/btc_leverage_tolerance.csv` | Levered MAE/DD tolerance |

## Figure Set

Body candidates:

| Figure | Article role |
|---|---|
| `outputs/figures/btc_bootstrap_mean_return.png` | Small-sample uncertainty and bootstrap lower bounds |
| `outputs/figures/btc_definition_robustness_heatmap.png` | Sign reversal under crash-definition stress |
| `outputs/figures/btc_cost_stress_heatmap.png` | Gross-to-net compression under cost stress |

Appendix candidates:

| Figure | Role |
|---|---|
| `outputs/figures/btc_entry_execution_stress.png` | Execution-delay sensitivity |
| `outputs/figures/btc_leverage_tolerance.png` | Levered path-risk sensitivity |
| `outputs/figures/btc_risk_env_robustness.png` | Risk-proxy sensitivity |
| `outputs/figures/btc_funding_definition_robustness.png` | Funding-threshold sensitivity |
| `outputs/figures/fragility_matrix_status.png` | Broken / fragile / watch counts |

## Minimal Package For AI Review

If another generated-AI system should review the experiment or help draft article analysis, use only:

```text
article_materials_btc_minimal_ai/
```

It contains five files:

| File | Role |
|---|---|
| `01_ANALYZE_THIS.ja.md` | Prompt, key results, article stance, and forbidden claims |
| `02_fragility_matrix.csv` | Breakable assumptions and practical responses |
| `03_bootstrap_uncertainty.png` | Bootstrap figure |
| `04_crash_definition_robustness.png` | Crash-definition figure |
| `05_cost_stress.png` | Cost-stress figure |

## Interpretation Notes

- This lab supports the published article's risk-management argument; it does not establish a live-deployable BTC strategy.
- The attractive point estimate is intentionally treated as a baseline to stress, not as a conclusion.
- `n=15` is central. Any article or summary should mention it before discussing PF.
- Bootstrap lower bounds, crash-definition dependence, 2022 stress-period weakness, cost compression, execution delay, and levered MAE are the article's main evidence.
- The Fragility Matrix is a conversion table from assumptions to operating responses. It is not proof of profitability.
- External-market variables are risk-environment proxies; avoid causal language such as "Nasdaq predicts BTC."
