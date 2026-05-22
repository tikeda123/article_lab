# 実装計画書：トレンドフォロー実験

## 1. 目的

この計画書は、`trend_following_experiment_outline_no_wfo.md` の実験骨子を、実装可能な作業単位に分解するための実装計画である。

本実験の目的は、USDJPYの実データを使い、単純なトレンドフォロー戦略に以下の損益構造が観察されるかを確認することである。

- 高勝率ではなく、平均利益が平均損失を上回る構造になるか
- 損益分布に右テールがあるか
- コスト控除後でも期待値が残るか
- 60分足と240分足で性質が変わるか
- ランダム方向エントリーより優位か
- 近傍パラメータでも構造が残るか
- entry delay を入れても構造が残るか
- 固定パラメータのOOSでも傾向が残るか

本実験ではWFOは実施しない。パラメータ再最適化ではなく、固定条件で損益構造が残るかを確認する。

---

## 2. 実装範囲

### 初回実装で行うこと

- USDJPY 60分足、240分足の読み込み
- 2023年から2025年への期間絞り込み
- 移動平均クロス戦略の実装
- 次足始値エントリー、次足始値決済
- 往復固定pipsコストの控除
- 取引ログの生成
- 基本評価指標の集計
- 損益分布、累積損益、ドローダウンの可視化
- 上位勝ちトレード除外テスト
- コスト感応度
- ランダム方向エントリー比較
- 近傍パラメータヒートマップ
- entry delay sensitivity
- 2023年から2024年を開発・分析期間、2025年をOOS確認期間とする固定パラメータ検証

### 初回実装で行わないこと

- WFO
- OOS期間での再最適化
- ブレイクアウト型戦略
- Efficiency Ratio、ADXなどの独立フィルター
- ATRベースやボラティリティターゲティングによるポジションサイズ調整
- 複数市場への展開
- bid / askを使った精密な約定再現
- スワップポイント、時間帯別スプレッド、指標発表時の流動性低下の再現

これらは、初回記事で広げすぎないために発展編へ回す。

---

## 3. 入力データ

使用するファイルは以下とする。

- `lab_5/USDJPY60.csv`
- `lab_5/USDJPY240.csv`

現在のCSVはヘッダーなしの区切りテキストとして扱う。

想定列：

```text
datetime open high low close volume
```

読み込み時の基本方針：

- `datetime` を日時としてparseする
- `open`, `high`, `low`, `close` をfloatとして扱う
- `volume` は初回実験では使わないが、列として保持する
- タイムゾーンは元データの仕様を確認し、記事では「データ時刻の前提」として明記する
- 欠損、重複、OHLCの異常値を事前チェックする

---

## 4. 実装ファイル構成案

最初は過度に分割せず、記事用の再現性を優先して単一スクリプト中心で作る。

```text
lab_5/
  run_trend_following_experiment.py
  trend_following_experiment_outline_no_wfo.md
  trend_following_edge_article_outline_improved.md
  trend_following_experiment_implementation_plan.md
  USDJPY60.csv
  USDJPY240.csv
  outputs/
    trend_following_ma_cross/
      summary_metrics.csv
      trade_log_60m.csv
      trade_log_240m.csv
      cost_sensitivity.csv
      top_trade_exclusion.csv
      random_direction_comparison.csv
      parameter_heatmap.csv
      entry_delay_sensitivity.csv
      fixed_oos_summary.csv
      figures/
        equity_curve.png
        drawdown_curve.png
        trade_pnl_histogram.png
        top_trade_exclusion.png
        cost_sensitivity.png
        random_direction_comparison.png
        parameter_heatmap_pf.png
        entry_delay_sensitivity.png
        fixed_oos_comparison.png
```

将来、実験が大きくなった場合のみ、データ読み込み、バックテスト、指標計算、可視化をモジュール分割する。

---

## 5. バックテスト仕様

### 基本戦略

移動平均クロス型を使う。

- 短期MA：20
- 長期MA：80
- 短期MA > 長期MA：ロング
- 短期MA < 長期MA：ショート
- 反対シグナルで決済し、同時にドテンする
- シグナルは終値確定後に判定する
- 約定は次足始値で行う

この `20 / 80` は最小構成の基準例であり、最良パラメータとして扱わない。

