# lab_10 BTC-only Article Materials

このディレクトリは、BTCのみを扱う記事を書くための材料を一箇所に集めたものです。

USDJPYの実験ログは `lab_10/outputs/` 側に残していますが、この記事では使いません。このパッケージには、記事本文・補足・分析確認に必要なBTC関連の結果だけを入れています。

## 使う順番

1. `article_writing_summary.ja.md` を読み、記事の主張、主要数値、使う図を確認する。
2. `reports/lab_10_experiment_report.md` で実験結果の全体像を確認する。
3. `reports/article_outline_alignment.md` で、記事骨子と実験結果の合致点を確認する。
4. `figures/body/` の3枚を本文用の図として使う。
5. 必要に応じて `figures/appendix/` と `tables/` を補足・脚注・検証用に使う。

## ディレクトリ構成

| ディレクトリ | 内容 | 用途 |
|---|---|---|
| `reports/` | BTC-onlyの分析レポート、骨子整合性、図表選定、Fragility Matrix | 記事本文の論理確認 |
| `tables/` | BTC実験のCSV結果 | 数値引用、追加集計、表作成 |
| `figures/body/` | 本文で優先して使う図 | 記事本文用 |
| `figures/appendix/` | 補足・長めの記事で使う図 | 補足、検証資料 |
| `lab7_baseline_reference/` | lab_7由来のBTCベースライン参照 | 背景確認、再現性確認 |

## 本文用の主要図

| 優先度 | 図 | 役割 |
|---:|---|---|
| 1 | `figures/body/btc_bootstrap_mean_return.png` | `Funding low x risk-on` の小標本不確実性を示す |
| 2 | `figures/body/btc_definition_robustness_heatmap.png` | crash定義を変えると候補が壊れることを示す |
| 3 | `figures/body/btc_cost_stress_heatmap.png` | grossの見た目がコストで圧縮されることを示す |

## 記事で強く言ってよいこと

- BTC急落は一律に買えるわけではない。
- `Funding low x risk-on` は面白い候補だが、証明済みの戦略ではない。
- `n=15`、bootstrap下限、crash定義、期間分割を見ると、候補は脆い。
- この記事の主張は「勝てる条件を見つけた」ではなく、「壊れる条件を先に調べる」である。

## 記事で避ける表現

- BTC急落は買い。
- `Funding low x risk-on` は有効戦略。
- NasdaqがBTCを直接予測する。
- bootstrapやFragility Matrixでエッジが証明された。

## 再生成元

元の出力は `lab_10/outputs/` にあります。このディレクトリは執筆用コピーです。

主要生成コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```
