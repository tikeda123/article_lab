# BTC-only 記事執筆サマリー

## 一文結論

BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、この条件は `n=15` と小さく、bootstrapの下限も0を下回る。さらに、crash定義や期間分割を変えると壊れるケースがある。したがって、ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。

## 記事の中心主張

この記事ではBTCのみを扱う。

主張は、BTC急落の買いシグナルを提示することではない。`Funding low x risk-on` という一見よい条件を題材にして、エッジ候補にも `error on error` があることを示す。

つまり、平均リターンやPFを見て終わるのではなく、次の疑いのダイヤルを動かす。

- サンプル数
- bootstrap不確実性
- コスト
- 約定遅延
- crash定義
- risk-on proxy
- Funding閾値
- 期間分割
- MAE/DDとレバレッジ

## 最初に出すべき主要数値

| 論点 | 数値 | 記事での使い方 |
|---|---:|---|
| 48h `Funding low x risk-on` | `n=15`, mean `+1.115%`, PF `2.073` | 候補としては面白いが小標本 |
| 48h bootstrap lower bound | mean 5% `-0.380%` | 点推定だけでは強く言えない |
| 24h bootstrap lower bound | mean 5% `-0.057%` | 24hでも下限は0を下回る |
| crash定義変更 | `full_sample_q025`: mean `-1.082%`, PF `0.666` | 定義を変えると壊れる |
| 2022 stress period | `n=4`, mean `-0.789%`, PF `0.505` | レジーム依存を示す |
| 48h `Funding high x risk-off` | mean `-0.100%`, PF `0.935` | 避ける急落候補として使う |
| 全急落48h | MaxDD `-42.441%` | 一律に急落を買う危険性を示す |

## 本文用の図

1. `figures/body/btc_bootstrap_mean_return.png`
   - 役割: `Funding low x risk-on` の小標本不確実性を示す。
   - 本文メッセージ: 点推定が良くても、推定誤差を重ねると強い主張はできない。

2. `figures/body/btc_definition_robustness_heatmap.png`
   - 役割: crash定義を変えると結論が変わることを示す。
   - 本文メッセージ: 「急落」の定義そのものが主観的なダイヤルである。

3. `figures/body/btc_cost_stress_heatmap.png`
   - 役割: grossのエッジがコストで圧縮されることを示す。
   - 本文メッセージ: バックテストの平均リターンは、執行・コスト前提込みで読む必要がある。

## 補足で使う図

| 図 | 使いどころ |
|---|---|
| `figures/appendix/btc_entry_execution_stress.png` | 約定遅延もリスクモデルの一部だと説明する |
| `figures/appendix/btc_risk_env_robustness.png` | risk-on proxyはBTCの直接予測ではなく文脈変数だと説明する |
| `figures/appendix/btc_funding_definition_robustness.png` | Funding閾値の主観性を説明する |
| `figures/appendix/btc_leverage_tolerance.png` | MAE/DDとレバレッジ耐性を補足する |
| `figures/appendix/fragility_matrix_status.png` | Fragility Matrixの全体像を補足する |

## 記事構成案

1. BTC急落は本当に買えるのか、という問いを置く。
2. まず全急落のDDと `Funding high x risk-off` を見せ、一律の急落買いを否定する。
3. `Funding low x risk-on` を「面白い候補」として提示する。
4. すぐに `n=15` とbootstrap下限を出し、点推定の危うさを示す。
5. crash定義、期間、コスト、約定を動かし、候補がどこで壊れるかを見る。
6. Fragility Matrixで、壊れる条件を実務対応に変換する。
7. 結論として、予測ではなく「壊れる条件を先に調べる」ことがファットテール実務だとまとめる。

## 使うレポート

| レポート | 役割 |
|---|---|
| `reports/lab_10_experiment_report.md` | 実験結果の全体サマリー |
| `reports/article_outline_alignment.md` | 記事骨子と結果の対応確認 |
| `reports/fragility_matrix.md` | 壊れる条件と実務対応の一覧 |
| `reports/article_figure_selection.md` | 図の採用判断 |
| `reports/btc_crash_fragility.md` | BTC実験の詳細確認 |

## 言い換えルール

避ける:

> BTC急落は `Funding low x risk-on` なら買える。

使う:

> BTC急落の `Funding low x risk-on` は、買える急落候補に見える。しかし、サンプル数、bootstrap、定義変更、期間分割を見ると、まだ有効戦略とは言えない。記事で扱うべきなのは、候補が壊れる条件である。

避ける:

> NasdaqがBTCを予測する。

使う:

> Nasdaqなどの外部市場は、BTC急落を分類するためのリスク環境 proxy として扱う。直接予測因子とは書かない。
