# article_lab: Quant Article Experiment Labs

Japanese: [README.ja.md](README.ja.md)

This repository stores reproducible experiment packages for quant and FX analysis articles. Each article or experiment is organized as a `lab_xxx` directory containing the source data, analysis code, generated figures, summary tables, and documentation needed to reproduce or inspect the article evidence.

The root README is an index. Detailed experiment goals, input data, reproduction commands, key outputs, results, and caveats are documented in each lab's own README.

## Learning Log and Feedback

These article labs also serve as a public learning log for ongoing quant and FX research. The code, data summaries, figures, and article notes are shared so that the assumptions and results can be inspected rather than treated as fixed conclusions.

Corrections, reproducibility checks, alternative interpretations, and new perspectives based on the published data or articles are welcome. When pointing out an issue, please refer to the relevant lab, script, output file, or article section where possible.

## Documentation Languages

The English documentation is the default entry point for GitHub and international readers.

| File | Role |
|---|---|
| `README.md` | English entry point |
| `README.ja.md` | Japanese documentation |
| `lab_xxx/README.md` | English lab documentation |
| `lab_xxx/README.ja.md` | Japanese lab documentation |

When updating a lab, keep the English and Japanese README files aligned on the experiment purpose, canonical outputs, reproduction commands, current results, and interpretation limits.

## Lab Expansion Policy

This repository is intended to grow by adding one `lab_xxx` directory per article or experiment.

Each lab should usually contain:

| Type | Content |
|---|---|
| `README.md` / `README.ja.md` | Canonical lab-level documentation |
| Input CSVs | Source data used for article validation |
| Python scripts | Analysis, figure generation, and article-summary generation code |
| Output directories | Reproducible CSV, Markdown, and PNG outputs |
| Article outlines | Draft article structure or text, when available |

The root README should not duplicate full experiment procedures. It should point readers to the relevant lab.

## Labs

| Lab | Topic | Input | English README | Japanese README | Main Output |
|---|---|---|---|---|---|
| `lab_1` | FX 240-minute moment analysis and edge exploration | USDJPY / EURUSD / AUDJPY 240-minute bars | [README](lab_1/README.md) | [日本語](lab_1/README.ja.md) | `lab_1/moment_analysis_outputs_2022plus/` |
| `lab_2` | Quantifying AUDJPY overbought and oversold conditions | AUDJPY 60-minute bars | [README](lab_2/README.md) | [日本語](lab_2/README.ja.md) | `lab_2/article_outputs/` |
| `lab_3` | FX Kelly criterion order risk management tool | No CSV; standalone HTML tool | [README](lab_3/README.md) | [日本語](lab_3/README.ja.md) | `lab_3/kelly_fx_position_size_tool.html` |
| `lab_4` | USDJPY 60-minute backtest overfitting and simplified PBO | USDJPY 60-minute bars | [README](lab_4/README.md) | [日本語](lab_4/README.ja.md) | `lab_4/results_summary.json`, `lab_4/figures/` |
| `lab_5` | USDJPY trend-following edge diagnostics | USDJPY 60-minute and 240-minute bars | [README](lab_5/README.md) | [日本語](lab_5/README.ja.md) | `lab_5/outputs/trend_following_ma_cross/`, `lab_5/outputs/article_figures/` |
| `lab_6` | BTC/ETH/SOL crypto crash-rebound diagnostics | BTCUSDT / ETHUSDT / SOLUSDT 240-minute bars | [README](lab_6/README.md) | [日本語](lab_6/README.ja.md) | `lab_6/outputs/crypto_crash_rebound_ohlcv/`, `lab_6/outputs/article_materials/` |

## lab_1 Summary

`lab_1` supports the Qiita article "[Quant Intro: Stop Predicting, Read the Distribution](https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf)".

The lab examines FX return distributions before attempting directional prediction. It compares moment statistics, skewness, kurtosis, extreme returns, mean reversion after tail events, and future returns by volatility regime across USDJPY, EURUSD, and AUDJPY 240-minute bars.

