# lab_4: USDJPY 60分足 バックテスト過学習・簡易PBO検証

English: [README.md](README.md)

このディレクトリは、AI時代のクオンツトレードで問題になりやすいバックテスト過学習を、USDJPY 60分足の実データで確認するための実験ラボである。

記事の目的は、AIやPythonで大量の売買ルールを簡単に試せるようになった環境では、最も良いバックテスト成績だけを見るのではなく、インサンプルで選ばれた戦略がアウトオブサンプルでも残るかを検証する必要がある、という点を説明することである。

この実験は完成した売買戦略の提案ではない。移動平均クロス戦略144候補を題材に、CSCV的な分割と簡易PBOで「選択プロセスそのものがどれくらい過去データに寄っているか」を観察する教育用実験である。

## 実験の位置づけ

この実験では、USDJPYの60分足データを使い、以下の順に分析している。

1. 2020年から2025年末までのUSDJPY 60分足OHLCを切り出す
2. 短期MA、長期MA、ATR損切り、ATR利確の組み合わせで144戦略候補を作る
3. 終値確定後にシグナルを判定し、次足始値で約定する前提で損益系列を作る
4. 往復1.0 pipsの取引コストを控除する
5. 各候補のフルサンプルSharpe、累積リターン、MaxDD、取引数を集計する
6. 損益行列を8ブロックに分け、4ブロックIS / 4ブロックOOSの全70通りを作る
7. 各組み合わせでIS Sharpe最良戦略を選び、その戦略のOOS順位とOOS損益を確認する
8. IS最良戦略がOOS中央値以下に落ちた割合を簡易PBOとして集計する
9. 記事用のCSV、Markdown、PNG図表、Excelサマリー、提出用zipを生成する

記事本文に対応する正本成果物は、`candidate_summary.csv`、`pbo_results.csv`、`results_summary.json`、`experiment_report.md`、`figures/`、`experiment_summary.xlsx` である。再配布や提出用には `backtest_overfitting_submission.zip` を使う。

## 入力データ

再現実行では、ヘッダーなし、タブ区切りのUSDJPY 60分足OHLCVを入力に使う。

| ファイル | 通貨ペア | 形式 |
|---|---|---|
| `USDJPY60(29).csv` | USDJPY | `timestamp, open, high, low, close, volume` |

現在の正本出力で記録されている入力データ品質は以下である。

| 項目 | 内容 |
|---|---:|
| 入力行数 | 100,000 |
| 入力データ開始 | `2010-03-18 18:00` |
| 入力データ終了 | `2026-04-02 12:00` |
| 実験対象行数 | 37,430 |
| 実験対象開始 | `2020-01-01 22:00` |
| 実験対象終了 | `2025-12-31 21:00` |
| 重複タイムスタンプ | 0 |
| 非単調ステップ | 0 |
| OHLC不整合行 | 0 |
| 1時間超ギャップ | 318 |

週末・祝日によるFX市場の休場はギャップとして数えている。補間は行っていない。

このリポジトリの `lab_4` 直下には、正本実行に使った生CSV本体は含めていない。再現する場合は同形式の `USDJPY60(29).csv` を別途用意し、`--input` で指定する。

## 実験環境

主スクリプトは単体Pythonで実行できる。必要な外部パッケージは `numpy` と `matplotlib` である。

| 項目 | 内容 |
|---|---|
| Python | Python 3 |
| numpy | 損益行列、Sharpe、CSCV集計に使用 |
| matplotlib | 記事用PNG図表の生成に使用 |
| artifact_tool | `experiment_summary.xlsx` とプレビューPNGの生成に使用 |

通常の再現では `run_backtest_overfitting_experiment.py` だけでCSV、JSON、Markdown、PNGを再生成できる。Excelサマリーを再生成するには、この環境で使った `artifact_tool` が必要である。

## 再現コマンド

リポジトリルートから正本相当の出力を再生成する場合は、入力CSVを指定して次を実行する。

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir lab_4/backtest_overfitting_submission
```

`lab_4` ディレクトリに移動して実行する場合は次でよい。

```bash
cd lab_4
python run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir ./backtest_overfitting_submission
```

既存の正本成果物を壊さずに試す場合は、必ず別の `--outdir` を指定する。

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_check
```

図表生成を省いてCSVとレポートだけ確認したい場合は、`--no-plots` を指定する。

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_no_plots \
  --no-plots