### 損益計算

USDJPYのpips換算は以下を基本とする。

```text
pips = price_diff * 100
```

ロング：

```text
gross_pnl_pips = (exit_price - entry_price) * 100
```

ショート：

```text
gross_pnl_pips = (entry_price - exit_price) * 100
```

ネット損益：

```text
net_pnl_pips = gross_pnl_pips - round_trip_cost_pips
```

コストは往復固定pipsとして、1つの完了トレードごとに控除する。

### コスト設定

最小構成では以下を使う。

- 0.0 pips
- 0.8 pips
- 1.0 pips
- 2.0 pips

記事本文では、0.8から1.0 pipsを現実的な近似例として扱い、2.0 pipsは耐性確認として使う。

---

## 6. 主要な実装関数案

`run_trend_following_experiment.py` には、以下の処理単位を用意する。

### データ処理

```text
load_price_csv(path) -> DataFrame
validate_price_data(df) -> dict
filter_period(df, start, end) -> DataFrame
```

確認する内容：

- 行数
- 開始日時、終了日時
- datetime重複
- 欠損
- OHLCの不整合

### シグナル生成

```text
add_ma_signal(df, short_window=20, long_window=80) -> DataFrame
```

出力する列：

- short_ma
- long_ma
- raw_signal
- signal_time

`raw_signal` は、終値確定後に分かる方向として扱う。

### トレード生成

```text
build_trade_log(df, signal_col, entry_delay_bars, round_trip_cost_pips) -> DataFrame
```

出力する列：

- entry_time
- exit_time
- direction
- entry_price
- exit_price
- gross_pnl_pips
- cost_pips
- net_pnl_pips
- holding_bars
- timeframe
- short_window
- long_window
- entry_delay_bars

entry delay は、シグナル確定後の約定をさらに遅らせる検証として扱う。

- delay 0：次足始値
- delay 1：さらに1本後の始値
- delay 2：さらに2本後の始値
- delay 4：さらに4本後の始値

エントリーと決済の両方に同じ遅延ルールを適用する。

### 評価指標

```text
calculate_metrics(trades) -> dict
calculate_drawdown(equity_curve) -> DataFrame
calculate_top_trade_dependency(trades, pct_list=[1, 5, 10]) -> DataFrame
```

最低限出す指標：

- total_pnl_pips
- trade_count
- win_rate
- profit_factor
- max_drawdown_pips
- avg_win_pips
- avg_loss_pips
- avg_win_loss_ratio
- median_trade_pips
- max_win_pips
- max_loss_pips
- pnl_skew
- top_1pct_win_contribution
- top_5pct_win_contribution
- top_10pct_win_contribution

### 可視化

```text
plot_equity_curve(...)
plot_drawdown(...)
plot_trade_pnl_histogram(...)
plot_cost_sensitivity(...)
plot_random_comparison(...)
plot_parameter_heatmap(...)
plot_entry_delay_sensitivity(...)
```

図は記事へ貼れるように、PNGで保存する。

---

## 7. 段階的な進め方

### Phase 0：データ監査

目的：

実験に使う価格データの前提を確認する。

実装内容：

- 60分足、240分足を読み込む
- 列名を付与する
- 日時、欠損、重複、期間を確認する
- 2023年から2025年に絞った件数を確認する

成果物：

- `data_audit.csv`
- コンソール上のデータ監査サマリー

完了条件：

- 60分足と240分足の開始・終了日時が確認できている
- 2023年から2025年の抽出ができている
- 欠損や重複の扱い方を決めている

---

### Phase 1：ベースライン戦略の実装

目的：

MA 20 / 80 の単純なトレンドフォローを、コスト0.0 pipsで正しく動かす。

実装内容：

- MA 20 / 80 を計算する
- ロング、ショートの方向シグナルを作る
- 次足始値でエントリー・決済する
- 反対シグナルでドテンする
- 取引ログを生成する

成果物：

- `trade_log_60m.csv`
- `trade_log_240m.csv`
- `summary_metrics.csv`

完了条件：

- 取引ログに entry / exit / direction / pnl が出ている
- 同じ終値でシグナル判定とエントリーをしていない
- 60分足と240分足の結果が別々に出ている

---

### Phase 2：基本指標と主要図の作成

