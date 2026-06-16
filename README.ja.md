# article_lab: クオンツ記事実験ラボ索引

English: [README.md](README.md)

このリポジトリは、クオンツ・FX分析記事に対応する実験コード、入力データ、図表、集計結果を `lab_xxx` 単位で管理するための作業場所である。

ルートの `README.md` は英語圏向けの入口、`README.ja.md` は日本語版の索引である。各実験の詳細な目的、入力データ、再現コマンド、主要出力、解釈上の注意点は、それぞれの `lab_xxx/README.md` と `lab_xxx/README.ja.md` を正本として扱う。

## 学習ログとフィードバック

このリポジトリに含まれる日々の記事・実験は、ある程度、私自身のクオンツ・FX分析の学習ログとしての役割も持っている。ここで公開しているコード、データ集計、図表、記事メモは、結論を固定するためではなく、前提や結果を後から検証できるようにするための材料である。

共有しているデータや記事の内容に基づいて、誤り、再現性の問題、別の解釈、または新しい視点があれば、指摘していただけるとありがたい。指摘する場合は、可能であれば対象の `lab_xxx`、スクリプト、出力ファイル、記事の該当箇所を添えてもらえると確認しやすい。

## ドキュメント言語方針

GitHubと英語圏ユーザー向けには英語版をデフォルト入口にする。日本語記事や日本語での作業文脈は `README.ja.md` に残す。

| ファイル | 役割 |
|---|---|
| `README.md` | 英語版の入口 |
| `README.ja.md` | 日本語版の入口 |
| `lab_xxx/README.md` | 各ラボの英語版README |
| `lab_xxx/README.ja.md` | 各ラボの日本語版README |

READMEを更新する場合は、英語版と日本語版の実験目的、正本出力、再現コマンド、現在結果、解釈上の注意点がずれないようにする。

## ラボ拡張方針

この `article_lab` は、記事ごと・実験ごとに `lab_xxx` 形式のサブディレクトリとして拡張していく前提で管理する。

各 `lab_xxx` には、原則として以下を置く。

| 種類 | 内容 |
|---|---|
| `README.md` / `README.ja.md` | 実験ラボ単位の正本説明 |
| 入力CSV | 記事検証に使う元データ |
| Pythonスクリプト | 集計・図表生成・記事用サマリ生成コード |
| 出力ディレクトリ | コードから再生成できるCSV、Markdown、PNG |
| 記事アウトライン | 記事構成案や本文草稿がある場合に配置 |

ルート README には詳細な実験手順を重複させず、どのラボを見ればよいかを示す。

## ラボ一覧

| ラボ | テーマ | 主な入力 | English | 日本語 | 主な出力 |
|---|---|---|---|---|---|
| `lab_1` | FX 240分足モーメント分析とエッジ探索 | USDJPY / EURUSD / AUDJPY 240分足 | [README](lab_1/README.md) | [日本語](lab_1/README.ja.md) | `lab_1/moment_analysis_outputs_2022plus/` |
| `lab_2` | AUDJPY 買われすぎ・売られすぎの定量化 | AUDJPY 60分足 | [README](lab_2/README.md) | [日本語](lab_2/README.ja.md) | `lab_2/article_outputs/` |
| `lab_3` | FX Kelly基準による注文リスク管理 | 入力CSVなし。単体HTMLツール | [README](lab_3/README.md) | [日本語](lab_3/README.ja.md) | `lab_3/kelly_fx_position_size_tool.html` |
| `lab_4` | USDJPY 60分足 バックテスト過学習・簡易PBO検証 | USDJPY 60分足 | [README](lab_4/README.md) | [日本語](lab_4/README.ja.md) | `lab_4/results_summary.json`, `lab_4/figures/` |
| `lab_5` | USDJPY トレンドフォロー・エッジ診断 | USDJPY 60分足・240分足 | [README](lab_5/README.md) | [日本語](lab_5/README.ja.md) | `lab_5/outputs/trend_following_ma_cross/`, `lab_5/outputs/article_figures/` |
| `lab_6` | BTC/ETH/SOL 暗号資産急落後リバウンド診断 | BTCUSDT / ETHUSDT / SOLUSDT 240分足 | [README](lab_6/README.md) | [日本語](lab_6/README.ja.md) | `lab_6/outputs/crypto_crash_rebound_ohlcv/`, `lab_6/outputs/article_materials/` |
| `lab_7` | BTC急落後リバウンド交互作用モデル | BTC / Nasdaq / S&P 500 / Dow / DAX 240分足とBTCUSDT Funding Rate | [README](lab_7/README.md) | [日本語](lab_7/README.ja.md) | `lab_7/outputs/interaction_model/` |
| `lab_8` | BTC急落フィルター候補のモンテカルロ生存性診断 | BTC / Nasdaq / S&P 500 / Dow / DAX 240分足とBTCUSDT Funding Rate | [README](lab_8/README.md) | [日本語](lab_8/README.ja.md) | `lab_8/outputs/monte_carlo/` |
| `lab_9` | USDJPY戦略開発における生成AIモデル評価 | USDJPY 30分足・60分足・240分足と共通プロンプト | [README](lab_9/README.md) | [日本語](lab_9/README.ja.md) | `lab_9/AI_MODEL_EVALUATION_SUMMARY.md`, `lab_9/gpt5_5pro/outputs/` |
| `lab_10` | BTC ファットテール実務・Fragility診断 | BTC / Nasdaq / S&P 500 / Dow / DAX 240分足とBTCUSDT Funding Rate | [README](lab_10/README.md) | [日本語材料](lab_10/article_materials_btc_only/README.ja.md) | `lab_10/outputs/report/lab_10_experiment_report.md`, `lab_10/outputs/tables/fragility_matrix.csv` |
| `lab_11` | FX 2年金利差トレンドフィルター | EURUSD / USDJPY 日次価格、USD / EUR / JPY 2年金利、FX Nexus レジーム・コスト文脈 | [README](lab_11/README.md) | [日本語](lab_11/README.ja.md) | `lab_11/outputs/yield_spread_filter/` |

