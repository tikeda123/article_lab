# BTC crash rebound interaction model experiment

## Setup

```text
BTC crash future return
= BTC crash event
+ Funding
+ external risk environment
+ Funding x external risk environment
```

- Frequency: 4H.
- Primary crash definition: rolling 2 sigma, using the previous 180 4H bars.
- Robustness crash definitions: rolling 1.5 sigma and full-sample lower 5%.
- Primary external risk-on: Nasdaq 5-day return > 0.
- Robustness external risk-on: S&P500 5-day return > 0 and broad 3-of-4 risk-on across Nasdaq/S&P500/Dow/DAX.
- Funding low: expanding lower 20% or negative Funding Rate known at signal time.
- Funding high: expanding upper 20%.
- Entry: next 4H open after signal confirmation.
- Exits: 24h, 48h, and supplementary 5d open-to-open.
- Event spacing: 24h cooldown.
- Metrics are gross of fees, spread, and slippage.
- P-values are naive and do not fully correct for time-series dependence.

## Data Coverage

- Common 4H panel: 13515 rows, 2017-05-23 04:00:00 to 2026-06-05 16:00:00.
- Full-sample lower 5% BTC 4H threshold: -2.3918%.

## Verdict

| question | answer | note |
| --- | --- | --- |
| 主条件は全急落より良いか | yes | rolling 2 sigma x Nasdaq 5d upでは、Funding低位 x risk-onが24h/48hとも全急落を上回る。 |
| Funding単体より改善するか | mixed | 24h/48hとも改善はあるが、差は大きくない。主役はFunding単体ではなく条件分類。 |
| risk-on単体より改善するか | mixed | 24hは改善、48hはrisk-on単体が強い。交互作用項の主張は慎重にする。 |
| 避けるべき急落は見えるか | yes_directionally | Funding高位 x risk-offは24h/48hで弱く、避ける候補として使いやすい。 |

## Primary Results

| event_def | horizon | risk_env | group | n | mean_ret_pct | median_ret_pct | win_rate_pct | profit_factor | t_stat | mean_mae_pct | worst_mae_pct | mean_mfe_pct | maxdd_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rolling_2sigma | 24h | nasdaq_5d_up | all_funding_covered_crashes | 201 | 0.341 | 0.290 | 53.234 | 1.260 | 1.190 | -3.727 | -36.617 | 3.051 | -30.823 |
| rolling_2sigma | 24h | nasdaq_5d_up | funding_high_x_risk_off | 26 | -0.242 | -0.779 | 42.308 | 0.837 | -0.365 | -4.330 | -12.258 | 2.605 | -19.250 |
| rolling_2sigma | 24h | nasdaq_5d_up | funding_low_only | 44 | 1.258 | 0.889 | 63.636 | 2.528 | 2.096 | -3.051 | -20.252 | 3.808 | -19.097 |
| rolling_2sigma | 24h | nasdaq_5d_up | funding_low_x_risk_on | 15 | 1.297 | 0.726 | 66.667 | 3.122 | 1.444 | -2.651 | -9.426 | 3.843 | -3.470 |
| rolling_2sigma | 24h | nasdaq_5d_up | risk_on_only | 88 | 0.423 | 0.331 | 54.545 | 1.406 | 1.143 | -3.418 | -36.617 | 2.861 | -27.800 |
| rolling_2sigma | 48h | nasdaq_5d_up | all_funding_covered_crashes | 201 | 0.603 | 0.851 | 61.194 | 1.368 | 1.647 | -4.716 | -36.617 | 4.155 | -42.441 |
| rolling_2sigma | 48h | nasdaq_5d_up | funding_high_x_risk_off | 26 | -0.100 | 0.254 | 53.846 | 0.935 | -0.138 | -5.347 | -13.622 | 3.203 | -18.777 |
| rolling_2sigma | 48h | nasdaq_5d_up | funding_low_only | 44 | 0.873 | 1.885 | 68.182 | 1.518 | 1.007 | -4.142 | -21.174 | 5.022 | -23.468 |
| rolling_2sigma | 48h | nasdaq_5d_up | funding_low_x_risk_on | 15 | 1.115 | 2.416 | 73.333 | 2.073 | 1.241 | -3.249 | -9.426 | 4.928 | -6.181 |
| rolling_2sigma | 48h | nasdaq_5d_up | risk_on_only | 88 | 1.431 | 1.322 | 67.045 | 2.375 | 3.024 | -4.025 | -36.617 | 4.323 | -16.394 |

