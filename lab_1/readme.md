# lab_1: FX 240分足モーメント分析実験

このディレクトリは、Qiita記事「[クオンツ入門 予測を捨て、分布を読め - クオンツトレードのためのモーメント分析とエッジ探索フレームワーク](https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf)」の根拠データ、集計スクリプト、図表出力をまとめた実験ラボである。

記事の目的は、価格の方向を直接予測する前に、FXリターン分布の形を確認し、どの通貨ペア・どの局面に条件付きリターンの深掘り価値があるかを探すことにある。この実験は売買戦略の最終バックテストではなく、エッジ候補を見つけるための探索フェーズである。

## 実験の位置づけ

この実験では、USDJPY、EURUSD、AUDJPY の240分足データを使い、以下の順に分析している。

1. 終値ベース対数リターンのモーメント比較
2. 観測された最大・最小リターンの確認
3. リターン分布の可視化
4. 上昇足後・下落足後の未来リターン分析
5. 上位・下位テール急変後の平均回帰分析
6. 過去20本ボラティリティの5分位別分析
7. AUDJPY急落後ロング候補の年別安定性と次足始値ベースの簡易リスク確認

記事本文に対応する正本は `moment_analysis_outputs_2022plus/` である。`moment_analysis_outputs/` は旧骨子向けの広い期間集計であり、記事URLの2022年以降版を説明するときは基本的に `moment_analysis_outputs_2022plus/` を参照する。

## 入力データ

入力CSVはこのディレクトリ直下に置かれている。いずれもヘッダーなし、タブ区切りの240分足OHLCVである。

| ファイル | 通貨ペア | 形式 |
|---|---|---|
| `USDJPY240.csv` | USDJPY | `timestamp, open, high, low, close, volume` |
| `EURUSD240.csv` | EURUSD | `timestamp, open, high, low, close, volume` |
| `AUDJPY240.csv` | AUDJPY | `timestamp, open, high, low, close, volume` |

2022年以降版では、3通貨ペアの共通期間だけを使う。

| 項目 | 内容 |
|---|---|
| 要求開始日 | `2022-01-01` |
| 実際の分析開始 | `2022-01-02 20:00:00` |
| 実際の分析終了 | `2026-04-02 12:00:00` |
| 足種 | 240分足 |
| 分析対象 | USDJPY / EURUSD / AUDJPY |
| 未来リターン | 1本後、3本後、6本後、12本後 |

実際の分析終了が `2026-04-02 12:00:00` になるのは、USDJPYのデータ終端が他2ペアより早く、3通貨ペアの共通期間で揃えているためである。

## 実験環境

このラボは単体Pythonスクリプトで実行できる。現在のローカル確認環境は以下の通り。

| 項目 | バージョン |
|---|---|
| Python | `3.11.5` |
| pandas | `2.3.2` |
| numpy | `2.3.3` |
| matplotlib | `3.10.6` |
| tabulate | `0.9.0` |

`tabulate` は `DataFrame.to_markdown()` によるMarkdownサマリ出力で使う。図表生成はGUIを使わない `matplotlib` の `Agg` バックエンドで行う。

## 再現コマンド

記事対応の2022年以降版を再生成する場合は、`lab_4` ディレクトリで次を実行する。

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir moment_analysis_outputs_2022plus \
  --start-date 2022-01-01 \
  --dpi 180
```

スクリプトのデフォルトも2022年以降版の出力に合わせてあるため、通常は次でも同じ出力先に再生成される。

```bash
python run_moment_analysis_edge_experiments.py
```

旧骨子のように開始日フィルタを外して広い共通期間で集計したい場合は、出力先を分けて実行する。

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir moment_analysis_outputs \
  --start-date ""
```

## Python実験ツールの使い方

実験ツール本体は `run_moment_analysis_edge_experiments.py` である。入力CSVを読み込み、集計CSV、記事用Markdown、図表PNGを一括生成する。

まず利用可能な引数を確認する。

```bash
python run_moment_analysis_edge_experiments.py --help
```

主な引数は以下である。

| 引数 | 既定値 | 用途 |
|---|---|---|
| `--data-dir` | このスクリプトのあるディレクトリ | `USDJPY240.csv`、`EURUSD240.csv`、`AUDJPY240.csv` を置いた入力ディレクトリ |
| `--output-dir` | `moment_analysis_outputs_2022plus` | 生成されるCSV、Markdown、図表の出力先 |
| `--start-date` | `2022-01-01` | 分析開始日時。空文字 `""` を指定すると開始日フィルタを外す |
| `--end-date` | なし | 分析終了日時。省略時は3通貨ペアの共通データ終端まで |
| `--dpi` | `180` | PNG図表の解像度 |

