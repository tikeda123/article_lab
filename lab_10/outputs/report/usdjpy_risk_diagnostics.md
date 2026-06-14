# USDJPY risk diagnostics

## Purpose

This experiment does not forecast the future risk of USDJPY. It shows how risk estimates move when the method, lookback window, and stress dial move.

## Data

- File: `data/usdjpy/USDJPY240.csv`
- Rows: 25,854
- Range: 2010-05-26 20:00:00 to 2026-06-10 20:00:00
- Frequency used for annualization: 1512 4H bars/year

## Window Risk Summary

| window_name | start | end | n | hist_var_99_pct | hist_es_99_pct | normal_var_99_pct | student_t_var_99_pct | maxdd_pct | max_recovery_bars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1y | 2025-06-10 20:00:00 | 2026-06-10 20:00:00 | 1611 | -0.5456 | -0.9201 | -0.4650 | -0.7491 | -4.2093 | 294 |
| 3y | 2023-06-11 20:00:00 | 2026-06-10 20:00:00 | 4830 | -0.6540 | -1.0379 | -0.5476 | -0.8536 | -13.6142 | 3118 |
| 5y | 2021-06-11 20:00:00 | 2026-06-10 20:00:00 | 8055 | -0.6940 | -1.1537 | -0.5778 | -0.8715 | -15.9196 | 3118 |
| full | 2010-05-27 00:00:00 | 2026-06-10 20:00:00 | 25853 | -0.6407 | -0.9760 | -0.5379 | -0.8276 | -20.5293 | 11026 |

## Key Read

- The weakest 99% ES window by this run is `5y`: -1.1537% per 4H bar.
- The largest historical max drawdown window is `full`: -20.529%.
- These values are baselines for doubt, not future upper bounds.

## Stress Dial Examples

| window_name | dial | stress_case | mean_ret_pct | hist_var_99_pct | hist_es_99_pct | maxdd_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 1y | cost_multiplier | cost_x5 | -0.0436 | -0.5956 | -0.9701 | -50.5237 |
| 1y | mean_degradation | mean_down_100pct | 0.0000 | -0.5519 | -0.9264 | -5.6485 |
| 1y | vol_multiplier | vol_x1.5 | 0.0064 | -0.8216 | -1.3833 | -6.5770 |
| 3y | cost_multiplier | cost_x5 | -0.0471 | -0.7040 | -1.0879 | -89.7375 |
| 3y | mean_degradation | mean_down_100pct | 0.0000 | -0.6569 | -1.0408 | -16.6147 |
| 3y | vol_multiplier | vol_x1.5 | 0.0029 | -0.9824 | -1.5583 | -20.9314 |
| 5y | cost_multiplier | cost_x5 | -0.0453 | -0.7440 | -1.2037 | -97.3917 |
| 5y | mean_degradation | mean_down_100pct | 0.0000 | -0.6987 | -1.1584 | -23.5097 |
| 5y | vol_multiplier | vol_x1.5 | 0.0047 | -1.0433 | -1.7329 | -23.5867 |
| full | cost_multiplier | cost_x5 | -0.0478 | -0.6907 | -1.0260 | -99.9996 |
| full | mean_degradation | mean_down_100pct | 0.0000 | -0.6429 | -0.9782 | -33.2032 |
| full | vol_multiplier | vol_x1.5 | 0.0022 | -0.9621 | -1.4651 | -33.2362 |

## Leverage Dial Example

The table below asks how much leverage is compatible with a 30% max allowed drawdown if historical max DD is doubled.

| window_name | dd_multiplier | max_allowed_dd_pct | stressed_maxdd_pct | leverage_limit |
| --- | --- | --- | --- | --- |
| 1y | 2.000 | 30.000 | -8.419 | 3.564 |
| 3y | 2.000 | 30.000 | -27.228 | 1.102 |
| 5y | 2.000 | 30.000 | -31.839 | 0.942 |
| full | 2.000 | 30.000 | -41.059 | 0.731 |

## Figures

- `outputs/figures/usdjpy_risk_method_comparison.png`
- `outputs/figures/usdjpy_rolling_var.png`

## Article Interpretation

- Risk estimates are not single truths. They move with method, lookback, and stress assumptions.
- Historical max DD is not a future loss cap.
- The practical article claim should be: use these numbers as a baseline, then explicitly apply doubt dials.
