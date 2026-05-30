# Phase 6 Report: Funding Rate 拡張

作成日: 2026-05-30

参照データ:

- `funding_rate_history.csv`
- `funding_profile.csv`
- `shock_mr_by_funding_events.csv`
- `shock_mr_by_funding_summary.csv`
- `figures/fig_12_lower5_mr_by_funding.png`

## 1. 目的

Phase 6 の目的は、急落後ロングを Funding Rate の状態で分類し、ロング過熱の巻き戻しと悲観過剰を分けることである。

Funding は Binance USD-M Futures の `fundingRate` API から取得した。4時間足シグナルには、シグナル時刻以前の直近 Funding をひも付けた。

Funding 分類は銘柄ごとの共通期間分布に基づく。

| 分類 | 条件 | 解釈 |
|---|---|---|
| `funding_high` | Funding が銘柄内80%分位以上 | ロング過熱寄り |
| `funding_low_or_negative` | Funding が20%分位以下、またはマイナス | 悲観・ショート過熱寄り |
| `funding_neutral` | 上記以外 | 中立 |

ロングの Funding 調整後リターンは、保有期間中の Funding 合計をグロスMRから差し引いた簡易値である。プラスFundingではロングが支払い、マイナスFundingではロングが受け取る前提で計算した。

## 2. Funding データ確認

| symbol   | source                                |   raw_funding_rows |   common_period_funding_rows | first_funding_timestamp   | last_funding_timestamp   |   funding_interval_break_count |   funding_rate_mean_pct |   funding_rate_median_pct |   funding_rate_q20_pct |   funding_rate_q80_pct |   funding_rate_min_pct |   funding_rate_max_pct |   negative_funding_share_pct |   common_bar_count |   missing_funding_bar_count |   missing_funding_bar_share_pct |   lower5_signal_count |   lower5_missing_funding_count |
|:---------|:--------------------------------------|-------------------:|-----------------------------:|:--------------------------|:-------------------------|-------------------------------:|------------------------:|--------------------------:|-----------------------:|-----------------------:|-----------------------:|-----------------------:|-----------------------------:|-------------------:|----------------------------:|--------------------------------:|----------------------:|-------------------------------:|
| BTCUSDT  | Binance USD-M Futures fundingRate API |               6354 |                         6352 | 2020-08-11 08:00          | 2026-05-29 08:00         |                              0 |              0.0105071  |                 0.0088505 |              0.0014396 |                   0.01 |              -0.119172 |               0.248993 |                      14.153  |              12704 |                           0 |                         0       |                   636 |                              0 |
| ETHUSDT  | Binance USD-M Futures fundingRate API |               6354 |                         6352 | 2020-08-11 08:00          | 2026-05-29 08:00         |                              0 |              0.0118873  |                 0.00908   |              0.0014482 |                   0.01 |              -0.356332 |               0.375    |                      14.8772 |              12704 |                           0 |                         0       |                   636 |                              0 |
| SOLUSDT  | Binance USD-M Futures fundingRate API |               6328 |                         6327 | 2020-09-13 16:00          | 2026-05-29 08:00         |                            101 |              0.00012726 |                 0.009291  |             -0.0039406 |                   0.01 |              -2        |               0.332469 |                      28.0228 |              12704 |                         201 |                         1.58218 |                   636 |                             39 |

## 3. 72H 急落後ロング: Funding階層別

| symbol   | funding_regime          |   horizon_hours |   count |   funding_rate_mean_pct |   holding_funding_sum_mean_pct |   gross_mr_return_mean_pct |   funding_adjusted_mr_return_mean_pct |   funding_adjusted_mr_win_rate_pct |   funding_adjusted_mr_return_t_stat |
|:---------|:------------------------|----------------:|--------:|------------------------:|-------------------------------:|---------------------------:|--------------------------------------:|-----------------------------------:|------------------------------------:|
| BTCUSDT  | funding_low_or_negative |              72 |     112 |               -0.006122 |                      -0.004104 |                   1.07507  |                              1.07917  |                            66.0714 |                            1.61465  |
| BTCUSDT  | funding_neutral         |              72 |     135 |                0.005519 |                       0.017608 |                   0.775301 |                              0.757693 |                            56.2963 |                            1.40575  |
| BTCUSDT  | funding_high            |              72 |     389 |                0.026474 |                       0.167105 |                   0.176894 |                              0.009789 |                            53.7275 |                            0.030311 |
| ETHUSDT  | funding_low_or_negative |              72 |     146 |               -0.013392 |                      -0.018553 |                   0.302707 |                              0.32126  |                            58.2192 |                            0.413465 |
| ETHUSDT  | funding_neutral         |              72 |     162 |                0.005165 |                       0.012509 |                  -0.593087 |                             -0.605596 |                            45.0617 |                           -0.985583 |
| ETHUSDT  | funding_high            |              72 |     328 |                0.031924 |                       0.196532 |                   0.298219 |                              0.101687 |                            53.6585 |                            0.189176 |
| SOLUSDT  | funding_low_or_negative |              72 |     159 |               -0.09055  |                      -1.52223  |                   2.9243   |                              4.44653  |                            67.2956 |                            4.04041  |
| SOLUSDT  | funding_neutral         |              72 |      99 |                0.004478 |                      -0.038887 |                   2.53133  |                              2.57022  |                            63.6364 |                            2.76231  |
| SOLUSDT  | funding_high            |              72 |     339 |                0.024864 |                       0.018695 |                   2.87778  |                              2.85909  |                            58.4071 |                            3.5652   |

## 4. 銘柄別の最良Funding条件

| symbol   | funding_regime          |   horizon_hours |   count |   funding_rate_mean_pct |   holding_funding_sum_mean_pct |   gross_mr_return_mean_pct |   funding_adjusted_mr_return_mean_pct |   funding_adjusted_mr_win_rate_pct |   funding_adjusted_mr_return_t_stat |
|:---------|:------------------------|----------------:|--------:|------------------------:|-------------------------------:|---------------------------:|--------------------------------------:|-----------------------------------:|------------------------------------:|
| BTCUSDT  | funding_low_or_negative |              24 |     112 |               -0.006122 |                      -0.00777  |                   1.32831  |                              1.33607  |                            64.2857 |                             3.13412 |
| ETHUSDT  | funding_low_or_negative |              24 |     146 |               -0.013392 |                      -0.015164 |                   0.880999 |                              0.896162 |                            56.8493 |                             1.87503 |
| SOLUSDT  | funding_low_or_negative |              72 |     159 |               -0.09055  |                      -1.52223  |                   2.9243   |                              4.44653  |                            67.2956 |                             4.04041 |

## 5. 記事での使い方

Phase 6 は、価格だけで見た急落後リバウンドを、Perpetual Futures 固有の需給状態で分解する材料である。

記事では、急落後リバウンドが Funding 高止まり局面でも成立するのか、または Funding 低下・マイナス局面で強いのかを比較する。Funding 高い局面の急落は、ロング過熱の巻き戻しであり、単純な押し目とは限らない。

この結果は Binance USD-M Funding に依存するため、現在の OHLCV が Spot 由来の場合は、価格データとFundingデータの市場が完全には一致しない可能性を注記する。