出力先には同名ファイルが再生成される。既存の正本を壊さず試す場合は、必ず別の `--output-dir` を指定する。

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir /tmp/lab4_moment_check \
  --start-date 2022-01-01 \
  --dpi 72
```

期間を変えて感度確認する場合は、`--start-date` と `--end-date` を指定する。どちらも包括的に扱われる。

```bash
python run_moment_analysis_edge_experiments.py \
  --data-dir . \
  --output-dir /tmp/lab4_moment_2024_2025 \
  --start-date 2024-01-01 \
  --end-date 2025-12-31
```

実行が成功すると、標準出力に実際の分析期間と出力先が表示される。

```text
Analysis period: 2022-01-02 20:00 to 2026-04-02 12:00
Wrote outputs to: moment_analysis_outputs_2022plus
```

出力を確認するときは、まずMarkdownサマリと候補要約CSVを見る。

```bash
sed -n '1,200p' moment_analysis_outputs_2022plus/article_experiment_summary.md
column -s, -t < moment_analysis_outputs_2022plus/edge_candidate_summary.csv
```

Pythonから集計結果を追加確認する場合は、次のようにCSVを読む。

```bash
python - <<'PY'
import pandas as pd

candidate = pd.read_csv("moment_analysis_outputs_2022plus/edge_candidate_summary.csv")
print(candidate[[
    "candidate",
    "horizon_hours",
    "count",
    "mr_return_mean_pct",
    "mr_win_rate_pct",
    "mr_return_t_stat",
]])
PY
```

実験条件のうち、次の値はコマンドライン引数ではなく、スクリプト内の定数で管理している。

| 定数 | 内容 |
|---|---|
| `PAIR_FILES` | 分析対象の通貨ペアと入力CSV |
| `HORIZONS` | 未来リターンを見る足数。現在は `1, 3, 6, 12` |
| `HORIZON_HOURS` | 240分足の本数を時間表記へ変換する対応表 |
| `SHOCK_LEVELS` | 急変条件の分位。現在は `5%`, `2.5%`, `1%` |
| `VOL_LABELS` | `vol20` の5分位ラベル |

たとえば「24時間後だけでなく72時間後も見たい」場合は、`HORIZONS` に `18` を追加し、`HORIZON_HOURS` に `18: 72` を追加してから、別の `--output-dir` へ再生成する。記事正本を更新する場合は、再生成後に `article_experiment_summary.md`、`edge_candidate_summary.csv`、該当図表、`experiment_conclusion_report.md` の整合性を確認する。

## スクリプトの処理内容

主スクリプトは `run_moment_analysis_edge_experiments.py` である。

- CSVを読み込み、タイムスタンプ欠損、OHLC欠損、重複タイムスタンプを整理する。
- 3通貨ペアの共通期間を切り出す。
- `log(close_t / close_{t-1}) * 100` で終値ベースの対数リターンを作る。
- 未来リターンを 1 / 3 / 6 / 12 本後で作る。
- 過去20本のリターン標準偏差から `Q1_low` から `Q5_high` までのボラティリティ階層を作る。
- 上位・下位 5%、2.5%、1% の急変条件で平均回帰リターンを集計する。
- AUDJPY下位5%急落後ロングについて、次足始値エントリー想定の簡易リターン、MAE、MFEも確認する。
- CSV表、Markdownサマリ、PNG図表を出力する。

平均回帰リターンは次の符号で定義している。

```text
上位テール急騰後ショート平均回帰 = -future_return
下位テール急落後ロング平均回帰 = +future_return
```

## 主要出力

記事対応の主要出力は `moment_analysis_outputs_2022plus/` にある。

| ファイル | 内容 |
|---|---|
| `article_experiment_summary.md` | 記事用の表形式サマリ |
| `experiment_conclusion_report.md` | 2022年以降版の結論レポート |
| `data_profile.csv` | 入力データ、共通期間、行数、欠損・重複確認 |
| `moment_summary.csv` | 平均、中央値、分散、標準偏差、歪度、超過尖度、最大・最小 |
| `direction_return_summary.csv` | 上昇足後・下落足後の未来リターン |
| `shock_mean_reversion_summary.csv` | 急変後平均回帰の全体集計 |
| `shock_mean_reversion_by_vol_summary.csv` | 急変後平均回帰のボラ階層別集計 |
| `vol_regime_summary.csv` | ボラ階層別の未来絶対リターン |
| `edge_candidate_summary.csv` | 記事で扱う代表候補の要約 |
| `annual_audjpy_q5_lower5_h6.csv` | AUDJPY Q5高ボラ・下位5%急落後ロングの年別確認 |
| `audjpy_path_risk_summary.csv` | 次足始値エントリー想定の簡易リターン、MAE、MFE |
| `audjpy_path_risk_events.csv` | AUDJPY急落後ロング候補のイベント明細 |

`moment_analysis_outputs_2022plus/figures/` には記事用の図表PNGがある。

| 図 | 内容 |
|---|---|
| `fig_01_moment_std_skew_kurtosis.png` | 標準偏差、歪度、超過尖度 |
| `fig_02_extreme_returns.png` | 観測された最大・最小4時間リターン |
| `fig_03_return_distribution_histograms.png` | リターン分布ヒストグラム |
| `fig_04_direction_future_returns.png` | 上昇足後・下落足後の未来リターン |
| `fig_05_shock_mean_reversion_by_horizon.png` | 急変後平均回帰のホライズン別比較 |
| `fig_06_vol_regime_future_abs_return_h6.png` | ボラ階層別の24時間後絶対リターン |
| `fig_07_audjpy_lower5_mr_by_vol.png` | AUDJPY下位5%急落後ロングのボラ階層別比較 |
| `fig_08_audjpy_q5_lower5_annual.png` | AUDJPY Q5高ボラ・下位5%急落後ロングの年別結果 |

## 主要結果

2022年以降データで最も明確に残った候補は、AUDJPYの急落後ロング平均回帰である。

| 候補 | 条件 | 期間 | 件数 | 平均回帰リターン | 勝率 | t値 |
|---|---|---:|---:|---:|---:|---:|
| USDJPY lower-tail long MR | 下位5%急落後ロング | 48時間 | 343 | `+0.0484%` | `54.52%` | `0.85` |
| EURUSD extreme-up short MR | 上位1%急騰後ショート | 12時間 | 69 | `-0.0059%` | `56.52%` | `-0.12` |
| AUDJPY lower-tail long MR | 下位5%急落後ロング | 48時間 | 343 | `+0.2024%` | `60.06%` | `3.18` |
| AUDJPY extreme-down long MR | 下位1%急落後ロング | 48時間 | 69 | `+0.3856%` | `62.32%` | `2.25` |
| AUDJPY Q5 lower-tail long MR | Q5高ボラ・下位5%急落後ロング | 24時間 | 168 | `+0.1446%` | `54.76%` | `1.66` |

記事の中心は「AUDJPYの高ボラ急落後24時間反発」単独ではなく、より広く「AUDJPYの急落後ロング平均回帰」に置くのが正確である。高ボラ条件は反発幅を大きくする補助条件になりうるが、年別安定性と逆行リスクを考えると、単独で強く主張しすぎない方がよい。

## リスク確認と限界

この実験はエッジ候補探索であり、完成した売買戦略ではない。

次足始値エントリーの簡易確認では、AUDJPY下位5%急落後ロングの24時間後平均リターンは `+0.1169%`、勝率は `57.48%` だった。Q5高ボラに限定した場合も、平均 `+0.1402%`、勝率 `54.76%` とプラスを維持している。

一方で、AUDJPY Q5高ボラ・下位5%急落後ロングの24時間保有では、平均MAEが `-0.9173%`、MAE 5%点が `-2.6542%` だった。平均回帰リターンがプラスでも、保有中に大きく逆行するケースがある。

実運用に進める前に、少なくとも以下の検証が必要である。

- 次足始値エントリー、指定時間後決済での正式バックテスト
- スプレッド、スリッページ、約定遅延の控除
- 固定損切り、ATR損切り、時間損切りの比較
- MAEに基づくロット調整
- 年別・四半期別・相場局面別の安定性確認
- WFOとHoldoutによる過剰最適化チェック

## 記事との対応

記事URLの本文は、このラボの2022年以降版出力をもとにしている。

- 使用データと分析条件: `data_profile.csv`
- モーメント比較: `moment_summary.csv` と `fig_01_moment_std_skew_kurtosis.png`
- 極端値確認: `moment_summary.csv` と `fig_02_extreme_returns.png`
- リターン分布: `fig_03_return_distribution_histograms.png`
- 方向別リターン: `direction_return_summary.csv` と `fig_04_direction_future_returns.png`
- 急変後平均回帰: `shock_mean_reversion_summary.csv` と `fig_05_shock_mean_reversion_by_horizon.png`
- ボラティリティ別分析: `vol_regime_summary.csv`、`shock_mean_reversion_by_vol_summary.csv`、`fig_06`、`fig_07`
- 年別安定性: `annual_audjpy_q5_lower5_h6.csv` と `fig_08_audjpy_q5_lower5_annual.png`
- 次足始値と最大逆行幅: `audjpy_path_risk_summary.csv`

結論文を確認する場合は、まず `moment_analysis_outputs_2022plus/experiment_conclusion_report.md` を読む。
