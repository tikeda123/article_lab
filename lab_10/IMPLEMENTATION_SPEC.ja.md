# lab_10 実装仕様: Published BTC Article Support

## 1. 目的

`lab_10` は、公開済み記事を支えるBTC-only実験パッケージである。

- 記事URL: https://qiita.com/tikeda123/items/091519af64bd22367c2d
- 対象: BTC急落後の `Funding low x risk-on`
- 目的: 良さそうに見える推定値がどの前提で壊れるかを診断する
- 非目的: 売買戦略の証明、BTC急落買いの推奨、外部市場によるBTC予測

## 2. ディレクトリ構成

```text
lab_10/
  data/lab_7/                         # lab_7からコピーしたBTC、Funding、外部市場データ
  reference/lab_7/                    # lab_7のREADME、コード、参照出力
  scripts/
    00_lab7_interaction_model_base.py # lab_7 baseline reproduction
    02_btc_crash_fragility.py         # BTC fragility diagnostics
    03_fragility_matrix.py            # article support matrix and reports
  outputs/
    tables/                           # BTC-only CSV outputs
    figures/                          # BTC-only figures
    report/                           # BTC-only reports
  article_materials_btc_minimal_ai/   # 生成AIに渡す最小5ファイル
  article_materials_btc_only/         # 執筆・検証用のBTC-only材料一式
```

## 3. 実行順序

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

## 4. Script 00: lab_7 baseline reproduction

### 入力

- `data/lab_7/BTCUSD240.csv`
- `data/lab_7/funding_rate_history.csv`
- `data/lab_7/USATECHIDXUSD240.csv`
- `data/lab_7/USA500IDXUSD240.csv`
- `data/lab_7/USA30IDXUSD240.csv`
- `data/lab_7/DEUIDXEUR240.csv`

### 出力

- `outputs/lab7_interaction_model_base/interaction_feature_panel.csv`
- `outputs/lab7_interaction_model_base/interaction_group_stats.csv`
- `outputs/lab7_interaction_model_base/interaction_contrasts.csv`
- `outputs/lab7_interaction_model_base/interaction_model_report.md`

### 記事での位置づけ

前回記事の条件分類を再現するための基準線である。ここでの `Funding low x risk-on` は、証明済みエッジではなく、後続のfragility診断で壊してみる候補である。

## 5. Script 02: BTC fragility diagnostics

### 主条件

| 項目 | 定義 |
|---|---|
| 時間足 | BTC 4H |
| 基準急落 | rolling 180本 sigma score `<= -2.0` |
| 基準risk-on | Nasdaq 5D return > 0 |
| 基準Funding low | lower 20% or negative |
| エントリー | 急落シグナル後の次4H open |
| 決済 | 24h, 48h, 5d |
| 評価 | open-to-open log return |

### 出力CSV

| ファイル | 内容 | 記事対応 |
|---|---|---|
| `btc_crash_baseline.csv` | 全急落、low funding x risk-on、high funding x risk-offの基準線 | 第8章、結論 |
| `btc_bootstrap_uncertainty.csv` | event-level bootstrap | 第9章 |
| `btc_definition_robustness.csv` | rolling sigma / full-sample quantileの急落定義変更 | 第10章 |
| `btc_subperiod_results.csv` | 2020-21, 2022, 2023-24, 2025-26など | 第11章 |
| `btc_cost_stress.csv` | gross, base, cost x2, cost x5 | 第11章 |
| `btc_entry_execution_stress.csv` | 4H/8H遅延、不利約定 | 第11章 |
| `btc_leverage_tolerance.csv` | 1x, 2x, 3xのMAE/DD | 第11章 |
| `btc_risk_env_robustness.csv` | Nasdaq, S&P500, broad proxy | 第12章 |
| `btc_funding_definition_robustness.csv` | Funding閾値変更 | 補足 |
| `btc_mae_dd_stress.csv` | stop/MAE/DD stress | 補足 |
| `btc_walk_forward.csv` | walk-forward補助確認 | 補足 |

### 出力図

| ファイル | 記事での役割 |
|---|---|
| `btc_bootstrap_mean_return.png` | 小標本とbootstrap下限 |
| `btc_definition_robustness_heatmap.png` | crash定義による符号反転 |
| `btc_cost_stress_heatmap.png` | コストでの圧縮 |
| `btc_entry_execution_stress.png` | 約定遅延 |
| `btc_leverage_tolerance.png` | レバレッジ時の経路損失 |
| `btc_risk_env_robustness.png` | risk-on proxy依存 |
| `btc_funding_definition_robustness.png` | Funding閾値依存 |

## 6. Script 03: Article support matrix

### 生成する表

| ファイル | 内容 |
|---|---|
| `outputs/tables/fragility_matrix.csv` | 公開記事第12章に対応する7行Matrix |
| `outputs/tables/article_key_metrics.csv` | 記事内で引用する主要数値 |

### Fragility Matrixの行

| 壊れる前提 | ストレス | 状態 |
|---|---|---|
| 小標本でも平均が安定 | 48h bootstrap `+1.115% -> -0.380%` | fragile |
| 急落定義に依存しない | 48h full_sample_q025 `+1.115% -> -1.082%` | broken |
| 特定レジームだけでない | 2022 stress `+1.115% -> -0.789%` | broken |
| コスト後も残る | cost x5 PF `2.073 -> 1.524` | fragile |
| 想定通り約定できる | 4H delay PF `2.073 -> 1.324` | fragile |
| 含み損に耐えられる | 3x worst MAE `-9.426% -> -28.277%` | watch |
| proxyは1つで十分 | S&P500 proxy PF `2.073 -> 1.616` | fragile |

### 生成するレポート

| ファイル | 目的 |
|---|---|
| `outputs/report/lab_10_experiment_report.md` | 記事根拠としての統合レポート |
| `outputs/report/article_outline_alignment.md` | 公開記事第8〜14章との対応表 |
| `outputs/report/fragility_matrix.md` | Matrixの説明 |
| `outputs/report/article_figure_selection.md` | 図表選定 |

## 7. 生成AIに渡す最小パッケージ

`article_materials_btc_minimal_ai/` は5ファイルだけにする。

| ファイル | 用途 |
|---|---|
| `01_ANALYZE_THIS.ja.md` | 依頼文、主要数値、禁止表現 |
| `02_fragility_matrix.csv` | 壊れる条件と実務対応 |
| `03_bootstrap_uncertainty.png` | 第9章の図 |
| `04_crash_definition_robustness.png` | 第10章の図 |
| `05_cost_stress.png` | 第11章の図 |

## 8. 検証

```bash
/Users/toikeda/miniconda3/bin/python -m py_compile \
  lab_10/scripts/00_lab7_interaction_model_base.py \
  lab_10/scripts/02_btc_crash_fragility.py \
  lab_10/scripts/03_fragility_matrix.py
```

## 9. 表現ルール

使う:

> `Funding low x risk-on` は面白い候補だが、`n=15`、bootstrap下限、定義変更、期間分割、コスト、約定、レバレッジを見ると、有効戦略とはまだ言えない。

避ける:

- BTC急落は買い。
- `Funding low x risk-on` は有効戦略。
- NasdaqがBTCを直接予測する。
- Fragility Matrixでエッジが証明された。
