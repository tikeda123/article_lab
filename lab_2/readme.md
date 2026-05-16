# lab_2: AUDJPY 買われすぎ・売られすぎ定量化実験

このディレクトリは、記事「クオンツトレーダーは『買われすぎ・売られすぎ』をどう判断するのか」の根拠データ、検証スクリプト、記事用図表出力をまとめた実験ラボである。

記事の目的は、「下がりすぎ」「上がりすぎ」という主観的な相場判断を、VWAP乖離Zスコアと直近リターンの過去分布内パーセンタイルに変換し、その後に本当に反発したかを確認することである。この実験は完成した売買戦略のバックテストではなく、買われすぎ・売られすぎを検証可能な仮説へ変換するための探索フェーズである。

## 実験の位置づけ

この実験では、AUDJPY の60分足データを使い、以下の順に分析している。

1. 24時間VWAPを計算する
2. 終値が24時間VWAPからどれだけ離れているかを計算する
3. VWAP乖離を過去500本の平均・標準偏差でZスコア化する
4. 直近1時間リターンを過去500本内パーセンタイルに変換する
5. VWAP乖離Zスコアとリターンパーセンタイルで、売られすぎ・買われすぎ候補を定義する
6. シグナル判定後の次足始値で入った前提で、4時間後の反発リターンを確認する
7. 無条件Long/Shortベースライン、ホライズン感度、年別安定性、損益分布を確認する

記事本文に対応する正本出力は `article_outputs/` である。PNG、CSV、Markdownの成果物はコードから再生成できるため、`lab_2` 直下には入力CSV、実験コード、記事アウトライン、READMEだけを置く。

## 入力データ

入力CSVはこのディレクトリ直下に置かれている。ヘッダーなし、タブ区切りの60分足OHLCVである。

| ファイル | 通貨ペア | 形式 |
|---|---|---|
| `AUDJPY60.csv` | AUDJPY | `timestamp, open, high, low, close, volume` |

現在の正本出力では、以下の範囲を使っている。

| 項目 | 内容 |
|---|---:|
| 入力行数 | 100,000 |
| 指標計算後の利用可能行数 | 99,473 |
| データ開始 | `2010-04-12 23:00:00` |
| データ終了 | `2026-04-24 20:00:00` |
| 実際の分析開始 | `2010-05-12 17:00:00` |
| 実際の分析終了 | `2026-04-24 15:00:00` |
| 足種 | 60分足 |
| 分析対象 | AUDJPY |

実際の分析開始が入力開始より遅いのは、過去500本のパーセンタイル/Zスコア計算と24時間VWAP計算にウォームアップ期間が必要なためである。実際の分析終了が入力終了より早いのは、シグナル判定後の次足始値エントリーと4時間後評価に未来足が必要なためである。

## 実験環境

このラボは単体Pythonスクリプトで実行できる。現在のローカル確認環境は以下の通り。

| 項目 | バージョン |
|---|---|
| Python | `3.11.5` |
| pandas | `2.3.2` |
| numpy | `2.3.3` |
| matplotlib | `3.10.6` |
| tabulate | `0.9.0` |

`tabulate` は `DataFrame.to_markdown()` によるMarkdownサマリ出力で使う。図表生成はGUIを使わない `matplotlib` の通常PNG保存で行う。環境に Noto CJK フォントがある場合は、日本語ラベル表示に使う。

## 再現コマンド

リポジトリルートから正本出力を再生成する場合は、次を実行する。

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py
```

`lab_2` ディレクトリに移動して実行する場合は次でよい。

```bash
cd lab_2
python audjpy_overbought_oversold_article_experiment.py
```

実行が成功すると、標準出力に条件別サマリー、実際の分析期間、出力先が表示される。

```text
Analysis period: 2010-05-12 17:00:00 to 2026-04-24 15:00:00
Saved files to: .../lab_2/article_outputs
```

出力先には同名ファイルが再生成される。既存の正本を壊さず試す場合は、必ず別の `--output-dir` を指定する。

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py \
  --output-dir /tmp/lab2_overbought_oversold_check \
  --dpi 80
```