## Figures

- `figures/figure02_primary_48h_mean_return.png`
- `figures/figure03_four_cell_24h_mean_return.png`
- `figures/figure04_four_cell_48h_mean_return.png`
- `figures/figure05_risk_proxy_low_funding_risk_on.png`
- `figures/figure06_interaction_coefficients.png`

## Primary Regression Coefficients

The intercept is `funding_not_low x risk_off`. The interaction coefficient is the extra effect of being both `funding_low` and `risk_on` beyond the separate Funding and risk-on effects.

| event_def | horizon | risk_env | term | coef_pct | se_pct | t_stat | naive_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rolling_2sigma | 24h | nasdaq_5d_up | intercept_not_low_risk_off | -0.0547 | 0.4430 | -0.1235 | 0.9019 |
| rolling_2sigma | 24h | nasdaq_5d_up | funding_low | 1.2916 | 0.8744 | 1.4770 | 0.1413 |
| rolling_2sigma | 24h | nasdaq_5d_up | risk_on | 0.2982 | 0.6497 | 0.4591 | 0.6467 |
| rolling_2sigma | 24h | nasdaq_5d_up | funding_low_x_risk_on | -0.2378 | 1.4455 | -0.1645 | 0.8695 |
| rolling_2sigma | 48h | nasdaq_5d_up | intercept_not_low_risk_off | -0.3134 | 0.5637 | -0.5560 | 0.5788 |
| rolling_2sigma | 48h | nasdaq_5d_up | funding_low | 1.0609 | 1.1127 | 0.9535 | 0.3415 |
| rolling_2sigma | 48h | nasdaq_5d_up | risk_on | 1.8090 | 0.8266 | 2.1884 | 0.0298 |
| rolling_2sigma | 48h | nasdaq_5d_up | funding_low_x_risk_on | -1.4415 | 1.8393 | -0.7838 | 0.4341 |

## Robustness Contrasts

