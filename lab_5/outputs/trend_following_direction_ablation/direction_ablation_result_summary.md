# Direction Ablation Result Summary

Scope: MA 20/80 USDJPY trend-following ablation.

- baseline_long_short: original long/short reversal logic
- long_only: short signals become flat exits
- short_filter_ma80_slope: short entries only when MA80 is falling over 20 bars
- short_filter_ma200_down: short entries only when close is below a falling MA200
- Execution and cost assumptions match the base experiment

## Full Period Metrics

| variant | timeframe | trade_count | total_pnl_pips | win_rate_pct | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_long_short | 60m | 292.000 | -140.100 | 35.274 | 0.990 | 2067.100 |
| baseline_long_short | 240m | 70.000 | 1746.600 | 41.429 | 1.304 | 2120.200 |
| long_only | 60m | 146.000 | 1215.300 | 41.781 | 1.181 | 1407.500 |
| long_only | 240m | 35.000 | 2164.600 | 54.286 | 2.127 | 505.000 |
| short_filter_ma80_slope | 60m | 268.000 | -657.700 | 36.940 | 0.947 | 2447.200 |
| short_filter_ma80_slope | 240m | 61.000 | 2536.600 | 42.623 | 1.615 | 1643.700 |
| short_filter_ma200_down | 60m | 261.000 | 863.000 | 35.632 | 1.079 | 1276.200 |
| short_filter_ma200_down | 240m | 58.000 | 1915.400 | 43.103 | 1.465 | 1065.300 |

## Fixed OOS Metrics

| variant | timeframe | trade_count | total_pnl_pips | win_rate_pct | profit_factor | max_drawdown_pips | period |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_long_short | 60m | 201.000 | -235.900 | 31.343 | 0.976 | 1586.700 | dev_2023_2024 |
| baseline_long_short | 60m | 92.000 | 75.500 | 43.478 | 1.021 | 1014.900 | oos_2025 |
| baseline_long_short | 240m | 42.000 | 2569.300 | 47.619 | 1.787 | 1436.000 | dev_2023_2024 |
| baseline_long_short | 240m | 29.000 | -808.000 | 31.034 | 0.686 | 2120.200 | oos_2025 |
| long_only | 60m | 100.000 | 1203.500 | 39.000 | 1.257 | 1099.700 | dev_2023_2024 |
| long_only | 60m | 46.000 | 11.800 | 47.826 | 1.006 | 1186.000 | oos_2025 |
| long_only | 240m | 21.000 | 2603.800 | 61.905 | 3.276 | 451.800 | dev_2023_2024 |
| long_only | 240m | 15.000 | -424.500 | 40.000 | 0.508 | 505.000 | oos_2025 |
| short_filter_ma80_slope | 60m | 178.000 | -332.900 | 33.146 | 0.962 | 1994.100 | dev_2023_2024 |
| short_filter_ma80_slope | 60m | 91.000 | -345.100 | 43.956 | 0.906 | 1463.800 | oos_2025 |
| short_filter_ma80_slope | 240m | 34.000 | 3399.100 | 52.941 | 2.604 | 547.100 | dev_2023_2024 |
| short_filter_ma80_slope | 240m | 28.000 | -847.800 | 28.571 | 0.595 | 1643.700 | oos_2025 |
| short_filter_ma200_down | 60m | 166.000 | 1375.200 | 33.735 | 1.186 | 1025.800 | dev_2023_2024 |
| short_filter_ma200_down | 60m | 95.000 | -512.200 | 38.947 | 0.855 | 1276.200 | oos_2025 |
| short_filter_ma200_down | 240m | 34.000 | 2176.000 | 50.000 | 1.783 | 1026.200 | dev_2023_2024 |
| short_filter_ma200_down | 240m | 25.000 | -245.900 | 32.000 | 0.827 | 1065.300 | oos_2025 |

## Direction Breakdown

