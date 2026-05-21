# article_lab: クオンツ記事実験ラボ索引

English: [README.md](README.md)

このリポジトリは、クオンツ・FX分析記事に対応する実験コード、入力データ、図表、集計結果を `lab_xxx` 単位で管理するための作業場所である。

ルートの `README.md` は英語圏向けの入口、`README.ja.md` は日本語版の索引である。各実験の詳細な目的、入力データ、再現コマンド、主要出力、解釈上の注意点は、それぞれの `lab_xxx/README.md` と `lab_xxx/README.ja.md` を正本として扱う。

## ドキュメント言語方針

GitHubと英語圏ユーザー向けには英語版をデフォルト入口にする。日本語記事や日本語での作業文脈は `README.ja.md` に残す。

| ファイル | 役割 |
|---|---|
| `README.md` | 英語版の入口 |
| `README.ja.md` | 日本語版の入口 |
| `lab_xxx/README.md` | 各ラボの英語版README |
| `lab_xxx/README.ja.md` | 各ラボの日本語版README |

READMEを更新する場合は、英語版と日本語版の実験目的、正本出力、再現コマンド、現在結果、解釈上の注意点がずれないようにする。

## ラボ拡張方針

この `article_lab` は、記事ごと・実験ごとに `lab_xxx` 形式のサブディレクトリとして拡張していく前提で管理する。

各 `lab_xxx` には、原則として以下を置く。

| 種類 | 内容 |
|---|---|
| `README.md` / `README.ja.md` | 実験ラボ単位の正本説明 |
| 入力CSV | 記事検証に使う元データ |
| Pythonスクリプト | 集計・図表生成・記事用サマリ生成コード |
| 出力ディレクトリ | コードから再生成できるCSV、Markdown、PNG |
| 記事アウトライン | 記事構成案や本文草稿がある場合に配置 |

ルート README には詳細な実験手順を重複させず、どのラボを見ればよいかを示す。

## ラボ一覧

| ラボ | テーマ | 主な入力 | English | 日本語 | 主な出力 |
|---|---|---|---|---|---|
| `lab_1` | FX 240分足モーメント分析とエッジ探索 | USDJPY / EURUSD / AUDJPY 240分足 | [README](lab_1/README.md) | [日本語](lab_1/README.ja.md) | `lab_1/moment_analysis_outputs_2022plus/` |
| `lab_2` | AUDJPY 買われすぎ・売られすぎの定量化 | AUDJPY 60分足 | [README](lab_2/README.md) | [日本語](lab_2/README.ja.md) | `lab_2/article_outputs/` |
| `lab_3` | FX Kelly基準による注文リスク管理 | 入力CSVなし。単体HTMLツール | [README](lab_3/README.md) | [日本語](lab_3/README.ja.md) | `lab_3/kelly_fx_position_size_tool.html` |
| `lab_4` | USDJPY 60分足 バックテスト過学習・簡易PBO検証 | USDJPY 60分足 | [README](lab_4/README.md) | [日本語](lab_4/README.ja.md) | `lab_4/results_summary.json`, `lab_4/figures/` |

## lab_1 概要

`lab_1` は、Qiita記事「[クオンツ入門 予測を捨て、分布を読め - クオンツトレードのためのモーメント分析とエッジ探索フレームワーク](https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf)」に対応する実験ラボである。

価格方向を直接予測する前に、FXリターン分布の形、歪度、尖度、急変後の平均回帰、ボラティリティ階層別の未来リターンを確認し、どの通貨ペア・どの局面に深掘り価値があるかを探す。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_1/README.ja.md](lab_1/README.ja.md) |
| 英語版 | [lab_1/README.md](lab_1/README.md) |
| 実験コード | `lab_1/run_moment_analysis_edge_experiments.py` |
| 入力データ | `USDJPY240.csv`, `EURUSD240.csv`, `AUDJPY240.csv` |
| 正本出力 | `lab_1/moment_analysis_outputs_2022plus/` |
| 位置づけ | エッジ候補探索。完成した売買戦略ではない |

## lab_2 概要

`lab_2` は、Qiita記事「[クオンツトレーダーは『買われすぎ・売られすぎ』をどう判断するのか](https://qiita.com/tikeda123/items/8dfcc1c09e34d5304d49)」に対応する実験ラボである。

「下がりすぎ」「上がりすぎ」という主観的な判断を、24時間VWAP乖離Zスコアと直近1時間リターンの過去500本内パーセンタイルに変換し、その後の反発リターンを検証する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_2/README.ja.md](lab_2/README.ja.md) |
| 英語版 | [lab_2/README.md](lab_2/README.md) |
| 実験コード | `lab_2/audjpy_overbought_oversold_article_experiment.py` |
| 記事アウトライン | `lab_2/quant_overbought_oversold_article_outline.md` |
| 入力データ | `AUDJPY60.csv` |
| 正本出力 | `lab_2/article_outputs/` |
| 位置づけ | 買われすぎ・売られすぎの数値化と反発候補領域の観察 |

