# article_lab: クオンツ記事実験ラボ索引

このリポジトリは、クオンツ・FX分析記事に対応する実験コード、入力データ、図表、集計結果を `lab_xxx` 単位で管理するための作業場所である。

ルートの `readme.md` はリポジトリ全体の索引であり、各実験の詳細な目的、入力データ、再現コマンド、主要出力、解釈上の注意点は、それぞれの `lab_xxx/readme.md` を正本として扱う。

## ラボ拡張方針

この `article_lab` は、記事ごと・実験ごとに `lab_xxx` 形式のサブディレクトリとして拡張していく前提で管理する。

各 `lab_xxx` には、原則として以下を置く。

| 種類 | 内容 |
|---|---|
| `readme.md` | 実験ラボ単位の正本説明 |
| 入力CSV | 記事検証に使う元データ |
| Pythonスクリプト | 集計・図表生成・記事用サマリ生成コード |
| 出力ディレクトリ | コードから再生成できるCSV、Markdown、PNG |
| 記事アウトライン | 記事構成案や本文草稿がある場合に配置 |

ルート README には詳細な実験手順を重複させず、どのラボを見ればよいかを示す。

## ラボ一覧

| ラボ | テーマ | 主な入力 | 正本README | 主な出力 |
|---|---|---|---|---|
| `lab_1` | FX 240分足モーメント分析とエッジ探索 | USDJPY / EURUSD / AUDJPY 240分足 | [lab_1/readme.md](lab_1/readme.md) | `lab_1/moment_analysis_outputs_2022plus/` |
| `lab_2` | AUDJPY 買われすぎ・売られすぎの定量化 | AUDJPY 60分足 | [lab_2/readme.md](lab_2/readme.md) | `lab_2/article_outputs/` |
| `lab_3` | FX Kelly基準による注文リスク管理 | 入力CSVなし。単体HTMLツール | [lab_3/readme.md](lab_3/readme.md) | `lab_3/kelly_fx_position_size_tool.html` |

## lab_1 概要

`lab_1` は、Qiita記事「[クオンツ入門 予測を捨て、分布を読め - クオンツトレードのためのモーメント分析とエッジ探索フレームワーク](https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf)」に対応する実験ラボである。

価格方向を直接予測する前に、FXリターン分布の形、歪度、尖度、急変後の平均回帰、ボラティリティ階層別の未来リターンを確認し、どの通貨ペア・どの局面に深掘り価値があるかを探す。

主な構成は以下である。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_1/readme.md](lab_1/readme.md) |
| 実験コード | `lab_1/run_moment_analysis_edge_experiments.py` |
| 入力データ | `USDJPY240.csv`, `EURUSD240.csv`, `AUDJPY240.csv` |
| 正本出力 | `lab_1/moment_analysis_outputs_2022plus/` |
| 位置づけ | エッジ候補探索。完成した売買戦略ではない |

## lab_2 概要

`lab_2` は、Qiita記事「[クオンツトレーダーは『買われすぎ・売られすぎ』をどう判断するのか](https://qiita.com/tikeda123/items/8dfcc1c09e34d5304d49)」に対応する実験ラボである。

「下がりすぎ」「上がりすぎ」という主観的な判断を、24時間VWAP乖離Zスコアと直近1時間リターンの過去500本内パーセンタイルに変換し、その後の反発リターンを検証する。

主な構成は以下である。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_2/readme.md](lab_2/readme.md) |
| 実験コード | `lab_2/audjpy_overbought_oversold_article_experiment.py` |
| 記事アウトライン | `lab_2/quant_overbought_oversold_article_outline.md` |
| 入力データ | `AUDJPY60.csv` |
| 正本出力 | `lab_2/article_outputs/` |
| 位置づけ | 買われすぎ・売られすぎの数値化と反発候補領域の観察 |

## lab_3 概要

`lab_3` は、Qiita記事「[FXで破産リスクを下げるための実践数学：Kelly基準を「損切り幅」と「注文数量」に落とし込む](https://qiita.com/tikeda123/items/d5e16444da576c545c43)」に対応するKelly基準ベースの注文リスク管理ツールである。

Kelly基準を「勝てる注文数量を出す公式」としてではなく、1回のトレードで許容できる最大損失額を求め、その金額を注文数量、損切り幅、1pip価値、証拠金使用率へ変換する教育用ツールとして扱う。

主な構成は以下である。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_3/readme.md](lab_3/readme.md) |
| HTMLツール | `lab_3/kelly_fx_position_size_tool.html` |
| 記事アウトライン | `lab_3/fx_kelly_article_outline_with_tools.md` |
| 入力データ | なし |
| 正本出力 | 単体HTMLツール |
| 位置づけ | Kelly基準を許容損失額、注文数量、損切り幅、証拠金使用率に変換する教育用チェックツール |

## 使い方

各ラボの詳細は、まず該当ラボの README を読む。

```bash
sed -n '1,220p' lab_1/readme.md
sed -n '1,220p' lab_2/readme.md
sed -n '1,220p' lab_3/readme.md
```

実験を再生成する場合も、各ラボ README に記載されたコマンドを正本とする。

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

既存の正本出力を壊さず試す場合は、各スクリプトの `--output-dir` を使って一時ディレクトリへ出力する。

## 管理方針

- ルート README は索引とラボ一覧に限定する。
- 実験の詳細、再現コマンド、主要結果、注意点は各 `lab_xxx/readme.md` に書く。
- コードから再生成できる成果物は、各ラボ内の専用出力ディレクトリにまとめる。
- 新しい記事・実験を追加する場合は、`lab_4`、`lab_5` のように新しいディレクトリを作る。
- 記事本文に使う数値は、各ラボの正本出力CSVまたはMarkdownから引用する。
