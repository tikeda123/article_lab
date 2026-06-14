# lab_7: BTC急落後リバウンド交互作用モデル

English: [README.md](README.md)

このラボは、Qiita記事「[BTC急落は買いなのか？](https://qiita.com/tikeda123/items/c38b1dbc85d02f99c32c)」、英語版「[Is a BTC Crash a "Buy"?](https://qiita.com/tikeda123/items/ef9000ba3d9fd349fadb)」、記事草稿 `BTC急落実験.pdf`、および `run_interaction_model_experiment.py` の交互作用モデル実験に対応する実験ラボである。中心の問いは、BTC急落を一律に「押し目買い」と扱ってよいのか、それとも Funding Rate と外部リスク環境によって「買える急落」と「避けるべき急落」に分けられるのかである。

このラボは、NasdaqがBTCを直接予測すると主張するものではない。Nasdaq、S&P 500、Dow、DAXは、BTC急落が広いリスクオン環境で起きているのか、リスクオフ環境で起きているのかを判断する文脈変数として使う。

このラボは投資助言ではなく、本番運用可能な売買システムでもない。記事用の根拠を再現可能な形で確認するための教育用診断パッケージである。

## 学習ログとフィードバック

このラボは、暗号資産市場で語られがちな「急落後は買い」という見方を、再現可能な検証項目へ落とし込むための公開学習ログでもある。コード、CSV出力、Markdownレポート、PNG図表は、前提や限界を後から確認できるように共有している。

共有しているスクリプト、出力ファイル、または記事草稿に基づいて、誤り、再現性の問題、実験設計への疑問、別の解釈があれば指摘していただけるとありがたい。

## 実験の位置づけ

この実験では、BTC 4時間足の急落イベントを以下の順に確認している。

1. `data/` の BTC、Nasdaq、S&P 500、Dow、DAX の 4H OHLCV CSV を読み込む
2. 5市場の共通タイムスタンプパネルを作る
3. BTCと株価指数の4Hリターン、5日リターンを計算する
4. 過去180本のローリングシグマスコアでBTC急落イベントを定義する
5. 補助検証として rolling 1.5 sigma と全期間下位5%の急落定義も作る
6. 同じ急落局面を重複計上しないよう、24時間のイベントクールダウンを入れる
7. シグナル時点で既知のBTCUSDT Funding Rateだけを使って結合する
8. Fundingを低位、マイナス、下位20%、高位、未取得に分類する
9. Nasdaq 5日リターン、S&P 500 5日リターン、Nasdaq/S&P 500/Dow/DAXの3-of-4判定で外部リスクオンを分類する
10. 次の4H足始値エントリー、24H/48H/5日固定決済でBTC未来リターンを見る
11. リターン、勝率、Profit Factor、MAE、MFE、ドローダウン、回帰係数、頑健性コントラスト、期間安定性を測る
12. CSV表、Markdownレポート、図表を `outputs/interaction_model/` に出力する

重要な読み方は、Funding Rateと外部リスク環境がBTC急落の分類に役立つ可能性はあるが、強く主張すべきなのは安定した線形交互作用ではなく、条件分類によるフィルタリングである、という点である。

## 主なファイル

| ファイル | 内容 |
|---|---|
| `run_interaction_model_experiment.py` | 交互作用モデル分析の主実験スクリプト |
| [BTC急落は買いなのか？](https://qiita.com/tikeda123/items/c38b1dbc85d02f99c32c) | 公開済み日本語Qiita記事 |
| [Is a BTC Crash a "Buy"?](https://qiita.com/tikeda123/items/ef9000ba3d9fd349fadb) | 公開済み英語Qiita記事 |
| `BTC急落実験.pdf` | 日本語の記事草稿と実験骨子 |
| `data/BTCUSD240.csv` | BTC 240分足OHLCV入力 |
| `data/USATECHIDXUSD240.csv` | Nasdaq 240分足OHLCV入力 |
| `data/USA500IDXUSD240.csv` | S&P 500 240分足OHLCV入力 |
| `data/USA30IDXUSD240.csv` | Dow 240分足OHLCV入力 |
| `data/DEUIDXEUR240.csv` | DAX 240分足OHLCV入力 |
| `data/funding_rate_history.csv` | Funding Rate履歴。スクリプト内ではBTCUSDTだけを使う |
| `outputs/interaction_model/` | 正本のCSV、Markdown、PNG出力 |
| `README.md` | このラボの英語版説明 |
| `README.ja.md` | このラボの日本語版説明 |

## 入力データ

現在の `lab_7` には入力CSV本体を含めている。

| ファイル | 行数 | 開始 | 終了 | 形式 |
|---|---:|---|---|---|
| `data/BTCUSD240.csv` | 17,775 | `2017-05-23 00:00:00` | `2026-06-05 20:00:00` | ヘッダーなし、タブ区切り `timestamp, open, high, low, close, volume` |
| `data/USATECHIDXUSD240.csv` | 19,175 | `2013-05-22 12:00:00` | `2026-06-05 20:00:00` | ヘッダーなし、タブ区切りOHLCV |
| `data/USA500IDXUSD240.csv` | 19,102 | `2013-05-23 00:00:00` | `2026-06-05 20:00:00` | ヘッダーなし、タブ区切りOHLCV |
| `data/USA30IDXUSD240.csv` | 19,652 | `2013-05-23 00:00:00` | `2026-06-05 20:00:00` | ヘッダーなし、タブ区切りOHLCV |
| `data/DEUIDXEUR240.csv` | 19,400 | `2013-05-21 12:00:00` | `2026-06-05 16:00:00` | ヘッダーなし、タブ区切りOHLCV |
| `data/funding_rate_history.csv` | 19,036 | `2020-08-11 00:00:00` | `2026-05-29 16:00:00` | Funding Rate履歴CSV |

`outputs/interaction_model/interaction_model_report.md` に記録されている現在のデータ範囲は以下である。

| 項目 | 値 |
|---|---:|
| 共通4Hパネル行数 | 13,515 |
| 共通パネル開始 | `2017-05-23 04:00:00` |
| 共通パネル終了 | `2026-06-05 16:00:00` |
| 全期間下位5% BTC 4Hリターン閾値 | `-2.3918%` |

Funding Rateは、12時間以内の直近過去値を `merge_asof` で結合する。Funding低位/高位のパーセンタイル判定は拡張パーセンタイルを使い、イベント時点から見て未来のFunding分布を使わない。

## 実験環境

主スクリプトは Python 3 で動作する。必要な外部パッケージは以下である。

| パッケージ | 用途 |
|---|---|
| pandas | CSV読み込み、パネル構築、表作成 |
| numpy | リターン計算と指標計算 |
| scipy | t検定と回帰のp値 |
| matplotlib | PNG図表生成 |

## 再現コマンド

リポジトリルートから、現在の出力を再生成する。

```bash
python lab_7/run_interaction_model_experiment.py
```

現在のスクリプトにはコマンドライン引数がない。出力先は次の固定ディレクトリである。

```text
lab_7/outputs/interaction_model/
```

実行すると、このディレクトリ内の正本CSV、Markdown、PNG出力を上書きする。

## スクリプトの挙動

主スクリプトは以下を行う。

- ヘッダーなしタブ区切りOHLCVを読み込み、タイムスタンプ順に並べる
- 5市場の4H共通パネルをinner joinで作る
- BTCと各株価指数の対数リターンを計算する
- 主急落イベントを `btc_sigma_score_180 <= -2.0` と定義する
- 補助急落イベントとして rolling 1.5 sigma と全期間下位5%を定義する
- 次の4H足始値エントリー、24H/48H/5日固定決済で評価する
- 保有期間中のMAEとMFEを計算する
- 主リスクオン条件を `Nasdaq 5日リターン > 0` とする
- S&P 500と広い3-of-4株価指数判定でリスクオン条件の頑健性を確認する
- Funding低位を「拡張パーセンタイル下位20%またはFunding Rateマイナス」と定義する
- Funding高位を「拡張パーセンタイル上位20%」と定義する
- 条件別集計、通常標準誤差の簡易OLS係数、頑健性コントラスト、期間安定性を出力する
- 特徴量パネル、集計表、生成レポート、図表を保存する

## 主な出力

`outputs/interaction_model/` の主な出力は以下である。

| ファイル | 内容 |
|---|---|
| `interaction_model_report.md` | 実験全体の生成レポート |
| `interaction_feature_panel.csv` | 急落、リスク環境、Funding、未来リターンを含む共通特徴量パネル |
| `interaction_group_stats.csv` | 条件グループ別のリターン、勝率、PF、MAE、MFE、ドローダウン |
| `interaction_regression_coefficients.csv` | Funding、risk-on、交互作用項のOLS係数 |
| `interaction_contrasts.csv` | 急落定義とリスク代理変数ごとの頑健性コントラスト |
| `interaction_period_stability.csv` | 主条件の期間安定性確認 |
| `figures/` | 生成された記事用図表 |

## 図表

`outputs/interaction_model/figures/` には5枚の生成図表がある。

| 図表 | 内容 |
|---|---|
| `figure02_primary_48h_mean_return.png` | 主条件48Hの条件グループ別平均リターン |
| `figure03_four_cell_24h_mean_return.png` | Funding低位/非低位とrisk-on/offの4セル24H平均リターン |
| `figure04_four_cell_48h_mean_return.png` | 4セル48H平均リターン |
| `figure05_risk_proxy_low_funding_risk_on.png` | リスク代理変数別のFunding低位 x risk-on平均リターン |
| `figure06_interaction_coefficients.png` | 通常標準誤差付きの交互作用係数 |

## 主要結果

Nasdaq 5日リスクオンを使った rolling 2 sigma BTC急落の主結果は以下である。

| グループ | 期間 | 件数 | 平均リターン | 勝率 | PF | 平均MAE | 最悪MAE | 最大DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Funding取得済み全急落 | 24H | 201 | `+0.341%` | `53.234%` | `1.260` | `-3.727%` | `-36.617%` | `-30.823%` |
| Funding低位のみ | 24H | 44 | `+1.258%` | `63.636%` | `2.528` | `-3.051%` | `-20.252%` | `-19.097%` |
| risk-onのみ | 24H | 88 | `+0.423%` | `54.545%` | `1.406` | `-3.418%` | `-36.617%` | `-27.800%` |
| Funding低位 x risk-on | 24H | 15 | `+1.297%` | `66.667%` | `3.122` | `-2.651%` | `-9.426%` | `-3.470%` |
| Funding高位 x risk-off | 24H | 26 | `-0.242%` | `42.308%` | `0.837` | `-4.330%` | `-12.258%` | `-19.250%` |
| Funding取得済み全急落 | 48H | 201 | `+0.603%` | `61.194%` | `1.368` | `-4.716%` | `-36.617%` | `-42.441%` |
| Funding低位 x risk-on | 48H | 15 | `+1.115%` | `73.333%` | `2.073` | `-3.249%` | `-9.426%` | `-6.181%` |
| Funding高位 x risk-off | 48H | 26 | `-0.100%` | `53.846%` | `0.935` | `-5.347%` | `-13.622%` | `-18.777%` |

`interaction_model_report.md` の生成判定は以下である。

| 問い | 判定 | 解釈 |
|---|---|---|
| 主条件は全急落より良いか | yes | rolling 2 sigma x Nasdaq 5日上昇では、Funding低位 x risk-onが24H/48Hとも全急落を上回る |
| Funding単体より改善するか | mixed | 改善はあるが、差は大きくない |
| risk-on単体より改善するか | mixed | 24Hは改善するが、48Hはrisk-on単体の方が強い |
| 避けるべき急落は見えるか | 方向としてyes | Funding高位 x risk-offは24H/48Hで弱い |

## 解釈上の注意

- 主条件の `funding_low_x_risk_on` は15件しかなく、標本数が小さい。
- 指標は手数料、スプレッド、スリッページ控除前である。
- p値は素朴な値であり、時系列依存を十分に補正していない。
- 交互作用係数は、強い線形交互作用を主張できるほど安定していない。
- より自然な記事主張は、NasdaqがBTCを直接予測するという話ではなく、Fundingと外部リスク環境がBTC急落を分類する助けになる、という話である。
- このラボは記事用の根拠パッケージであり、本番運用戦略ではない。
