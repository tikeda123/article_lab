# lab_10 実装仕様書

## 1. 目的

`lab_10` は、記事「ファットテールを織り込んだ“つもり”になっていないか」の実証パートを作るための実験ラボである。

目的は、ファットテールを正確に予測することではない。リスク推定やエッジ候補が、データ期間、分布仮定、コスト、約定、定義、ストレス水準によってどれだけ揺れるかを確認し、`error on error` を実データで説明できる形にすることである。

記事本文では **BTCのみ** を扱う。USDJPY実験は内部検討ログとして保持するが、記事本文、記事用図表、記事骨子との整合性分析からは外す。

中心メッセージは次の一文に集約する。

> ファットテールを織り込むとは、正しい未来分布を当てることではなく、リスクを測るモデルにも誤差があることを認め、エッジ候補がどの条件で壊れるかを見つけ、その結果を運用ルールに変えることである。

## 2. 非目的

- USDJPY の将来リスクを正確に当てること。
- BTC 急落後の買い戦略が有効であると証明すること。
- `Funding low x risk-on` を売買推奨にすること。
- p 値や単一の平均リターンで戦略の有効性を断定すること。
- 最適なファットテール分布を一つ選ぶこと。

## 3. 実験全体の構成

| 実験 | 対象 | 目的 | 記事での役割 |
|---|---|---|---|
| 実験1 | USDJPY 4H | VaR、ES、最大DD、レバレッジ上限が手法・期間・仮定で揺れることを内部確認する | 記事には使わない内部ログ |
| 実験2 | BTC急落 x Funding Rate x 外部リスク環境 | `lab_7` のエッジ候補がコスト、定義、期間、約定で壊れるか検証する | エッジ候補は平均リターンではなく壊れる条件で見ることを示す |
| 実験3 | BTC Fragility Matrix | BTC の壊れる要因を一覧化する | 分析結果を運用ルールへ変換する橋渡しにする |

## 4. ディレクトリ構成

実装後の完成形は以下とする。

```text
lab_10/
  IMPLEMENTATION_SPEC.ja.md
  data/
    usdjpy/
      USDJPY240.csv
    lab_7/
      BTCUSD240.csv
      DEUIDXEUR240.csv
      USA30IDXUSD240.csv
      USA500IDXUSD240.csv
      USATECHIDXUSD240.csv
      funding_rate_history.csv
  scripts/
    00_lab7_interaction_model_base.py
    01_usdjpy_risk_diagnostics.py
    02_btc_crash_fragility.py
    03_fragility_matrix.py
  outputs/
    tables/
    figures/
    report/
    lab7_interaction_model_base/
  reference/
    lab_7/
      run_interaction_model_experiment.py
      README.md
      README.ja.md
      BTC急落実験.pdf
      outputs/
        interaction_model/
```

### 4.1 コピー済みの流用資産

`lab_7` から流用するデータとコードは、`lab_10` 内にコピーして固定する。`lab_10` の実験は、原則として `../lab_7` を直接参照しない。

| コピー先 | コピー元 | 用途 |
|---|---|---|
| `data/lab_7/BTCUSD240.csv` | `../lab_7/data/BTCUSD240.csv` | BTC 4H OHLCV |
| `data/lab_7/USATECHIDXUSD240.csv` | `../lab_7/data/USATECHIDXUSD240.csv` | Nasdaq proxy |
| `data/lab_7/USA500IDXUSD240.csv` | `../lab_7/data/USA500IDXUSD240.csv` | S&P500 proxy |
| `data/lab_7/USA30IDXUSD240.csv` | `../lab_7/data/USA30IDXUSD240.csv` | Dow proxy |
| `data/lab_7/DEUIDXEUR240.csv` | `../lab_7/data/DEUIDXEUR240.csv` | DAX proxy |
| `data/lab_7/funding_rate_history.csv` | `../lab_7/data/funding_rate_history.csv` | BTCUSDT Funding Rate |
| `scripts/00_lab7_interaction_model_base.py` | `../lab_7/run_interaction_model_experiment.py` | `lab_10` 用にパスだけ調整したベースライン再現コード |
| `reference/lab_7/run_interaction_model_experiment.py` | `../lab_7/run_interaction_model_experiment.py` | 元コードの参照用コピー |
| `reference/lab_7/outputs/interaction_model/*` | `../lab_7/outputs/interaction_model/*` | 既存 `lab_7` 結果の参照 |

