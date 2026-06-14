# lab_10 Phase 3-5 実行サマリー

実行日: 2026-06-14

## 実行範囲

本サマリーは、`EXPERIMENT_PLAN.ja.md` の Phase 3 から Phase 5 までを対象にする。

記事ではBTCのみを扱う。USDJPY実験は内部検討ログとして残すが、本サマリーのPhase 3-5評価、統合レポート、図表選定、記事骨子との整合性分析には使わない。

| Phase | 内容 | 状態 |
|---|---|---|
| Phase 3 | Fragility Matrix 作成 | 完了 |
| Phase 4 | 統合レポート作成 | 完了 |
| Phase 5 | 記事骨子との整合性分析 | 完了 |

実行コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

## 生成物

| 成果物 | ファイル |
|---|---|
| Fragility Matrix CSV | `outputs/tables/fragility_matrix.csv` |
| Fragility Matrix レポート | `outputs/report/fragility_matrix.md` |
| 統合レポート | `outputs/report/lab_10_experiment_report.md` |
| 記事骨子との整合性分析 | `outputs/report/article_outline_alignment.md` |
| 図表選定メモ | `outputs/report/article_figure_selection.md` |
| Matrixステータス図 | `outputs/figures/fragility_matrix_status.png` |

## Phase 3: BTC-only Fragility Matrix

記事向けの Fragility Matrix は、BTC行だけに絞った9行を生成した。内部確認用の全行Matrixは `outputs/tables/fragility_matrix_all_internal.csv` に分離した。

| 対象 | broken | fragile | watch |
|---|---:|---:|---:|
| BTC crash edge candidate | 3 | 5 | 1 |

主な読み方:

- BTCでは、`Funding low x risk-on` の小標本、コスト、約定遅延、crash定義、期間依存が主要な壊れる要因になった。
- `Funding high x risk-off` は、買える急落候補ではなく避ける急落候補として使いやすい。

## Phase 4: 統合レポート

統合レポートでは、Phase 0-3の結果を1本にまとめた。

記事に使える結論:

- BTCの `Funding low x risk-on` は候補性があるが、`n=15` と小さく、bootstrap下限も0を下回るため強く主張できない。
- BTCだけでも、「正しい未来分布を当てる」より、「前提が壊れる条件を探し、運用ルールに変える」という記事骨子を支えられる。

言いすぎてはいけない結論:

- BTC急落は買いである。
- `Funding low x risk-on` は有効戦略である。
- NasdaqがBTCを直接予測する。

## Phase 5: 記事骨子との整合性分析

記事骨子の主要主張は、実験結果とおおむね合致した。

| 記事骨子の主張 | 判定 | 根拠 |
|---|---|---|
| BTC急落は一律に買えるわけではない | support | 全急落、`Funding low x risk-on`、`Funding high x risk-off` でDDとPFが変わる |
| エッジ候補にも error on error がある | support | `n=15`、bootstrap下限、crash定義、期間分割で結論が揺れる |
| 主観を隠さず、疑いのダイヤルとして扱う | support | コスト倍率、Funding閾値、risk-on proxy、約定遅延が結論を動かす |
| エッジ候補は平均リターンではなく壊れる条件で見る | support | `Funding low x risk-on` は平均は良いが、`n=15` とbootstrap下限が弱い |
| Fragility Matrixで運用ルールへ変換する | support | Matrix各行に practical response を付けた |

## 記事への反映方針

記事本文では、`Funding low x risk-on` を成功例としてではなく、次の形で扱う。

> BTC急落の `Funding low x risk-on` は、平均リターンだけを見ると面白い候補に見える。しかし、この条件は `n=15` と小さく、bootstrapの下限も0を下回る。したがって、ここで見るべきなのは「勝てる条件」ではなく、「どの前提が崩れたら候補が壊れるか」である。

この表現なら、記事骨子の `error on error` と「戦略が壊れる条件を探す」という主張に合致する。