## Python実験ツールの使い方

実験ツール本体は `audjpy_overbought_oversold_article_experiment.py` である。入力CSVを読み込み、集計CSV、記事用Markdown、図表PNGを一括生成する。

まず利用可能な引数を確認する。

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py --help
```

主な引数は以下である。

| 引数 | 既定値 | 用途 |
|---|---|---|
| `--input-csv` | `lab_2/AUDJPY60.csv` | 入力するAUDJPY 60分足CSV |
| `--output-dir` | `lab_2/article_outputs` | 生成されるCSV、Markdown、図表の出力先 |
| `--roll` | `500` | リターンパーセンタイルとVWAP乖離Zスコアの過去本数 |
| `--vwap-window` | `24` | 24時間VWAPを計算するローリング本数 |
| `--primary-horizon` | `4` | 記事本文で主に扱う反発評価ホライズン |
| `--horizons` | `1,2,4,8,12,24` | ホライズン感度で比較する評価時間 |
| `--cost-pips` | `0.8` | 往復コストpips |
| `--pip-size` | `0.01` | JPYペアの1pip換算 |
| `--dpi` | `200` | PNG図表の解像度 |

たとえば、4時間後ではなく8時間後を主結果にして試す場合は、正本とは別の出力先を指定して実行する。

```bash
python lab_2/audjpy_overbought_oversold_article_experiment.py \
  --primary-horizon 8 \
  --output-dir /tmp/lab2_horizon8_check
```

出力を確認するときは、まず記事用Markdownサマリと条件別サマリーCSVを見る。

```bash
sed -n '1,180p' lab_2/article_outputs/14_article_experiment_summary.md
column -s, -t < lab_2/article_outputs/03_article_condition_summary.csv
```

Pythonから結果を追加確認する場合は、次のようにCSVを読む。

```bash
python - <<'PY'
import pandas as pd