USDJPY 主データは `lab_9/inputdata/USDJPY240.csv` から `data/usdjpy/USDJPY240.csv` にコピー済みとする。

## 5. 共通実装方針

### 5.1 実行環境

Python 3 を前提とする。最低限必要なライブラリは以下。

| ライブラリ | 用途 |
|---|---|
| pandas | CSV 読み込み、時系列処理、表出力 |
| numpy | リターン、VaR、ES、DD 計算 |
| scipy | Student-t、統計量、信頼区間補助 |
| matplotlib | 記事用図表 |

### 5.2 出力ルール

- CSV は `outputs/tables/` に保存する。
- PNG は `outputs/figures/` に保存する。
- 記事にそのまま貼れる Markdown 要約は `outputs/report/` に保存する。
- 既存の `reference/` は上書きしない。
- `scripts/00_lab7_interaction_model_base.py` の出力先は `outputs/lab7_interaction_model_base/` とする。
- すべての実験で gross と net を分ける。
- net 計算に使ったコスト仮定は必ず CSV に列として残す。

### 5.3 共通評価指標

| 指標 | 定義 | 記事での使い方 |
|---|---|---|
| `n` | 対象イベント数またはリターン数 | 標本誤差の大きさを示す |
| `mean_ret_pct` | 平均リターン | エッジ候補の基準線 |
| `median_ret_pct` | 中央値リターン | 平均が外れ値に引っ張られていないかを見る |
| `win_rate_pct` | 勝率 | 直感的な説明に使うが過信しない |
| `profit_factor` | 総利益 / 絶対総損失 | コスト控除後に 1 を超えるか見る |
| `var_95_pct`, `var_99_pct` | 5%、1% 分位の損失 | 左尾リスクを見る |
| `es_95_pct`, `es_99_pct` | VaR 超過後の平均損失 | VaR の先を見る |
| `mean_mae_pct` | 平均含み損 | 通常時の資金耐性 |
| `worst_mae_pct` | 最悪含み損 | 強制ロスカット耐性 |
| `maxdd_pct` | 資金曲線の最大DD | 停止ルールと必要資本 |
| `recovery_bars` | DD 回復までの本数 | 運用継続性 |
| `bootstrap_ci_low_pct` | 平均リターンの下側信頼区間 | 標本誤差を見せる |

## 6. 実験1: USDJPY リスク推定診断

### 6.1 スクリプト

```text
scripts/01_usdjpy_risk_diagnostics.py
```

### 6.2 入力

```text
data/usdjpy/USDJPY240.csv
```

想定形式はヘッダーなし、タブ区切り。

```text
timestamp open high low close volume
```

### 6.3 前処理

1. `timestamp` を `datetime64` に変換する。
2. 時刻昇順にソートする。
3. 重複タイムスタンプは最後の行を採用する。
4. `open`, `high`, `low`, `close`, `volume` を数値化する。
5. `close_to_close_log_ret` を計算する。
6. `open_to_open_log_ret` を計算する。
7. リスク指標の主計算には `close_to_close_log_ret` を使う。

### 6.4 リスク推定窓

| 窓 | 実装 |
|---|---|
| 1年 | 直近 365 日 |
| 3年 | 直近 1095 日 |
| 5年 | 直近 1825 日 |
| 全期間 | 全データ |

時間ベースで切る。固定本数にしない。

### 6.5 ベースライン指標

各窓について以下を計算する。

| 列名 | 内容 |
|---|---|
| `window_name` | `1y`, `3y`, `5y`, `full` |
| `start`, `end` | 使用期間 |
| `n` | リターン数 |
| `mean_ret_pct` | 平均 4H リターン |
| `vol_pct` | 標準偏差 |
| `annualized_vol_pct` | 年率換算ボラ |
| `skew` | 歪度 |
| `kurtosis` | 尖度 |
| `hist_var_95_pct` | ヒストリカル 5% VaR |
| `hist_var_99_pct` | ヒストリカル 1% VaR |
| `hist_es_95_pct` | ヒストリカル 5% ES |
| `hist_es_99_pct` | ヒストリカル 1% ES |
| `normal_var_95_pct` | 正規分布 5% VaR |
| `normal_var_99_pct` | 正規分布 1% VaR |
| `student_t_var_95_pct` | Student-t 5% VaR |
| `student_t_var_99_pct` | Student-t 1% VaR |
| `maxdd_pct` | リターン系列の最大DD |
| `max_recovery_bars` | 最大回復期間 |

