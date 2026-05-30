# Phase 4 Report: 次足始値エントリーと MAE/MFE

作成日: 2026-05-30

参照データ:

- `phase4_candidate_table.csv`
- `path_risk_summary.csv`
- `path_risk_events.csv`
- `simple_backtest_summary.csv`
- `simple_backtest_events.csv`
- `figures/fig_08_path_risk_mae_mfe.png`
- `figures/fig_09_simple_equity_curve.png`
- `figures/fig_10_simple_drawdown_curve.png`

## 1. 目的

Phase 4 の目的は、Phase 2 と Phase 3 で見えた急落後ロング候補を、実売買に近い次足始値エントリーへ置き換えたときに、優位性と途中逆行がどの程度残るかを確認することである。

シグナルは4時間足終値で判定し、エントリーは次の4時間足始値、決済は候補ごとの時間決済とした。MAE/MFE はエントリー足から決済足までの高値・安値で測定している。

## 2. 検証候補

| candidate_id               | candidate_label   | source_phase          | symbol   | shock_side   | shock_level   | direction   | vol_regime_filter   |   threshold_pct |   horizon_bars |   horizon_hours |   source_count |   source_mr_return_mean_pct |   source_mr_win_rate_pct |
|:---------------------------|:------------------|:----------------------|:---------|:-------------|:--------------|:------------|:--------------------|----------------:|---------------:|----------------:|---------------:|----------------------------:|-------------------------:|
| BTCUSDT_lower5_all_h48     | BTC all 48H       | phase2_lower5_best    | BTCUSDT  | lower        | 5pct          | long        | all                 |        -1.89877 |             12 |              48 |            636 |                    0.494299 |                  55.6604 |
| ETHUSDT_lower5_all_h24     | ETH all 24H       | phase2_lower5_best    | ETHUSDT  | lower        | 5pct          | long        | all                 |        -2.5347  |              6 |              24 |            636 |                    0.345341 |                  55.6604 |
| SOLUSDT_lower5_all_h72     | SOL all 72H       | phase2_lower5_best    | SOLUSDT  | lower        | 5pct          | long        | all                 |        -3.7213  |             18 |              72 |            636 |                    2.5185   |                  61.478  |
| BTCUSDT_lower5_Q5_high_h48 | BTC Q5 48H        | phase3_lower5_Q5_best | BTCUSDT  | lower        | 5pct          | long        | Q5_high             |        -1.89877 |             12 |              48 |            324 |                    1.0495   |                  57.716  |
| ETHUSDT_lower5_Q5_high_h72 | ETH Q5 72H        | phase3_lower5_Q5_best | ETHUSDT  | lower        | 5pct          | long        | Q5_high             |        -2.5347  |             18 |              72 |            340 |                    0.907751 |                  58.2353 |
| SOLUSDT_lower5_Q5_high_h72 | SOL Q5 72H        | phase3_lower5_Q5_best | SOLUSDT  | lower        | 5pct          | long        | Q5_high             |        -3.7213  |             18 |              72 |            336 |                    4.35392  |                  66.6667 |

## 3. 全シグナルの経路リスク

重複シグナルも含め、条件を満たす全イベントで次足始値ベースのリターンと MAE/MFE を集計した。

| candidate_label   |   event_count |   horizon_hours |   next_open_return_mean_pct |   next_open_return_median_pct |   win_rate_pct |   profit_factor |   mae_mean_pct |   mae_worst_pct |   mfe_mean_pct |   mfe_best_pct |
|:------------------|--------------:|----------------:|----------------------------:|------------------------------:|---------------:|----------------:|---------------:|----------------:|---------------:|---------------:|
| BTC all 48H       |           636 |              48 |                    0.496414 |                      0.509654 |        55.9748 |         1.27259 |       -5.11257 |        -36.8271 |        4.37032 |        23.8651 |
| ETH all 24H       |           636 |              24 |                    0.343071 |                      0.524523 |        55.6604 |         1.17851 |       -5.56265 |        -57.2095 |        4.15067 |        27.3268 |
| SOL all 72H       |           636 |              72 |                    2.5201   |                      2.75332  |        61.478  |         1.61971 |      -11.6441  |        -96.9345 |       12.3781  |        65.3926 |
| BTC Q5 48H        |           324 |              48 |                    1.04973  |                      0.960208 |        58.0247 |         1.54029 |       -6.00263 |        -36.8271 |        5.63175 |        23.8651 |
| ETH Q5 72H        |           340 |              72 |                    0.902584 |                      1.57187  |        58.2353 |         1.2567  |      -10.5276  |        -65.4687 |        8.55368 |        41.3253 |
| SOL Q5 72H        |           336 |              72 |                    4.34908  |                      3.96862  |        66.369  |         2.06725 |      -13.6506  |        -87.3176 |       16.0497  |        65.1904 |

## 4. 簡易バックテスト

簡易バックテストでは、候補ごとに同時保有を1つに限定し、既存ポジションの決済前に出たシグナルをスキップした。これはポートフォリオ最終検証ではなく、イベント重複を取り除いた診断である。

`final_cumulative_return_pct` は各イベントのログリターンを複利換算した参考値であり、手数料、スリッページ、資金制約、約定制約は入れていない。そのため、数値の大きさは売買成績としてそのまま扱わない。

| candidate_label   |   all_event_count |   selected_event_count |   skipped_overlap_count |   mean_return_pct |   win_rate_pct |   profit_factor |   final_cumulative_return_pct |   max_drawdown_pct |
|:------------------|------------------:|-----------------------:|------------------------:|------------------:|---------------:|----------------:|------------------------------:|-------------------:|
| BTC all 48H       |               636 |                    337 |                     299 |          0.313361 |        56.0831 |        1.17812  |                      187.493  |           -53.9548 |
| ETH all 24H       |               636 |                    423 |                     213 |         -0.052206 |        53.4279 |        0.972107 |                      -19.8148 |           -63.2064 |
| SOL all 72H       |               636 |                    274 |                     362 |          1.57256  |        59.854  |        1.42512  |                     7335.23   |           -69.238  |
| BTC Q5 48H        |               324 |                    149 |                     175 |          0.769257 |        56.3758 |        1.38525  |                      214.619  |           -39.2781 |
| ETH Q5 72H        |               340 |                    120 |                     220 |          0.389687 |        52.5    |        1.12135  |                       59.6198 |           -65.7119 |
| SOL Q5 72H        |               336 |                    113 |                     223 |          4.55828  |        69.0265 |        2.40385  |                    17158      |           -59.971  |

## 5. 記事での使い方

全シグナル平均で最も高い次足始値リターンは `SOL Q5 72H` の 4.349% だった。

重複を除いた簡易累積の参考値では `SOL Q5 72H` が 17158.012% と最大だった。

一方、最大ドローダウンが最も深かったのは `SOL all 72H` の -69.238% である。

この結果は、急落後リバウンドが平均では残っても、実際には途中逆行とイベント重複の影響を受けることを示す。記事では、Phase 2/3 の平均回帰だけで結論を出さず、Phase 4 の MAE とドローダウンをセットで提示する。