## lab_1 概要

`lab_1` は、Qiita記事「[クオンツ入門 予測を捨て、分布を読め - クオンツトレードのためのモーメント分析とエッジ探索フレームワーク](https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf)」に対応する実験ラボである。

価格方向を直接予測する前に、FXリターン分布の形、歪度、尖度、急変後の平均回帰、ボラティリティ階層別の未来リターンを確認し、どの通貨ペア・どの局面に深掘り価値があるかを探す。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_1/README.ja.md](lab_1/README.ja.md) |
| 英語版 | [lab_1/README.md](lab_1/README.md) |
| 実験コード | `lab_1/run_moment_analysis_edge_experiments.py` |
| 入力データ | `USDJPY240.csv`, `EURUSD240.csv`, `AUDJPY240.csv` |
| 正本出力 | `lab_1/moment_analysis_outputs_2022plus/` |
| 位置づけ | エッジ候補探索。完成した売買戦略ではない |

## lab_2 概要

`lab_2` は、Qiita記事「[クオンツトレーダーは『買われすぎ・売られすぎ』をどう判断するのか](https://qiita.com/tikeda123/items/8dfcc1c09e34d5304d49)」に対応する実験ラボである。

「下がりすぎ」「上がりすぎ」という主観的な判断を、24時間VWAP乖離Zスコアと直近1時間リターンの過去500本内パーセンタイルに変換し、その後の反発リターンを検証する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_2/README.ja.md](lab_2/README.ja.md) |
| 英語版 | [lab_2/README.md](lab_2/README.md) |
| 実験コード | `lab_2/audjpy_overbought_oversold_article_experiment.py` |
| 記事アウトライン | `lab_2/quant_overbought_oversold_article_outline.md` |
| 入力データ | `AUDJPY60.csv` |
| 正本出力 | `lab_2/article_outputs/` |
| 位置づけ | 買われすぎ・売られすぎの数値化と反発候補領域の観察 |

## lab_3 概要

`lab_3` は、Qiita記事「[FXで破産リスクを下げるための実践数学：Kelly基準を「損切り幅」と「注文数量」に落とし込む](https://qiita.com/tikeda123/items/d5e16444da576c545c43)」に対応するKelly基準ベースの注文リスク管理ツールである。

Kelly基準を「勝てる注文数量を出す公式」としてではなく、1回のトレードで許容できる最大損失額を求め、その金額を注文数量、損切り幅、1pip価値、証拠金使用率へ変換する教育用ツールとして扱う。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_3/README.ja.md](lab_3/README.ja.md) |
| 英語版 | [lab_3/README.md](lab_3/README.md) |
| HTMLツール | `lab_3/kelly_fx_position_size_tool.html` |
| 記事アウトライン | `lab_3/fx_kelly_article_outline_with_tools.md` |
| 入力データ | なし |
| 正本出力 | 単体HTMLツール |
| 位置づけ | Kelly基準を許容損失額、注文数量、損切り幅、証拠金使用率に変換する教育用チェックツール |