VaR/ES は損失をマイナス値で出す。記事用表では絶対値表示に変換してもよいが、生CSVでは符号を残す。

### 6.6 rolling VaR

以下の rolling 窓で、ヒストリカル VaR と ES を時系列で出す。

| rolling window | 目的 |
|---|---|
| 1年 | 直近重視 |
| 3年 | 中期 |
| 5年 | 長期 |

出力:

```text
outputs/tables/usdjpy_rolling_var.csv
outputs/figures/usdjpy_rolling_var.png
```

図は `hist_var_99_pct` と `hist_es_99_pct` を中心にする。

### 6.7 疑いのダイヤル

USDJPY では、リスク推定値が以下の主観的ストレスでどう変わるかを見る。

| ダイヤル | 水準 | 疑っている仮定 |
|---|---|---|
| ボラ倍率 | `1.0`, `1.1`, `1.2`, `1.5` | 過去ボラが将来も続く |
| 最大DD倍率 | `1.0`, `1.5`, `2.0`, `3.0` | 過去最大DDが将来上限である |
| コスト倍率 | `1.0`, `2.0`, `5.0` | 平常時コストで約定できる |
| 平均リターン劣化 | `0%`, `-25%`, `-50%`, `-100%` | 過去の期待値が続く |

出力:

```text
outputs/tables/usdjpy_stress_dials.csv
outputs/tables/usdjpy_dd_capital_table.csv
outputs/tables/usdjpy_leverage_limits.csv
```

### 6.8 レバレッジ上限

最大許容DDを `20%`, `30%`, `50%` とし、以下で概算する。

```text
leverage_limit = abs(max_allowed_dd_pct / stressed_maxdd_pct)
```

`stressed_maxdd_pct` が `0` または欠損の場合は `NaN` とする。

記事では、これは正しいレバレッジの答えではなく、過去最大DDを何倍で見るかによって許容レバレッジが大きく変わる例として使う。

### 6.9 実験1の成果物

| ファイル | 内容 |
|---|---|
| `outputs/tables/usdjpy_risk_summary.csv` | 窓別 VaR/ES/DD 比較 |
| `outputs/tables/usdjpy_rolling_var.csv` | rolling VaR/ES |
| `outputs/tables/usdjpy_stress_dials.csv` | ボラ、DD、コスト、期待値劣化のストレス |
| `outputs/tables/usdjpy_dd_capital_table.csv` | DD倍率と必要資本 |
| `outputs/tables/usdjpy_leverage_limits.csv` | 許容DD別レバレッジ上限 |
| `outputs/figures/usdjpy_rolling_var.png` | rolling VaR 図 |
| `outputs/figures/usdjpy_risk_method_comparison.png` | 手法別リスク値比較 |
| `outputs/report/usdjpy_risk_diagnostics.md` | 内部検討ログ。記事本文には使わない |

## 7. 実験2: BTC 急落エッジ候補の Fragility 検証

### 7.1 スクリプト

```text
scripts/02_btc_crash_fragility.py
```

このスクリプトは `scripts/00_lab7_interaction_model_base.py` のロジックを土台にする。ただし、元の `lab_7` の結論を強めるためではなく、壊れる条件を検証するために拡張する。

### 7.2 入力

```text
data/lab_7/BTCUSD240.csv
data/lab_7/USATECHIDXUSD240.csv
data/lab_7/USA500IDXUSD240.csv
data/lab_7/USA30IDXUSD240.csv
data/lab_7/DEUIDXEUR240.csv
data/lab_7/funding_rate_history.csv
```

### 7.3 ベースライン再現

まず以下を実行して、`lab_7` のベースラインを `lab_10` 内で再現する。

