# BTC Fragility Matrix

Source article: https://qiita.com/tikeda123/items/091519af64bd22367c2d

## Purpose

This matrix is the experiment-side support for article sections 10-12. It does not prove a BTC edge. It converts the attractive-looking `Funding low x risk-on` candidate into break conditions and practical responses.

## Status Counts

| status | count |
| --- | --- |
| fragile | 4 |
| broken | 2 |
| watch | 1 |

## Matrix

| breakable_assumption | stress_case | metric | baseline_value | stressed_value | fragility_status | practical_response |
| --- | --- | --- | --- | --- | --- | --- |
| 小標本でも平均が安定 | 48h bootstrap | mean_ret_pct | 1.115% | -0.380% | fragile | 主張を弱め、サイズを落とす。 |
| 急落定義に依存しない | 48h full_sample_q025 | mean_ret_pct / PF | 1.115% / PF 2.073 | -1.082% / PF 0.666 | broken | 複数定義で確認し、定義ロバスト性を先に公開する。 |
| 特定レジームだけでない | 48h 2022 stress period | mean_ret_pct / PF | 1.115% / PF 2.073 | -0.789% / PF 0.505 | broken | 期間分割で主張を弱める、または限定する。 |
| コスト後も残る | 48h cost_x5 | mean_ret_pct / PF | 1.115% / PF 2.073 | 0.615% / PF 1.524 | fragile | コスト上限を設定し、ネットで報告する。 |
| 想定通り約定できる | 48h delay_4h | mean_ret_pct / PF | 1.115% / PF 2.073 | 0.475% / PF 1.324 | fragile | 約定遅延耐性を確認し、指値/成行ルールを再設計する。 |
| 含み損に耐えられる | 48h 3x leverage | worst_mae_pct | -9.426% | -28.277% | watch | MAE/DDからレバレッジ上限と強制縮小ルールを設計する。 |
| proxyは1つで十分 | 48h S&P500 5D up | mean_ret_pct / PF | 1.115% / PF 2.073 | 0.811% / PF 1.616 | fragile | risk-on proxyを複数化し、因果表現を避ける。 |

## Article Interpretation

- `Funding low x risk-on` is an interesting baseline, not a tradable conclusion.
- The article-supported evidence is strongest where the candidate breaks or becomes fragile: `n=15`, bootstrap lower bound below zero, crash-definition reversal, 2022 stress-period weakness, cost compression, execution delay, and levered MAE.
- External-market variables are risk-environment proxies. They must not be described as direct BTC predictors.