## lab_4 概要

`lab_4` は、Qiita記事「[AIでエッジ探しが簡単になった時代に、そのバックテストは本物か？PBOで過学習を確認する](https://qiita.com/tikeda123/items/ab7070663e8e002e785f)」に対応する実験ラボである。

AI時代のクオンツ探索で問題になりやすいバックテスト過学習を、USDJPY 60分足の実データで確認する。

移動平均クロス戦略144候補を題材に、8ブロックのCSCV的なIS/OOS分割と簡易PBOで、ISで選ばれた戦略がOOSでも残るかを確認する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_4/README.ja.md](lab_4/README.ja.md) |
| 英語版 | [lab_4/README.md](lab_4/README.md) |
| 記事 | [日本語](https://qiita.com/tikeda123/items/ab7070663e8e002e785f) / [English](https://qiita.com/tikeda123/items/fd589372f78ffa4c48fb) |
| 実験コード | `lab_4/run_backtest_overfitting_experiment.py` |
| 記事アウトライン | `lab_4/ai_edge_backtest_overfitting_outline.md`, `lab_4/backtest_overfitting_experiment_outline.md` |
| 入力データ | 外部 `USDJPY60(29).csv` |
| 正本出力 | `lab_4/results_summary.json`, `lab_4/experiment_report.md`, `lab_4/figures/` |
| 位置づけ | 簡易CSCV/PBOによる過学習リスク確認。完成した売買戦略ではない |

## lab_5 概要

`lab_5` は、Qiita記事「[トレンドフォローにエッジはあるのか――「遅れて入る」戦略がなぜ生き残るのか](https://qiita.com/tikeda123/items/e599112d88c912a86125)」および [英語版](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2) に対応するラボである。

USDJPY 60分足・240分足に単純な MA 20/80 クロスを適用し、トレンドフォローがコスト控除後でも右テール依存の損益構造を持つか、また固定2025 OOSでその構造が残るかを確認する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_5/README.ja.md](lab_5/README.ja.md) |
| 英語版 | [lab_5/README.md](lab_5/README.md) |
| 記事 | [日本語](https://qiita.com/tikeda123/items/e599112d88c912a86125) / [English](https://qiita.com/tikeda123/items/be91a8ff85324c7c39a2) |
| 実験コード | `lab_5/run_trend_following_experiment.py`, `lab_5/run_trend_following_direction_ablation.py`, `lab_5/save_article_figures.py` |
| 記事メモ | `lab_5/trend_following_edge_article_outline_improved.md`, `lab_5/trend_following_experiment_analysis_and_discussion.md` |
| 入力データ | `lab_5/USDJPY60.csv`, `lab_5/USDJPY240.csv` |
| 正本出力 | `lab_5/outputs/trend_following_ma_cross/`, `lab_5/outputs/trend_following_direction_ablation/`, `lab_5/outputs/article_figures/` |
| 位置づけ | トレンドフォロー構造とOOS崩れの診断。完成した売買戦略ではない |

## lab_6 概要

`lab_6` は、Qiita記事「[仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a)」と、`lab_6/BTC_ETH_SOL_crypto_quant_article_plan.docx.md` の BTC/ETH/SOL 暗号資産急落後リバウンド記事に対応するラボである。

BTCUSDT、ETHUSDT、SOLUSDT の240分足OHLCVを使い、下位テール急落後に短期リバウンド候補があるのか、それとも買ってはいけない「落ちるナイフ」なのかを診断する。価格分布だけでなく、ボラティリティ階層、次足始値エントリーのMAE/MFE、年別安定性、Funding Rate、Open Interest、清算データ取得制約まで確認する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_6/README.ja.md](lab_6/README.ja.md) |
| 英語版 | [lab_6/README.md](lab_6/README.md) |
| 記事 | [仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a) |
| 実験コード | `lab_6/run_crypto_crash_rebound_experiment.py` |
| 記事メモ | `lab_6/BTC_ETH_SOL_crypto_quant_article_plan.docx.md`, `lab_6/crypto_crash_rebound_experiment_plan.md` |
| 入力データ | `lab_6/BTCUSDT240.csv`, `lab_6/ETHUSDT240.csv`, `lab_6/SOLUSDT240.csv` |
| 正本出力 | `lab_6/outputs/crypto_crash_rebound_ohlcv/`, `lab_6/outputs/article_materials/` |
| 位置づけ | 急落後リバウンド候補と市場構造データ制約の診断。完成した売買戦略ではない |

## lab_7 概要

`lab_7` は、Qiita記事「[BTC急落は買いなのか？](https://qiita.com/tikeda123/items/c38b1dbc85d02f99c32c)」および英語版「[Is a BTC Crash a "Buy"?](https://qiita.com/tikeda123/items/ef9000ba3d9fd349fadb)」に対応するラボである。

BTC急落を一律に「押し目買い」と扱ってよいのか、それとも Funding Rate と外部リスク環境で「買える急落」と「避けるべき急落」に分けられるのかを確認する。BTC、Nasdaq、S&P 500、Dow、DAX の240分足OHLCVとBTCUSDT Funding Rate履歴を使う。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_7/README.ja.md](lab_7/README.ja.md) |
| 英語版 | [lab_7/README.md](lab_7/README.md) |
| 記事 | [BTC急落は買いなのか？](https://qiita.com/tikeda123/items/c38b1dbc85d02f99c32c) / [Is a BTC Crash a "Buy"?](https://qiita.com/tikeda123/items/ef9000ba3d9fd349fadb) |
| 実験コード | `lab_7/run_interaction_model_experiment.py` |
| 記事草稿 | `lab_7/BTC急落実験.pdf` |
| 入力データ | `lab_7/data/BTCUSD240.csv`, `lab_7/data/USATECHIDXUSD240.csv`, `lab_7/data/USA500IDXUSD240.csv`, `lab_7/data/USA30IDXUSD240.csv`, `lab_7/data/DEUIDXEUR240.csv`, `lab_7/data/funding_rate_history.csv` |
| 正本出力 | `lab_7/outputs/interaction_model/` |
| 位置づけ | BTC急落イベントの条件分類診断。完成した売買戦略ではない |

## lab_8 概要

`lab_8` は、Qiita記事「[BTC急落は本当に買えるのか？ ── モンテカルロで見る最大DDと生存確率](https://qiita.com/tikeda123/items/00fd5022d0d0ca0c80d5)」に対応するラボである。

`lab_7` で見つけたBTC急落フィルター候補、特に「BTC急落 x Funding低位 x 外部Risk-on環境」について、モンテカルロで最終リターン、最大ドローダウン、DD到達率、レバレッジ耐性、コスト耐性を確認する。単一の過去順序で良く見えたかではなく、繰り返し取りに行ったときに資金曲線が生き残れるかを診断する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_8/README.ja.md](lab_8/README.ja.md) |
| 英語版 | [lab_8/README.md](lab_8/README.md) |
| 記事 | [BTC急落は本当に買えるのか？ ── モンテカルロで見る最大DDと生存確率](https://qiita.com/tikeda123/items/00fd5022d0d0ca0c80d5) |
| 実験コード | `lab_8/run_monte_carlo_experiment.py` |
| 実験設計 | `lab_8/実験設計ドキュメント.pdf` |
| 入力データ | `lab_8/data/BTCUSD240.csv`, `lab_8/data/USATECHIDXUSD240.csv`, `lab_8/data/USA500IDXUSD240.csv`, `lab_8/data/USA30IDXUSD240.csv`, `lab_8/data/DEUIDXEUR240.csv`, `lab_8/data/funding_rate_history.csv` |
| 正本出力 | `lab_8/outputs/monte_carlo/` |
| 位置づけ | モンテカルロによる生存性・ドローダウン診断。完成した売買戦略ではない |

## lab_9 概要

`lab_9` は、Qiita記事「[クオンツトレードに最適な生成AIはどれか？ ― Claude Fable5 / GPT 5.5 Pro / GPT 5.5 High をUSDJPY戦略開発で比較した](https://qiita.com/tikeda123/items/63e6882cacadbdce1bc4)」に対応するラボである。

Claude Fable5、GPT 5.5 Pro、GPT 5.5 Highに同一のUSDJPYクオンツリサーチプロンプトを与え、データ診断、戦略候補の設計、WFO、コスト考慮、ロバスト性確認、ベンチマーク比較、採用/棄却判断の品質を比較する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_9/README.ja.md](lab_9/README.ja.md) |
| 英語版 | [lab_9/README.md](lab_9/README.md) |
| 記事 | [クオンツトレードに最適な生成AIはどれか？ ― Claude Fable5 / GPT 5.5 Pro / GPT 5.5 High をUSDJPY戦略開発で比較した](https://qiita.com/tikeda123/items/63e6882cacadbdce1bc4) |
| 共通プロンプト | `lab_9/inputdata/prompto.md` |
| 入力データ | `lab_9/inputdata/USDJPY30.csv`, `lab_9/inputdata/USDJPY60.csv`, `lab_9/inputdata/USDJPY240.csv` |
| 正本出力 | `lab_9/AI_MODEL_EVALUATION_SUMMARY.md`, `lab_9/gpt5_5pro/outputs/` |
| 位置づけ | クオンツリサーチ工程におけるAIモデル評価。完成した売買戦略ではない |

## lab_10 概要

`lab_10` は、Qiita記事「[ファットテールを織り込んだ"つもり"になっていないか](https://qiita.com/tikeda123/items/091519af64bd22367c2d)」に対応するラボである。

`lab_7` のBTC急落条件候補、特に `Funding low x risk-on` を、有効戦略として証明するのではなく、どの前提で壊れるかを診断する。小標本bootstrap、crash定義変更、2022年ストレス期、コスト、約定遅延、risk-on proxy変更、レバレッジ時MAEを確認し、Fragility Matrixとして運用対応へ変換する。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_10/README.md](lab_10/README.md) |
| 日本語材料 | [lab_10/article_materials_btc_only/README.ja.md](lab_10/article_materials_btc_only/README.ja.md) |
| 記事 | [ファットテールを織り込んだ"つもり"になっていないか](https://qiita.com/tikeda123/items/091519af64bd22367c2d) |
| 実験コード | `lab_10/scripts/00_lab7_interaction_model_base.py`, `lab_10/scripts/02_btc_crash_fragility.py`, `lab_10/scripts/03_fragility_matrix.py` |
| 入力データ | `lab_10/data/lab_7/` |
| 正本出力 | `lab_10/outputs/report/lab_10_experiment_report.md`, `lab_10/outputs/tables/fragility_matrix.csv`, `lab_10/article_materials_btc_minimal_ai/` |
| 位置づけ | ファットテールとerror on errorのFragility診断。完成した売買戦略ではない |

## lab_11 概要

`lab_11` は、Qiita記事「[FXは2年金利差でどこまで説明できるのか？ ― 水準ではなく「変化の向き」で見るトレンドフィルター](https://qiita.com/tikeda123/items/2bf3c18cbec6b4f3527a)」に対応するラボである。

EURUSD と USDJPY を対象に、2年金利差が価格トレンドをどこまで説明できるかを検証する。金利差の水準、変化方向、価格と金利差の一致、乖離、レジーム別の効き方を比較し、金利特徴量はT+1以降にだけ使うリーク防止を入れている。

| 項目 | 内容 |
|---|---|
| 詳細説明 | [lab_11/README.ja.md](lab_11/README.ja.md) |
| 英語版 | [lab_11/README.md](lab_11/README.md) |
| 記事 | [FXは2年金利差でどこまで説明できるのか？ ― 水準ではなく「変化の向き」で見るトレンドフィルター](https://qiita.com/tikeda123/items/2bf3c18cbec6b4f3527a) |
| 実験コード | `lab_11/run_yield_spread_experiment.py` |
| 記事メモ | `lab_11/article_base.md`, `lab_11/lab_base.md` |
| 入力データ | ローカル FX Nexus DuckDB と財務省 historical JGB CSV |
| 正本出力 | `lab_11/outputs/yield_spread_filter/` |
| 位置づけ | FX金利差の環境フィルター診断。完成した売買戦略ではない |

## 使い方

英語圏の読者は、各ラボの `README.md` を読む。

```bash
sed -n '1,220p' lab_1/README.md
sed -n '1,220p' lab_2/README.md
sed -n '1,220p' lab_3/README.md
sed -n '1,220p' lab_4/README.md
sed -n '1,220p' lab_5/README.md
sed -n '1,220p' lab_6/README.md
sed -n '1,220p' lab_7/README.md
sed -n '1,220p' lab_8/README.md
sed -n '1,220p' lab_9/README.md
sed -n '1,220p' lab_10/README.md
sed -n '1,220p' lab_11/README.md
```

日本語記事や日本語での作業では、各ラボの `README.ja.md` を読む。

```bash
sed -n '1,220p' lab_1/README.ja.md
sed -n '1,220p' lab_2/README.ja.md
sed -n '1,220p' lab_3/README.ja.md
sed -n '1,220p' lab_4/README.ja.md
sed -n '1,220p' lab_5/README.ja.md
sed -n '1,220p' lab_6/README.ja.md
sed -n '1,220p' lab_7/README.ja.md
sed -n '1,220p' lab_8/README.ja.md
sed -n '1,220p' lab_9/README.ja.md
sed -n '1,220p' lab_10/article_materials_btc_only/README.ja.md
sed -n '1,220p' lab_11/README.ja.md
```

実験を再生成する場合も、各ラボREADMEに記載されたコマンドを正本とする。

```bash
python lab_1/run_moment_analysis_edge_experiments.py
python lab_2/audjpy_overbought_oversold_article_experiment.py
```

`lab_3` はPython実験ではなく単体HTMLツールである。ローカルHTTPサーバーで確認する場合は、リポジトリルートで次を実行する。

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

その後、ブラウザで次を開く。

```text
http://127.0.0.1:8765/lab_3/kelly_fx_position_size_tool.html
```

`lab_4` は入力CSVを明示して実行する。

```bash
python lab_4/run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir /tmp/lab4_pbo_check
```

`lab_5` は入力CSVを `lab_5/` に含めている。

```bash
python lab_5/run_trend_following_experiment.py \
  --output-dir /tmp/lab5_trend_following_check
```

`lab_6` は入力CSVを `lab_6/` に含めている。

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --output-dir /tmp/lab6_crypto_crash_rebound_check
```

`lab_7` は入力CSVを `lab_7/data/` に含めている。

```bash
python lab_7/run_interaction_model_experiment.py
```

現在の `lab_7` スクリプトは `lab_7/outputs/interaction_model/` に直接出力する。

`lab_8` は入力CSVを `lab_8/data/` に含めている。

```bash
python3 lab_8/run_monte_carlo_experiment.py
```

現在の `lab_8` スクリプトは `lab_8/outputs/monte_carlo/` に直接出力する。

`lab_9` は、まずモデル評価サマリを読む。GPT 5.5 ProとGPT 5.5 Highのスクリプトは、リポジトリ相対パスで再実行できる。

```bash
sed -n '1,220p' lab_9/AI_MODEL_EVALUATION_SUMMARY.md
python3 lab_9/gpt5_5pro/usdjpy_wfo_quant_research.py \
  --files lab_9/inputdata/USDJPY30.csv lab_9/inputdata/USDJPY60.csv lab_9/inputdata/USDJPY240.csv \
  --outdir /tmp/lab9_gpt55pro_check
```

`lab_10` は入力CSVを `lab_10/data/lab_7/` に含めている。

```bash
/Users/toikeda/miniconda3/bin/python lab_10/scripts/00_lab7_interaction_model_base.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/02_btc_crash_fragility.py
/Users/toikeda/miniconda3/bin/python lab_10/scripts/03_fragility_matrix.py
```

`lab_11` はローカル FX Nexus DuckDB に依存し、財務省 historical JGB CSV を取得して再生成する。

```bash
python3 lab_11/run_yield_spread_experiment.py
```

現在の `lab_11` スクリプトは `lab_11/outputs/yield_spread_filter/` に直接出力する。

スクリプトが `--output-dir` や `--outdir` を提供している場合は、既存の正本出力を壊さず試すために一時ディレクトリへ出力する。

## 管理方針

- `README.md` は英語版の入口として扱う。
- `README.ja.md` は日本語版の入口として扱う。
- ルート README は索引とラボ一覧に限定する。
- 実験の詳細、再現コマンド、主要結果、注意点は各 `lab_xxx/README.md` と `lab_xxx/README.ja.md` に書く。
- コードから再生成できる成果物は、各ラボ内の専用出力ディレクトリにまとめる。
- 新しい記事・実験を追加する場合は、`lab_12`、`lab_13` のように新しいディレクトリを作る。
- 記事本文に使う数値は、各ラボの正本出力CSV、JSON、Markdownから引用する。