| event_def | horizon | risk_env | low_on_minus_all_pct | low_on_minus_funding_low_only_pct | low_on_minus_risk_on_only_pct | high_off_minus_all_pct | difference_in_differences_pct | mean_low_on_pct | mean_low_off_pct | mean_not_low_on_pct | mean_not_low_off_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full_sample_q05 | 24h | broad_3of4_5d_up | 1.265 | 0.332 | 1.414 | -0.268 | 0.983 | 1.379 | 0.833 | -0.433 | 0.005 |
| full_sample_q05 | 24h | nasdaq_5d_up | 0.981 | 0.049 | 1.135 | -0.666 | 0.322 | 1.096 | 1.017 | -0.318 | -0.074 |
| full_sample_q05 | 24h | sp500_5d_up | 1.200 | 0.268 | 1.361 | -0.040 | 0.921 | 1.315 | 0.851 | -0.421 | 0.036 |
| full_sample_q05 | 48h | broad_3of4_5d_up | 1.106 | 0.157 | 0.925 | -0.367 | -0.195 | 1.509 | 1.252 | 0.324 | -0.128 |
| full_sample_q05 | 48h | nasdaq_5d_up | 2.122 | 1.173 | 1.590 | -0.518 | 0.921 | 2.525 | 0.649 | 0.546 | -0.409 |
| full_sample_q05 | 48h | sp500_5d_up | 1.554 | 0.605 | 1.165 | -0.290 | 0.245 | 1.957 | 0.911 | 0.472 | -0.330 |
| rolling_1_5sigma | 24h | broad_3of4_5d_up | 1.078 | 0.395 | 1.047 | -0.013 | 0.514 | 1.173 | 0.596 | -0.064 | -0.127 |
| rolling_1_5sigma | 24h | nasdaq_5d_up | 0.780 | 0.098 | 0.698 | -0.574 | -0.189 | 0.876 | 0.730 | 0.059 | -0.276 |
| rolling_1_5sigma | 24h | sp500_5d_up | 0.872 | 0.189 | 0.869 | -0.184 | 0.197 | 0.967 | 0.680 | -0.055 | -0.145 |
| rolling_1_5sigma | 48h | broad_3of4_5d_up | 0.155 | -0.174 | -0.139 | 0.246 | -1.057 | 0.300 | 0.554 | 0.464 | -0.339 |
| rolling_1_5sigma | 48h | nasdaq_5d_up | 0.494 | 0.166 | -0.088 | -0.534 | -1.248 | 0.640 | 0.393 | 0.743 | -0.752 |
| rolling_1_5sigma | 48h | sp500_5d_up | 0.125 | -0.204 | -0.143 | -0.159 | -1.159 | 0.270 | 0.580 | 0.439 | -0.410 |
| rolling_2sigma | 24h | broad_3of4_5d_up | 1.476 | 0.560 | 1.549 | -0.107 | 1.070 | 1.817 | 0.996 | -0.060 | 0.189 |
| rolling_2sigma | 24h | nasdaq_5d_up | 0.956 | 0.040 | 0.874 | -0.583 | -0.238 | 1.297 | 1.237 | 0.244 | -0.055 |
| rolling_2sigma | 24h | sp500_5d_up | 1.074 | 0.157 | 1.189 | 0.005 | 0.466 | 1.415 | 1.168 | -0.032 | 0.187 |
| rolling_2sigma | 48h | broad_3of4_5d_up | 0.334 | 0.065 | 0.020 | -0.069 | -0.570 | 0.937 | 0.843 | 0.913 | 0.248 |
| rolling_2sigma | 48h | nasdaq_5d_up | 0.512 | 0.242 | -0.316 | -0.703 | -1.442 | 1.115 | 0.748 | 1.496 | -0.313 |
| rolling_2sigma | 48h | sp500_5d_up | 0.208 | -0.062 | -0.167 | -0.493 | -1.017 | 0.811 | 0.908 | 1.014 | 0.094 |

## Period Stability

