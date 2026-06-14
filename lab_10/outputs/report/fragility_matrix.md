# BTC Fragility Matrix

## 日本語要約

この記事ではBTCのみを扱う。したがって、このFragility Matrixも `BTC crash edge candidate` の行だけに絞っている。

主役は `Funding low x risk-on` というBTC急落後の反発候補である。ただし、目的はエッジの証明ではない。サンプル数、コスト、約定、crash定義、risk-on proxy、Funding閾値、期間、MAE/DD/レバレッジを動かしたときに、候補がどこで壊れるかを見る。

## Status Counts

| fragility_status | count |
| --- | --- |
| broken | 3 |
| fragile | 5 |
| watch | 1 |

## Matrix

| fragility_source | stress_case | metric | baseline_value | stressed_value | fragility_status | practical_response |
| --- | --- | --- | --- | --- | --- | --- |
| sample_size | Bootstrap, 48h Funding low x risk-on | bootstrap mean return 5% lower bound | 1.115% | -0.380% | fragile | Lead with sample size and uncertainty before mentioning PF. |
| cost | 48h cost x5 | mean_ret_pct / PF | 1.115% / PF 2.073 | 0.615% / PF 1.524 | fragile | Set cost ceilings and report net results. |
| execution | 48h entry delayed by 4H | mean_ret_pct / PF | 1.115% / PF 2.073 | 0.475% / PF 1.324 | fragile | Require entry-delay tolerance before treating the signal as usable. |
| crash_definition | 48h full-sample lower 2.5% | mean_ret_pct / PF | 1.115% / PF 2.073 | -1.082% / PF 0.666 | broken | Publish definition robustness before naming a condition buyable. |
| risk_env_definition | 48h S&P500 5D up | mean_ret_pct / PF | 1.115% / PF 2.073 | 0.811% / PF 1.616 | fragile | Use multiple risk-on proxies and avoid causal wording. |
| funding_definition | 48h Funding negative only | n / mean_ret_pct | n=15, mean 1.115% | n=13, mean 1.386% | fragile | Report Funding definitions side by side. |
| subperiod | 48h 2022 stress period | mean_ret_pct / PF | 1.115% / PF 2.073 | -0.789% / PF 0.505 | broken | Use period splits to weaken or qualify public claims. |
| mae_dd_leverage | 48h 3x leverage | worst_mae_pct | -9.426% | -28.277% | watch | Define leverage caps and forced-reduction rules from MAE/DD. |
| avoid_condition | 48h Funding high x risk-off | mean_ret_pct / PF | All crashes 0.603% / PF 1.368 | High funding x risk-off -0.100% / PF 0.935 | broken | Use high-funding/risk-off as an avoid or size-reduction condition. |

## Interpretation

- `Funding low x risk-on` は、平均リターンとPFだけを見ると面白い候補に見える。
- しかし、主条件は `n=15` と小さく、bootstrap下限も0を下回るため、強い主張はできない。
- `full_sample_q025` や2022ストレス期では壊れるため、定義依存・期間依存を記事本文で必ず示す。
- `Funding high x risk-off` は、買える急落ではなく避ける急落候補として使いやすい。
- 記事の結論は「BTC急落は買い」ではなく、「エッジ候補にも error on error があり、壊れる条件を先に調べるべき」である。
