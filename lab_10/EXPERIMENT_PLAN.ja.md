# lab_10 実験計画書

## 1. ゴール

`lab_10` のゴールは、BTC急落データを使って、ファットテール実務記事の主張を実データで検証し、結果と分析をレポートにまとめることである。

記事本文では **BTCのみ** を扱う。USDJPYリスク推定診断は内部検討ログとして残すが、記事本文、記事用図表、記事骨子との整合性分析には使わない。

最終成果物では、単に数表を作るだけでなく、以下を明確に判定する。

1. BTC実験の結果は、記事骨子の中心メッセージと合っているか。
2. `error on error`、つまり「リスク推定にも誤差があり、その誤差の見積もりにも誤差がある」という主張を実データで説明できるか。
3. `lab_7` 由来の `Funding low x risk-on` は、エッジ証明ではなく「壊れる条件を調べる候補」として適切に扱えているか。
4. 結果を、ポジションサイズ、レバレッジ上限、停止ルール、コスト上限、外部環境フィルターなどの実務ルールへ接続できるか。

## 2. 対象文書と実装仕様

本計画は、以下の文書と実装仕様に基づく。

| 区分 | ファイル | 役割 |
|---|---|---|
| 記事骨子 | `ファットテール実務記事_改訂骨子_error_on_error反映版.pdf` | 記事全体の主張と章立て |
| 実験骨子 | `ファットテール実務記事_実験骨子.pdf` | USDJPY/BTC/Fragility Matrix の実験案 |
| 実装仕様 | `IMPLEMENTATION_SPEC.ja.md` | スクリプト、入力、出力、指標、判定条件 |
| BTCベース | `reference/lab_7/` | `lab_7` の元コード、データ、既存出力 |

## 3. 実験の中心仮説

本実験では、未来分布や売買エッジを「当てる」のではなく、次の仮説を検証する。

| 仮説 | 実験で見ること | 期待される読み方 |
|---|---|---|
| H1 | BTC の `Funding low x risk-on` は一見よい候補に見えても、コスト、定義、期間、約定、MAE/DD で評価が揺れる | エッジ候補にも推定誤差がある |
| H2 | BTCの壊れる条件を一覧化すると、記事骨子の「測る・疑う・行動する」という3層構造に接続できる | 分析は運用ルールへ変換できる |
| H3 | USDJPYを使わなくても、BTCだけで `error on error` の記事主張を説明できる | 記事の焦点をBTCに絞る |
| H4 | 結果が弱い、または不安定でも、記事の主張とは矛盾しない | 本記事の目的は有効戦略の証明ではなく、前提の脆さの可視化である |

## 4. 成果物

### 4.1 最終成果物

| 成果物 | 保存先 | 内容 |
|---|---|---|
| 実験結果レポート | `outputs/report/lab_10_experiment_report.md` | BTCとFragility Matrix の結果と解釈 |
| 記事骨子との整合性分析 | `outputs/report/article_outline_alignment.md` | BTC実験が各章の主張を支える点・弱める点・追加説明が必要な点 |
| 図表選定メモ | `outputs/report/article_figure_selection.md` | 記事に載せるべき図表、載せない図表、理由 |
| Fragility Matrix | `outputs/tables/fragility_matrix.csv` と `outputs/report/fragility_matrix.md` | 壊れる要因、指標、実務対応の統合表 |

### 4.2 中間成果物

| 実験 | 主な出力 |
|---|---|
| USDJPY内部ログ | `usdjpy_risk_summary.csv`, `usdjpy_rolling_var.csv`, `usdjpy_stress_dials.csv`, `usdjpy_leverage_limits.csv` |
| BTC | `btc_cost_stress.csv`, `btc_entry_execution_stress.csv`, `btc_definition_robustness.csv`, `btc_risk_env_robustness.csv`, `btc_funding_definition_robustness.csv`, `btc_subperiod_results.csv`, `btc_bootstrap_uncertainty.csv` |
| 統合 | `fragility_matrix.csv`, `fragility_matrix.md`, `fragility_matrix_status.png` |

## 5. 実験フェーズ

### Phase 0: ベースライン再現

目的:

- `lab_10` 内にコピーした `lab_7` データとコードで、`lab_7` の基準結果を再現する。
- 以後の追加検証が、元の `lab_7` と同じ基準線から始まっていることを確認する。

実行:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
```

確認項目:

- `outputs/lab7_interaction_model_base/interaction_group_stats.csv` が生成される。
- `reference/lab_7/outputs/interaction_model/interaction_group_stats.csv` と主要CSVが一致する。
- `Funding low x risk-on` を「買える急落の証明」ではなく、追加ストレス検証の対象候補として扱う。

完了条件:

- 主要CSVの差分なし。
- 基準条件、イベント数、期間、risk-on 定義、Funding 定義をレポートに記録する。

### Phase 1: USDJPY リスク推定診断

目的:

- 同じUSDJPYデータでも、リスク推定値が手法・窓幅・ストレス仮定で揺れることを内部検討として確認する。
- 記事本文には使わない。記事ではBTCだけで「過去データを信じすぎない」「リスク推定そのものにも誤差がある」を説明する。

実行予定:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/01_usdjpy_risk_diagnostics.py
```

