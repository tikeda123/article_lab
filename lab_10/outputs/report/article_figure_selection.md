# BTC-Only Article Figure Selection

## Selection Rule

記事ではBTCのみを扱うため、USDJPY図は本文・補足の候補から外す。

## Recommended Figures

| priority | figure | use | article_section | include |
| --- | --- | --- | --- | --- |
| 1 | btc_bootstrap_mean_return.png | Show that the attractive candidate has small-sample uncertainty. | 標本誤差とerror on error | yes |
| 2 | btc_definition_robustness_heatmap.png | Show that changing crash definitions can break the candidate. | 定義を動かすと何が壊れるか | yes |
| 3 | btc_cost_stress_heatmap.png | Show gross-to-net fragility under cost assumptions. | コストでエッジは残るか | yes |
| 4 | btc_entry_execution_stress.png | Show that execution timing is part of the risk model. | 約定前提を疑う | optional |
| 5 | btc_risk_env_robustness.png | Show risk-on proxy sensitivity. | 外部リスク環境は文脈変数 | appendix |
| 6 | btc_funding_definition_robustness.png | Show Funding threshold sensitivity. | Funding閾値の主観性 | appendix |
| 7 | btc_leverage_tolerance.png | Show leveraged path-risk sensitivity. | MAE/DDとレバレッジ耐性 | appendix |
| 8 | fragility_matrix_status.png | Summarize BTC broken/fragile/watch counts. | Fragility Matrix | appendix |

## Suggested Body Set

本文ではまず以下の3枚に絞る。

1. `outputs/figures/btc_bootstrap_mean_return.png`
2. `outputs/figures/btc_definition_robustness_heatmap.png`
3. `outputs/figures/btc_cost_stress_heatmap.png`

記事が長くなる場合のみ、`btc_entry_execution_stress.png` を追加する。