```bash
python lab_10/scripts/00_lab7_interaction_model_base.py
```

出力:

```text
outputs/lab7_interaction_model_base/
```

再現後、`reference/lab_7/outputs/interaction_model/interaction_group_stats.csv` と主要値が一致することを確認する。

許容差:

```text
absolute tolerance <= 1e-9 for raw numeric CSV values
```

### 7.4 ベース実験定義

| 項目 | 基準設定 |
|---|---|
| 足 | 4H |
| 急落イベント | BTC 4H リターンが rolling 180 本 sigma score で `<= -2.0` |
| event spacing | 24H cooldown、つまり 6 本 |
| エントリー | シグナル確定後の次 4H 始値 |
| 決済 | 24H、48H、5日 |
| 主 risk-on | Nasdaq 5日リターン `> 0` |
| 主 Funding low | expanding percentile `<= 20%` または Funding Rate `< 0` |
| 主 Funding high | expanding percentile `>= 80%` |
| 主グループ | `Funding low x risk-on` |
| 危険比較 | `Funding high x risk-off` |

### 7.5 条件グループ

最低限、以下を出す。

| group | 定義 | 記事での扱い |
|---|---|---|
| `all_funding_covered_crashes` | Funding regime が取得できる全急落 | 基準線 |
| `funding_low_only` | Funding low の急落 | Funding 単体 |
| `risk_on_only` | risk-on の急落 | 外部環境単体 |
| `funding_low_x_risk_on` | Funding low かつ risk-on | 買える急落候補 |
| `funding_high_x_risk_off` | Funding high かつ risk-off | 避ける急落候補 |
| `funding_not_low_x_risk_off` | Funding low ではなく risk-off | 交互作用比較の基準 |

### 7.6 コスト・スリッページ検証

コストは「真のコスト」ではなく、疑いのダイヤルとして置く。

| case | round-trip cost | 用途 |
|---|---:|---|
| `gross` | `0 bps` | 既存結果との比較 |
| `base_cost` | `10 bps` | 現実的な基準線 |
| `cost_x2` | `20 bps` | 危機時の悪化 |
| `cost_x5` | `50 bps` | 急落時の極端な悪化 |

net return:

```text
net_log_return = gross_log_return - round_trip_cost_bps / 10000
```

出力:

```text
outputs/tables/btc_cost_stress.csv
outputs/figures/btc_cost_stress_heatmap.png
```

### 7.7 エントリー遅延・約定悪化

| case | entry_lag_bars | adverse_entry_bps | 目的 |
|---|---:|---:|---|
| `next_open` | 1 | 0 | `lab_7` 基準 |
| `delay_4h` | 2 | 0 | 1本遅れ |
| `delay_8h` | 3 | 0 | 2本遅れ |
| `adverse_10bps` | 1 | 10 | 約定品質悪化 |
| `adverse_25bps` | 1 | 25 | 急落時の不利約定 |

ロング前提の不利約定は、entry price を上にずらす。

```text
effective_entry = entry_open * (1 + adverse_entry_bps / 10000)
gross_log_return = log(exit_open / effective_entry)
```

出力:

```text
outputs/tables/btc_entry_execution_stress.csv
outputs/figures/btc_entry_execution_stress.png
```

### 7.8 crash 定義変更

| event_def | 定義 | 目的 |
|---|---|---|
| `rolling_1_5sigma` | rolling 180 sigma score `<= -1.5` | 広めの急落 |
| `rolling_2sigma` | rolling 180 sigma score `<= -2.0` | 基準 |
| `rolling_2_5sigma` | rolling 180 sigma score `<= -2.5` | 厳しめの急落 |
| `full_sample_q05` | BTC 4H return が全期間下位 5% | rolling 定義依存の確認 |
| `full_sample_q025` | BTC 4H return が全期間下位 2.5% | 極端急落 |

`lab_7` には `rolling_1_5sigma`, `rolling_2sigma`, `full_sample_q05` が既にある。`rolling_2_5sigma` と `full_sample_q025` を追加する。

出力:

```text
outputs/tables/btc_definition_robustness.csv
outputs/figures/btc_definition_robustness_heatmap.png
```

### 7.9 risk-on 定義変更

