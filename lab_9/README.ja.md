# lab_9: USDJPY戦略開発における生成AIモデル評価

English: [README.md](README.md)

このラボは、Qiita記事「[クオンツトレードに最適な生成AIはどれか？ ― Claude Fable5 / GPT 5.5 Pro / GPT 5.5 High をUSDJPY戦略開発で比較した](https://qiita.com/tikeda123/items/63e6882cacadbdce1bc4)」に対応する実験・評価パッケージである。

同一のUSDJPYクオンツ戦略開発プロンプトを、Claude Fable5、GPT 5.5 Pro、GPT 5.5 Highの3モデルに与え、データ診断、戦略候補の設計、バックテスト、Walk Forward Optimization、コスト考慮、ロバスト性確認、ベンチマーク比較、採用/棄却判断までを比較した。

このラボは投資助言ではなく、本番運用可能な売買システムでもない。生成AIをクオンツリサーチ工程に使う場合、どのモデルがどの工程に強いかを確認するための教育用評価パッケージである。

## 完結性

`lab_9` の評価材料はこのディレクトリ内で完結する。

| 種類 | 場所 |
|---|---|
| 公開記事 | [クオンツトレードに最適な生成AIはどれか？ ― Claude Fable5 / GPT 5.5 Pro / GPT 5.5 High をUSDJPY戦略開発で比較した](https://qiita.com/tikeda123/items/63e6882cacadbdce1bc4) |
| 共通プロンプト | `inputdata/prompto.md` |
| 入力データ | `inputdata/USDJPY30.csv`, `inputdata/USDJPY60.csv`, `inputdata/USDJPY240.csv` |
| 評価サマリ | `AI_MODEL_EVALUATION_SUMMARY.md` |
| 正本モデル出力 | `gpt5_5pro/` |
| セカンドオピニオン実装出力 | `gpt_5_5_high/` |
| 批判的レビュー用出力 | `fable5/` |

過去の一部ラボと異なり、`lab_9` には単一のトップレベル実験スクリプトはない。共通プロンプト、共通入力データ、各モデルの成果物、最終評価サマリをまとめた比較パッケージとして扱う。

## 評価対象

3モデルには同一タスクを与え、以下の観点で評価した。

| 評価軸 | 内容 |
|---|---|
| データ診断 | 期間、件数、時間足、欠損、重複、OHLC整合性、外れ値、ボラティリティ、トレンド/レンジ性 |
| 戦略候補の幅 | トレンド、ブレイクアウト、平均回帰、ボラティリティフィルター、レジーム判定 |
| WFOの厳密性 | 時系列順、train / validation / test分離、OOS fold管理 |
| 約定・コストの現実性 | 過去データだけでシグナルを作り、次足約定と取引コストを考慮 |
| ロバスト性 | パラメータ、コスト、レジーム、Monte Carlo / bootstrap、ロング/ショート依存 |
| ベンチマーク制御 | Buy & Hold、常時ロング、常時ショート、常時フラットとの比較 |
| 最終判断 | 十分なエッジがなければ「採用しない」と結論づけられるか |

## モデル別成果物

| ディレクトリ | 役割 | 主な成果物 |
|---|---|---|
| `gpt5_5pro/` | 記事実験の正本結果 | `USDJPY_report.md`, `AI_EVALUATION_REPORT_gpt55_pro.md`, `usdjpy_wfo_quant_research.py`, `outputs/*.csv`, `outputs/*.png` |
| `gpt_5_5_high/` | 実装力の高い代替候補生成 | `AI_EVALUATION_REPORT_gpt55_high.md`, `usdjpy_wfo_strategy.py`, `output_csv/*.csv`, `*.png` |
| `fable5/` | 批判的解釈・記事考察用 | `USDJPY_quant_analysis_report.md`, `AI_EVALUATION_REPORT_fable.md`, `usdjpy_wfo.py`, `fold_results.csv`, `wfo_results.png` |

## 最終順位

| 順位 | モデルディレクトリ | スコア | 評価 |
|---:|---|---:|---|
| 1 | `gpt5_5pro/` | 90 / 100 | 最も完成度の高いクオンツリサーチパッケージ |
| 2 | `gpt_5_5_high/` | 77 / 100 | 実装力は高いが、最終判断が弱い |
| 3 | `fable5/` | 67 / 100 | 批判的解釈は鋭いが、コード再現性が弱い |

## スコアマトリクス

| モデル | データ | 戦略幅 | WFO | 約定 | ロバスト | ベンチ | 成果物 | 合計 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT 5.5 Pro | 9 | 9 | 18 | 14 | 14 | 14 | 12 | 90 |
| GPT 5.5 High | 8 | 9 | 17 | 14 | 12 | 7 | 10 | 77 |
| Claude Fable5 | 8 | 8 | 10 | 7 | 13 | 13 | 8 | 67 |

## 主要結果

GPT 5.5 Proを正本結果とする理由は、最も完成度の高い再現可能な研究パッケージを作ったうえで、選定戦略をライブ単独戦略としては採用しないと判断できたためである。

GPT 5.5 Proが選んだ4H Donchian Breakout / トレンドフォロー系候補は、OOSでプラスではあったが、単純なUSDJPY常時ロングに負けていた。

| 候補 | 総リターン | 年率リターン | Sharpe | Calmar | 最大DD |
|---|---:|---:|---:|---:|---:|
| 4H Breakout WFO | +58.2% | +3.36% | 0.403 | 0.210 | -16.0% |
| USDJPY常時ロング | +93.9% | +4.88% | 0.562 | 0.238 | -20.5% |

したがって、研究上の結論は「見かけ上プラスの戦略はあるが、独立した戦略アルファというより、リスク管理付きのUSDJPYロングベータに近い」である。

## 実験環境

生成されたスクリプトは主に以下を使う。

```text
numpy
pandas
matplotlib
```

プロンプトでは `scipy` と `scikit-learn` も許容しているが、レビュー済みスクリプトはTA-Libのような導入が難しい依存には頼っていない。

## 再現・確認コマンド

まず評価サマリを読む。

```bash
sed -n '1,220p' lab_9/AI_MODEL_EVALUATION_SUMMARY.md
```

GPT 5.5 Pro実装を一時ディレクトリへ再実行する。

```bash
python3 lab_9/gpt5_5pro/usdjpy_wfo_quant_research.py \
  --files lab_9/inputdata/USDJPY30.csv lab_9/inputdata/USDJPY60.csv lab_9/inputdata/USDJPY240.csv \
  --outdir /tmp/lab9_gpt55pro_check \
  --strategy-filter breakout \
  --bootstrap-sims 500
```

GPT 5.5 High実装を一時ディレクトリへ再実行する。

```bash
python3 lab_9/gpt_5_5_high/usdjpy_wfo_strategy.py \
  --data lab_9/inputdata/USDJPY30.csv lab_9/inputdata/USDJPY60.csv lab_9/inputdata/USDJPY240.csv \
  --outdir /tmp/lab9_gpt55high_check
```

Fable5のスクリプトはレビュー対象として有用だが、`main()` に外部パスが固定されている。そのため、スクリプトをリポジトリ相対パスへ修正しない限り、`fable5/USDJPY_quant_analysis_report.md`、`fable5/fold_results.csv`、`fable5/wfo_results.png` をレビュー済み成果物として扱う。

## 主な成果物

| ファイル | 内容 |
|---|---|
| `AI_MODEL_EVALUATION_SUMMARY.md` | 3モデル横断の最終評価と記事向け結果サマリ |
| `inputdata/prompto.md` | 各モデルに与えた共通プロンプト |
| `inputdata/USDJPY30.csv` | USDJPY 30分足OHLCV |
| `inputdata/USDJPY60.csv` | USDJPY 60分足OHLCV |
| `inputdata/USDJPY240.csv` | USDJPY 240分足OHLCV |
| `gpt5_5pro/USDJPY_report.md` | GPT 5.5 Proの研究レポート |
| `gpt5_5pro/AI_EVALUATION_REPORT_gpt55_pro.md` | GPT 5.5 Proの評価レポート |
| `gpt5_5pro/outputs/benchmark_comparison.csv` | 常時ロング、常時ショート、常時フラットとの重要な比較 |
| `gpt5_5pro/outputs/selected_4h_breakout_monte_carlo_summary.csv` | BootstrapとDDリスクのサマリ |
| `gpt_5_5_high/AI_EVALUATION_REPORT_gpt55_high.md` | GPT 5.5 Highの評価レポート |
| `gpt_5_5_high/output_csv/usdjpy_wfo_summary.csv` | GPT 5.5 Highの戦略ファミリー別WFO比較 |
| `fable5/AI_EVALUATION_REPORT_fable.md` | Claude Fable5の評価レポート |
| `fable5/USDJPY_quant_analysis_report.md` | Fable5の研究ナラティブと棄却ロジック |

## 解釈上の注意

- スコアは筆者の評価軸に基づくものであり、モデル能力の絶対順位ではない。
- 各モデルの出力は1回の試行であり、統計的に安定したモデルランキングではない。
- GPT 5.5 Proが1位なのは、取引可能な戦略を見つけたからではなく、実装品質と偽陽性の棄却判断が最も揃っていたからである。
- GPT 5.5 Highは候補生成には有用だが、30分足MAクロスの好成績には、ベンチマーク比較とロングベータ制御が不足している。
- Claude Fable5は、USDJPYのプラス成績が独立アルファではなくロングベータである可能性を説明する批判的レビューとして有用である。
- 3モデルのどれも、価格データ単独でライブ運用可能なUSDJPY単独戦略を確立していない。
