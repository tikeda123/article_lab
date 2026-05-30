# Phase 5 Report: 年別安定性

作成日: 2026-05-30

参照データ:

- `annual_condition_summary.csv`
- `annual_condition_events.csv`
- `annual_stability_summary.csv`
- `figures/fig_11_annual_condition_summary.png`

## 1. 目的

Phase 5 の目的は、Phase 2 から Phase 4 で見えた急落後リバウンド候補が、特定年だけの外れ値に依存していないかを確認することである。

年別集計では、シグナル発生年を基準にイベントを分けた。2020年は SOL のデータ開始が途中であり、2026年は 2026-05-29 までの途中年であるため、どちらも部分年として扱う。

## 2. 対象候補

今回の年別確認では、以下を同じ形式に正規化した。

- Phase 2 の下位5%急落後ロング候補
- Phase 2 の上位5%急騰後ショート候補
- Phase 3 の Q5 高ボラ下位5%急落後ロング候補
- Phase 4 の次足始値エントリー候補
- Phase 4 の重複除外済み次足始値エントリー候補

## 3. 候補別の年別安定性サマリー

| candidate_label                  |   total_event_count |   years_with_events |   ok_years |   positive_year_count |   positive_year_rate_pct |   mean_of_annual_means_pct |   min_annual_mean_pct |   max_annual_mean_pct |   worst_annual_drawdown_pct | stability_label     |
|:---------------------------------|--------------------:|--------------------:|-----------:|----------------------:|-------------------------:|---------------------------:|----------------------:|----------------------:|----------------------------:|:--------------------|
| P2 BTC lower5 all close 48H long |                 633 |                   7 |          7 |                     6 |                  85.7143 |                   0.79416  |             -1.00172  |              2.29538  |                    -86.9073 | broad_positive      |
| P2 BTC upper5 all close 4H short |                 635 |                   7 |          7 |                     5 |                  71.4286 |                  -0.061788 |             -0.643785 |              0.299779 |                    -22.0694 | mixed_or_sparse     |
| P2 ETH lower5 all close 24H long |                 635 |                   7 |          7 |                     5 |                  71.4286 |                   0.33216  |             -0.761232 |              0.923112 |                    -80.398  | broad_positive      |
| P2 ETH upper5 all close 4H short |                 635 |                   7 |          7 |                     3 |                  42.8571 |                  -0.041566 |             -0.313244 |              0.291413 |                    -30.2564 | mixed_or_sparse     |
| P2 SOL lower5 all close 72H long |                 634 |                   7 |          6 |                     6 |                  85.7143 |                   1.97272  |             -1.65104  |              6.64706  |                    -98.579  | broad_positive      |
| P2 SOL upper5 all close 4H short |                 631 |                   7 |          6 |                     3 |                  42.8571 |                  -0.086118 |             -1.13637  |              0.452247 |                    -51.0679 | mixed_or_sparse     |
| P3 BTC lower5 Q5 close 48H long  |                 324 |                   7 |          5 |                     6 |                  85.7143 |                   1.77813  |             -0.490602 |              3.32481  |                    -67.3042 | broad_positive      |
| P3 ETH lower5 Q5 close 72H long  |                 340 |                   7 |          5 |                     4 |                  57.1429 |                   1.21651  |             -1.23561  |              3.99043  |                    -96.6484 | positive_but_uneven |
| P3 SOL lower5 Q5 close 72H long  |                 336 |                   6 |          6 |                     5 |                  83.3333 |                   3.94694  |             -0.712743 |              9.00175  |                    -94.1996 | broad_positive      |
| P4 all-signal BTC Q5 48H         |                 324 |                   7 |          5 |                     6 |                  85.7143 |                   1.76775  |             -0.490366 |              3.36271  |                    -67.2314 | broad_positive      |
| P4 all-signal BTC all 48H        |                 636 |                   7 |          7 |                     6 |                  85.7143 |                   0.761083 |             -1.00135  |              2.23304  |                    -86.8997 | broad_positive      |
| P4 all-signal ETH Q5 72H         |                 340 |                   7 |          5 |                     4 |                  57.1429 |                   1.22508  |             -1.22966  |              4.02871  |                    -96.6375 | positive_but_uneven |
| P4 all-signal ETH all 24H        |                 636 |                   7 |          7 |                     5 |                  71.4286 |                   0.320686 |             -0.737906 |              0.929242 |                    -80.3835 | broad_positive      |
| P4 all-signal SOL Q5 72H         |                 336 |                   6 |          6 |                     5 |                  83.3333 |                   3.93327  |             -0.71939  |              8.98127  |                    -94.2202 | broad_positive      |
| P4 all-signal SOL all 72H        |                 636 |                   7 |          6 |                     6 |                  85.7143 |                   1.95507  |             -1.65933  |              6.64386  |                    -98.5825 | broad_positive      |
| P4 nonoverlap BTC Q5 48H         |                 149 |                   7 |          3 |                     5 |                  71.4286 |                   0.889673 |             -3.18251  |              3.4936   |                    -39.2781 | positive_but_uneven |
| P4 nonoverlap BTC all 48H        |                 337 |                   7 |          7 |                     6 |                  85.7143 |                   0.468178 |             -0.691257 |              1.75784  |                    -46.4497 | broad_positive      |
| P4 nonoverlap ETH Q5 72H         |                 120 |                   7 |          3 |                     3 |                  42.8571 |                  -0.162144 |             -6.29503  |              5.22668  |                    -54.6516 | mixed_or_sparse     |
| P4 nonoverlap ETH all 24H        |                 423 |                   7 |          7 |                     4 |                  57.1429 |                   0.039967 |             -1.21751  |              1.11925  |                    -60.2012 | positive_but_uneven |
| P4 nonoverlap SOL Q5 72H         |                 113 |                   6 |          4 |                     5 |                  83.3333 |                   3.77368  |             -1.34393  |              7.4576   |                    -59.971  | broad_positive      |
| P4 nonoverlap SOL all 72H        |                 274 |                   7 |          6 |                     6 |                  85.7143 |                   1.18676  |             -1.50423  |              5.62058  |                    -62.1442 | broad_positive      |

