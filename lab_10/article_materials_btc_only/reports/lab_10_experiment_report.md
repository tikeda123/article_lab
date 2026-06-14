# BTC-Only Experiment Report

## 日本語要約

この記事ではBTCのみを扱う。USDJPYの実験ログは残しているが、記事本文・図表選定・骨子整合性分析には使わない。

中心テーマは、BTC急落後の `Funding low x risk-on` が「買える急落」候補に見えるとしても、それをそのまま有効戦略として扱ってよいのか、という点である。

結論は明確である。`Funding low x risk-on` は面白い候補だが、主条件は `n=15` と小さく、bootstrapの下限も0を下回る。したがって、記事では成功例ではなく、`error on error` を説明するための「壊れる条件を調べる候補」として扱う。

## 1. Purpose And Non-Purpose

Purpose:

- BTC急落後の反発候補が、どの前提で壊れるかを見る。
- Funding、外部リスク環境、コスト、定義、期間、約定、MAE/DDを疑いのダイヤルとして扱う。
- 記事骨子の「エッジ候補にも error on error がある」を実データで説明する。

Non-purpose:

- BTC急落は買いだと主張すること。
- `Funding low x risk-on` を有効戦略として証明すること。
- NasdaqがBTCを直接予測すると主張すること。

## 2. Reproducibility

Main commands used:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

Phase 0 reproduced the copied `lab_7` baseline. The regenerated major CSVs matched the copied reference CSVs.

## 3. BTC Baseline

| horizon | group | n | mean_ret_pct | profit_factor | mean_mae_pct | worst_mae_pct | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | all_funding_covered_crashes | 201 | 0.341 | 1.260 | -3.727 | -36.617 | -30.823 | watch |
| 24h | funding_low_x_risk_on | 15 | 1.297 | 3.122 | -2.651 | -9.426 | -3.470 | fragile |
| 24h | funding_high_x_risk_off | 26 | -0.242 | 0.837 | -4.330 | -12.258 | -19.250 | broken |
| 48h | all_funding_covered_crashes | 201 | 0.603 | 1.368 | -4.716 | -36.617 | -42.441 | watch |
| 48h | funding_low_x_risk_on | 15 | 1.115 | 2.073 | -3.249 | -9.426 | -6.181 | fragile |
| 48h | funding_high_x_risk_off | 26 | -0.100 | 0.935 | -5.347 | -13.622 | -18.777 | broken |
| 5d | all_funding_covered_crashes | 201 | 0.647 | 1.231 | -7.078 | -50.636 | -70.074 | watch |
| 5d | funding_low_x_risk_on | 15 | 2.194 | 2.907 | -4.454 | -14.642 | -12.193 | fragile |
| 5d | funding_high_x_risk_off | 26 | 0.089 | 1.033 | -7.458 | -28.058 | -25.112 | watch |

## 4. Bootstrap Uncertainty

| horizon | n | mean_p05_pct | mean_p50_pct | mean_p95_pct | pf_p05 | pf_p50 | pf_p95 | is_ci_fragile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | 15 | -0.057 | 1.247 | 2.781 | 0.940 | 3.126 | 13.946 | True |
| 48h | 15 | -0.380 | 1.155 | 2.479 | 0.798 | 2.135 | 8.714 | True |

Interpretation:

- 24h/48hとも点推定は良いが、`n=15` しかない。
- bootstrap mean 5% lower bound は24h/48hとも0を下回る。
- 記事本文では、平均リターンやPFより先に `n` と不確実性を出す。

## 5. Cost Stress

| horizon | cost_case | cost_bps | n | mean_ret_pct | profit_factor | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| 24h | gross | 0.000 | 15 | 1.297 | 3.122 | fragile |
| 24h | base_cost | 10.000 | 15 | 1.197 | 2.857 | fragile |
| 24h | cost_x2 | 20.000 | 15 | 1.097 | 2.611 | fragile |
| 24h | cost_x5 | 50.000 | 15 | 0.797 | 1.988 | fragile |
| 48h | gross | 0.000 | 15 | 1.115 | 2.073 | fragile |
| 48h | base_cost | 10.000 | 15 | 1.015 | 1.952 | fragile |
| 48h | cost_x2 | 20.000 | 15 | 0.915 | 1.837 | fragile |
| 48h | cost_x5 | 50.000 | 15 | 0.615 | 1.524 | fragile |

## 6. Crash Definition Robustness

| event_def | n | mean_ret_pct | profit_factor | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- |
| rolling_1_5sigma | 24 | 0.640 | 1.580 | -6.787 | watch |
| rolling_2sigma | 15 | 1.115 | 2.073 | -6.181 | fragile |
| rolling_2_5sigma | 7 | 1.654 | 2.671 | -1.145 | fragile |
| full_sample_q05 | 24 | 2.525 | 4.470 | -9.841 | watch |
| full_sample_q025 | 8 | -1.082 | 0.666 | -18.213 | broken |

## 7. Subperiod Stability

| period | n | mean_ret_pct | profit_factor | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- |
| all | 15 | 1.115 | 2.073 | -6.181 | fragile |
| 2020_2021 | 2 | -0.932 | 0.677 | 0.000 | broken |
| 2022_stress | 4 | -0.789 | 0.505 | -0.974 | broken |
| 2023_2024 | 3 | 3.095 | - | 0.000 | fragile |
| 2025_2026 | 6 | 2.077 | 4.626 | -3.378 | fragile |
| post_btc_etf | 8 | 2.588 | 7.025 | -3.378 | fragile |

## 8. BTC Fragility Matrix

| fragility_source | stress_case | fragility_status | article_message | practical_response |
| --- | --- | --- | --- | --- |
| sample_size | Bootstrap, 48h Funding low x risk-on | fragile | The subgroup is interesting, but n is too small for a strong claim. | Lead with sample size and uncertainty before mentioning PF. |
| cost | 48h cost x5 | fragile | Gross backtests are not enough. | Set cost ceilings and report net results. |
| execution | 48h entry delayed by 4H | fragile | Execution assumptions are part of the risk model. | Require entry-delay tolerance before treating the signal as usable. |
| crash_definition | 48h full-sample lower 2.5% | broken | Edge estimates depend on definitions. | Publish definition robustness before naming a condition buyable. |
| risk_env_definition | 48h S&P500 5D up | fragile | External markets are context filters, not direct BTC predictors. | Use multiple risk-on proxies and avoid causal wording. |
| funding_definition | 48h Funding negative only | fragile | Subjective thresholds must be explicit. | Report Funding definitions side by side. |
| subperiod | 48h 2022 stress period | broken | Regime dependence is central to edge uncertainty. | Use period splits to weaken or qualify public claims. |
| mae_dd_leverage | 48h 3x leverage | watch | Mean return must be read with path loss and leverage tolerance. | Define leverage caps and forced-reduction rules from MAE/DD. |
| avoid_condition | 48h Funding high x risk-off | broken | The useful claim is classification, not universal dip buying. | Use high-funding/risk-off as an avoid or size-reduction condition. |

## 9. Article-Ready Conclusion

BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、この条件は `n=15` と小さく、bootstrapの下限も0を下回る。さらに、crash定義や期間分割を変えると壊れるケースがある。したがって、ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。