```

実行が成功すると、標準出力に出力先、行数、戦略候補数、PBO、OOS損失確率、フルサンプル最良戦略がJSONで表示される。

## Python実験ツールの使い方

実験ツール本体は `run_backtest_overfitting_experiment.py` である。入力CSVを読み込み、戦略候補の損益系列、CSCV/PBO集計、記事用図表、Markdownレポートを一括生成する。

まず利用可能な引数を確認する。

```bash
python lab_4/run_backtest_overfitting_experiment.py --help
```

主な引数は以下である。

| 引数 | 既定値 | 用途 |
|---|---|---|
| `--input` | `/mnt/data/USDJPY60(29).csv` | 入力するUSDJPY 60分足CSV |
| `--outdir` | `/mnt/data/backtest_overfitting_submission` | 生成されるCSV、JSON、Markdown、図表の出力先 |
| `--start` | `2020-01-01 00:00` | 実験開始日時。指定時刻以上の最初の足から使う |
| `--end-exclusive` | `2026-01-01 00:00` | 実験終了日時。この時刻未満の足を使う |
| `--no-plots` | なし | PNG図表生成を省略する |

出力を確認するときは、まず実験レポートとJSONサマリーを見る。

```bash
sed -n '1,140p' lab_4/experiment_report.md
python -m json.tool lab_4/results_summary.json
```

候補戦略とCSCVの詳細を確認する場合は、次を使う。

```bash
column -s, -t < lab_4/candidate_summary.csv | sed -n '1,15p'
column -s, -t < lab_4/pbo_results.csv | sed -n '1,15p'
```

Pythonから主要KPIだけを確認する場合は、次のように読む。

```bash
python - <<'PY'
import json