| Item | Content |
|---|---|
| Details | [lab_1/README.md](lab_1/README.md) |
| Script | `lab_1/run_moment_analysis_edge_experiments.py` |
| Input data | `USDJPY240.csv`, `EURUSD240.csv`, `AUDJPY240.csv` |
| Canonical output | `lab_1/moment_analysis_outputs_2022plus/` |
| Role | Edge-candidate exploration, not a finished trading strategy |

## lab_2 Summary

`lab_2` supports the Qiita article "[How Quant Traders Judge Overbought and Oversold Conditions](https://qiita.com/tikeda123/items/8dfcc1c09e34d5304d49)".

The lab converts subjective ideas such as "too low" or "too high" into a 24-hour VWAP deviation Z-score and a rolling percentile of the latest 1-hour return, then checks whether price actually rebounds after those conditions.

| Item | Content |
|---|---|
| Details | [lab_2/README.md](lab_2/README.md) |
| Script | `lab_2/audjpy_overbought_oversold_article_experiment.py` |
| Article outline | `lab_2/quant_overbought_oversold_article_outline.md` |
| Input data | `AUDJPY60.csv` |
| Canonical output | `lab_2/article_outputs/` |
| Role | Quantifying overbought/oversold conditions and observing rebound candidate zones |

## lab_3 Summary

`lab_3` supports the Qiita article "[Practical Math for Reducing FX Ruin Risk: Turning Kelly into Stop Width and Order Size](https://qiita.com/tikeda123/items/d5e16444da576c545c43)".

The lab provides a standalone educational HTML tool that translates the Kelly criterion into maximum acceptable loss, order size, stop width, pip value, and margin usage. It also includes a ruin-resilience simulator.

| Item | Content |
|---|---|
| Details | [lab_3/README.md](lab_3/README.md) |
| HTML tool | `lab_3/kelly_fx_position_size_tool.html` |
| Article outline | `lab_3/fx_kelly_article_outline_with_tools.md` |
| Input data | None |
| Canonical output | Standalone HTML tool |
| Role | Educational pre-order risk check tool |

## lab_4 Summary

`lab_4` supports the Qiita article "[AI Makes Edge Discovery Easy, But Is That Backtest Real? How to Check Backtest Overfitting with PBO](https://qiita.com/tikeda123/items/fd589372f78ffa4c48fb)".

The lab demonstrates how to inspect backtest overfitting risk in the AI-assisted strategy-search era. It uses USDJPY 60-minute data, generates 144 moving-average crossover strategy candidates, and evaluates whether the strategy selected in-sample remains competitive out-of-sample.