## 4. Phase 4 重複除外候補の読み取り

| candidate_label           |   total_event_count |   years_with_events |   ok_years |   positive_year_count |   positive_year_rate_pct |   mean_of_annual_means_pct |   min_annual_mean_pct |   max_annual_mean_pct |   worst_annual_drawdown_pct | stability_label     |
|:--------------------------|--------------------:|--------------------:|-----------:|----------------------:|-------------------------:|---------------------------:|----------------------:|----------------------:|----------------------------:|:--------------------|
| P4 nonoverlap BTC Q5 48H  |                 149 |                   7 |          3 |                     5 |                  71.4286 |                   0.889673 |             -3.18251  |               3.4936  |                    -39.2781 | positive_but_uneven |
| P4 nonoverlap BTC all 48H |                 337 |                   7 |          7 |                     6 |                  85.7143 |                   0.468178 |             -0.691257 |               1.75784 |                    -46.4497 | broad_positive      |
| P4 nonoverlap ETH Q5 72H  |                 120 |                   7 |          3 |                     3 |                  42.8571 |                  -0.162144 |             -6.29503  |               5.22668 |                    -54.6516 | mixed_or_sparse     |
| P4 nonoverlap ETH all 24H |                 423 |                   7 |          7 |                     4 |                  57.1429 |                   0.039967 |             -1.21751  |               1.11925 |                    -60.2012 | positive_but_uneven |
| P4 nonoverlap SOL Q5 72H  |                 113 |                   6 |          4 |                     5 |                  83.3333 |                   3.77368  |             -1.34393  |               7.4576  |                    -59.971  | broad_positive      |
| P4 nonoverlap SOL all 72H |                 274 |                   7 |          6 |                     6 |                  85.7143 |                   1.18676  |             -1.50423  |               5.62058 |                    -62.1442 | broad_positive      |

Phase 4 重複除外候補の中で、年別の陽性率と年別平均が最も強かったのは `P4 nonoverlap SOL Q5 72H` である。

一方、最も弱かったのは `P4 nonoverlap ETH Q5 72H` であり、Phase 4 単体で主張するには弱い。

## 5. Q5高ボラ次足始値候補の年別詳細