分析観点:

| 観点 | 見る指標 | レポートでの論点 |
|---|---|---|
| 手法差 | 正規VaR、ヒストリカルVaR、ES、Student-t VaR | 手法を使っただけではリスクは一意に決まらない |
| 窓幅差 | 1年、3年、5年、全期間 | 直近重視と長期重視で推定値が変わる |
| 左尾 | VaR 99%、ES 99%、最大DD | 平均や標準偏差では壊れ方が見えにくい |
| レバレッジ | DD倍率、許容DD別レバレッジ上限 | 過去最大DDを上限扱いすると危険 |
| 疑いのダイヤル | ボラ倍率、DD倍率、コスト倍率 | 主観的ストレスを明示し、複数水準で確認する |

完了条件:

- `outputs/report/usdjpy_risk_diagnostics.md` が生成される。
- 記事用図表には使わない。
- 「USDJPYの未来リスクを予測した」という表現を避けた解釈になっている。

### Phase 2: BTC 急落エッジ候補の Fragility 検証

目的:

- `lab_7` 由来の `Funding low x risk-on` を、エッジ証明ではなく壊れる条件を調べる対象として検証する。
- 記事骨子の「エッジ候補にも error on error がある」を支える。

実行予定:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
```

分析観点:

| 検証 | 主な問い | レポートでの論点 |
|---|---|---|
| コスト | gross の見栄えは net でも残るか | コスト控除前で結論を出さない |
| 約定遅延 | 次の4H始値で入れない場合も残るか | バックテストの執行前提を疑う |
| crash定義 | `-1.5σ`, `-2σ`, `-2.5σ`, 下位5%, 下位2.5%で変わるか | 定義誤差を確認する |
| risk-on定義 | Nasdaq、S&P500、3-of-4、強いrisk-onで変わるか | 外部リスク環境 proxy への依存を見る |
| Funding定義 | negative、lower 20%、lower 10%、high 20%で変わるか | 閾値設定に主観が入る |
| 期間分割 | 2020-2021、2022、2023-2024、2025-2026で残るか | レジーム依存を見る |
| MAE/DD | 含み損、最大DD、stop、レバレッジで耐えるか | 平均リターンではなく壊れ方を見る |
| bootstrap | 小標本で平均やPFがどれだけ揺れるか | `n` と推定不確実性を前面に出す |

完了条件:

- `outputs/report/btc_crash_fragility.md` が生成される。
- `Funding low x risk-on` について、少なくとも `n`、コスト耐性、定義依存、期間依存、MAE/DD、bootstrap 不確実性を記録する。
- 「BTC急落は買い」と読める表現を排除する。

### Phase 3: Fragility Matrix 作成

目的:

- BTCの結果を、壊れる前提、見る指標、実務対応に変換する。
- 記事骨子の「戦略が壊れる条件を探す」「測る・疑う・行動する」をBTCだけで実務表に落とす。

実行予定:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

出力:

```text
outputs/tables/fragility_matrix.csv
outputs/report/fragility_matrix.md
outputs/figures/fragility_matrix_status.png
```

Fragility Matrix の最低列:

```text
target
fragility_source
assumption_being_doubted
stress_case
metric
baseline_value
stressed_value
break_condition
fragility_status
article_message
practical_response
```

完了条件:

- 記事用の Matrix はBTCだけで構成される。
- 各行に「記事で何を言えるか」と「実務対応」が入っている。
- `survives_this_test` を「有効戦略」と誤読しない注記がある。

### Phase 4: 統合レポート作成

目的:

- Phase 0-3 の結果を、記事素材として読める1本のレポートにまとめる。
- 成功した検証だけでなく、弱い結果、不安定な結果、記事で言いすぎてはいけない点を明示する。

出力:

```text
outputs/report/lab_10_experiment_report.md
```

推奨構成:

1. Executive Summary
2. 実験の目的と非目的
3. 使用データと再現性
4. BTC: エッジ候補はどこで壊れるか
5. BTC Fragility Matrix: 壊れる前提と実務対応
6. 記事に使えるBTC図表
7. 記事で言ってよいこと、言ってはいけないこと
8. 残る制約と追加検証

必須記載:

- 使ったデータ期間。
- 各主要条件の `n`。
- gross と net の違い。
- crash定義、risk-on定義、Funding定義。
- 小標本と複数検定の注意。
- 投資助言ではないこと。

完了条件:

- 数値、図表、解釈が同じレポート内でつながっている。
- 記事本文へ移植できる短い結論文がある。
- 弱い結果を隠していない。

### Phase 5: 記事骨子との整合性分析

目的:

- 実験結果が、記事骨子の各章に対して何を支え、何を弱め、どこに追記が必要かを判定する。

出力:

```text
outputs/report/article_outline_alignment.md
```

整合性判定の形式:

| 記事骨子の主張 | 対応する実験結果 | 判定 | 記事での扱い |
|---|---|---|---|
| 過去データは基準線であって上限ではない | BTC全急落、条件別急落、期間分割 | support / partial / weak / conflict | どのBTC表・図を使うか |
| リスク推定そのものにも誤差がある | BTC bootstrap、crash定義変更、risk-on proxy変更 | support / partial / weak / conflict | error on error の説明に使う |
| 主観を隠さない | コスト倍率、Funding閾値、crash定義、risk-on proxy | support / partial / weak / conflict | 疑いのダイヤルとして示す |
| エッジ候補は壊れる条件で見る | BTC コスト、定義、期間、約定、MAE/DD | support / partial / weak / conflict | `Funding low x risk-on` の扱いを制限する |
| 最終的に運用ルールへ変える | Fragility Matrix | support / partial / weak / conflict | 実務対応表として掲載 |

判定基準:

| 判定 | 意味 |
|---|---|
| `support` | 実験結果が記事骨子の主張を直接支える |
| `partial` | 主張の方向は支えるが、制約や追加説明が必要 |
| `weak` | 実験結果だけでは支えが弱い |
| `conflict` | 記事骨子の表現を修正すべき |

完了条件:

- 記事骨子の主要章に対して、少なくとも1つの実験結果または制約が対応している。
- `conflict` または `weak` がある場合、記事側の修正文案を出す。
- 記事の結論が、実験結果より強くなっていない。

## 6. レポートでの結論ルール

### 6.1 強く言ってよいこと

- リスク推定値は、手法、窓幅、分布仮定、ストレス設定で変わる。
- 過去最大DDは将来最大DDの上限ではない。
- `Funding low x risk-on` は、BTC急落後の反発候補として検討する価値はある。
- ただし、その評価はサンプル数、コスト、定義、期間、約定前提に依存する。
- ファットテール実務では、正しい分布を当てるより、戦略が壊れる条件を探すことが重要である。

### 6.2 強く言ってはいけないこと

- USDJPY の将来リスクを予測できた。
- BTC急落は買いである。
- `Funding low x risk-on` は有効戦略である。
- Nasdaq が BTC を直接予測する。
- Student-t、VaR、ES、EVT を使えばファットテール対応は十分である。
- `survives_this_test` は実運用可能という意味である。

## 7. 品質管理

### 7.1 再現性チェック

- 実行コマンドを `outputs/report/lab_10_experiment_report.md` に残す。
- 使用したデータファイル名と行数を記録する。
- `lab_7` ベースライン再現結果と参照コピーの差分を確認する。
- スクリプトは `lab_10` 内のデータだけを参照する。

### 7.2 数値チェック

- `n` が小さい条件は、本文で必ず明記する。
- PF が無限大になるケースは、損失件数が少ないだけでないか確認する。
- bootstrap の下限が 0 以下なら、平均リターンの主張を弱める。
- gross のみでよく見える条件は、net とコストストレスを必ず併記する。

### 7.3 記事表現チェック

- 「予測」「証明」「有効戦略」という語を使いすぎない。
- 「候補」「診断」「壊れる条件」「疑いのダイヤル」「基準線」という語を優先する。
- 主要図表には、制約を1文で添える。
- 投資助言ではないことを明記する。

## 8. 実行順序とゲート

| 順序 | 作業 | ゲート |
|---:|---|---|
| 1 | ベースライン再現 | `lab_7` 参照CSVと差分なし |
| 2 | USDJPY内部ログ | 内部確認用として生成済み。記事には使わない |
| 3 | BTC Fragility 実験 | コスト、定義、期間、約定、MAE/DD、bootstrap の表が生成済み |
| 4 | Fragility Matrix | BTC の壊れる条件が統合済み |
| 5 | 統合レポート | 結果、分析、制約、記事用結論が揃っている |
| 6 | 記事骨子整合性分析 | 各主張に support / partial / weak / conflict が付いている |

## 9. リスクと対処

| リスク | 影響 | 対処 |
|---|---|---|
| BTC 条件付きサンプルが小さい | エッジ候補を強く言えない | `n`、bootstrap、期間分割を前面に出す |
| コストでエッジが消える | 記事の見栄えが弱くなる | それ自体を「壊れる条件」として使う |
| USDJPY の手法差が小さい | error on error の説明が弱くなる | rolling VaR、DD倍率、レバレッジ上限に重点を移す |
| 図表が多すぎる | 記事が散漫になる | 本文3-5枚、補足CSVに分離する |
| 記事骨子より結果が弱い | 主張過剰になる | 骨子側の表現を弱める修正文案を出す |

## 10. 完了条件

本計画の完了条件は以下。

- `outputs/report/lab_10_experiment_report.md` が存在する。
- `outputs/report/article_outline_alignment.md` が存在する。
- `outputs/tables/fragility_matrix.csv` が存在する。
- 記事に使う図表候補が選定されている。
- `Funding low x risk-on` をエッジ証明として扱っていない。
- 記事骨子との合致、不一致、追加説明が必要な点が明示されている。
- 最終結論が「正しい未来分布を当てる」ではなく「壊れる条件を探し、運用ルールへ変える」に着地している。
