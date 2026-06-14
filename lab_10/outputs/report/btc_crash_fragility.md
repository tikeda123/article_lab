# BTC crash fragility experiment

## Purpose

This experiment reuses the `lab_7` BTC crash, Funding Rate, and external risk-on setup, but does not try to prove a tradable edge. It asks where the candidate breaks.

## Data

- Common 4H panel: 13515 rows
- Range: 2017-05-23 04:00:00 to 2026-06-05 16:00:00
- Full-sample lower 5% BTC 4H threshold: -2.3918%
- Full-sample lower 2.5% BTC 4H threshold: -3.4308%
- Primary condition: `rolling_2sigma x nasdaq_5d_up x lower_20_or_negative`

## Baseline Candidate

| horizon | group | n | mean_ret_pct | win_rate_pct | profit_factor | mean_mae_pct | worst_mae_pct | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | all_funding_covered_crashes | 201 | 0.341 | 53.234 | 1.260 | -3.727 | -36.617 | -30.823 | watch |
| 24h | funding_low_x_risk_on | 15 | 1.297 | 66.667 | 3.122 | -2.651 | -9.426 | -3.470 | fragile |
| 24h | funding_high_x_risk_off | 26 | -0.242 | 42.308 | 0.837 | -4.330 | -12.258 | -19.250 | broken |
| 48h | all_funding_covered_crashes | 201 | 0.603 | 61.194 | 1.368 | -4.716 | -36.617 | -42.441 | watch |
| 48h | funding_low_x_risk_on | 15 | 1.115 | 73.333 | 2.073 | -3.249 | -9.426 | -6.181 | fragile |
| 48h | funding_high_x_risk_off | 26 | -0.100 | 53.846 | 0.935 | -5.347 | -13.622 | -18.777 | broken |
| 5d | all_funding_covered_crashes | 201 | 0.647 | 56.716 | 1.231 | -7.078 | -50.636 | -70.074 | watch |
| 5d | funding_low_x_risk_on | 15 | 2.194 | 66.667 | 2.907 | -4.454 | -14.642 | -12.193 | fragile |
| 5d | funding_high_x_risk_off | 26 | 0.089 | 61.538 | 1.033 | -7.458 | -28.058 | -25.112 | watch |

## Cost Stress: Funding low x risk-on

| horizon | cost_case | cost_bps | n | mean_ret_pct | profit_factor | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | gross | 0.000 | 15 | 1.297 | 3.122 | -3.470 | fragile |
| 24h | base_cost | 10.000 | 15 | 1.197 | 2.857 | -3.567 | fragile |
| 24h | cost_x2 | 20.000 | 15 | 1.097 | 2.611 | -3.663 | fragile |
| 24h | cost_x5 | 50.000 | 15 | 0.797 | 1.988 | -3.952 | fragile |
| 48h | gross | 0.000 | 15 | 1.115 | 2.073 | -6.181 | fragile |
| 48h | base_cost | 10.000 | 15 | 1.015 | 1.952 | -6.368 | fragile |
| 48h | cost_x2 | 20.000 | 15 | 0.915 | 1.837 | -6.555 | fragile |
| 48h | cost_x5 | 50.000 | 15 | 0.615 | 1.524 | -7.114 | fragile |

## Entry and Execution Stress: Funding low x risk-on

| horizon | entry_case | entry_lag_bars | adverse_entry_bps | n | mean_ret_pct | profit_factor | fragility_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | next_open | 1 | 0.000 | 15 | 1.297 | 3.122 | fragile |
| 24h | adverse_10bps | 1 | 10.000 | 15 | 1.197 | 2.857 | fragile |
| 24h | adverse_25bps | 1 | 25.000 | 15 | 1.048 | 2.494 | fragile |
| 24h | delay_4h | 2 | 0.000 | 15 | 0.770 | 1.771 | fragile |
| 24h | delay_8h | 3 | 0.000 | 15 | 0.693 | 1.886 | fragile |
| 48h | next_open | 1 | 0.000 | 15 | 1.115 | 2.073 | fragile |
| 48h | adverse_10bps | 1 | 10.000 | 15 | 1.015 | 1.952 | fragile |
| 48h | adverse_25bps | 1 | 25.000 | 15 | 0.865 | 1.782 | fragile |
| 48h | delay_4h | 2 | 0.000 | 15 | 0.475 | 1.324 | fragile |
| 48h | delay_8h | 3 | 0.000 | 15 | 1.057 | 1.684 | fragile |

