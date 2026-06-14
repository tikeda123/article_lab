# BTC-Only Article Outline Alignment

## 日本語要約

この記事ではBTCのみを扱う。USDJPYは本文には出さない。

BTCのみでも、記事骨子の中心主張は成立する。むしろ `Funding low x risk-on` という一見よい候補が、サンプル数・bootstrap・定義変更・期間分割で脆さを見せるため、`error on error` の説明としてはBTCに絞った方が読みやすい。

## Alignment Table

| article_claim | evidence | judgment | article_handling | revision_needed |
| --- | --- | --- | --- | --- |
| BTC急落は一律に買えるわけではない | All crashes 48h MaxDD is -42.441%; Funding high x risk-off 48h mean is -0.100%. | support | Use classification framing instead of universal dip-buying. | Avoid any headline that reads as BTC crash buy signal. |
| `Funding low x risk-on` は候補だが証明ではない | 48h mean is 1.115% with PF 2.073, but n=15. | support | Present it as a candidate to stress, not as an edge conclusion. | Place n=15 next to the first mention of the candidate. |
| エッジ候補にも error on error がある | Bootstrap 48h mean 5% lower bound is -0.380%. | support | Use bootstrap uncertainty as the clearest empirical expression of error-on-error. | Do not lead with PF; lead with estimate uncertainty. |
| 定義を変えると候補は壊れ得る | 48h full-sample lower 2.5% mean is -1.082% with PF 0.666. | support | Use the crash-definition heatmap in the body. | Add a sentence that crash definition is a subjective stress dial. |
| 期間分割でレジーム依存を見る必要がある | 2022 stress-period 48h mean is -0.789% with n=4. | support | Use the 2022 slice as a warning against smooth all-period conclusions. | Do not claim the candidate is stable across regimes. |
| 外部市場はBTCの直接予測ではなく文脈変数である | Risk-on proxy changes the estimate in robustness tables. | support | Use external risk-on/off as classification context. | Remove or soften any sentence saying Nasdaq predicts BTC. |
| 分析は運用ルールへ変換する | 9 BTC matrix rows map assumptions to practical responses. | support | Use the BTC Fragility Matrix as the final practical section. | Add responses such as cost ceilings, entry-delay tolerance, leverage caps, and avoid-condition filters. |

## Overall Judgment

BTC-only構成で問題ない。記事の主張は、次の形に絞る。

> BTC急落の `Funding low x risk-on` は面白い候補に見える。しかし、`n=15`、bootstrap下限、定義依存、期間依存を考えると、これを有効戦略とは言えない。重要なのは、候補が壊れる条件を先に見つけることである。