| risk_env | 定義 | 目的 |
|---|---|---|
| `nasdaq_5d_up` | Nasdaq 5日リターン `> 0` | 基準 |
| `sp500_5d_up` | S&P500 5日リターン `> 0` | Nasdaq 依存の確認 |
| `broad_3of4_5d_up` | Nasdaq/S&P500/Dow/DAX のうち 3つ以上が `> 0` | 広い外部環境 |
| `nasdaq_5d_gt_1pct` | Nasdaq 5日リターン `> +1%` | 強い risk-on |
| `sp500_5d_gt_1pct` | S&P500 5日リターン `> +1%` | 強い米国株 risk-on |

出力:

```text
outputs/tables/btc_risk_env_robustness.csv
outputs/figures/btc_risk_env_robustness.png
```

### 7.10 Funding 定義変更

| funding_case | 定義 | 目的 |
|---|---|---|
| `negative` | Funding Rate `< 0` | 明確な悲観 |
| `lower_20_or_negative` | expanding percentile `<= 20%` または `< 0` | `lab_7` 基準 |
| `lower_20_only` | expanding percentile `<= 20%` | 分位だけ |
| `lower_10_or_negative` | expanding percentile `<= 10%` または `< 0` | より極端な悲観 |
| `high_20` | expanding percentile `>= 80%` | 過熱比較 |
| `high_10` | expanding percentile `>= 90%` | 極端な過熱 |

出力:

```text
outputs/tables/btc_funding_definition_robustness.csv
outputs/figures/btc_funding_definition_robustness.png
```

### 7.11 期間分割

| period | 条件 | 目的 |
|---|---|---|
| `all` | 全期間 | 基準 |
| `2020_2021` | `2020-01-01 <= t < 2022-01-01` | 強気・高流動性期 |
| `2022_stress` | `2022-01-01 <= t < 2023-01-01` | 暗号資産ストレス期 |
| `2023_2024` | `2023-01-01 <= t < 2025-01-01` | 回復期 |
| `2025_2026` | `2025-01-01 <= t` | 直近期 |
| `post_btc_etf` | `2024-01-11 <= t` | ETF後 |

出力:

```text
outputs/tables/btc_subperiod_results.csv
outputs/figures/btc_subperiod_results.png
```

### 7.12 walk-forward 検証

過剰最適化を避けるため、条件選択と評価を分ける。

最低限の仕様:

| fold | train | test |
|---|---|---|
| `wf_1` | 2020-2021 | 2022 |
| `wf_2` | 2020-2022 | 2023 |
| `wf_3` | 2020-2023 | 2024 |
| `wf_4` | 2020-2024 | 2025-2026 |

train で選ぶのは「どの条件が良かったか」ではなく、候補条件 `Funding low x risk-on` が過去でどう見えていたかに留める。test では固定条件として評価する。

出力:

```text
outputs/tables/btc_walk_forward.csv
```

### 7.13 MAE/DD/レバレッジ耐性

対象は主に `funding_low_x_risk_on` と `funding_high_x_risk_off`。

| stress | 内容 |
|---|---|
| `stop_3pct` | 保有中 MAE が `-3%` 以下なら損切りした近似 |
| `stop_5pct` | 保有中 MAE が `-5%` 以下なら損切りした近似 |
| `stop_10pct` | 保有中 MAE が `-10%` 以下なら損切りした近似 |
| `leverage_1x` | MAE/DD を 1倍換算 |
| `leverage_2x` | MAE/DD を 2倍換算 |
| `leverage_3x` | MAE/DD を 3倍換算 |

ストップ近似は、厳密な intrabar 約定価格を復元できないため、まずは以下の保守的な近似でよい。

```text
if mae <= stop_level:
    stopped_return = stop_level - cost
else:
    stopped_return = exit_return - cost
```

レバレッジ耐性:

```text
levered_mae = mae * leverage
levered_return = net_return * leverage
margin_breach = levered_mae <= -margin_threshold
```

`margin_threshold` は `30%`, `50%`, `80%` を出す。

出力:

```text
outputs/tables/btc_mae_dd_stress.csv
outputs/tables/btc_leverage_tolerance.csv
outputs/figures/btc_leverage_tolerance.png
```