| candidate_label          |   year |   event_count |   mean_return_pct |   win_rate_pct |   profit_factor |   max_drawdown_pct | annual_status   |
|:-------------------------|-------:|--------------:|------------------:|---------------:|----------------:|-------------------:|:----------------|
| P4 nonoverlap BTC Q5 48H |   2020 |             9 |          2.66723  |        66.6667 |        3.12413  |           -7.23999 | LOW_COUNT       |
| P4 nonoverlap BTC Q5 48H |   2021 |            69 |          0.585684 |        50.7246 |        1.25915  |          -39.2781  | OK              |
| P4 nonoverlap BTC Q5 48H |   2022 |            36 |         -0.28982  |        55.5556 |        0.887018 |          -29.885   | OK              |
| P4 nonoverlap BTC Q5 48H |   2023 |             8 |          2.12658  |        75      |       11.3876   |           -1.15548 | LOW_COUNT       |
| P4 nonoverlap BTC Q5 48H |   2024 |            14 |          3.4936   |        85.7143 |        6.19325  |           -6.61459 | OK              |
| P4 nonoverlap BTC Q5 48H |   2025 |             9 |          0.826938 |        44.4444 |        1.91302  |           -4.29259 | LOW_COUNT       |
| P4 nonoverlap BTC Q5 48H |   2026 |             4 |         -3.18251  |        25      |        0.319889 |          -13.1046  | LOW_COUNT       |
| P4 nonoverlap ETH Q5 72H |   2020 |             7 |         -1.54129  |        57.1429 |        0.73504  |          -24.8975  | LOW_COUNT       |
| P4 nonoverlap ETH Q5 72H |   2021 |            49 |          0.891634 |        53.0612 |        1.30274  |          -48.2946  | OK              |
| P4 nonoverlap ETH Q5 72H |   2022 |            30 |         -0.489874 |        43.3333 |        0.889209 |          -54.6516  | OK              |
| P4 nonoverlap ETH Q5 72H |   2023 |             2 |          1.16972  |       100      |      nan        |            0       | LOW_COUNT       |
| P4 nonoverlap ETH Q5 72H |   2024 |             9 |          5.22668  |        88.8889 |       33.74     |           -1.42651 | LOW_COUNT       |
| P4 nonoverlap ETH Q5 72H |   2025 |            20 |         -0.09684  |        50      |        0.95908  |          -24.8253  | OK              |
| P4 nonoverlap ETH Q5 72H |   2026 |             3 |         -6.29503  |         0      |        0        |          -17.209   | LOW_COUNT       |
| P4 nonoverlap SOL Q5 72H |   2020 |            25 |          4.08786  |        68      |        2.03545  |          -30.6091  | OK              |
| P4 nonoverlap SOL Q5 72H |   2021 |            50 |          7.4576   |        76      |        4.74922  |          -34.9361  | OK              |
| P4 nonoverlap SOL Q5 72H |   2022 |            18 |         -1.34393  |        66.6667 |        0.81746  |          -59.971   | OK              |
| P4 nonoverlap SOL Q5 72H |   2023 |            10 |          0.083996 |        40      |        1.05527  |          -11.9042  | OK              |
| P4 nonoverlap SOL Q5 72H |   2024 |             6 |          6.96717  |        83.3333 |       17.4169   |           -2.51419 | LOW_COUNT       |
| P4 nonoverlap SOL Q5 72H |   2025 |             4 |          5.38942  |        50      |        2.16582  |          -12.619   | LOW_COUNT       |
| P4 nonoverlap SOL Q5 72H |   2026 |             0 |        nan        |       nan      |      nan        |          nan       | NO_EVENTS       |

## 6. 急騰後ショート候補

Phase 2 では急騰後ショート候補も確認しているが、年別安定性の観点では記事の主役にしにくい候補である。

| candidate_label                  |   total_event_count |   years_with_events |   ok_years |   positive_year_count |   positive_year_rate_pct |   mean_of_annual_means_pct |   min_annual_mean_pct |   max_annual_mean_pct |   worst_annual_drawdown_pct | stability_label   |
|:---------------------------------|--------------------:|--------------------:|-----------:|----------------------:|-------------------------:|---------------------------:|----------------------:|----------------------:|----------------------------:|:------------------|
| P2 BTC upper5 all close 4H short |                 635 |                   7 |          7 |                     5 |                  71.4286 |                  -0.061788 |             -0.643785 |              0.299779 |                    -22.0694 | mixed_or_sparse   |
| P2 ETH upper5 all close 4H short |                 635 |                   7 |          7 |                     3 |                  42.8571 |                  -0.041566 |             -0.313244 |              0.291413 |                    -30.2564 | mixed_or_sparse   |
| P2 SOL upper5 all close 4H short |                 631 |                   7 |          6 |                     3 |                  42.8571 |                  -0.086118 |             -1.13637  |              0.452247 |                    -51.0679 | mixed_or_sparse   |

## 7. 記事での使い方

Phase 5 は、Phase 4 までの候補を記事でどこまで強く主張できるかを決めるための確認である。

年別に見ると、平均リターンが高い候補でも、年によって成績が大きく変わる。特に高ボラ急落後ロングは、反発が大きい年では非常に強く見える一方、ドローダウンも深くなりやすい。

記事では、全期間平均だけでなく、年別のばらつきを必ず併記する。2020年と2026年は部分年であり、SOLは2020年の件数が少ないため、強い結論には使わない。
