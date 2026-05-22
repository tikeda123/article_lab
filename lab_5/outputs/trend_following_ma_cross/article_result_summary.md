# Article Result Summary

Scope: USDJPY MA cross trend-following experiment.

- Strategy: MA 20 / 80
- Execution: close-confirmed signal, next-open trade
- Main cost: 1.0 round-trip pips
- Main period: 2023-01-01 <= timestamp < 2026-01-01
- Development period: 2023-2024
- OOS period: 2025
- No WFO and no OOS re-optimization

## Baseline Metrics

| timeframe | trade_count | total_pnl_pips | win_rate_pct | profit_factor | max_drawdown_pips | avg_win_loss_ratio | top_5pct_win_contribution_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60m | 292.000 | -140.100 | 35.274 | 0.990 | 2067.100 | 1.816 | 21.428 |
| 240m | 70.000 | 1746.600 | 41.429 | 1.304 | 2120.200 | 1.843 | 28.014 |

## OOS-Centered Reading

The main result is not that the 240m strategy won over the full period.
The important diagnostic result is that 240m looked strong in 2023-2024 and then broke in the fixed 2025 OOS period.
This makes the experiment useful as a backtest-skepticism exercise rather than a parameter search.

## Cost Sensitivity

| timeframe | cost_pips | total_pnl_pips | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- |
| 60m | 0.000 | 151.900 | 1.011 | 1901.100 |
| 60m | 0.800 | -81.700 | 0.994 | 2033.900 |
| 60m | 1.000 | -140.100 | 0.990 | 2067.100 |
| 60m | 2.000 | -432.100 | 0.968 | 2233.100 |
| 240m | 0.000 | 1816.600 | 1.318 | 2097.200 |
| 240m | 0.800 | 1760.600 | 1.307 | 2115.600 |
| 240m | 1.000 | 1746.600 | 1.304 | 2120.200 |
| 240m | 2.000 | 1676.600 | 1.290 | 2143.200 |

## Buy & Hold / Always Long Comparison

| variant | timeframe | period | trade_count | total_pnl_pips | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- | --- | --- |
| ma_cross_long_short | 60m | full_2023_2025 | 292.000 | -140.100 | 0.990 | 2067.100 |
| ma_cross_long_only | 60m | full_2023_2025 | 146.000 | 1215.300 | 1.181 | 1407.500 |
| always_long_buy_hold | 60m | full_2023_2025 | 1.000 | 2569.700 | inf | -0.000 |
| ma_cross_long_short | 60m | dev_2023_2024 | 201.000 | -235.900 | 0.976 | 1586.700 |
| ma_cross_long_only | 60m | dev_2023_2024 | 100.000 | 1203.500 | 1.257 | 1099.700 |
| always_long_buy_hold | 60m | dev_2023_2024 | 1.000 | 2640.900 | inf | -0.000 |
| ma_cross_long_short | 60m | oos_2025 | 92.000 | 75.500 | 1.021 | 1014.900 |
| ma_cross_long_only | 60m | oos_2025 | 46.000 | 11.800 | 1.006 | 1186.000 |
| always_long_buy_hold | 60m | oos_2025 | 1.000 | -52.900 | 0.000 | -0.000 |
| ma_cross_long_short | 240m | full_2023_2025 | 70.000 | 1746.600 | 1.304 | 2120.200 |
| ma_cross_long_only | 240m | full_2023_2025 | 35.000 | 2164.600 | 2.127 | 505.000 |
| always_long_buy_hold | 240m | full_2023_2025 | 1.000 | 2581.600 | inf | -0.000 |
| ma_cross_long_short | 240m | dev_2023_2024 | 42.000 | 2569.300 | 1.787 | 1436.000 |
| ma_cross_long_only | 240m | dev_2023_2024 | 21.000 | 2603.800 | 3.276 | 451.800 |
| always_long_buy_hold | 240m | dev_2023_2024 | 1.000 | 2637.300 | inf | -0.000 |
| ma_cross_long_short | 240m | oos_2025 | 29.000 | -808.000 | 0.686 | 2120.200 |
| ma_cross_long_only | 240m | oos_2025 | 15.000 | -424.500 | 0.508 | 505.000 |
| always_long_buy_hold | 240m | oos_2025 | 1.000 | -41.000 | 0.000 | -0.000 |