### 7.14 ブートストラップ信頼区間

サンプル数の小ささを記事で明示するため、主グループには bootstrap を入れる。

最低仕様:

- resampling: event 単位の iid bootstrap
- iterations: `10000`
- seed: `42`
- 対象指標: mean return, PF, win rate
- CI: 5%, 50%, 95%

時系列依存を厳密に補正する目的ではなく、`n=15` などの小標本で推定がどれだけ揺れるかを見せる目的とする。

出力:

```text
outputs/tables/btc_bootstrap_uncertainty.csv
outputs/figures/btc_bootstrap_mean_return.png
```

### 7.15 壊れた判定

各 stress case に対して、以下の判定列を作る。

| 列名 | 判定 |
|---|---|
| `is_small_sample` | `n < 30` |
| `is_very_small_sample` | `n < 20` |
| `is_mean_broken` | `mean_ret_pct <= 0` |
| `is_pf_broken` | `profit_factor <= 1` |
| `is_ci_fragile` | bootstrap 5% 下限 `<= 0` |
| `is_drawdown_severe` | `maxdd_pct <= -20` |
| `is_execution_fragile` | 4H/8H 遅延で mean または PF が基準から大きく悪化 |
| `is_cost_fragile` | `base_cost` で PF <= 1 または `cost_x2` で mean <= 0 |

総合判定:

| `fragility_status` | 条件 |
|---|---|
| `broken` | `is_mean_broken` または `is_pf_broken` |
| `fragile` | `is_very_small_sample` または `is_ci_fragile` または `is_cost_fragile` |
| `watch` | `is_small_sample` または `is_drawdown_severe` |
| `survives_this_test` | 上記に該当しない |

重要: `survives_this_test` は「有効戦略」を意味しない。この実験条件ではまだ壊れなかった、という意味に限定する。

### 7.16 実験2の成果物

| ファイル | 内容 |
|---|---|
| `outputs/tables/btc_crash_baseline.csv` | `lab_7` ベースライン再計算 |
| `outputs/tables/btc_cost_stress.csv` | コストでの壊れ方 |
| `outputs/tables/btc_entry_execution_stress.csv` | 約定遅延・不利約定での壊れ方 |
| `outputs/tables/btc_definition_robustness.csv` | crash 定義変更 |
| `outputs/tables/btc_risk_env_robustness.csv` | risk-on 定義変更 |
| `outputs/tables/btc_funding_definition_robustness.csv` | Funding 定義変更 |
| `outputs/tables/btc_subperiod_results.csv` | 期間分割 |
| `outputs/tables/btc_walk_forward.csv` | walk-forward |
| `outputs/tables/btc_mae_dd_stress.csv` | MAE/DD/stop |
| `outputs/tables/btc_leverage_tolerance.csv` | レバレッジ耐性 |
| `outputs/tables/btc_bootstrap_uncertainty.csv` | 小標本の推定揺れ |
| `outputs/report/btc_crash_fragility.md` | 記事用要約 |

## 8. 実験3: BTC Fragility Matrix

### 8.1 スクリプト

```text
scripts/03_fragility_matrix.py
```

### 8.2 入力

```text
outputs/tables/btc_cost_stress.csv
outputs/tables/btc_entry_execution_stress.csv
outputs/tables/btc_definition_robustness.csv
outputs/tables/btc_risk_env_robustness.csv
outputs/tables/btc_funding_definition_robustness.csv
outputs/tables/btc_subperiod_results.csv
outputs/tables/btc_mae_dd_stress.csv
outputs/tables/btc_leverage_tolerance.csv
```

### 8.3 出力列

```text
target
fragility_source
assumption_being_doubted
stress_case
metric
baseline_value
stressed_value
change
break_condition
fragility_status
article_message
practical_response
```

### 8.4 対象別の行

BTC:

| `fragility_source` | `assumption_being_doubted` | `practical_response` |
|---|---|---|
| `sample_size` | 条件付き平均が安定している | 主張を弱め、n を明記する |
| `cost` | gross の優位性が net でも残る | コスト上限を決める |
| `execution` | 次の始値で入れる | 遅延耐性を確認する |
| `crash_definition` | 急落定義に依存しない | 定義別に結果を併記する |
| `risk_env_definition` | Nasdaq proxy だけで十分 | 外部環境指標を複数化する |
| `funding_definition` | Funding low の閾値が安定している | 閾値感度を併記する |
| `subperiod` | どのレジームでも残る | 期間依存を明記する |
| `mae_dd_leverage` | 含み損に耐えられる | レバレッジ制限を置く |

