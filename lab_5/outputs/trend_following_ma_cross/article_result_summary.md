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

## Direction Breakdown

| timeframe | period | direction | trade_count | total_pnl_pips | win_rate_pct | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60m | full_2023_2025 | long | 146.000 | 1215.300 | 41.781 | 1.181 | 1407.500 |
| 60m | full_2023_2025 | short | 146.000 | -1355.400 | 28.767 | 0.801 | 1720.400 |
| 60m | dev_2023_2024 | long | 100.000 | 1203.500 | 39.000 | 1.257 | 1099.700 |
| 60m | dev_2023_2024 | short | 101.000 | -1435.800 | 23.762 | 0.723 | 1591.900 |
| 60m | oos_2025 | long | 46.000 | 11.800 | 47.826 | 1.006 | 1186.000 |
| 60m | oos_2025 | short | 45.000 | 80.400 | 40.000 | 1.050 | 488.600 |
| 240m | full_2023_2025 | long | 35.000 | 2164.600 | 54.286 | 2.127 | 505.000 |
| 240m | full_2023_2025 | short | 35.000 | -418.000 | 28.571 | 0.891 | 1707.400 |
| 240m | dev_2023_2024 | long | 21.000 | 2502.000 | 61.905 | 3.187 | 451.800 |
| 240m | dev_2023_2024 | short | 21.000 | -34.500 | 33.333 | 0.984 | 1405.600 |
| 240m | oos_2025 | long | 14.000 | -337.400 | 42.857 | 0.565 | 505.000 |
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

## Random Direction Comparison

| timeframe | total_pnl_pips | profit_factor | actual_total_pnl_percentile | actual_profit_factor_percentile |
| --- | --- | --- | --- | --- |
| 60m | -140.100 | 0.990 | 50.300 | 50.300 |
| 240m | 1746.600 | 1.304 | 77.500 | 77.500 |

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
