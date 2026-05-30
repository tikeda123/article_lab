# Phase 7 Report: Open Interest / 清算拡張

作成日: 2026-05-30

参照データ:

- `open_interest_history.csv`
- `oi_profile.csv`
- `shock_mr_by_oi_events.csv`
- `shock_mr_by_oi_summary.csv`
- `liquidation_profile.csv`
- `shock_mr_by_liquidation_summary.csv`
- `figures/fig_13_lower5_mr_by_oi.png`
- `figures/fig_14_liquidation_regime_summary.png`

## 1. 目的

Phase 7 の目的は、急落を Open Interest の増減で分解し、投げ売り完了に近い急落と、ポジションが積み上がったままの急落を分けることである。

Binance の `openInterestHist` API は今回、全期間ではなく直近ローリングウィンドウだけを返した。そのため、Phase 7 は 2020-2026 の全期間結論ではなく、取得できた直近ウィンドウの診断として扱う。

## 2. Open Interest データ確認

| symbol   | api_limitation                                                        |   oi_rows | first_oi_timestamp   | last_oi_timestamp   |   oi_window_days |   lower5_signal_count |   lower5_with_oi_count |   upper5_signal_count |   upper5_with_oi_count |
|:---------|:----------------------------------------------------------------------|----------:|:---------------------|:--------------------|-----------------:|----------------------:|-----------------------:|----------------------:|-----------------------:|
| BTCUSDT  | API returned a recent rolling window only, not full 2020-2026 history |       174 | 2026-04-30 16:00     | 2026-05-29 12:00    |          28.8333 |                   636 |                      1 |                   636 |                      2 |
| ETHUSDT  | API returned a recent rolling window only, not full 2020-2026 history |       174 | 2026-04-30 16:00     | 2026-05-29 12:00    |          28.8333 |                   636 |                      3 |                   636 |                      1 |
| SOLUSDT  | API returned a recent rolling window only, not full 2020-2026 history |       174 | 2026-04-30 16:00     | 2026-05-29 12:00    |          28.8333 |                   636 |                      1 |                   636 |                      0 |

## 3. 下位5%急落後ロング: 72H

| symbol   | shock_side   | oi_regime          |   horizon_hours |   count |   oi_value_change_24h_mean_pct |   mr_return_mean_pct |   mr_win_rate_pct |   mr_return_t_stat |
|:---------|:-------------|:-------------------|----------------:|--------:|-------------------------------:|---------------------:|------------------:|-------------------:|
| BTCUSDT  | lower        | price_down_oi_up   |              72 |       1 |                        2.98766 |            -0.768769 |            0      |         nan        |
| ETHUSDT  | lower        | price_down_oi_down |              72 |       3 |                       -0.66188 |             0.045312 |           33.3333 |           0.030135 |
| SOLUSDT  | lower        | price_down_oi_down |              72 |       1 |                       -1.30316 |            -4.1814   |            0      |         nan        |

## 4. 上位5%急騰後ショート: 24H

| symbol   | shock_side   | oi_regime        |   horizon_hours |   count |   oi_value_change_24h_mean_pct |   mr_return_mean_pct |   mr_win_rate_pct |   mr_return_t_stat |
|:---------|:-------------|:-----------------|----------------:|--------:|-------------------------------:|---------------------:|------------------:|-------------------:|
| BTCUSDT  | upper        | price_up_oi_down |              24 |       1 |                       -2.21185 |             2.62302  |               100 |                nan |
| BTCUSDT  | upper        | price_up_oi_up   |              24 |       1 |                        1.1054  |            -0.747705 |                 0 |                nan |
| ETHUSDT  | upper        | price_up_oi_up   |              24 |       1 |                        5.65852 |             0.104442 |               100 |                nan |

## 5. 清算データ取得状況

| symbol   | endpoint                                        |   http_status | api_status   | analysis_status              | message                                                       |
|:---------|:------------------------------------------------|--------------:|:-------------|:-----------------------------|:--------------------------------------------------------------|
| BTCUSDT  | https://fapi.binance.com/fapi/v1/allForceOrders |           400 | UNAVAILABLE  | SKIPPED_ENDPOINT_UNAVAILABLE | {"code":400,"msg":"The endpoint has been out of maintenance"} |
| ETHUSDT  | https://fapi.binance.com/fapi/v1/allForceOrders |           400 | UNAVAILABLE  | SKIPPED_ENDPOINT_UNAVAILABLE | {"code":400,"msg":"The endpoint has been out of maintenance"} |
| SOLUSDT  | https://fapi.binance.com/fapi/v1/allForceOrders |           400 | UNAVAILABLE  | SKIPPED_ENDPOINT_UNAVAILABLE | {"code":400,"msg":"The endpoint has been out of maintenance"} |

清算履歴は、今回の実行では公開APIから取得できなかった。そのため、Phase 7 の清算分類は未実施であり、`shock_mr_by_liquidation_summary.csv` は空のスキーマ出力として保存した。

## 6. 記事での使い方

Open Interest は、急落時にポジションが減ったのか増えたのかを見る補助材料になる。

`price_down_oi_down` は、価格下落と同時にOIも減っており、デレバレッジや投げ売りが進んだ可能性を示す。一方、`price_down_oi_up` は、価格下落中にもOIが増えており、新規ショート増加またはロング捕まりが残っている可能性を示す。

ただし今回のOIは直近ウィンドウだけで、イベント数も少ない。記事では結論として強く使わず、Phase 7は「本来必要な追加データ」と「今回のAPI制約」を示す材料にするのが妥当である。