summary = pd.read_csv("lab_2/article_outputs/03_article_condition_summary.csv")
print(summary[[
    "condition",
    "direction",
    "n",
    "rebound_probability_%",
    "mean_net_return_bps",
    "excess_vs_baseline_bps",
]])
PY
```

## スクリプトの処理内容

主スクリプトは `audjpy_overbought_oversold_article_experiment.py` である。

- `AUDJPY60.csv` を読み込み、日時順に並べ、OHLCVを数値化する。
- `close.pct_change()` で直近1時間リターンを作る。
- 直近1時間リターンが過去500本内で何パーセンタイルにあるかを計算する。
- `typical price = (high + low + close) / 3` と出来高から24時間VWAPを計算する。
- `close / vwap_24h - 1` でVWAP乖離を作り、過去500本の平均・標準偏差でZスコア化する。
- シグナル判定は60分足の終値時点、エントリーは次足始値、評価は指定ホライズン後の始値で行う。
- 往復コスト0.8 pipsを控除したLong/Shortリターンを計算する。
- 売られすぎ候補ではLong反発、買われすぎ候補ではShort反落として評価する。
- 無条件Long/Shortベースライン、条件別サマリー、ヒートマップ、ホライズン感度、年別安定性、リターン分布を出力する。

## 売られすぎ・買われすぎの定義

この実験では、売られすぎ・買われすぎを次のように定義している。

| 条件 | 方向 | 定義 |
|---|---|---|
| 売られすぎ候補 | Long | `VWAP Z <= -2.0` かつ `ret pct <= 10` |
| 強い売られすぎ候補 | Long | `VWAP Z <= -2.5` かつ `ret pct <= 5` |
| 買われすぎ候補 | Short | `VWAP Z >= 2.0` かつ `ret pct >= 90` |
| 強い買われすぎ候補 | Short | `VWAP Z >= 2.5` かつ `ret pct >= 95` |

ここでの条件は、即時の売買シグナルではなく、反発が起きやすいかもしれない候補領域である。

## 主要出力

記事対応の主要出力は `article_outputs/` にある。

| ファイル | 内容 |
|---|---|
| `00_article_judgement_map_overbought_oversold.png` | 買われすぎ・売られすぎの定義を説明する概念図 |
| `01_article_heatmap_contrarian_mean_bps.png` | 逆張り4時間リターンの期待値ヒートマップ |
| `02_article_heatmap_rebound_probability.png` | 反発確率ヒートマップ |
| `03_article_condition_summary.csv` | 記事本文に使う条件別サマリー |
| `04_heatmap_mean_bps_matrix.csv` | ヒートマップ期待値の数値表 |
| `05_heatmap_probability_matrix.csv` | ヒートマップ反発確率の数値表 |
| `06_heatmap_sample_count_matrix.csv` | ヒートマップの評価対象サンプル数 |
| `07_article_condition_summary_bars.png` | 条件別サマリー棒グラフ |
| `08_article_horizon_sensitivity.png` | 1/2/4/8/12/24時間後の感度比較 |
| `09_article_annual_stability.png` | 強い候補条件の年別安定性 |
| `10_article_return_distribution_boxplot.png` | 条件別4時間後リターン分布 |
| `11_horizon_sensitivity_summary.csv` | ホライズン感度の数値表 |
| `12_annual_condition_summary.csv` | 年別条件別サマリー |
| `13_baseline_summary.csv` | 無条件Long/Shortベースライン |
| `14_article_experiment_summary.md` | 記事用の表形式サマリ |

記事を書くときは、まず `14_article_experiment_summary.md` を確認し、本文用の数値は `03_article_condition_summary.csv` と `13_baseline_summary.csv` で裏取りする。

## 主要結果

主評価ホライズンは4時間後である。シグナル判定後の次足始値で入り、4時間後の始値で評価し、往復0.8 pipsを控除している。

| 条件 | 方向 | 件数 | 反発確率 | 平均リターン | 無条件平均との差 |
|---|---|---:|---:|---:|---:|
| 売られすぎ候補 | Long | 1,549 | 53.32% | +1.56 bps | +2.31 bps |
| 強い売られすぎ候補 | Long | 670 | 53.28% | +5.09 bps | +5.84 bps |
| 買われすぎ候補 | Short | 889 | 51.74% | +3.31 bps | +4.41 bps |
| 強い買われすぎ候補 | Short | 326 | 53.37% | +5.95 bps | +7.05 bps |

4時間後の無条件ベースラインは、Long平均が -0.75 bps、Short平均が -1.10 bps である。したがって、強い売られすぎ候補と強い買われすぎ候補は、どちらも無条件エントリーより改善している。

## 解釈上の注意点

この結果は、すぐに売買戦略として使えるという意味ではない。

- 反発確率は50%を少し上回る程度であり、勝率だけで強い戦略とは言えない。
- 平均リターンはプラスだが、p5側の損失幅も大きい。
- 年別に見ると負ける年がある。
- 損切り、利確、最大逆行幅、スリッページ、時間帯、トレンド/レンジ分離は未検証である。
- Walk-Forward検証、Holdout検証、DryRunは行っていない。

記事では、この実験を「買われすぎ・売られすぎを数値化し、反発しやすい領域を観察するための入口」として扱う。

## 記事との対応

この記事で強調するべき点は、次の変換である。

```text
下がりすぎに見える
=> 過去500本の中で下位10%の急落であり、かつVWAPから2標準偏差以上下に乖離している
```

同じように、買われすぎも主観ではなく、VWAP乖離Zスコアとリターンパーセンタイルで定義する。重要なのは、異常状態そのものではなく、その異常状態のあとにリターン分布がどう変わったかを確認することである。