目的：

記事に必要な最低限の評価指標と図を作る。

実装内容：

- 勝率
- Profit Factor
- MaxDD
- 平均利益
- 平均損失
- 平均利益 / 平均損失
- 損益ヒストグラム
- 累積損益曲線
- ドローダウン曲線

成果物：

- `summary_metrics.csv`
- `figures/equity_curve.png`
- `figures/drawdown_curve.png`
- `figures/trade_pnl_histogram.png`

完了条件：

- 勝率だけでは評価できないことを示す指標が揃っている
- 右テールの有無を図で確認できる
- MaxDDと停滞を確認できる

---

### Phase 3：コスト感応度

目的：

固定pipsコストでエッジが消えるかを確認する。

実装内容：

- 0.0 / 0.8 / 1.0 / 2.0 pipsで再計算する
- 60分足と240分足を比較する
- コスト別に総損益、PF、MaxDD、勝率を集計する

成果物：

- `cost_sensitivity.csv`
- `figures/cost_sensitivity.png`

完了条件：

- 0コストでしか成立しないのか、現実的コストでも残るのかを判定できる
- 60分足と240分足のコスト耐性差を確認できる

---

### Phase 4：右テール依存の確認

目的：

トレンドフォローらしい右テール依存の強さを定量化する。

実装内容：

- 上位1％、5％、10％の勝ちトレード寄与率を計算する
- 上位勝ちトレード除外後の累積損益を再計算する
- 通常ケースと除外ケースを比較する

成果物：

- `top_trade_exclusion.csv`
- `figures/top_trade_exclusion.png`

完了条件：

- 少数の勝ちトレードにどの程度依存しているかを説明できる
- 「右テール依存は強みであり脆弱性でもある」という記事の主張につながる

---

### Phase 5：ランダム方向エントリー比較

目的：

シグナルの方向判断に意味があったかをnull modelで確認する。

実装内容：

- 実戦略の取引時点と保有期間は維持する
- ロング / ショート方向だけをランダム化する
- 乱数seedを固定する
- 1000回を目安にシミュレーションする
- 実戦略がランダム分布のどの位置にあるかを集計する

成果物：

- `random_direction_comparison.csv`
- `figures/random_direction_comparison.png`

完了条件：

- 実戦略の総損益とPFがランダム分布のどのパーセンタイルにあるかを確認できる
- ランダムと差がない場合も、その結論を記事に書ける

---

### Phase 6：近傍パラメータヒートマップ

目的：

MA 20 / 80 の一点だけに依存していないかを確認する。

実装内容：

- 短期MA：10, 20, 30, 40, 60
- 長期MA：60, 80, 120, 160, 200
- 短期MA >= 長期MA の組み合わせは除外する
- コスト1.0 pipsを基本ケースにする
- 60分足、240分足それぞれでPF、総損益、MaxDDを集計する

成果物：

- `parameter_heatmap.csv`
- `figures/parameter_heatmap_pf.png`

完了条件：

- 良い領域が面として存在するかを確認できる
- ただし、OOSで良いパラメータを選び直さない
- ヒートマップは選別ではなく、頑健性確認として扱う

---

### Phase 7：entry delay sensitivity

目的：

次足始値でしか成立しない脆い戦略ではないかを確認する。

実装内容：

- delay 0, 1, 2, 4を比較する
- delay 0は通常の次足始値エントリーとする
- エントリーと決済の両方に遅延を適用する
- 総損益、PF、MaxDD、勝率、平均利益、平均損失、トレード数を比較する

成果物：

- `entry_delay_sensitivity.csv`
- `figures/entry_delay_sensitivity.png`

完了条件：

- 少し遅れても構造が残るのか、すぐ崩れるのかを説明できる
- 「遅れて入る」戦略の妥当性と限界を記事に接続できる

---

### Phase 8：固定パラメータOOS確認

目的：

開発・分析期間で観察した損益構造が、OOSでも残るかを確認する。

期間：

- 開発・分析期間：2023年から2024年
- OOS確認期間：2025年
- 2026年以降：将来のHoldout候補として残す

実装内容：

