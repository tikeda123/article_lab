# lab_10 BTC Article-Support Experiment Report

Source article: https://qiita.com/tikeda123/items/091519af64bd22367c2d

## Executive Summary

This lab now supports the published BTC-only article. The experiment does not try to re-prove `Funding low x risk-on` as an edge. It treats that candidate as a baseline estimate and asks where the estimate breaks.

The core article claim is supported: `Funding low x risk-on` looks interesting at the point-estimate level, but the claim is fragile under small-sample uncertainty, crash-definition changes, 2022 stress-period slicing, cost, execution delay, and leverage path risk.

## Key Metrics For The Article

| topic | value | article_role |
| --- | --- | --- |
| 48h Funding low x risk-on baseline | n=15, mean 1.115%, PF 2.073 | 面白い候補だが結論ではない基準線 |
| 24h Funding low x risk-on baseline | n=15, mean 1.297%, PF 3.122 | 24hでも小標本制約は同じ |
| 48h bootstrap lower bound | mean 5% -0.380% | error on errorの中心証拠 |
| 24h bootstrap lower bound | mean 5% -0.057% | 24hでも下限は0を下回る |
| Crash definition stress | full_sample_q025 mean -1.082%, PF 0.666 | 急落定義を動かすと候補が壊れる |
| 2022 stress period | n=4, mean -0.789%, PF 0.505 | レジーム依存を示す |
| 48h Funding high x risk-off | mean -0.100%, PF 0.935 | 避ける急落候補 |
| 48h all crashes | MaxDD -42.441% | 一律の急落買いは左尾・DDが重い |

## Baseline: Measure First

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

## Error On Error: Bootstrap Uncertainty

| horizon | n | mean_p05_pct | mean_p50_pct | mean_p95_pct | pf_p05 | pf_p50 | pf_p95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | 15 | -0.057 | 1.247 | 2.781 | 0.940 | 3.126 | 13.946 |
| 48h | 15 | -0.380 | 1.155 | 2.479 | 0.798 | 2.135 | 8.714 |

Article reading:

- The 48h point estimate is positive, but the 5% bootstrap lower bound is negative.
- This does not prove the edge is absent. It means the positive expectation cannot be stated strongly with `n=15`.

## Definition Stress

| event_def | n | mean_ret_pct | profit_factor | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- |
| rolling_1_5sigma | 24 | 0.640 | 1.580 | -6.787 | watch |
| rolling_2sigma | 15 | 1.115 | 2.073 | -6.181 | fragile |
| rolling_2_5sigma | 7 | 1.654 | 2.671 | -1.145 | fragile |
| full_sample_q05 | 24 | 2.525 | 4.470 | -9.841 | watch |
| full_sample_q025 | 8 | -1.082 | 0.666 | -18.213 | broken |

Article reading:

- The `full_sample_q025` stress changes the 48h mean from positive to negative.
- This is the clearest definition-dependence result and should remain near the center of the article.

## Regime, Cost, Execution, And Leverage

Subperiod:

| period | n | mean_ret_pct | profit_factor | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- |
| all | 15 | 1.115 | 2.073 | -6.181 | fragile |
| 2020_2021 | 2 | -0.932 | 0.677 | 0.000 | broken |
| 2022_stress | 4 | -0.789 | 0.505 | -0.974 | broken |
| 2023_2024 | 3 | 3.095 | - | 0.000 | fragile |
| 2025_2026 | 6 | 2.077 | 4.626 | -3.378 | fragile |
| post_btc_etf | 8 | 2.588 | 7.025 | -3.378 | fragile |

Cost:

| cost_case | cost_bps | n | mean_ret_pct | profit_factor | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| gross | 0.000 | 15 | 1.115 | 2.073 | -6.181 | fragile |
| base_cost | 10.000 | 15 | 1.015 | 1.952 | -6.368 | fragile |
| cost_x2 | 20.000 | 15 | 0.915 | 1.837 | -6.555 | fragile |
| cost_x5 | 50.000 | 15 | 0.615 | 1.524 | -7.114 | fragile |

Execution:

| entry_case | entry_lag_bars | adverse_entry_bps | n | mean_ret_pct | profit_factor | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| next_open | 1 | 0.000 | 15 | 1.115 | 2.073 | fragile |
| delay_4h | 2 | 0.000 | 15 | 0.475 | 1.324 | fragile |
| delay_8h | 3 | 0.000 | 15 | 1.057 | 1.684 | fragile |
| adverse_25bps | 1 | 25.000 | 15 | 0.865 | 1.782 | fragile |

Leverage:

| leverage | n | mean_ret_pct | worst_mae_pct | maxdd_pct | margin_breach_30pct_count |
| --- | --- | --- | --- | --- | --- |
| 1.000 | 15.000 | 1.115 | -9.426 | -6.181 | 0.000 |
| 2.000 | 15.000 | 2.230 | -18.851 | -11.979 | 0.000 |
| 3.000 | 15.000 | 3.345 | -28.277 | -17.419 | 0.000 |

## Fragility Matrix

| breakable_assumption | stress_case | baseline_value | stressed_value | fragility_status | practical_response |
| --- | --- | --- | --- | --- | --- |
| 小標本でも平均が安定 | 48h bootstrap | 1.115% | -0.380% | fragile | 主張を弱め、サイズを落とす。 |
| 急落定義に依存しない | 48h full_sample_q025 | 1.115% / PF 2.073 | -1.082% / PF 0.666 | broken | 複数定義で確認し、定義ロバスト性を先に公開する。 |
| 特定レジームだけでない | 48h 2022 stress period | 1.115% / PF 2.073 | -0.789% / PF 0.505 | broken | 期間分割で主張を弱める、または限定する。 |
| コスト後も残る | 48h cost_x5 | 1.115% / PF 2.073 | 0.615% / PF 1.524 | fragile | コスト上限を設定し、ネットで報告する。 |
| 想定通り約定できる | 48h delay_4h | 1.115% / PF 2.073 | 0.475% / PF 1.324 | fragile | 約定遅延耐性を確認し、指値/成行ルールを再設計する。 |
| 含み損に耐えられる | 48h 3x leverage | -9.426% | -28.277% | watch | MAE/DDからレバレッジ上限と強制縮小ルールを設計する。 |
| proxyは1つで十分 | 48h S&P500 5D up | 1.115% / PF 2.073 | 0.811% / PF 1.616 | fragile | risk-on proxyを複数化し、因果表現を避ける。 |

## Article-Safe Conclusion

BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、`n=15`、bootstrap下限、crash定義、期間分割、コスト、約定、レバレッジを動かすと、強い主張はできない。ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。