### 8.5 出力

```text
outputs/tables/fragility_matrix.csv
outputs/report/fragility_matrix.md
outputs/figures/fragility_matrix_status.png
```

## 9. 記事に使う図表候補

優先順位は以下。

| 優先 | 図表 | 理由 |
|---:|---|---|
| 1 | `btc_cost_stress_heatmap.png` | gross では良く見える候補がコストでどう変わるかを直感的に示せる |
| 2 | `btc_definition_robustness_heatmap.png` | 定義依存を説明しやすい |
| 3 | `btc_bootstrap_mean_return.png` | `n=15` の小標本誤差を示せる |
| 4 | `btc_entry_execution_stress.png` | 約定遅延で候補がどれだけ劣化するかを示せる |
| 5 | `fragility_matrix_status.png` | 最終的な実務整理に使える |

記事では図を増やしすぎない。本文には 3-5 枚、補足に CSV 一覧を置く。

## 10. 記事での表現ルール

BTC について使ってよい表現:

- `Funding low x risk-on は面白いエッジ候補に見える。`
- `ただし、サンプル数、コスト、定義、約定、期間分割に依存する。`
- `この実験の目的は、エッジの証明ではなく、壊れる条件の確認である。`
- `この条件ではまだ壊れなかった、という言い方に留める。`

避ける表現:

- `BTC急落は買いである。`
- `Funding low x risk-on は有効戦略である。`
- `Nasdaq が BTC を予測する。`
- `p 値が有意なので実運用可能である。`
- `ファットテールを織り込めた。`

USDJPY について:

- USDJPYは記事本文では扱わない。
- 既存のUSDJPY出力は内部検討ログとして残す。
- 記事用図表、記事骨子との整合性分析、本文の実験説明には含めない。

## 11. 実装順序

1. `scripts/00_lab7_interaction_model_base.py` を実行し、`lab_10` 内で `lab_7` ベースラインを再現する。
2. `scripts/01_usdjpy_risk_diagnostics.py` は内部検討ログとして保持する。記事用成果物には使わない。
3. `scripts/02_btc_crash_fragility.py` を実装し、BTC 急落エッジ候補のコスト、約定、定義、期間、MAE/DD、レバレッジ耐性を出す。
4. `scripts/03_fragility_matrix.py` を実装し、壊れる要因を統合表にする。
5. `outputs/report/` に記事用の短い要約 Markdown を作る。
6. 図表を確認し、本文に使うものを 3-5 個に絞る。

## 12. 検証コマンド

最低限、以下を通す。

```bash
python -m py_compile lab_10/scripts/00_lab7_interaction_model_base.py
python lab_10/scripts/00_lab7_interaction_model_base.py
```

実装完了後は以下も通す。

```bash
python -m py_compile lab_10/scripts/01_usdjpy_risk_diagnostics.py
python -m py_compile lab_10/scripts/02_btc_crash_fragility.py
python -m py_compile lab_10/scripts/03_fragility_matrix.py

python lab_10/scripts/01_usdjpy_risk_diagnostics.py
python lab_10/scripts/02_btc_crash_fragility.py
python lab_10/scripts/03_fragility_matrix.py
```

## 13. 完了条件

実装完了の条件は以下。

- `lab_10` だけで主要実験が再現できる。
- `lab_7` の入力データとベースコードが `lab_10` にコピーされている。
- `../lab_7` を直接参照しなくても BTC 実験が動く。
- BTC のコスト、約定、定義、risk-on、Funding、期間、MAE/DD、レバレッジ耐性表が出ている。
- `fragility_matrix.csv` が出ている。
- `outputs/report/` に記事用要約がある。
- 記事用要約、記事骨子との整合性分析、図表選定はBTCのみで構成されている。
- 記事本文で、エッジ候補を強く言いすぎないための制約が明記されている。