| variant | timeframe | period | direction | trade_count | total_pnl_pips | profit_factor | max_drawdown_pips |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_long_short | 60m | full_2023_2025 | short | 146.000 | -1355.400 | 0.801 | 1720.400 |
| baseline_long_short | 60m | full_2023_2025 | long | 146.000 | 1215.300 | 1.181 | 1407.500 |
| baseline_long_short | 60m | dev_2023_2024 | short | 101.000 | -1439.400 | 0.723 | 1591.900 |
| baseline_long_short | 60m | dev_2023_2024 | long | 100.000 | 1203.500 | 1.257 | 1099.700 |
| baseline_long_short | 60m | oos_2025 | short | 46.000 | 63.700 | 1.039 | 488.600 |
| baseline_long_short | 60m | oos_2025 | long | 46.000 | 11.800 | 1.006 | 1186.000 |
| baseline_long_short | 240m | full_2023_2025 | short | 35.000 | -418.000 | 0.891 | 1707.400 |
| baseline_long_short | 240m | full_2023_2025 | long | 35.000 | 2164.600 | 2.127 | 505.000 |
| baseline_long_short | 240m | dev_2023_2024 | short | 21.000 | -34.500 | 0.984 | 1405.600 |
| baseline_long_short | 240m | dev_2023_2024 | long | 21.000 | 2603.800 | 3.276 | 451.800 |
| baseline_long_short | 240m | oos_2025 | long | 15.000 | -424.500 | 0.508 | 505.000 |
| baseline_long_short | 240m | oos_2025 | short | 14.000 | -383.500 | 0.775 | 1707.400 |
| long_only | 60m | full_2023_2025 | long | 146.000 | 1215.300 | 1.181 | 1407.500 |
| long_only | 60m | dev_2023_2024 | long | 100.000 | 1203.500 | 1.257 | 1099.700 |
| long_only | 60m | oos_2025 | long | 46.000 | 11.800 | 1.006 | 1186.000 |
| long_only | 240m | full_2023_2025 | long | 35.000 | 2164.600 | 2.127 | 505.000 |
| long_only | 240m | dev_2023_2024 | long | 21.000 | 2603.800 | 3.276 | 451.800 |
| long_only | 240m | oos_2025 | long | 15.000 | -424.500 | 0.508 | 505.000 |
| short_filter_ma80_slope | 60m | full_2023_2025 | short | 122.000 | -1873.000 | 0.677 | 2012.600 |
| short_filter_ma80_slope | 60m | full_2023_2025 | long | 146.000 | 1215.300 | 1.181 | 1407.500 |
| short_filter_ma80_slope | 60m | dev_2023_2024 | short | 78.000 | -1536.400 | 0.630 | 1998.100 |
| short_filter_ma80_slope | 60m | dev_2023_2024 | long | 100.000 | 1203.500 | 1.257 | 1099.700 |
| short_filter_ma80_slope | 60m | oos_2025 | short | 45.000 | -356.900 | 0.786 | 377.600 |
| short_filter_ma80_slope | 60m | oos_2025 | long | 46.000 | 11.800 | 1.006 | 1186.000 |
| short_filter_ma80_slope | 240m | full_2023_2025 | short | 26.000 | 372.000 | 1.169 | 1230.900 |
| short_filter_ma80_slope | 240m | full_2023_2025 | long | 35.000 | 2164.600 | 2.127 | 505.000 |
| short_filter_ma80_slope | 240m | dev_2023_2024 | short | 13.000 | 795.300 | 1.816 | 377.300 |
| short_filter_ma80_slope | 240m | dev_2023_2024 | long | 21.000 | 2603.800 | 3.276 | 451.800 |
| short_filter_ma80_slope | 240m | oos_2025 | long | 15.000 | -424.500 | 0.508 | 505.000 |
| short_filter_ma80_slope | 240m | oos_2025 | short | 13.000 | -423.300 | 0.656 | 1230.900 |
| short_filter_ma200_down | 60m | full_2023_2025 | short | 115.000 | -352.300 | 0.916 | 754.900 |
| short_filter_ma200_down | 60m | full_2023_2025 | long | 146.000 | 1215.300 | 1.181 | 1407.500 |
| short_filter_ma200_down | 60m | dev_2023_2024 | short | 66.000 | 171.700 | 1.064 | 754.900 |
| short_filter_ma200_down | 60m | dev_2023_2024 | long | 100.000 | 1203.500 | 1.257 | 1099.700 |
| short_filter_ma200_down | 60m | oos_2025 | long | 46.000 | 11.800 | 1.006 | 1186.000 |
| short_filter_ma200_down | 60m | oos_2025 | short | 49.000 | -524.000 | 0.655 | 741.400 |
| short_filter_ma200_down | 240m | full_2023_2025 | short | 23.000 | -249.200 | 0.886 | 1084.700 |
| short_filter_ma200_down | 240m | full_2023_2025 | long | 35.000 | 2164.600 | 2.127 | 505.000 |
| short_filter_ma200_down | 240m | dev_2023_2024 | short | 13.000 | -427.800 | 0.738 | 1084.700 |
| short_filter_ma200_down | 240m | dev_2023_2024 | long | 21.000 | 2603.800 | 3.276 | 451.800 |
| short_filter_ma200_down | 240m | oos_2025 | long | 15.000 | -424.500 | 0.508 | 505.000 |
| short_filter_ma200_down | 240m | oos_2025 | short | 10.000 | 178.600 | 1.319 | 560.300 |

## Interpretation Boundary

These are ablations, not tuned production rules.
If a short-suppression rule improves the full period but fails OOS, it should be treated as diagnostic evidence rather than a selected strategy.
