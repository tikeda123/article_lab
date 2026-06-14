# Article Alignment Report

Source article: https://qiita.com/tikeda123/items/091519af64bd22367c2d

## Purpose

This report checks whether the lab_10 outputs support the published article. The answer is yes: the outputs now focus on the BTC `Funding low x risk-on` candidate and the assumptions that make it fragile.

## Alignment Table

| article_section | experiment_support | status |
| --- | --- | --- |
| 8 まず見るべきは平均ではなくn | 48h Funding low x risk-on is n=15. | support |
| 9 error on error | 48h bootstrap mean 5% lower bound is -0.380%; 24h is -0.057%. | support |
| 10 crash定義を動かす | 48h full_sample_q025 changes mean to -1.082% and PF to 0.666. | support |
| 11 期間・コスト・約定・レバレッジ | 2022 stress is negative; cost_x5 and delay_4h compress the estimate; 3x MAE reaches -28.277%. | support |
| 12 Fragility Matrix | 7 rows map breakable assumptions to practical responses. | support |
| 14 避けるべき誤解 | Baseline and stress results support weaker wording: candidate, not proven strategy. | support |

## Key Metrics

| topic | value | article_role |
| --- | --- | --- |
| 48h Funding low x risk-on baseline | n=15, mean 1.115%, PF 2.073 | 面白い候補だが結論ではない基準線 |
| 24h Funding low x risk-on baseline | n=15, mean 1.297%, PF 3.122 | 24hでも小標本制約は同じ |
| 48h bootstrap lower bound | mean 5% -0.380% | error on errorの中心証拠 |
| 24h bootstrap lower bound | mean 5% -0.057% | 24hでも下限は0を下回る |
| Crash definition stress | full_sample_q025 mean -1.082%, PF 0.666 | 急落定義を動かすと候補が壊れる |
| 2022 stress period | n=4, mean -0.789%, PF 0.505 | レジーム依存を示す |
| 48h Funding high x risk-off | mean -0.100%, PF 0.935 | 避ける急落候補 |
| 48h all crashes | MaxDD -42.441% | 一律の急落買いは左尾・DDが重い |

## Remaining Guardrails

- Do not call `Funding low x risk-on` a proven edge.
- Do not describe Nasdaq or S&P500 as direct BTC predictors.
- Keep `n=15` and bootstrap lower bounds near the first mention of the candidate.
- Treat the Fragility Matrix as a conversion table from weak assumptions to operating rules, not as proof of profitability.