summary = json.load(open("lab_4/results_summary.json", encoding="utf-8"))
print("PBO:", summary["pbo_median_or_worse_rate"])
print("OOS loss probability:", summary["oos_loss_probability"])
print("Best:", summary["full_sample_best_strategy"])
PY
```

## スクリプトの処理内容

主スクリプトは `run_backtest_overfitting_experiment.py` である。

- タブ区切りOHLCVを読み込み、タイムスタンプ、OHLC、ギャップ、重複、OHLC整合性を確認する。
- `--start` 以上、`--end-exclusive` 未満の期間を実験対象にする。
- 14期間ATRを計算し、SL/TP判定に使う。エントリー時点では直前足までのATRだけを参照する。
- 短期MA `5, 10, 20, 30` と長期MA `50, 100, 150, 200` のクロスでLong/Shortシグナルを作る。
- SLは `none, ATR 1.0, ATR 1.5`、TPは `none, ATR 1.5, ATR 2.0` を組み合わせる。
- シグナル判定は前足終値、約定は次足始値で行う。
- 往復1.0 pipsを片道コストとしてエントリー・決済時に控除する。
- 同時保有は1ポジションのみとし、反対シグナルでは既存ポジションを閉じてから反対方向に入る。
- 同一足内でSLとTPの両方に到達した場合は、保守的にSLを優先する。
- 各戦略候補のバー別リターンをT×N損益行列として保存する。
- 8ブロックから4ブロックISを選ぶ70通りで、IS Sharpe最良戦略のOOS成績を評価する。

簡易PBOは次の定義で扱う。

```text
簡易PBO = ISでSharpe最良だった戦略が、OOS順位で中央値以下に落ちた割合
```

この実験では144候補なので、OOS順位が73位から144位になった場合を「中央値以下」として数える。

## 主要出力

`lab_4` 直下の主要出力は以下である。

| ファイル | 内容 |
|---|---|
| `candidate_summary.csv` | 144戦略候補のフルサンプル評価 |
| `pbo_results.csv` | 70通りのIS/OOS検証結果 |
| `pnl_matrix.csv.gz` | T×Nの損益行列。gzip圧縮CSV |
| `best_strategy_timeseries.csv` | フルサンプルSharpe最良戦略の損益時系列 |
| `results_summary.json` | 実験条件、データ品質、主要KPI |
| `experiment_report.md` | 提出・記事確認用の短いMarkdownレポート |
| `experiment_summary.xlsx` | Summary、候補一覧、PBO結果、データ品質をまとめたExcel |
| `experiment_summary_preview.png` | Excelサマリーのプレビュー画像 |
| `backtest_overfitting_submission.zip` | 提出用成果物一式 |
| `run_backtest_overfitting_experiment.py` | 再現用コード |
| `create_summary_workbook.py` | Excelサマリー生成用コード |
| `backtest_overfitting_experiment_outline.md` | 実データPBO検証の記事用実験骨子 |
| `ai_edge_backtest_overfitting_outline.md` | 論文紹介・AI時代の過学習リスク記事骨子 |

`figures/` には記事用の図表PNGがある。

| 図 | 内容 |
|---|---|
| `fig1_sharpe_distribution.png` | 144候補のフルサンプルSharpe分布 |
| `fig2_is_vs_oos_sharpe.png` | ISで選ばれた戦略のIS SharpeとOOS Sharpe |
| `fig3_oos_rank_distribution.png` | IS最良戦略のOOS順位分布 |
| `fig4_simplified_pbo.png` | 簡易PBOの比率 |
| `fig5_oos_loss_probability.png` | OOS損失確率 |
| `fig6_best_strategy_equity_curve.png` | フルサンプルSharpe最良戦略の累積損益曲線 |

## 主要結果

現在の正本出力では、戦略候補数は144、CSCV組み合わせ数は70である。

| 指標 | 結果 |
|---|---:|
| 簡易PBO | `5.71%` |
| OOS損失確率 | `35.71%` |
| 選択戦略の平均IS Sharpe | `0.7474` |
| 選択戦略の平均OOS Sharpe | `0.1187` |
| 選択戦略の平均OOS順位 | `32.43 / 144` |
| 選択戦略のOOS順位中央値 | `30.0 / 144` |

フルサンプルSharpe上位5戦略は以下である。

| rank | strategy_id | Sharpe | CumReturn | MaxDD | Trades | WinRate |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `ma_s20_l50_sl_none_tp_none` | `0.5717` | `35.45%` | `-10.13%` | 786 | `38.17%` |
| 2 | `ma_s20_l50_sl_atr1_5_tp_none` | `0.5396` | `31.93%` | `-10.25%` | 1659 | `30.08%` |
| 3 | `ma_s10_l50_sl_atr1_5_tp_none` | `0.5088` | `29.41%` | `-11.27%` | 1715 | `29.15%` |
| 4 | `ma_s10_l50_sl_none_tp_none` | `0.4990` | `29.87%` | `-17.23%` | 938 | `34.97%` |
| 5 | `ma_s10_l50_sl_atr1_0_tp_none` | `0.4543` | `25.32%` | `-12.27%` | 2271 | `24.39%` |

簡易PBOは低く、少なくともこの144候補・この期間・この分割方法では、ISで選ばれた戦略がOOS順位の中央値以下に落ちるケースは少なかった。一方で、選択戦略の平均OOS Sharpeは平均IS Sharpeより大きく低下しており、OOS累積リターンがマイナスになる組み合わせも35.71%ある。

## 解釈上の注意点

この結果は、移動平均クロス戦略が将来も収益を出すことを保証しない。

- 簡易PBOは、候補群と分割方法に依存する。
- PBOが低くても、OOS Sharpeの劣化やOOS損失確率は別に確認する必要がある。
- 今回の検証はUSDJPY 60分足、2020年から2025年末までの範囲に限定している。
- 2026年以降の未使用Holdoutや別データソースでの確認は行っていない。
- スリッページ、約定拒否、流動性低下、急変時の約定飛びは簡略化している。
- MAクロス144候補以外の探索空間では、PBOやOOS順位分布が変わる可能性がある。
- PBOを下げること自体を最適化目標にすると、それも過学習になりうる。

記事では、この実験を「最良バックテストを選ぶための手法」ではなく、「良すぎるバックテストを疑い、IS/OOS劣化と探索回数を可視化するための入口」として扱う。

## 記事との対応

記事骨子は `ai_edge_backtest_overfitting_outline.md` と `backtest_overfitting_experiment_outline.md` にある。

記事で強調するべき点は、次の整理である。

```text
AI時代には、エッジ候補を大量に作ることが簡単になる。
しかし、候補を大量に試すほど、過去データに偶然合った戦略も見つかりやすくなる。

重要なのは、最も良いバックテストをそのまま信じることではない。
何通り試したか、ISで選ばれた戦略がOOSで残るか、
OOS順位・OOS損失確率・PBOを確認することである。
```

本文で数値を引用する場合は、まず `results_summary.json` と `experiment_report.md` を確認する。候補別の詳細は `candidate_summary.csv`、CSCVの各組み合わせは `pbo_results.csv`、図表は `figures/` を参照する。

このラボの結論は、「PBOが低いからこの戦略を採用できる」ではない。正確には、「バックテスト過学習を議論するには、最高成績の戦略だけでなく、候補群全体、IS/OOSの分割、選択後のOOS順位、損失確率をセットで見る必要がある」ということである。