| event_def | horizon | risk_env | period | group | n | mean_ret_pct | win_rate_pct | profit_factor | mean_mae_pct | maxdd_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rolling_2sigma | 24h | nasdaq_5d_up | 2020_plus | all_funding_covered_crashes | 201 | 0.341 | 53.234 | 1.260 | -3.727 | -30.823 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2020_plus | funding_high_x_risk_off | 26 | -0.242 | 42.308 | 0.837 | -4.330 | -19.250 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2020_plus | funding_low_x_risk_on | 15 | 1.297 | 66.667 | 3.122 | -2.651 | -3.470 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2021_plus | all_funding_covered_crashes | 193 | 0.325 | 52.332 | 1.244 | -3.760 | -30.823 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2021_plus | funding_high_x_risk_off | 25 | -0.171 | 44.000 | 0.883 | -4.373 | -19.250 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2021_plus | funding_low_x_risk_on | 15 | 1.297 | 66.667 | 3.122 | -2.651 | -3.470 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2022_rate_hike | all_funding_covered_crashes | 33 | -0.652 | 48.485 | 0.721 | -5.121 | -25.855 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2022_rate_hike | funding_high_x_risk_off | 0 | - | - | - | - | - |
| rolling_2sigma | 24h | nasdaq_5d_up | 2022_rate_hike | funding_low_x_risk_on | 4 | 0.333 | 50.000 | 1.286 | -3.136 | -1.613 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2023_plus | all_funding_covered_crashes | 128 | 0.405 | 52.344 | 1.423 | -2.843 | -23.461 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2023_plus | funding_high_x_risk_off | 22 | -0.321 | 40.909 | 0.800 | -4.385 | -19.250 |
| rolling_2sigma | 24h | nasdaq_5d_up | 2023_plus | funding_low_x_risk_on | 9 | 0.684 | 66.667 | 2.363 | -1.437 | -3.470 |
| rolling_2sigma | 24h | nasdaq_5d_up | all | all_funding_covered_crashes | 201 | 0.341 | 53.234 | 1.260 | -3.727 | -30.823 |
| rolling_2sigma | 24h | nasdaq_5d_up | all | funding_high_x_risk_off | 26 | -0.242 | 42.308 | 0.837 | -4.330 | -19.250 |
| rolling_2sigma | 24h | nasdaq_5d_up | all | funding_low_x_risk_on | 15 | 1.297 | 66.667 | 3.122 | -2.651 | -3.470 |
| rolling_2sigma | 24h | nasdaq_5d_up | post_btc_etf | all_funding_covered_crashes | 91 | 0.405 | 52.747 | 1.404 | -3.068 | -23.461 |
| rolling_2sigma | 24h | nasdaq_5d_up | post_btc_etf | funding_high_x_risk_off | 15 | -0.658 | 33.333 | 0.606 | -4.582 | -10.117 |
| rolling_2sigma | 24h | nasdaq_5d_up | post_btc_etf | funding_low_x_risk_on | 8 | 0.801 | 75.000 | 2.505 | -1.471 | -3.470 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2020_plus | all_funding_covered_crashes | 201 | 0.603 | 61.194 | 1.368 | -4.716 | -42.441 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2020_plus | funding_high_x_risk_off | 26 | -0.100 | 53.846 | 0.935 | -5.347 | -18.777 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2020_plus | funding_low_x_risk_on | 15 | 1.115 | 73.333 | 2.073 | -3.249 | -6.181 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2021_plus | all_funding_covered_crashes | 193 | 0.445 | 59.585 | 1.260 | -4.790 | -42.441 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2021_plus | funding_high_x_risk_off | 25 | -0.117 | 52.000 | 0.927 | -5.431 | -18.777 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2021_plus | funding_low_x_risk_on | 15 | 1.115 | 73.333 | 2.073 | -3.249 | -6.181 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2022_rate_hike | all_funding_covered_crashes | 33 | -1.123 | 57.576 | 0.626 | -6.468 | -42.441 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2022_rate_hike | funding_high_x_risk_off | 0 | - | - | - | - | - |
| rolling_2sigma | 48h | nasdaq_5d_up | 2022_rate_hike | funding_low_x_risk_on | 4 | -0.789 | 50.000 | 0.505 | -4.245 | -0.974 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2023_plus | all_funding_covered_crashes | 128 | 0.458 | 59.375 | 1.334 | -3.793 | -27.893 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2023_plus | funding_high_x_risk_off | 22 | -0.445 | 50.000 | 0.742 | -5.134 | -18.777 |
| rolling_2sigma | 48h | nasdaq_5d_up | 2023_plus | funding_low_x_risk_on | 9 | 2.416 | 88.889 | 7.327 | -1.465 | -3.378 |
| rolling_2sigma | 48h | nasdaq_5d_up | all | all_funding_covered_crashes | 201 | 0.603 | 61.194 | 1.368 | -4.716 | -42.441 |
| rolling_2sigma | 48h | nasdaq_5d_up | all | funding_high_x_risk_off | 26 | -0.100 | 53.846 | 0.935 | -5.347 | -18.777 |
| rolling_2sigma | 48h | nasdaq_5d_up | all | funding_low_x_risk_on | 15 | 1.115 | 73.333 | 2.073 | -3.249 | -6.181 |
| rolling_2sigma | 48h | nasdaq_5d_up | post_btc_etf | all_funding_covered_crashes | 91 | 0.173 | 56.044 | 1.104 | -4.367 | -27.893 |
| rolling_2sigma | 48h | nasdaq_5d_up | post_btc_etf | funding_high_x_risk_off | 15 | -0.736 | 40.000 | 0.588 | -5.681 | -8.591 |
| rolling_2sigma | 48h | nasdaq_5d_up | post_btc_etf | funding_low_x_risk_on | 8 | 2.588 | 87.500 | 7.025 | -1.502 | -3.378 |

## Interpretation

- The cleanest article claim is not that Nasdaq predicts BTC.
- The practical claim is that Funding and external risk-on/off conditions help classify BTC crashes.
- `Funding low x risk-on` is a candidate for buyable drops.
- `Funding high x risk-off` is a candidate for avoidable drops.
- The linear interaction term is not guaranteed to be stable across definitions, so the article should emphasize conditional filtering and sample-size caveats.