## Direction Breakdown

| timeframe | period | direction | trade_count | total_pnl_pips | win_rate_pct | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60m | full_2023_2025 | long | 146.000 | 1215.300 | 41.781 | 1.181 | 1407.500 |
| 60m | full_2023_2025 | short | 146.000 | -1355.400 | 28.767 | 0.801 | 1720.400 |
| 60m | dev_2023_2024 | long | 100.000 | 1203.500 | 39.000 | 1.257 | 1099.700 |
| 60m | dev_2023_2024 | short | 101.000 | -1439.400 | 23.762 | 0.723 | 1591.900 |
| 60m | oos_2025 | long | 46.000 | 11.800 | 47.826 | 1.006 | 1186.000 |
| 60m | oos_2025 | short | 46.000 | 63.700 | 39.130 | 1.039 | 488.600 |
| 240m | full_2023_2025 | long | 35.000 | 2164.600 | 54.286 | 2.127 | 505.000 |
| 240m | full_2023_2025 | short | 35.000 | -418.000 | 28.571 | 0.891 | 1707.400 |
| 240m | dev_2023_2024 | long | 21.000 | 2603.800 | 61.905 | 3.276 | 451.800 |
| 240m | dev_2023_2024 | short | 21.000 | -34.500 | 33.333 | 0.984 | 1405.600 |
| 240m | oos_2025 | long | 15.000 | -424.500 | 40.000 | 0.508 | 505.000 |
| 240m | oos_2025 | short | 14.000 | -383.500 | 21.429 | 0.775 | 1707.400 |

## Top Winning Trade Exclusion

| timeframe | excluded_top_win_pct | total_pnl_pips | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- |
| 60m | 0.000 | -140.100 | 0.990 | 2067.100 |
| 60m | 1.000 | -1236.200 | 0.908 | 2588.200 |
| 60m | 5.000 | -3001.400 | 0.778 | 3547.700 |
| 60m | 10.000 | -4571.900 | 0.661 | 4954.100 |
| 240m | 0.000 | 1746.600 | 1.304 | 2120.200 |
| 240m | 1.000 | 629.100 | 1.109 | 2120.200 |
| 240m | 5.000 | -352.900 | 0.939 | 2120.200 |
| 240m | 10.000 | -1127.300 | 0.804 | 2120.200 |

## Top Winning Trade Concentration

| timeframe | measure | selected_trade_count | selected_pnl_pips | share_of_winning_pips_pct | share_of_total_net_pnl_pct |
| --- | --- | --- | --- | --- | --- |
| 60m | top_1_winning_trades | 1.000 | 575.000 | 4.306 | -410.421 |
| 60m | top_3_winning_trades | 3.000 | 1616.100 | 12.103 | -1153.533 |
| 60m | top_5_winning_trades | 5.000 | 2492.300 | 18.664 | -1778.944 |
| 60m | top_1pct_winning_trades | 2.000 | 1096.100 | 8.209 | -782.370 |
| 60m | top_5pct_winning_trades | 6.000 | 2861.300 | 21.428 | -2042.327 |
| 60m | top_10pct_winning_trades | 11.000 | 4431.800 | 33.189 | -3163.312 |
| 240m | top_1_winning_trades | 1.000 | 1117.500 | 14.911 | 63.981 |
| 240m | top_3_winning_trades | 3.000 | 2873.900 | 38.347 | 164.543 |
| 240m | top_5_winning_trades | 5.000 | 4165.600 | 55.583 | 238.498 |
| 240m | top_1pct_winning_trades | 1.000 | 1117.500 | 14.911 | 63.981 |
| 240m | top_5pct_winning_trades | 2.000 | 2099.500 | 28.014 | 120.205 |
| 240m | top_10pct_winning_trades | 3.000 | 2873.900 | 38.347 | 164.543 |

## Random Direction Comparison

| timeframe | total_pnl_pips | profit_factor | actual_total_pnl_percentile | actual_profit_factor_percentile |
| --- | --- | --- | --- | --- |
| 60m | -140.100 | 0.990 | 50.300 | 50.300 |
| 240m | 1746.600 | 1.304 | 77.500 | 77.500 |

## Random Direction Test Design