## lab_3 概要

`lab_3` は、Qiita記事「[FXで破産リスクを下げるための実践数学：Kelly基準を「損切り幅」と「注文数量」に落とし込む](https://qiita.com/tikeda123/items/d5e16444da576c545c43)」に対応するKelly基準ベースの注文リスク管理ツールである。

Kelly基準を「勝てる注文数量を出す公式」としてではなく、1回のトレードで許容できる最大損失額を求め、その金額を注文数量、損切り幅、1pip価値、証拠金使用率へ変換する教育用ツールとして扱う。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_3/README.ja.md](lab_3/README.ja.md) |
| 英語版 | [lab_3/README.md](lab_3/README.md) |
| HTMLツール | `lab_3/kelly_fx_position_size_tool.html` |
| 記事アウトライン | `lab_3/fx_kelly_article_outline_with_tools.md` |
| 入力データ | なし |
| 正本出力 | 単体HTMLツール |
| 位置づけ | Kelly基準を許容損失額、注文数量、損切り幅、証拠金使用率に変換する教育用チェックツール |

## lab_4 概要

`lab_4` は、Qiita記事「[AIでエッジ探しが簡単になった時代に、そのバックテストは本物か？PBOで過学習を確認する](https://qiita.com/tikeda123/items/ab7070663e8e002e785f)」に対応する実験ラボである。

AI時代のクオンツ探索で問題になりやすいバックテスト過学習を、USDJPY 60分足の実データで確認する。

移動平均クロス戦略144候補を題材に、8ブロックのCSCV的なIS/OOS分割と簡易PBOで、ISで選ばれた戦略がOOSでも残るかを確認する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_4/README.ja.md](lab_4/README.ja.md) |
| 英語版 | [lab_4/README.md](lab_4/README.md) |
| 記事 | [日本語](https://qiita.com/tikeda123/items/ab7070663e8e002e785f) / [English](https://qiita.com/tikeda123/items/fd589372f78ffa4c48fb) |
| 実験コード | `lab_4/run_backtest_overfitting_experiment.py` |
| 記事アウトライン | `lab_4/ai_edge_backtest_overfitting_outline.md`, `lab_4/backtest_overfitting_experiment_outline.md` |
| 入力データ | 外部 `USDJPY60(29).csv` |
| 正本出力 | `lab_4/results_summary.json`, `lab_4/experiment_report.md`, `lab_4/figures/` |
| 位置づけ | 簡易CSCV/PBOによる過学習リスク確認。完成した売買戦略ではない |

## 使い方

英語圏の読者は、各ラボの `README.md` を読む。

```bash
sed -n '1,220p' lab_1/README.md
sed -n '1,220p' lab_2/README.md
sed -n '1,220p' lab_3/README.md
sed -n '1,220p' lab_4/README.md
```

日本語記事や日本語での作業では、各ラボの `README.ja.md` を読む。

```bash
sed -n '1,220p' lab_1/README.ja.md
sed -n '1,220p' lab_2/README.ja.md
sed -n '1,220p' lab_3/README.ja.md
sed -n '1,220p' lab_4/README.ja.md
```

実験を再生成する場合も、各ラボREADMEに記載されたコマンドを正本とする。

```bash
python lab_1/run_moment_analysis_edge_experiments.py
python lab_2/audjpy_overbought_oversold_article_experiment.py
```

`lab_3` はPython実験ではなく単体HTMLツールである。ローカルHTTPサーバーで確認する場合は、リポジトリルートで次を実行する。

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

その後、ブラウザで次を開く。

```text
http://127.0.0.1:8765/lab_3/kelly_fx_position_size_tool.html
```

`lab_4` は入力CSVを明示して実行する。

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_check
```

既存の正本出力を壊さず試す場合は、各スクリプトの `--output-dir` や `--outdir` を使って一時ディレクトリへ出力する。

## 管理方針

- `README.md` は英語版の入口として扱う。
- `README.ja.md` は日本語版の入口として扱う。
- ルート README は索引とラボ一覧に限定する。
- 実験の詳細、再現コマンド、主要結果、注意点は各 `lab_xxx/README.md` と `lab_xxx/README.ja.md` に書く。
- コードから再生成できる成果物は、各ラボ内の専用出力ディレクトリにまとめる。
- 新しい記事・実験を追加する場合は、`lab_5`、`lab_6` のように新しいディレクトリを作る。
- 記事本文に使う数値は、各ラボの正本出力CSV、JSON、Markdownから引用する。