- MA 20 / 80 を固定する
- コストは0.8 / 1.0 / 2.0 pipsを確認する
- OOS期間ではパラメータを再最適化しない
- 開発期間とOOS期間で同じ指標を比較する
- OOSでもランダム方向エントリー比較を行う

成果物：

- `fixed_oos_summary.csv`
- `figures/fixed_oos_comparison.png`

完了条件：

- OOSでも損益構造が残るかを確認できる
- OOSで崩れた場合も、どの構造が崩れたのかを説明できる
- 「固定パラメータOOS」であり、WFOではないことが明確になっている

---

### Phase 9：記事用の結果整理

目的：

実験結果を記事に貼れる形へ整理する。

実装内容：

- 主要表を1つにまとめる
- 記事に貼る図を選定する
- 良い結果、悪い結果のどちらでも解釈できるコメントを用意する
- 限界を明記する

記事に必ず入れる観点：

- これは恒久的なエッジの証明ではない
- 固定pipsコストは近似である
- bid / askとスリッページは完全再現していない
- USDJPYだけでは一般化できない
- 2023年から2025年だけでは期間が短い
- WFOや複数市場展開は発展編である

成果物：

- `article_result_summary.md`
- 記事掲載候補の図一式

完了条件：

- 記事本文へ移せる表と図が揃っている
- 結論が過剰主張になっていない

---

## 8. 実行コマンド案

初回は以下のように、同じスクリプトで全フェーズを再現できる形にする。

```bash
python lab_5/run_trend_following_experiment.py \
  --input-60m lab_5/USDJPY60.csv \
  --input-240m lab_5/USDJPY240.csv \
  --start 2023-01-01 \
  --end 2026-01-01 \
  --dev-end 2025-01-01 \
  --short-window 20 \
  --long-window 80 \
  --costs 0.0 0.8 1.0 2.0 \
  --random-runs 1000 \
  --output-dir lab_5/outputs/trend_following_ma_cross
```

段階実行を可能にする場合は、以下のような `--stage` を用意する。

```bash
python lab_5/run_trend_following_experiment.py --stage audit
python lab_5/run_trend_following_experiment.py --stage baseline
python lab_5/run_trend_following_experiment.py --stage robustness
python lab_5/run_trend_following_experiment.py --stage oos
python lab_5/run_trend_following_experiment.py --stage all
```

最初は `--stage all` を作るより、Phase 0からPhase 2までを確実に通してから、後続の検証を足す。

---

## 9. 実装順序の優先順位

優先度1：

1. データ読み込みと監査
2. MA 20 / 80 の取引ログ生成
3. 基本指標
4. 累積損益、ドローダウン、損益ヒストグラム

優先度2：

1. コスト感応度
2. 上位勝ちトレード除外
3. ランダム方向エントリー比較

優先度3：

1. 近傍パラメータヒートマップ
2. entry delay sensitivity
3. 固定パラメータOOS比較

優先度4：

1. 記事用サマリー
2. 図の体裁調整
3. 結果解釈文の整理

---

## 10. 品質確認チェックリスト

実装後、以下を確認する。

- 終値でシグナルを判定し、同じ終値で約定していない
- 約定は次足始値になっている
- コストは往復固定pipsとして1トレードごとに控除している
- 60分足と240分足を混ぜて集計していない
- 2025年OOSでパラメータを再最適化していない
- ランダム比較はseed固定で再現できる
- ヒートマップはパラメータ選別ではなく頑健性確認として扱っている
- OOSで良かったパラメータを後から選んでいない
- 生成物が `lab_5/outputs/` 以下にまとまっている
- 記事で使う図とCSVの対応が追跡できる

---

## 11. 最終的な到達点

初回実装の完了状態は、以下とする。

- USDJPY 60分足、240分足でMAクロス実験が再現できる
- コスト控除後の損益構造が確認できる
- 右テール依存を定量化できる
- ランダム方向エントリーとの比較ができる
- 近傍パラメータの安定性が確認できる
- entry delay に対する耐性が確認できる
- 固定パラメータOOSの結果が出ている
- 記事へ貼れる表と図が揃っている

この状態まで進めば、記事では「トレンドフォローに恒久的なエッジがある」とは断定せず、以下の範囲で結論を書ける。

> この市場・期間・時間足・コスト前提では、トレンドフォローに期待される損益構造が観察されるかを確認した。
