# lab_12: Portfolio Diversification, Covariance, and Fat-Tail Risk

日本語: [README.ja.md](README.ja.md)

This lab supports the Japanese Qiita article "[「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク](https://qiita.com/tikeda123/items/125802e6ed4468c7037e)".

It uses small synthetic-data experiments to show why the number of holdings alone does not determine diversification, why correlation changes across regimes, why variance estimates become unstable under fat tails, and why low Pearson correlation can coexist with severe joint downside risk.

This is an educational quant-article experiment. It is not investment advice, not a live trading signal, and not a production portfolio-construction system.

## Layout

| Type | Path |
|---|---|
| Published article | [「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク](https://qiita.com/tikeda123/items/125802e6ed4468c7037e) |
| Article source | `分散したつもりの罠_qiita.md` |
| Experiment scripts | `exp1_n_vs_correlation.py` through `exp5_fat_tail_strategies.py` |
| Generated figures | `figs/` |

## Data Dependencies

No external market data is required. All five scripts generate synthetic data internally. Random-number seeds are fixed so that the article values can be reproduced.

## Experiments

| Experiment | File | Question |
|---|---|---|
| Number of assets vs. common correlation | `exp1_n_vs_correlation.py` | How much risk remains when the number of equally weighted assets increases but common correlation stays positive? |
| Regime-dependent correlation | `exp2_regime_correlation.py` | How different are full-sample, normal-day, upside, and downside correlations? |
| Sample-variance stability | `exp3_sample_variance_stability.py` | How quickly does sample volatility stabilize under Normal and Student-t tails? |
| Low correlation vs. tail dependence | `exp4_tail_dependence.py` | Can two return pairs share similar second moments but have very different joint crashes? |
| Same mean and volatility, different loss shape | `exp5_fat_tail_strategies.py` | What changes when two strategies have the same arithmetic mean, volatility, and Sharpe but different tails? |

## Environment

Required Python packages:

```text
numpy
pandas
scipy
matplotlib
```

The charts use `Noto Sans CJK JP` for Japanese labels. Install that font, or change `plt.rcParams["font.family"]` in the scripts to another Japanese-capable font available in your environment.

## Reproduce

From the repository root:

```bash
python3 lab_12/exp1_n_vs_correlation.py
python3 lab_12/exp2_regime_correlation.py
python3 lab_12/exp3_sample_variance_stability.py
python3 lab_12/exp4_tail_dependence.py
python3 lab_12/exp5_fat_tail_strategies.py
```

Each script is independent. The scripts print their numerical summaries to standard output and write the article figures to `lab_12/figs/`.

## Main Outputs

| File | Description |
|---|---|
| `figs/fig1_n_vs_rho.png` | Portfolio volatility by number of assets and common correlation |
| `figs/fig2_regime_corr.png` | Full-sample, central-80%, and downside correlation matrices |
| `figs/fig3_sample_var.png` | Sample-standard-deviation convergence under Normal and Student-t distributions |
| `figs/fig4_tail_dependence.png` | Synthetic joint-crash data versus a matched bivariate Normal sample |
| `figs/fig4b_estimation_instability.png` | Sampling instability of the empirical 1% lower-tail dependence estimate |
| `figs/fig5_fat_tail_strategies.png` | Equity curves and return distributions for symmetric and short-volatility-style strategies |

## Key Results

- With common correlation `rho = 0.5`, increasing the asset count from 10 to 100 only lowers annualized volatility from 14.83% to 14.21% when each asset has 20% volatility.
- In the regime-switching example, average pairwise correlation is 0.36 for the full sample, -0.05 in the central 80% of market-return days, and 0.63 on the bottom 10% of days.
- A single -15% observation raises the estimated annualized volatility of a 1,000-day low-volatility sample from 4.71% to 8.88%.
- The tail-dependence experiment produces similar Pearson correlation and portfolio volatility in two samples, but worst portfolio days of -41.69% and -6.96%.
- The two strategy samples in Experiment 5 have the same realized arithmetic mean, sample volatility, and zero-rate Sharpe. Their maximum-drawdown paths remain different: the worst day accounts for 10.5% versus 50.8% of peak-to-trough log loss.

## Interpretation Notes

- The experiments isolate specific mechanisms. They are not calibrated forecasts of real markets.
- Conditional-correlation estimates are affected by selection bias; compare upside and downside conditions rather than reading downside correlation alone.
- Student-t with `nu = 3` has finite variance, so sample standard deviation is consistent, but convergence is slower and less regular than under a Normal distribution.
- Empirical tail-dependence estimates use very few observations at deep thresholds and should not be treated as stable optimization inputs.
- Experiment 5 matches realized arithmetic means, not compound annual returns. Geometric returns can differ because the return distributions differ.
