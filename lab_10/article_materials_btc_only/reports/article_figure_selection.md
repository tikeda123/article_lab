# Article Figure Selection

Source article: https://qiita.com/tikeda123/items/091519af64bd22367c2d

## Recommended Figures

| priority | figure | article_section | role | include |
| --- | --- | --- | --- | --- |
| 1 | btc_bootstrap_mean_return.png | 9 error on error | Show small-sample uncertainty and negative bootstrap lower bounds. | body |
| 2 | btc_definition_robustness_heatmap.png | 10 crash definition | Show sign reversal under full_sample_q025. | body |
| 3 | btc_cost_stress_heatmap.png | 11 cost | Show gross-to-net compression under cost stress. | body |
| 4 | btc_entry_execution_stress.png | 11 execution | Show delay sensitivity. | appendix |
| 5 | btc_leverage_tolerance.png | 11 leverage | Show path-risk and levered MAE. | appendix |
| 6 | btc_risk_env_robustness.png | 12 risk proxy | Show proxy sensitivity without causal wording. | appendix |
| 7 | fragility_matrix_status.png | 12 Fragility Matrix | Summarize broken/fragile/watch counts. | appendix |

## Minimal Set For AI Review

Use only these files when asking another model to analyze the article:

1. `article_materials_btc_minimal_ai/01_ANALYZE_THIS.ja.md`
2. `article_materials_btc_minimal_ai/02_fragility_matrix.csv`
3. `article_materials_btc_minimal_ai/03_bootstrap_uncertainty.png`
4. `article_materials_btc_minimal_ai/04_crash_definition_robustness.png`
5. `article_materials_btc_minimal_ai/05_cost_stress.png`