| Item | Content |
|---|---|
| Details | [lab_4/README.md](lab_4/README.md) |
| Article | [English](https://qiita.com/tikeda123/items/fd589372f78ffa4c48fb) / [Japanese](https://qiita.com/tikeda123/items/ab7070663e8e002e785f) |
| Script | `lab_4/run_backtest_overfitting_experiment.py` |
| Article outlines | `lab_4/ai_edge_backtest_overfitting_outline.md`, `lab_4/backtest_overfitting_experiment_outline.md` |
| Input data | External `USDJPY60(29).csv` in tab-separated OHLCV format |
| Canonical output | `lab_4/results_summary.json`, `lab_4/experiment_report.md`, `lab_4/figures/` |
| Role | Educational simplified CSCV/PBO overfitting-risk check, not a production strategy |

## lab_5 Summary

`lab_5` supports the Qiita article "[トレンドフォローにエッジはあるのか――「遅れて入る」戦略がなぜ生き残るのか](https://qiita.com/tikeda123/items/e599112d88c912a86125)" and its English version, [Does Trend Following Have an Edge? — Why a Strategy That "Enters Late" Survives](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2).

The lab uses simple MA 20/80 crossover rules on USDJPY 60-minute and 240-minute bars to inspect whether trend following produces a cost-adjusted, right-tail-dependent PnL structure, and whether that structure survives a fixed 2025 OOS check.

| Item | Content |
|---|---|
| Details | [lab_5/README.md](lab_5/README.md) |
| Japanese | [lab_5/README.ja.md](lab_5/README.ja.md) |
| Article | [Japanese](https://qiita.com/tikeda123/items/e599112d88c912a86125) / [Does Trend Following Have an Edge? — Why a Strategy That "Enters Late" Survives](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2) |
| Scripts | `lab_5/run_trend_following_experiment.py`, `lab_5/run_trend_following_direction_ablation.py`, `lab_5/save_article_figures.py` |
| Article notes | `lab_5/trend_following_edge_article_outline_improved.md`, `lab_5/trend_following_experiment_analysis_and_discussion.md` |
| Input data | `lab_5/USDJPY60.csv`, `lab_5/USDJPY240.csv` |
| Canonical output | `lab_5/outputs/trend_following_ma_cross/`, `lab_5/outputs/trend_following_direction_ablation/`, `lab_5/outputs/article_figures/` |
| Role | Trend-following structure and OOS-failure diagnostics, not a production strategy |

## lab_6 Summary

`lab_6` supports the Japanese Qiita article "[仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a)" and the BTC/ETH/SOL crypto crash-rebound article work in `lab_6/BTC_ETH_SOL_crypto_quant_article_plan.docx.md`.

The lab examines whether lower-tail crypto crashes are short-term rebound candidates, or whether some crashes should be treated as falling-knife conditions. It starts from BTCUSDT, ETHUSDT, and SOLUSDT 240-minute OHLCV, then adds volatility regimes, next-open entry path risk, annual stability, Funding Rate, Open Interest, and liquidation-data availability.

| Item | Content |
|---|---|
| Details | [lab_6/README.md](lab_6/README.md) |
| Japanese | [lab_6/README.ja.md](lab_6/README.ja.md) |
| Article | [仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a) |
| Script | `lab_6/run_crypto_crash_rebound_experiment.py` |
| Article notes | `lab_6/BTC_ETH_SOL_crypto_quant_article_plan.docx.md`, `lab_6/crypto_crash_rebound_experiment_plan.md` |
| Input data | `lab_6/BTCUSDT240.csv`, `lab_6/ETHUSDT240.csv`, `lab_6/SOLUSDT240.csv` |
| Canonical output | `lab_6/outputs/crypto_crash_rebound_ohlcv/`, `lab_6/outputs/article_materials/` |
| Role | Crash-rebound candidate diagnostics and market-structure limitations, not a production strategy |

## Usage

Start with the README for the lab you want to inspect.

```bash
sed -n '1,220p' lab_1/README.md
sed -n '1,220p' lab_2/README.md
sed -n '1,220p' lab_3/README.md
sed -n '1,220p' lab_4/README.md
sed -n '1,220p' lab_5/README.md
sed -n '1,220p' lab_6/README.md
```

Use the Japanese files when working directly with the Japanese Qiita article text.

```bash
sed -n '1,220p' lab_1/README.ja.md
sed -n '1,220p' lab_2/README.ja.md
sed -n '1,220p' lab_3/README.ja.md
sed -n '1,220p' lab_4/README.ja.md
sed -n '1,220p' lab_5/README.ja.md
sed -n '1,220p' lab_6/README.ja.md
```

For regeneration, use the commands documented in each lab README.

```bash
python lab_1/run_moment_analysis_edge_experiments.py
python lab_2/audjpy_overbought_oversold_article_experiment.py
```

`lab_3` is a standalone HTML tool. To inspect it through a local HTTP server:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open:

```text
http://127.0.0.1:8765/lab_3/kelly_fx_position_size_tool.html
```

For `lab_4`, provide the source USDJPY 60-minute CSV explicitly.

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_check
```

For `lab_5`, the input CSVs are included under `lab_5/`.

```bash
python lab_5/run_trend_following_experiment.py \
  --output-dir /tmp/lab5_trend_following_check
```

For `lab_6`, the input CSVs are included under `lab_6/`.

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --output-dir /tmp/lab6_crypto_crash_rebound_check
```

When experimenting, write to a temporary output directory instead of overwriting canonical outputs.

## Maintenance Policy

- Keep `README.md` as the English entry point.
- Keep `README.ja.md` as the Japanese companion documentation.
- Keep the root README focused on the index and lab list.
- Put experiment details, reproduction commands, current results, and caveats in each lab README.
- Store regenerable outputs in a dedicated output path inside each lab.
- Add new articles or experiments as `lab_7`, `lab_8`, and so on.
- Cite article numbers from canonical output CSV, JSON, or Markdown files, not from hand-written summaries alone.
