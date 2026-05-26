# lab_5: USDJPY トレンドフォロー・エッジ診断

English: [README.md](README.md)

このディレクトリは、Qiita記事「[トレンドフォローにエッジはあるのか――「遅れて入る」戦略がなぜ生き残るのか](https://qiita.com/tikeda123/items/e599112d88c912a86125)」および [英語版](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2) に対応する実験ラボである。

目的は、MA 20/80 が完成した売買戦略かどうかを示すことではない。トレンドフォローが、コスト控除後、右テール依存、ランダム方向比較、近傍パラメータ、entry delay、固定OOS確認を通して、どの程度「エッジらしい損益構造」を残すかを観察することである。

このラボは投資助言ではなく、本番運用可能な売買システムでもない。記事用の根拠を再現可能な形で確認するための教育用診断パッケージである。

## 学習ログとフィードバック

このラボは、トレンドフォローの考え方を再現可能な検証項目へ落とし込むための公開学習ログでもある。コード、CSV出力、図表、記事メモは、前提や限界を後から確認できるように共有している。

共有しているスクリプト、出力ファイル、または記事草稿に基づいて、誤り、再現性の問題、実験設計への疑問、別の解釈があれば指摘していただけるとありがたい。

## 実験の位置づけ

この実験では、USDJPY の60分足と240分足を使い、以下の順に確認している。

1. ローカルのタブ区切り USDJPY 60分足・240分足 OHLCV CSV を読み込む
2. 欠損タイムスタンプ、OHLC欠損、重複タイムスタンプ、OHLC不整合、マーケットギャップを監査する
3. `2023-01-01 <= timestamp < 2026-01-01` を実験対象にする
4. `2023-2024` を開発・分析期間、`2025` を固定OOS期間として扱う
5. 両時間足で単純な MA 20/80 クロス戦略を実行する
6. シグナルは終値確定後に判定し、次足始値で約定する
7. 往復コストを控除し、主ケースは `1.0` pips とする
8. フル期間、開発期間、OOS期間の成績を比較する
9. コスト感応度、上位勝ちトレード依存、ランダム方向比較、パラメータ面、entry delay、月次損益、方向別寄与を診断する
10. long only と short抑制フィルターの方向アブレーションを別スクリプトで確認する
11. 記事用図表を `article_figures/` に番号付きでまとめる

重要な読み方は、240分足ベースラインがフル期間および2023-2024では強く見えた一方、固定2025 OOSで崩れた点である。このため、このラボは「良いパラメータを選ぶ実験」ではなく、トレンドフォローの損益構造とバックテスト懐疑のための実験として扱う。

## 主なファイル

| ファイル | 内容 |
|---|---|
| `run_trend_following_experiment.py` | MAクロス本体、診断、CSV出力、図表生成 |
| `run_trend_following_direction_ablation.py` | long only と short抑制アブレーション |
| `save_article_figures.py` | 記事用図表を番号付きファイルへコピーするスクリプト |
| `USDJPY60.csv` | USDJPY 60分足の入力データ |
| `USDJPY240.csv` | USDJPY 240分足の入力データ |
| `trend_following_edge_article_outline_improved.md` | 改善版の記事アウトライン |
| `trend_following_experiment_analysis_and_discussion.md` | 分析・考察メモ |
| `trend_following_experiment_implementation_plan.md` | 実装計画 |
| `trend_following_experiment_outline_no_wfo.md` | WFOなし実験アウトライン |
| `README.md` | このラボの英語版説明 |
| `README.ja.md` | このラボの日本語版説明 |

## 入力データ

現在の `lab_5` には入力CSV本体を含めている。

| ファイル | 時間足 | 形式 |
|---|---|---|
| `USDJPY60.csv` | 60分足 | ヘッダーなし、タブ区切り `datetime, open, high, low, close, volume` |
| `USDJPY240.csv` | 240分足 | ヘッダーなし、タブ区切り `datetime, open, high, low, close, volume` |

`outputs/trend_following_ma_cross/data_audit.csv` に記録されている現在のデータ監査値は以下である。

| 時間足 | 元行数 | 整理後行数 | 入力開始 | 入力終了 | 実験対象行数 | 開発行数 | OOS行数 | ギャップ数 |
|---|---:|---:|---|---|---:|---:|---:|---:|
| 60分足 | 100,000 | 100,000 | `2010-03-18 18:00` | `2026-04-02 12:00` | 18,700 | 12,474 | 6,226 | 859 |
| 240分足 | 25,855 | 25,855 | `2010-03-18 08:00` | `2026-04-02 12:00` | 4,835 | 3,225 | 1,610 | 854 |

週末・祝日などのFX市場休場はギャップとして数えている。補間は行っていない。

## 実験環境

主スクリプトは Python 3 で動作する。必要な外部パッケージは以下である。

| パッケージ | 用途 |
|---|---|
| pandas | CSV読み込み、売買ログ、集計表 |
| numpy | 指標計算、ランダム方向比較、配列計算 |
| matplotlib | PNG図表生成 |

## 再現コマンド

リポジトリルートから、主実験の出力を再生成する。

```bash
python lab_5/run_trend_following_experiment.py
```

既存の正本出力を壊さずに確認する場合は、一時ディレクトリへ出力する。

```bash
python lab_5/run_trend_following_experiment.py \
  --output-dir /tmp/lab5_trend_following_check
```

方向アブレーションを再生成する。

```bash
python lab_5/run_trend_following_direction_ablation.py
```

確認用には一時ディレクトリを使う。

```bash
python lab_5/run_trend_following_direction_ablation.py \
  --output-dir /tmp/lab5_direction_ablation_check
```

生成済み図表を記事用の番号付きファイルへコピーする。

```bash
python lab_5/save_article_figures.py
```

## Python実験ツールの使い方

利用可能な引数は以下で確認する。

```bash
python lab_5/run_trend_following_experiment.py --help
python lab_5/run_trend_following_direction_ablation.py --help
python lab_5/save_article_figures.py --help
```

主実験スクリプトの重要な引数は以下である。

| 引数 | 既定値 | 用途 |
|---|---|---|
| `--input-60m` | `lab_5/USDJPY60.csv` | USDJPY 60分足CSV |
| `--input-240m` | `lab_5/USDJPY240.csv` | USDJPY 240分足CSV |
| `--output-dir` | `lab_5/outputs/trend_following_ma_cross` | 主実験の出力先 |
| `--start` | `2023-01-01` | 実験開始日時。以上 |
| `--end` | `2026-01-01` | 実験終了日時。未満 |
| `--dev-end` | `2025-01-01` | 開発期間とOOS期間の境界 |
| `--short-window` | `20` | 短期MA期間 |
| `--long-window` | `80` | 長期MA期間 |
| `--costs` | `0.0 0.8 1.0 2.0` | 往復コストpips |
| `--random-runs` | `1000` | ランダム方向シミュレーション回数 |
| `--seed` | `12345` | 乱数シード |
| `--stage` | `all` | `audit`, `baseline`, `robustness`, `oos`, `all` の部分実行 |

方向アブレーションの重要な引数は以下である。

| 引数 | 既定値 | 用途 |
|---|---|---|
| `--output-dir` | `lab_5/outputs/trend_following_direction_ablation` | アブレーション出力先 |
| `--round-trip-cost-pips` | `1.0` | 往復コストpips |
| `--slope-lookback-bars` | `20` | MA下向き判定の参照バー数 |
| `--regime-ma-window` | `200` | MA200 shortフィルター用のレジームMA期間 |

## スクリプトの処理内容

主スクリプトは以下を行う。

- タブ区切りOHLCVを読み込み、時刻順に並べる。
- タイムスタンプまたはOHLCに欠損がある行を除外する。
- 重複タイムスタンプは最後の行を残す。
- OHLC不整合とマーケットギャップを確認する。
- `--start <= timestamp < --end` の範囲を使う。
- 指定した短期・長期MAでシグナルを作る。
- 前足終値でシグナルを確定し、次足始値で約定する。
- 目標方向が変わったときにドテンする。
- 完了した各トレードから往復コストを控除する。
- 60分足と240分足を同じ固定MA 20/80ルールで評価する。
- フル期間 `2023-2025`、開発期間 `2023-2024`、OOS期間 `2025` に分けて集計する。
- 堅牢性診断と記事用図表を生成する。

方向アブレーションでは、同じ MA 20/80 ルールを固定し、short の扱いだけを変更する。

| バリアント | 内容 |
|---|---|
| `baseline_long_short` | 元の long / short ドテン |
| `long_only` | short シグナルでは新規shortせず、longを手仕舞ってflatにする |
| `short_filter_ma80_slope` | MA80が20本前より下向きのときだけshortを許可する |
| `short_filter_ma200_down` | 終値が下向きMA200を下回るときだけshortを許可する |

## 主要出力

`outputs/trend_following_ma_cross/` の主な出力は以下である。

| ファイル | 内容 |
|---|---|
| `article_result_summary.md` | 記事用の主要結果サマリー |
| `data_audit.csv` | 入力データ品質と対象行数の監査 |
| `summary_metrics.csv` | 時間足・コスト別のフル期間指標 |
| `fixed_oos_summary.csv` | 時間足・コスト別の開発/OOS分割指標 |
| `direction_breakdown.csv` | long / short の損益寄与 |
| `buy_hold_comparison.csv` | MA long/short、long only、always long の比較 |
| `cost_sensitivity.csv` | コスト感応度 |
| `top_trade_exclusion.csv` | 上位勝ちトレード除外後の成績 |
| `top_trade_contribution.csv` | 大勝ちトレードへの集中度 |
| `random_direction_comparison.csv` | ランダム方向シミュレーション内での実戦略位置 |
| `parameter_heatmap.csv` | パラメータ面の集計 |
| `parameter_heatmap_dev_oos_comparison.csv` | 開発期間とOOS期間のパラメータ比較 |
| `entry_delay_sensitivity.csv` | 追加entry delayの感応度 |
| `monthly_pnl.csv` | 月次損益 |
| `run_risk_summary.csv` | 連敗と水面下期間の診断 |
| `trade_log_60m.csv` | 60分足のトレードログ |
| `trade_log_240m.csv` | 240分足のトレードログ |

`outputs/trend_following_direction_ablation/` の主な出力は以下である。

| ファイル | 内容 |
|---|---|
| `direction_ablation_result_summary.md` | 方向アブレーションのサマリー |
| `direction_ablation_summary.csv` | バリアント別フル期間指標 |
| `direction_ablation_breakdown.csv` | バリアント別・方向別の寄与 |
| `direction_ablation_trade_log.csv` | アブレーションのトレードログ |

記事用図表は以下である。

| ファイル | 内容 |
|---|---|
| `outputs/article_figures/figure_index.md` | 番号付き図表インデックス |
| `outputs/article_figures/figure_index.csv` | 図表メタデータCSV |
| `outputs/article_figures/figure01_*.png` から `figure19_*.png` | 記事用PNGファイル |

## 記事用図表

`outputs/article_figures/` には19個の番号付き図表がある。

| 図 | 内容 |
|---|---|
| 1 | ベースライン累積損益 |
| 2 | ベースラインDrawdown |
| 3 | トレード損益分布 |
| 4 | コスト感応度 |
| 5 | 固定パラメータの開発期間/OOS比較 |
| 6 | MAクロス、long only、always long の比較 |
| 7 | long / short の損益寄与 |
| 8 | 上位勝ちトレード除外 |
| 9 | ランダム方向比較 |
| 10-12 | フル期間、開発期間、OOS期間のパラメータPFヒートマップ |
| 13 | 開発期間PFとOOS PFの比較 |
| 14 | entry delay 感応度 |
| 15 | 月次損益 |
| 16-19 | 方向アブレーション診断 |

## 主要結果

MA 20/80、往復コスト1.0 pips のベースラインは以下である。

| 時間足 | 取引数 | 総損益 | 勝率 | Profit Factor | MaxDD |
|---|---:|---:|---:|---:|---:|
| 60分足 | 292 | `-140.1 pips` | `35.27%` | `0.990` | `2067.1 pips` |
| 240分足 | 70 | `+1746.6 pips` | `41.43%` | `1.304` | `2120.2 pips` |

往復コスト1.0 pips の固定開発/OOS分割は以下である。

| 時間足 | 2023-2024 開発損益 | 開発PF | 2025 OOS損益 | OOS PF |
|---|---:|---:|---:|---:|
| 60分足 | `-235.9 pips` | `0.976` | `+75.5 pips` | `1.021` |
| 240分足 | `+2569.3 pips` | `1.787` | `-808.0 pips` | `0.686` |

方向別寄与は以下である。

| 時間足 | 期間 | long損益 | short損益 |
|---|---|---:|---:|
| 60分足 | 2023-2025 フル期間 | `+1215.3 pips` | `-1355.4 pips` |
| 240分足 | 2023-2025 フル期間 | `+2164.6 pips` | `-418.0 pips` |
| 60分足 | 2025 OOS | `+11.8 pips` | `+63.7 pips` |
| 240分足 | 2025 OOS | `-424.5 pips` | `-383.5 pips` |

堅牢性診断の主な読み方は以下である。

| 確認項目 | 60分足 | 240分足 | 読み方 |
|---|---:|---:|---|
| コスト2.0 pips時の総損益 | `-432.1` | `+1676.6` | フル期間では240分足の方がコスト耐性が高い |
| 上位5%勝ちトレード除外後 | `-3001.4` | `-352.9` | 右テール依存が大きい |
| ランダム方向比較での位置 | `50.3` | `77.5` | 60分足はほぼランダム、240分足は上位寄りだが決定的ではない |
| 最大水面下期間 | `866.6日` | `344.3日` | どちらも長い待機期間を許容する必要がある |

## 方向アブレーション結果

フル期間の方向アブレーションは以下である。

| バリアント | 60分足損益 | 60分足PF | 240分足損益 | 240分足PF |
|---|---:|---:|---:|---:|
| `baseline_long_short` | `-140.1` | `0.990` | `+1746.6` | `1.304` |
| `long_only` | `+1215.3` | `1.181` | `+2164.6` | `2.127` |
| `short_filter_ma80_slope` | `-657.7` | `0.947` | `+2536.6` | `1.615` |
| `short_filter_ma200_down` | `+863.0` | `1.079` | `+1915.4` | `1.465` |

固定2025 OOSの方向アブレーションは以下である。

| バリアント | 60分足OOS損益 | 60分足OOS PF | 240分足OOS損益 | 240分足OOS PF |
|---|---:|---:|---:|---:|
| `baseline_long_short` | `+75.5` | `1.021` | `-808.0` | `0.686` |
| `long_only` | `+11.8` | `1.006` | `-424.5` | `0.508` |
| `short_filter_ma80_slope` | `-345.1` | `0.906` | `-847.8` | `0.595` |
| `short_filter_ma200_down` | `-512.2` | `0.855` | `-245.9` | `0.827` |

これらのアブレーションは、short exposure がベースライン結果をどの程度悪化させたかを診断するためのものである。最終採用戦略ではない。2025 OOS はすでに見ているため、ここを改善する追加フィルターは、次の未使用Holdoutで確認するまでは post-hoc な探索として扱う必要がある。

## 解釈上の注意点

このラボは、USDJPY の恒久的なトレンドフォローエッジを証明しない。

- フル期間では240分足が60分足より良く見えたが、固定2025 OOSでは崩れた。
- 240分足のフル期間プラスは、大きな勝ちトレードへの依存が大きい。
- 60分足シグナルはランダム方向比較で中央値付近だった。
- この期間ではlong側がshort側より強かったが、対象期間のUSDJPYレジームの影響である可能性がある。
- 方向フィルターやlong onlyは診断用アブレーションであり、検証済みの本番ルールではない。
- 主実験ではWFOもOOS再最適化も行っていない。
- スリッページ、約定拒否、流動性低下、STOP、急変時の約定飛びは簡略化している。

記事で安全に言える結論は、以下の範囲に留めるのがよい。

```text
トレンドフォローは、高勝率ではなく、右テール依存の損益構造を持ち得る。
今回のUSDJPY 240分足では開発期間にその構造が見えた。
しかし固定2025 OOSで崩れたため、この結果は恒久的エッジの証明ではなく、
トレンドフォロー構造と検証上の限界を示す診断結果である。
```

## 記事との対応

公開記事:

- 日本語: [トレンドフォローにエッジはあるのか――「遅れて入る」戦略がなぜ生き残るのか](https://qiita.com/tikeda123/items/e599112d88c912a86125)
- English: [英語版記事](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2)

記事草稿と補助メモは以下である。

| ファイル | 役割 |
|---|---|
| `trend_following_edge_article_outline_improved.md` | 改善版の記事アウトライン |
| `trend_following_experiment_analysis_and_discussion.md` | 分析・考察メモ |
| `trend_following_experiment_outline_no_wfo.md` | WFOなし実験アウトライン |
| `trend_following_experiment_implementation_plan.md` | 実装計画 |

記事の中心メッセージは、次の境界に合わせる。

```text
トレンドフォローは高勝率の予測手法ではない。
価格変化の継続性と右テールを取りに行く構造である。
今回のUSDJPY実験では、240分足の開発期間にその構造が見えたが、
固定2025 OOSで崩れたため、結果は恒久的エッジの証明ではなく診断である。
```
