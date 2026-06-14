# lab_10 Phase 0-2 実行サマリー

実行日: 2026-06-14

## 実行範囲

本サマリーは、`EXPERIMENT_PLAN.ja.md` の Phase 0 から Phase 2 までを対象にする。

記事ではBTCのみを扱う。Phase 1のUSDJPY診断は内部検討ログとして保持するが、記事本文・記事用図表・骨子整合性分析には使わない。

| Phase | 内容 | 状態 |
|---|---|---|
| Phase 0 | `lab_7` ベースライン再現 | 完了 |
| Phase 1 | USDJPY リスク推定診断 | 完了 |
| Phase 2 | BTC 急落エッジ候補の Fragility 検証 | 完了 |

使用Python:

```bash
/Users/toikeda/miniconda3/bin/python
```

## Phase 0: lab_7 ベースライン再現

実行コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
```

確認結果:

- `lab_10/outputs/lab7_interaction_model_base/` にベースライン出力を再生成した。
- 主要CSVは `lab_10/reference/lab_7/outputs/interaction_model/` の参照コピーと差分なし。
- 以後のBTC実験は、元の `lab_7` と同じ基準線から開始できる。

## Phase 1: USDJPY リスク推定診断

実行コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/01_usdjpy_risk_diagnostics.py
```

主な出力:

| ファイル | 内容 |
|---|---|
| `outputs/tables/usdjpy_risk_summary.csv` | 窓別のVaR/ES/DD比較 |
| `outputs/tables/usdjpy_rolling_var.csv` | rolling VaR/ES |
| `outputs/tables/usdjpy_stress_dials.csv` | ボラ、コスト、平均劣化ストレス |
| `outputs/tables/usdjpy_dd_capital_table.csv` | DD倍率と必要資本 |
| `outputs/tables/usdjpy_leverage_limits.csv` | DD倍率別レバレッジ上限 |
| `outputs/report/usdjpy_risk_diagnostics.md` | USDJPY実験レポート |
| `outputs/figures/usdjpy_risk_method_comparison.png` | リスク手法比較図 |
| `outputs/figures/usdjpy_rolling_var.png` | rolling VaR/ES図 |

主要結果:

| 窓 | n | Hist VaR 99% | Hist ES 99% | Normal VaR 99% | Student-t VaR 99% | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 1y | 1,611 | -0.546% | -0.920% | -0.465% | -0.749% | -4.209% |
| 3y | 4,830 | -0.654% | -1.038% | -0.548% | -0.854% | -13.614% |
| 5y | 8,055 | -0.694% | -1.154% | -0.578% | -0.871% | -15.920% |
| full | 25,853 | -0.641% | -0.976% | -0.538% | -0.828% | -20.529% |

読み方:

- 同じUSDJPYでも、窓幅と手法でリスク推定値が動く。
- 正規VaRは、ヒストリカルESやStudent-t VaRより薄い左尾を出しやすい。
- 最大DDは全期間で `-20.529%` だが、これは将来上限ではなく疑うための基準線である。
- 5年窓のHist ES 99%は `-1.154%` と、この実験では最も厳しい4H左尾推定になった。

内部検討上の位置づけ:

- USDJPY診断は、リスク推定が手法・窓幅・DD倍率で揺れることを確認する内部ログである。
- 記事本文では使わない。
- USDJPYの将来リスクを当てた、という表現は避ける。

## Phase 2: BTC 急落エッジ候補の Fragility 検証

実行コマンド:

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
```

主な出力:

| ファイル | 内容 |
|---|---|
| `outputs/tables/btc_crash_baseline.csv` | BTC急落ベースライン |
| `outputs/tables/btc_cost_stress.csv` | コストストレス |
| `outputs/tables/btc_entry_execution_stress.csv` | 約定遅延・不利約定ストレス |
| `outputs/tables/btc_definition_robustness.csv` | crash定義ロバスト性 |
| `outputs/tables/btc_risk_env_robustness.csv` | risk-on定義ロバスト性 |
| `outputs/tables/btc_funding_definition_robustness.csv` | Funding定義ロバスト性 |
| `outputs/tables/btc_subperiod_results.csv` | 期間分割 |
| `outputs/tables/btc_walk_forward.csv` | walk-forward |
| `outputs/tables/btc_mae_dd_stress.csv` | stop/MAE/DDストレス |
| `outputs/tables/btc_leverage_tolerance.csv` | レバレッジ耐性 |
| `outputs/tables/btc_bootstrap_uncertainty.csv` | bootstrap不確実性 |
| `outputs/report/btc_crash_fragility.md` | BTC実験レポート |

ベースライン主要結果:

| horizon | group | n | mean | PF | mean MAE | worst MAE | MaxDD | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 24h | all crashes | 201 | +0.341% | 1.260 | -3.727% | -36.617% | -30.823% | watch |
| 24h | Funding low x risk-on | 15 | +1.297% | 3.122 | -2.651% | -9.426% | -3.470% | fragile |
| 24h | Funding high x risk-off | 26 | -0.242% | 0.837 | -4.330% | -12.258% | -19.250% | broken |
| 48h | all crashes | 201 | +0.603% | 1.368 | -4.716% | -36.617% | -42.441% | watch |
| 48h | Funding low x risk-on | 15 | +1.115% | 2.073 | -3.249% | -9.426% | -6.181% | fragile |
| 48h | Funding high x risk-off | 26 | -0.100% | 0.935 | -5.347% | -13.622% | -18.777% | broken |

bootstrap:

| horizon | n | mean 5% | mean 50% | mean 95% | PF 5% | PF 50% | PF 95% | fragile |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 24h | 15 | -0.057% | +1.247% | +2.781% | 0.940 | 3.126 | 13.946 | true |
| 48h | 15 | -0.380% | +1.155% | +2.479% | 0.798 | 2.135 | 8.714 | true |

読み方:

- `Funding low x risk-on` は平均・PFだけ見ると面白い候補に見える。
- ただし主条件は `n=15` しかなく、bootstrapの5%下限は24h/48hとも0を下回る。
- したがって、この条件は「有効戦略」ではなく「壊れる条件を調べる候補」として扱うべきである。
- `Funding high x risk-off` は24h/48hで平均とPFが弱く、避ける急落候補として比較対象にしやすい。
- 全急落を買うケースはMaxDDが大きく、左尾・DDの説明に使える。

記事骨子との関係:

- 「エッジ候補にも error on error がある」を支える。
- 「平均リターンではなく、コスト、定義、期間、約定、MAE/DDで壊れる条件を見る」という記事骨子に合う。
- `Funding low x risk-on` を強く言いすぎると骨子から外れるため、必ず `n=15` とbootstrap下限を併記する。

## Phase 0-2時点の暫定結論

Phase 0-2の結果は、記事骨子とおおむね合致している。

特に合致している点:

- BTC実験は、一見よいエッジ候補でも小標本・コスト・定義・期間で不安定になることを示している。
- BTCだけでも「正しい未来分布を当てる」より「壊れる前提を探す」という記事の方向に合う。

注意点:

- BTCの主条件は魅力的に見えるが、`n=15` のため主張は弱める必要がある。
- Phase 3以降では、Fragility Matrixにより「壊れる条件」と「実務対応」を明確に対応付ける必要がある。
- Phase 4以降の統合レポートでは、成功例よりも制約と疑いのダイヤルを前面に出すべきである。
