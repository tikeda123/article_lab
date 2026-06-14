# lab_10 実験計画: BTC Fragility Diagnostics

## 1. 前提

この記事は公開済みのQiita記事を正とする。

- 記事: https://qiita.com/tikeda123/items/091519af64bd22367c2d
- タイトル: ファットテールを織り込んだ"つもり"になっていないか
- 実験対象: BTC急落後の `Funding low x risk-on`
- 実験目的: エッジ証明ではなく、良さそうに見える推定値がどの前提で壊れるかを診断する

## 2. 記事に合わせた実験ゴール

記事で支えるべき主張は次の1文である。

> ファットテールをリスク管理に織り込むとは、正しい未来分布を当てることではない。リスクを測るモデルにも誤差があることを認め、良さそうに見えるエッジ候補がどの条件で壊れるかを見つけ、その結果を運用ルールに変えることである。

したがって、lab_10の実験は次の問いに絞る。

1. `Funding low x risk-on` の点推定は、サンプル数とbootstrapでどれだけ不安定か。
2. crash定義を変えると、48h候補は壊れるか。
3. 2022年ストレス期など期間分割で候補は残るか。
4. コスト、約定遅延、レバレッジで候補はどれだけ圧縮されるか。
5. risk-on proxyを変えたとき、直接予測ではなく文脈変数として扱えるか。
6. 壊れる条件をFragility Matrixとして運用対応へ変換できるか。

## 3. やらないこと

- `Funding low x risk-on` を有効戦略として証明しない。
- BTC急落は買い、という結論を出さない。
- NasdaqやS&P500をBTCの直接予測因子として扱わない。
- 古い実験骨子の別資産診断を保持しない。
- 公開記事に出ていない補助実験を、記事の中心根拠として扱わない。

## 4. データと再利用範囲

`lab_7` のBTC急落分類を再利用する。

| 入力 | 用途 |
|---|---|
| `data/lab_7/BTCUSD240.csv` | BTC 4H価格 |
| `data/lab_7/funding_rate_history.csv` | Funding Rate |
| `data/lab_7/USATECHIDXUSD240.csv` | Nasdaq系risk-on proxy |
| `data/lab_7/USA500IDXUSD240.csv` | S&P500系risk-on proxy |
| `data/lab_7/USA30IDXUSD240.csv` | broad proxy |
| `data/lab_7/DEUIDXEUR240.csv` | broad proxy |

## 5. Phase構成

### Phase 0: lab_7 baseline reproduction

目的:

- 前回記事のBTC急落分類をlab_10内で再現する。
- `Funding low x risk-on` が「面白い候補に見えるが、まだ証明ではない」基準線を作る。

コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
```

主要成果物:

- `outputs/lab7_interaction_model_base/interaction_model_report.md`
- `outputs/lab7_interaction_model_base/interaction_group_stats.csv`
- `outputs/lab7_interaction_model_base/interaction_contrasts.csv`

### Phase 1: BTC fragility diagnostics

目的:

- 公開記事の第8〜11章に対応する実験結果を作る。
- 平均やPFではなく、`n`、bootstrap下限、crash定義、期間、コスト、約定、MAE/DDを中心に読む。

コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
```

主要成果物:

| 成果物 | 記事での役割 |
|---|---|
| `btc_crash_baseline.csv` | 48h `Funding low x risk-on` の `n=15`, mean `+1.115%`, PF `2.073` を基準線にする |
| `btc_bootstrap_uncertainty.csv` | 48h bootstrap mean 5%下限 `-0.380%` を示す |
| `btc_definition_robustness.csv` | `full_sample_q025` で48h mean `-1.082%`, PF `0.666` に壊れることを示す |
| `btc_subperiod_results.csv` | 2022 stress periodで `n=4`, mean `-0.789%`, PF `0.505` を示す |
| `btc_cost_stress.csv` | 48h cost x5で PF `2.073 -> 1.524` に圧縮されることを示す |
| `btc_entry_execution_stress.csv` | 48h 4H遅延で PF `2.073 -> 1.324` に圧縮されることを示す |
| `btc_leverage_tolerance.csv` | 3x worst MAE `-28.277%` を示す |
| `btc_risk_env_robustness.csv` | risk-on proxyは直接予測因子ではなく文脈変数だと示す |

### Phase 2: Article support matrix

目的:

- 公開記事の第12章 `Fragility Matrix` と一致する表を生成する。
- 壊れる前提を、実務対応へ変換する。

コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

主要成果物:

| 成果物 | 用途 |
|---|---|
| `outputs/tables/fragility_matrix.csv` | 記事第12章に対応する7行Matrix |
| `outputs/tables/article_key_metrics.csv` | 記事に引用する主要数値 |
| `outputs/report/lab_10_experiment_report.md` | 実験結果の統合レポート |
| `outputs/report/article_outline_alignment.md` | 公開記事との整合性確認 |
| `outputs/report/article_figure_selection.md` | 記事用図の選定 |
| `article_materials_btc_minimal_ai/` | 生成AIに渡す最小5ファイル |

## 6. 記事に対応する主要数値

| 記事内の論点 | 実験結果 | 解釈 |
|---|---:|---|
| 48h基準線 | `n=15`, mean `+1.115%`, PF `2.073` | 面白い候補だが結論ではない |
| 24h基準線 | `n=15`, mean `+1.297%`, PF `3.122` | 24hでも小標本 |
| 48h bootstrap | mean 5%下限 `-0.380%` | プラス期待値を強く主張できない |
| 24h bootstrap | mean 5%下限 `-0.057%` | 24hも下限は0を下回る |
| crash定義 | `full_sample_q025`: mean `-1.082%`, PF `0.666` | 定義変更で壊れる |
| 2022 stress | `n=4`, mean `-0.789%`, PF `0.505` | レジーム依存 |
| cost x5 | 48h PF `2.073 -> 1.524` | グロス優位はコストで圧縮 |
| 4H delay | 48h PF `2.073 -> 1.324` | 約定前提はリスクモデルの一部 |
| 3x leverage | worst MAE `-28.277%` | 平均は経路損失とセットで読む |

## 7. 記事用図

本文で優先する図:

1. `outputs/figures/btc_bootstrap_mean_return.png`
2. `outputs/figures/btc_definition_robustness_heatmap.png`
3. `outputs/figures/btc_cost_stress_heatmap.png`

補足で使う図:

- `outputs/figures/btc_entry_execution_stress.png`
- `outputs/figures/btc_leverage_tolerance.png`
- `outputs/figures/btc_risk_env_robustness.png`
- `outputs/figures/fragility_matrix_status.png`

## 8. 検証チェック

```bash
/Users/toikeda/miniconda3/bin/python -m py_compile \
  lab_10/scripts/00_lab7_interaction_model_base.py \
  lab_10/scripts/02_btc_crash_fragility.py \
  lab_10/scripts/03_fragility_matrix.py

/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

## 9. 最終判断

lab_10は、公開記事の根拠パッケージとしてBTC fragility診断に特化する。結論は「BTC急落は買い」ではなく、「良さそうに見える候補を、壊れる前提から読む」である。