## Crash Definition Robustness: Funding low x risk-on, 48h

| event_def | n | mean_ret_pct | profit_factor | mean_mae_pct | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| full_sample_q025 | 8 | -1.082 | 0.666 | -6.811 | -18.213 | broken |
| full_sample_q05 | 24 | 2.525 | 4.470 | -3.035 | -9.841 | watch |
| rolling_1_5sigma | 24 | 0.640 | 1.580 | -3.612 | -6.787 | watch |
| rolling_2_5sigma | 7 | 1.654 | 2.671 | -4.440 | -1.145 | fragile |
| rolling_2sigma | 15 | 1.115 | 2.073 | -3.249 | -6.181 | fragile |

## Risk-on Proxy Robustness: Funding low x risk-on, 48h

| risk_env | n | mean_ret_pct | profit_factor | mean_mae_pct | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| broad_3of4_5d_up | 14 | 0.937 | 1.745 | -3.631 | -6.181 | fragile |
| nasdaq_5d_gt_1pct | 12 | 0.779 | 1.600 | -2.930 | -6.181 | fragile |
| nasdaq_5d_up | 15 | 1.115 | 2.073 | -3.249 | -6.181 | fragile |
| sp500_5d_gt_1pct | 9 | 1.697 | 3.394 | -2.295 | -0.974 | fragile |
| sp500_5d_up | 16 | 0.811 | 1.616 | -3.512 | -6.181 | fragile |

## Funding Definition Robustness: Funding low x risk-on, 48h

| funding_case | n | mean_ret_pct | profit_factor | mean_mae_pct | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| lower_10_or_negative | 13 | 1.386 | 2.768 | -3.133 | -3.378 | fragile |
| lower_20_only | 15 | 1.115 | 2.073 | -3.249 | -6.181 | fragile |
| lower_20_or_negative | 15 | 1.115 | 2.073 | -3.249 | -6.181 | fragile |
| negative | 13 | 1.386 | 2.768 | -3.133 | -3.378 | fragile |

## Subperiod Stability: Funding low x risk-on, 48h

| period | n | mean_ret_pct | profit_factor | mean_mae_pct | maxdd_pct | fragility_status |
| --- | --- | --- | --- | --- | --- | --- |
| 2020_2021 | 2 | -0.932 | 0.677 | -9.289 | 0.000 | broken |
| 2022_stress | 4 | -0.789 | 0.505 | -4.245 | -0.974 | broken |
| 2023_2024 | 3 | 3.095 | - | -1.409 | 0.000 | fragile |
| 2025_2026 | 6 | 2.077 | 4.626 | -1.493 | -3.378 | fragile |
| all | 15 | 1.115 | 2.073 | -3.249 | -6.181 | fragile |
| post_btc_etf | 8 | 2.588 | 7.025 | -1.502 | -3.378 | fragile |

## Bootstrap Uncertainty

| horizon | n | mean_p05_pct | mean_p50_pct | mean_p95_pct | pf_p05 | pf_p50 | pf_p95 | is_ci_fragile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24h | 15 | -0.057 | 1.247 | 2.781 | 0.940 | 3.126 | 13.946 | True |
| 48h | 15 | -0.380 | 1.155 | 2.479 | 0.798 | 2.135 | 8.714 | True |

## Figures

- `outputs/figures/btc_cost_stress_heatmap.png`
- `outputs/figures/btc_entry_execution_stress.png`
- `outputs/figures/btc_definition_robustness_heatmap.png`
- `outputs/figures/btc_risk_env_robustness.png`
- `outputs/figures/btc_funding_definition_robustness.png`
- `outputs/figures/btc_leverage_tolerance.png`
- `outputs/figures/btc_bootstrap_mean_return.png`

## Article Interpretation

- `Funding low x risk-on` remains an interesting candidate, but the primary 24h/48h condition has very small `n`.
- The candidate must be discussed through sample size, cost, entry assumptions, definition changes, period dependence, and left-tail path risk.
- The clean article claim is not "buy BTC crashes"; it is "an edge-looking subgroup still needs error-on-error diagnostics."
