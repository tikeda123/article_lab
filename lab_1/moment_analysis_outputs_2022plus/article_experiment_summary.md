# Moment Analysis Edge Experiments

- Requested period: start=2022-01-01 00:00, end=none
- Analysis period: 2022-01-02 20:00 to 2026-04-02 12:00
- Return definition: close-to-close log return in percent.
- Screening horizons: 1, 3, 6, and 12 bars on 240-minute data.
- Caveat: these are edge-discovery statistics, not net trade backtests.

## Data Profile

| source_file   | requested_start     | requested_end   | analysis_start      | analysis_end        |   raw_rows |   duplicate_timestamps |   missing_timestamp_rows |   missing_ohlc_rows |   clean_rows | first_timestamp     | last_timestamp      | pair   |   common_rows |
|:--------------|:--------------------|:----------------|:--------------------|:--------------------|-----------:|-----------------------:|-------------------------:|--------------------:|-------------:|:--------------------|:--------------------|:-------|--------------:|
| USDJPY240.csv | 2022-01-01 00:00:00 |                 | 2022-01-02 20:00:00 | 2026-04-02 12:00:00 |      25855 |                      0 |                        0 |                   0 |        25855 | 2010-03-18 08:00:00 | 2026-04-02 12:00:00 | USDJPY |          6849 |
| EURUSD240.csv | 2022-01-01 00:00:00 |                 | 2022-01-02 20:00:00 | 2026-04-02 12:00:00 |      25850 |                      0 |                        0 |                   0 |        25850 | 2010-04-13 00:00:00 | 2026-04-24 20:00:00 | EURUSD |          6849 |
| AUDJPY240.csv | 2022-01-01 00:00:00 |                 | 2022-01-02 20:00:00 | 2026-04-02 12:00:00 |      25851 |                      0 |                        0 |                   0 |        25851 | 2010-04-12 12:00:00 | 2026-04-24 20:00:00 | AUDJPY |          6848 |

## Moment Summary

| pair   |   return_count |   mean_pct |   median_pct |   variance_pct2 |   std_pct |      skew |   excess_kurtosis |   max_pct |   min_pct |
|:-------|---------------:|-----------:|-------------:|----------------:|----------:|----------:|------------------:|----------:|----------:|
| USDJPY |           6848 |   0.004771 |     0.00847  |        0.069663 |  0.263938 | -1.2543   |          20.7389  |   2.20191 |  -3.50178 |
| EURUSD |           6848 |   0.00022  |     0        |        0.039992 |  0.199981 |  0.268543 |           9.81305 |   2.3534  |  -1.78854 |
| AUDJPY |           6847 |   0.004005 |     0.008391 |        0.090809 |  0.301345 | -0.178294 |          13.7414  |   4.28624 |  -3.15566 |

## Article Candidate Summary

| candidate                    | source_table                | pair   | condition   | vol_regime   |   horizon_bars |   horizon_hours |   count |   threshold_pct |   mr_return_mean_pct |   mr_win_rate_pct |   mr_return_t_stat |
|:-----------------------------|:----------------------------|:-------|:------------|:-------------|---------------:|----------------:|--------:|----------------:|---------------------:|------------------:|-------------------:|
| USDJPY lower-tail long MR    | shock_mr_summary.csv        | USDJPY | lower_5pct  | all          |             12 |              48 |     343 |       -0.386162 |             0.048381 |           54.5189 |           0.851911 |
| EURUSD extreme-up short MR   | shock_mr_summary.csv        | EURUSD | upper_1pct  | all          |              3 |              12 |      69 |        0.584502 |            -0.005897 |           56.5217 |          -0.119274 |
| AUDJPY lower-tail long MR    | shock_mr_summary.csv        | AUDJPY | lower_5pct  | all          |             12 |              48 |     343 |       -0.480162 |             0.202448 |           60.0583 |           3.18473  |
| AUDJPY extreme-down long MR  | shock_mr_summary.csv        | AUDJPY | lower_1pct  | all          |             12 |              48 |      69 |       -0.837783 |             0.385607 |           62.3188 |           2.24919  |
| AUDJPY Q5 lower-tail long MR | shock_mr_by_vol_summary.csv | AUDJPY | lower_5pct  | Q5_high      |              6 |              24 |     168 |       -0.480162 |             0.144615 |           54.7619 |           1.65763  |

## Next-open Path-risk Check

| candidate                          | pair   |   horizon_bars |   horizon_hours |   threshold_pct |   count |   next_open_return_mean_pct |   next_open_return_median_pct |   next_open_win_rate_pct |   mae_mean_pct |   mae_5pct_pct |   mfe_mean_pct |   mfe_95pct_pct |
|:-----------------------------------|:-------|---------------:|----------------:|----------------:|--------:|----------------------------:|------------------------------:|-------------------------:|---------------:|---------------:|---------------:|----------------:|
| AUDJPY lower5 long h6 next-open    | AUDJPY |              6 |              24 |       -0.480162 |     341 |                    0.116866 |                      0.156135 |                  57.478  |      -0.744618 |       -2.02299 |       0.736082 |         1.90228 |
| AUDJPY Q5 lower5 long h6 next-open | AUDJPY |              6 |              24 |       -0.480162 |     168 |                    0.140177 |                      0.176109 |                  54.7619 |      -0.917333 |       -2.65422 |       0.893154 |         2.28559 |

## Main Figures

- fig_01_moment_std_skew_kurtosis.png
- fig_02_extreme_returns.png
- fig_03_return_distribution_histograms.png
- fig_04_direction_future_returns.png
- fig_05_shock_mean_reversion_by_horizon.png
- fig_06_vol_regime_future_abs_return_h6.png
- fig_07_audjpy_lower5_mr_by_vol.png
- fig_08_audjpy_q5_lower5_annual.png