| timeframe | random_runs | entry_timing_fixed | trade_count_fixed | holding_periods_fixed | direction_only_randomized | long_short_ratio_preserved | random_total_pnl_exceed_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60m | 1000.000 | True | True | True | True | False | 49.700 |
| 240m | 1000.000 | True | True | True | True | False | 22.500 |

## Dev vs OOS Parameter Surface

| timeframe | short_window | long_window | dev_profit_factor | oos_profit_factor | pf_delta_oos_minus_dev | dev_positive_oos_positive |
| --- | --- | --- | --- | --- | --- | --- |
| 240m | 30.000 | 120.000 | 5.241 | 0.647 | -4.594 | False |
| 240m | 30.000 | 160.000 | 4.182 | 0.642 | -3.540 | False |
| 240m | 20.000 | 200.000 | 4.173 | 0.369 | -3.804 | False |
| 240m | 20.000 | 120.000 | 4.083 | 0.596 | -3.486 | False |
| 240m | 40.000 | 160.000 | 3.834 | 0.781 | -3.052 | False |
| 60m | 10.000 | 200.000 | 1.404 | 0.511 | -0.894 | False |
| 60m | 10.000 | 160.000 | 1.385 | 0.576 | -0.809 | False |
| 60m | 20.000 | 160.000 | 1.356 | 0.513 | -0.843 | False |
| 60m | 20.000 | 200.000 | 1.306 | 0.557 | -0.748 | False |
| 60m | 10.000 | 60.000 | 1.252 | 1.240 | -0.012 | True |

## Entry Delay Sensitivity

| timeframe | entry_delay_bars | total_pnl_pips | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- |
| 60m | 0.000 | -140.100 | 0.990 | 2067.100 |
| 60m | 1.000 | -1152.900 | 0.919 | 2850.200 |
| 60m | 2.000 | -1232.100 | 0.913 | 2680.100 |
| 60m | 4.000 | -1401.900 | 0.903 | 2277.400 |
| 240m | 0.000 | 1746.600 | 1.304 | 2120.200 |
| 240m | 1.000 | 2416.600 | 1.421 | 2019.300 |
| 240m | 2.000 | 2551.400 | 1.480 | 1647.400 |
| 240m | 4.000 | 2286.800 | 1.449 | 1732.400 |

Lag 1-2 improving on 240m should not be read as a universal rule to enter late.
It only suggests that the 240m signal captured a longer time-scale continuation in this sample.

## Monthly PnL and Time Under Water

| timeframe | max_consecutive_losses | max_time_under_water_days | max_time_under_water_trades | monthly_win_rate_pct | worst_month_pips | best_month_pips | ends_underwater |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60m | 10.000 | 866.583 | 228.000 | 58.333 | -594.800 | 1064.800 | True |
| 240m | 6.000 | 344.333 | 23.000 | 55.172 | -571.100 | 982.000 | True |

## Fixed Parameter OOS

| timeframe | period | cost_pips | total_pnl_pips | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- | --- |
| 60m | dev_2023_2024 | 0.800 | -195.700 | 0.980 | 1574.700 |
| 60m | oos_2025 | 0.800 | 93.900 | 1.026 | 1009.300 |
| 60m | dev_2023_2024 | 1.000 | -235.900 | 0.976 | 1586.700 |
| 60m | oos_2025 | 1.000 | 75.500 | 1.021 | 1014.900 |
| 60m | dev_2023_2024 | 2.000 | -436.900 | 0.956 | 1712.800 |
| 60m | oos_2025 | 2.000 | -16.500 | 0.996 | 1042.900 |
| 240m | dev_2023_2024 | 0.800 | 2577.700 | 1.791 | 1433.600 |
| 240m | oos_2025 | 0.800 | -802.200 | 0.687 | 2115.600 |
| 240m | dev_2023_2024 | 1.000 | 2569.300 | 1.787 | 1436.000 |
| 240m | oos_2025 | 1.000 | -808.000 | 0.686 | 2120.200 |
| 240m | dev_2023_2024 | 2.000 | 2527.300 | 1.769 | 1448.000 |
| 240m | oos_2025 | 2.000 | -837.000 | 0.677 | 2143.200 |

## Interpretation Boundary

This experiment does not prove a permanent trend-following edge.
It checks whether the expected trend-following PnL structure appears under this market, period, timeframe, and fixed-cost assumption.
The results should be interpreted as an article experiment, not investment advice or a production trading system.
