# lab_8: BTC急落エッジ候補のモンテカルロ検証

English: [README.md](README.md)

このラボは、`実験設計ドキュメント.pdf` の内容に対応する実験実装である。`lab_7` で見つけた「BTC急落 x Funding低位 x 外部Risk-on環境」の候補について、平均リターンやProfit Factorだけでなく、モンテカルロによって最大ドローダウン、30%/50%DD到達確率、資金半減確率、レバレッジ耐性、コスト耐性を確認する。

このラボは投資助言ではなく、本番運用可能な売買システムでもない。記事用の根拠を再現可能な形で確認するための教育用診断パッケージである。

## 完結性

`lab_8` の実験はこのディレクトリ内だけで完結する。

| 種類 | 場所 |
|---|---|
| 実験設計 | `実験設計ドキュメント.pdf` |
| 入力データ | `data/` |
| 実験コード | `run_monte_carlo_experiment.py` |
| 依存メモ | `requirements.txt` |
| 正本出力 | `outputs/monte_carlo/` |

スクリプトは他の `lab_xxx` のPythonファイルをimportしない。入力も `lab_8/data/` だけを読む。

## 比較群

| ID | グループ名 | 条件 |
|---|---|---|
| G0 | `G0_all_crashes` | Funding取得済みの全BTC急落 |
| G1 | `G1_funding_low` | Funding低位またはマイナス |
| G2 | `G2_risk_on` | Nasdaq 5日リターンがプラス |
| G3 | `G3_funding_low_x_risk_on` | Funding低位 x Risk-on |
| G4 | `G4_avoid_high_funding_risk_off` | 全急落からFunding高位 x Risk-offを除外 |
| G5 | `G5_high_funding_x_risk_off` | Funding高位 x Risk-off |

## 実験内容

実装済みのモンテカルロ手法は以下である。

| 手法 | 内容 |
|---|---|
| `original_order` | 実際の順番で資金曲線を作る |
| `shuffle` | 同じ損益を重複なしで並べ替える |
| `iid_bootstrap` | 損益を重複ありで再抽出する |
| `block_bootstrap` | 固定長ブロックで再抽出する |
| `stationary_bootstrap` | ランダム長ブロックで再抽出する |
| `regime_aware_bootstrap` | 年・Risk-on/off・Funding区分ごとに再抽出する |

実験メニューは設計書に沿って、全急落 vs 条件付きフィルター、G3の少数サンプル問題、24h本命セル vs 48h Risk-on、避けるフィルター、レバレッジ感応度、コスト感応度を出力する。

## 入力データ

| ファイル | 内容 |
|---|---|
| `data/BTCUSD240.csv` | BTC 240分足OHLCV |
| `data/USATECHIDXUSD240.csv` | Nasdaq 240分足OHLCV |
| `data/USA500IDXUSD240.csv` | S&P 500 240分足OHLCV |
| `data/USA30IDXUSD240.csv` | Dow 240分足OHLCV |
| `data/DEUIDXEUR240.csv` | DAX 240分足OHLCV |
| `data/funding_rate_history.csv` | Funding Rate履歴。実験ではBTCUSDTだけを使う |

## 実験環境

必要な外部パッケージは以下だけである。

```text
numpy
pandas
```

PNG図表生成はこの実装には含めていないため、`matplotlib` は不要である。

## 再現コマンド

リポジトリルートから実行する。

```bash
python3 lab_8/run_monte_carlo_experiment.py
```

シミュレーション本数を変える場合:

```bash
python3 lab_8/run_monte_carlo_experiment.py --n-sims 10000 --seed 20260609
```

## 主な出力

| ファイル | 内容 |
|---|---|
| `outputs/monte_carlo/data_profile.csv` | 入力データの行数・期間確認 |
| `outputs/monte_carlo/feature_panel.csv` | 急落、Funding、Risk-on、未来リターンを含む共通パネル |
| `outputs/monte_carlo/trade_events.csv` | cooldown後かつFunding取得済みの急落イベント |
| `outputs/monte_carlo/original_trade_metrics.csv` | 実順序の取引指標 |
| `outputs/monte_carlo/monte_carlo_summary.csv` | 主モンテカルロ手法の集計 |
| `outputs/monte_carlo/experiment1_group_comparison.csv` | 全急落 vs 条件フィルター |
| `outputs/monte_carlo/experiment2_small_sample_iid.csv` | G3少数サンプル問題 |
| `outputs/monte_carlo/experiment3_horizon_tradeoff.csv` | 24h本命セル vs 48h Risk-on |
| `outputs/monte_carlo/experiment4_avoid_filter_effect.csv` | Funding高位 x Risk-off除外効果 |
| `outputs/monte_carlo/experiment5_leverage_sensitivity.csv` | レバレッジ感応度 |
| `outputs/monte_carlo/experiment6_cost_sensitivity.csv` | 片道コスト感応度 |
| `outputs/monte_carlo/figure_index.csv` | 生成SVG図表の一覧 |
| `outputs/monte_carlo/figures/*.svg` | 記事説明用のSVG図表 |
| `outputs/monte_carlo/monte_carlo_experiment_report.md` | 記事用の生成レポート |
| `outputs/monte_carlo/analysis_report.ja.md` | 実験主旨に沿った日本語の結果分析レポート |

## 図表

生成レポートには、説明に使いやすいように以下のSVG図表を埋め込んでいる。

| 図表 | 内容 |
|---|---|
| `figure01_iid_24h_final_return_q05.svg` | 24h i.i.d. bootstrapの最終リターン下位5% |
| `figure02_iid_24h_mdd_q05.svg` | 24h i.i.d. bootstrapの最大DD下位5% |
| `figure03_g3_method_mdd_q05.svg` | G3の手法別DDストレス |
| `figure04_horizon_tradeoff_final_return_q05.svg` | 24h本命セルと48h Risk-onの比較 |
| `figure05_leverage_prob_dd30.svg` | レバレッジ別30%DD到達確率 |
| `figure06_cost_prob_dd30.svg` | コスト別30%DD到達確率 |

## 解釈上の注意

- `G3_funding_low_x_risk_on` は15件しかないため、良い結果でも運用可能とは断定しない。
- コストは片道bpsとして指定し、各トレードから往復 `2 x one_way_cost_bps` を控除する。
- レバレッジはコスト控除後の単純リターンに掛ける。1トレードの損失が100%を超える場合は破産として扱う。
- モンテカルロは「エッジらしきものを取りに行ったときに生き残れるか」を見るための診断である。
