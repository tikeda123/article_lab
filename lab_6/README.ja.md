# lab_6: BTC/ETH/SOL 暗号資産急落後リバウンド診断

English: [README.md](README.md)

このラボは、Qiita記事「[仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a)」、`BTC_ETH_SOL_crypto_quant_article_plan.docx.md` の BTC/ETH/SOL 暗号資産クオンツ記事案、`crypto_crash_rebound_experiment_plan.md` の実験計画に対応する実験ラボである。中心の問いは、暗号資産の急落後は本当に買いなのか、それとも買ってはいけない「落ちるナイフ」も存在するのかである。

このラボは、完成した売買戦略を作ることを目的にしない。記事用の根拠として、以下を分けるための診断パッケージである。

- 買ってよい可能性がある急落
- 待つべき急落
- 追加の市場構造データなしには買ってはいけない急落

このラボは投資助言ではなく、本番運用可能な売買システムでもない。記事用の根拠を再現可能な形で確認するための教育用診断パッケージである。

## 学習ログとフィードバック

このラボは、暗号資産市場で語られがちな「急落後は反発する」という見方を、再現可能な検証項目へ落とし込むための公開学習ログでもある。コード、CSV出力、Markdownレポート、図表、記事素材パッケージは、前提や限界を後から確認できるように共有している。

共有しているスクリプト、出力ファイル、または記事草稿に基づいて、誤り、再現性の問題、実験設計への疑問、別の解釈があれば指摘していただけるとありがたい。

## 実験の位置づけ

この実験では、BTCUSDT、ETHUSDT、SOLUSDT の240分足を使い、以下の順に確認している。

1. ローカルのタブ区切り BTC/ETH/SOL 4H OHLCV CSV を読み込む
2. 欠損タイムスタンプ、OHLCVパース失敗、重複タイムスタンプ、OHLC不整合、時刻飛びを監査する
3. 共通期間 `2020-08-11 04:00` から `2026-05-29 12:00` を使う
4. 4H対数リターンのモーメント、歪度、尖度、テールイベントを比較する
5. 下位急落・上位急騰イベント後の 4H / 8H / 12H / 24H / 48H / 72H 未来リターンを見る
6. 下位急落後リバウンドを、過去20本の実現ボラティリティ5分位で分解する
7. 終値同時エントリーの仮定をやめ、次の4H足始値エントリーと時間決済で確認する
8. MAE、MFE、Profit Factor、ドローダウン、重複除外の簡易イベントバックテストを見る
9. 2020年から2026年途中までの年別安定性を確認する
10. Binance USD-M Funding Rate で、ロング過熱の急落と Funding低下・マイナス時の急落を分ける
11. 取得できる範囲で Open Interest と清算データの診断を追加する
12. 記事執筆用素材を `outputs/article_materials/` にまとめる

重要な読み方は、価格データ上では急落後リバウンド候補が見える一方、特に高ボラ局面では途中逆行リスクも大きい点である。そのため、このラボでは Funding Rate、Open Interest、清算データの取得可能性、MAE/MFE、年別安定性を、補足ではなく必須の文脈として扱う。

## 主なファイル

| ファイル | 内容 |
|---|---|
| `run_crypto_crash_rebound_experiment.py` | Phase 0 から Phase 7 までの主実験スクリプト |
| `BTCUSDT240.csv` | BTCUSDT 240分足OHLCV入力 |
| `ETHUSDT240.csv` | ETHUSDT 240分足OHLCV入力 |
| `SOLUSDT240.csv` | SOLUSDT 240分足OHLCV入力 |
| `BTC_ETH_SOL_crypto_quant_article_plan.docx.md` | 記事計画と構成案 |
| `crypto_crash_rebound_experiment_plan.md` | フェーズ別の実験計画書 |
| `outputs/crypto_crash_rebound_ohlcv/` | 正本のCSV、Markdown、PNG出力 |
| `outputs/article_materials/` | 計画、元データ、レポート、表、イベント明細、番号付き図表を集めた記事素材パッケージ |
| `README.md` | このラボの英語版説明 |
| `README.ja.md` | このラボの日本語版説明 |

## 入力データ

現在の `lab_6` には入力CSV本体を含めている。

| ファイル | 銘柄 | 時間足 | 形式 |
|---|---|---|---|
| `BTCUSDT240.csv` | BTCUSDT | 240分足 | ヘッダーなし、タブ区切り `timestamp, open, high, low, close, volume` |
| `ETHUSDT240.csv` | ETHUSDT | 240分足 | ヘッダーなし、タブ区切り `timestamp, open, high, low, close, volume` |
| `SOLUSDT240.csv` | SOLUSDT | 240分足 | ヘッダーなし、タブ区切り `timestamp, open, high, low, close, volume` |

`outputs/crypto_crash_rebound_ohlcv/data_profile.csv` に記録されている現在のデータ監査値は以下である。

| 銘柄 | 元行数 | 整理後行数 | 入力開始 | 入力終了 | 共通期間行数 | 共通期間欠損行数 | 時刻飛び数 | 状態 |
|---|---:|---:|---|---|---:|---:|---:|---|
| BTCUSDT | 19,227 | 19,227 | `2017-08-17 04:00` | `2026-05-29 12:00` | 12,704 | 1 | 10 | WARN |
| ETHUSDT | 19,227 | 19,227 | `2017-08-17 04:00` | `2026-05-29 12:00` | 12,704 | 1 | 10 | WARN |
| SOLUSDT | 12,704 | 12,704 | `2020-08-11 04:00` | `2026-05-29 12:00` | 12,704 | 1 | 1 | WARN |

3銘柄横比較の共通期間は `2020-08-11 04:00` から `2026-05-29 12:00` である。4時間足ではない時刻飛びをまたぐリターンと未来リターンは、統計計算から除外している。

## 実験環境

主スクリプトは Python 3 で動作する。必要な外部パッケージは以下である。

| パッケージ | 用途 |
|---|---|
| pandas | CSV読み込み、イベント明細、集計表 |
| numpy | リターン計算と指標計算 |
| matplotlib | PNG図表生成 |

Funding Rate、Open Interest、清算エンドポイントのデータ取得には、Python標準ライブラリのHTTP機能を使っている。

## 再現コマンド

リポジトリルートから、現在の Phase 0 から Phase 7 までの出力を再生成する。

```bash
python lab_6/run_crypto_crash_rebound_experiment.py
```

既存の正本出力を壊さずに確認する場合は、一時ディレクトリへ出力する。

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --output-dir /tmp/lab6_crypto_crash_rebound_check
```

特定フェーズまで実行する。

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --phase phase5 \
  --output-dir /tmp/lab6_phase5_check
```

Funding Rate または Open Interest のキャッシュを更新したい場合は、以下を使う。

```bash
python lab_6/run_crypto_crash_rebound_experiment.py \
  --refresh-funding \
  --refresh-open-interest \
  --output-dir /tmp/lab6_refresh_check
```

## Python実験ツールの使い方

利用可能な引数は以下で確認する。

```bash
python lab_6/run_crypto_crash_rebound_experiment.py --help
```

重要な引数は以下である。

| 引数 | 既定値 | 用途 |
|---|---|---|
| `--data-dir` | `lab_6/` | `BTCUSDT240.csv`, `ETHUSDT240.csv`, `SOLUSDT240.csv` を置いたディレクトリ |
| `--output-dir` | `lab_6/outputs/crypto_crash_rebound_ohlcv` | 生成CSV、Markdown、PNGの出力先 |
| `--phase` | `phase7` | `phase0` から `phase7` までを実行する。後続フェーズは前段出力も再生成する |
| `--refresh-funding` | off | キャッシュ済みCSVがあっても Binance Funding Rate 履歴を再取得する |
| `--refresh-open-interest` | off | キャッシュ済みCSVがあっても Binance Open Interest 履歴を再取得する |
| `--dpi` | `180` | 図表のDPI |

## スクリプトの処理内容

主スクリプトは以下を行う。

- ヘッダーなし・タブ区切りOHLCVを読み込み、時刻順に並べる。
- タイムスタンプまたはOHLCに欠損がある行を除外する。
- 重複タイムスタンプは最後の行を残す。
- OHLC不整合と時刻飛びを確認する。
- `log(close_t / close_{t-1}) * 100` を対数リターンとして使う。
- 4時間足ではない時刻飛びをまたぐリターンと未来リターンを除外する。
- 急落・急騰閾値は、各銘柄自身の全期間リターン分布から定義する。
- 下位・上位の 5%、2.5%、1% テールイベントを評価する。
- 4H、8H、12H、24H、48H、72H のホライズンを評価する。
- 過去20本の実現ボラティリティ5分位でレジームを分ける。
- 急落シグナル後の次足始値エントリー、時間決済、MAE、MFE、Profit Factor、ドローダウンを確認する。
- 2020年から2026年途中までの年別安定性を作る。
- Phase 6 と Phase 7 では、Binance USD-M の Funding Rate と Open Interest 履歴を取得または再利用する。
- 清算履歴エンドポイントが利用できない場合は、結果を捏造せず、データ制約として記録する。

## 主要出力

`outputs/crypto_crash_rebound_ohlcv/` の主な出力は以下である。

| ファイル | 内容 |
|---|---|
| `article_experiment_summary.md` | 実験全体の生成サマリー |
| `data_profile.csv` | 入力データ品質と共通期間監査 |
| `timestamp_gap_events.csv` | 時刻飛びの根拠 |
| `moment_summary.csv` | 銘柄別4Hリターンモーメント |
| `direction_return_summary.csv` | 上昇足・下落足後の未来リターン |
| `shock_mean_reversion_summary.csv` | テール急変後の平均回帰イベントスタディ |
| `phase2_candidate_summary.csv` | Phase 2 の記事候補条件 |
| `vol_regime_summary.csv` | ボラティリティレジームのプロフィール |
| `shock_mean_reversion_by_vol_summary.csv` | ボラティリティ別のテール急変後結果 |
| `phase3_lower5_by_vol_candidate_summary.csv` | Phase 3 の Q5 急落後リバウンド候補 |
| `phase4_candidate_table.csv` | 次足始値エントリー候補定義 |
| `path_risk_summary.csv` | MAE、MFE、経路リスクの集計 |
| `simple_backtest_summary.csv` | 重複除外イベントバックテスト集計 |
| `annual_condition_summary.csv` | 年別・条件別集計 |
| `annual_stability_summary.csv` | 年別安定性指標 |
| `funding_profile.csv` | Funding Rate のカバレッジと分布 |
| `shock_mr_by_funding_summary.csv` | Funding階層別の急落後リバウンド |
| `oi_profile.csv` | Open Interest のカバレッジと制約 |
| `shock_mr_by_oi_summary.csv` | OI階層別の急落後リバウンド |
| `liquidation_profile.csv` | 清算エンドポイントの利用可否 |

記事素材パッケージは以下である。

| パス | 内容 |
|---|---|
| `outputs/article_materials/README.md` | 記事素材パッケージのガイド |
| `outputs/article_materials/planning/` | 計画書と再現スクリプト |
| `outputs/article_materials/source_data/` | OHLCV、Funding Rate、Open Interest の元データ |
| `outputs/article_materials/reports/` | Phase 1 から Phase 7 までのレポート |
| `outputs/article_materials/tables/` | 記事で引用しやすい集計CSV |
| `outputs/article_materials/event_tables/` | イベント単位の明細CSV |
| `outputs/article_materials/figures/` | 番号付き記事用図表 |
| `outputs/article_materials/figure_index.csv` | 図表メタデータ |
| `outputs/article_materials/table_index.csv` | 表メタデータ |
| `outputs/article_materials/report_index.csv` | レポートメタデータ |
| `outputs/article_materials/source_data_index.csv` | 元データメタデータ |

## 記事用図表

`outputs/article_materials/figures/` には15個の番号付き図表がある。

| 図 | 内容 |
|---|---|
| 1-4 | モーメント、極端リターン、分布ヒストグラム、QQ診断 |
| 5-6 | 方向別未来リターンとホライズン別急変後平均回帰 |
| 7-8 | ボラティリティレジームと下位5%急落後リバウンド |
| 9-11 | 次足始値エントリーの経路リスク、簡易エクイティ、ドローダウン |
| 12 | 年別条件サマリー |
| 13 | Funding階層別の急落後リバウンド |
| 14 | Open Interest階層別の急落後リバウンド |
| 15 | 清算データ取得状況と制約 |

## 主要結果

Phase 2 の終値ベースイベントスタディで見た、下位5%急落後ロング候補は以下である。

| 銘柄 | 下位5%閾値 | 最良ホライズン | 件数 | 平均MR | 中央値MR | 勝率 | t値 |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | `-1.8988%` | 48H | 636 | `+0.4943%` | `+0.4808%` | `55.66%` | `2.23` |
| ETHUSDT | `-2.5347%` | 24H | 636 | `+0.3453%` | `+0.5708%` | `55.66%` | `1.51` |
| SOLUSDT | `-3.7213%` | 72H | 636 | `+2.5185%` | `+2.7538%` | `61.48%` | `4.32` |

Phase 3 の Q5高ボラ・下位5%急落後ロング候補は以下である。

| 銘柄 | Q5最良ホライズン | 件数 | 平均MR | 中央値MR | 勝率 | t値 |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 48H | 324 | `+1.0495%` | `+0.9602%` | `57.72%` | `2.98` |
| ETHUSDT | 72H | 340 | `+0.9078%` | `+1.5715%` | `58.24%` | `1.63` |
| SOLUSDT | 72H | 336 | `+4.3539%` | `+4.0895%` | `66.67%` | `4.91` |

Phase 4 の次足始値エントリーと経路リスクは以下である。

| 候補 | 件数 | 決済 | 平均リターン | 勝率 | PF | 平均MAE | 最悪MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTC all 48H | 636 | 48H | `+0.4964%` | `55.97%` | `1.27` | `-5.1126%` | `-36.8271%` |
| ETH all 24H | 636 | 24H | `+0.3431%` | `55.66%` | `1.18` | `-5.5627%` | `-57.2095%` |
| SOL all 72H | 636 | 72H | `+2.5201%` | `61.48%` | `1.62` | `-11.6441%` | `-96.9345%` |
| BTC Q5 48H | 324 | 48H | `+1.0497%` | `58.02%` | `1.54` | `-6.0026%` | `-36.8271%` |
| ETH Q5 72H | 340 | 72H | `+0.9026%` | `58.24%` | `1.26` | `-10.5276%` | `-65.4687%` |
| SOL Q5 72H | 336 | 72H | `+4.3491%` | `66.37%` | `2.07` | `-13.6506%` | `-87.3176%` |

Phase 4 の重複除外イベントバックテストの主な結果は以下である。

| 候補 | 採用件数 | 平均リターン | 勝率 | PF | 平均MAE | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| BTC Q5 48H | 149 | `+0.7693%` | `56.38%` | `1.39` | `-5.3196%` | `-39.2781%` |
| ETH Q5 72H | 120 | `+0.3897%` | `52.50%` | `1.12` | `-8.6000%` | `-65.7119%` |
| SOL Q5 72H | 113 | `+4.5583%` | `69.03%` | `2.40` | `-12.2134%` | `-59.9710%` |

Funding Rate 拡張の主な結果は以下である。

| 銘柄 | 最良Funding条件 | ホライズン | 件数 | Gross MR | Funding調整後MR | 調整後勝率 | 調整後t値 |
|---|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | `funding_low_or_negative` | 24H | 112 | `+1.3283%` | `+1.3361%` | `64.29%` | `3.13` |
| ETHUSDT | `funding_low_or_negative` | 24H | 146 | `+0.8810%` | `+0.8962%` | `56.85%` | `1.88` |
| SOLUSDT | `funding_low_or_negative` | 72H | 159 | `+2.9243%` | `+4.4465%` | `67.30%` | `4.04` |

## 解釈上の注意点

このラボは、暗号資産の急落をすべて買うべきだと証明するものではない。

- Phase 2 では終値ベースの急落後リバウンド候補が見えるが、全期間分位を使った探索分析である。
- Phase 3 では、強いリバウンド候補が高ボラティリティ局面に集中している。
- Phase 4 では、次足始値エントリーでも一部の平均リターンは残るが、MAE とドローダウンが大きい。
- SOL Q5 72H は数値上最も強いが、経路リスクも非常に大きい。
- ETH は重複シグナルを除くと弱くなる。
- BTC Q5 48H は SOL ほど派手ではないが、このサンプルでは相対的にリスクが抑えられている。
- Phase 5 では年別のばらつきがあり、2020年と2026年は部分年として慎重に扱う必要がある。
- Phase 6 の Funding Rate は Binance USD-M Futures データであり、OHLCV が現物由来の場合は市場ソースの不一致を注記する必要がある。
- Phase 7 の Open Interest はAPIが直近ローリングウィンドウしか返さなかったため、全期間結論ではなく制約・次ステップとして扱う。
- 清算履歴は今回試した公開エンドポイントから取得できず、その制約を明示している。

記事で安全に言える結論は、以下の範囲に留めるのがよい。

```text
価格データだけを見ると、BTC、ETH、SOL には急落後リバウンド候補がある。
特に高ボラ局面の下位テール急落後は平均回帰が強く見える。
しかし、それは安全な押し目買いルールではない。
大きなMAE、ドローダウン、年別のばらつき、市場構造の曖昧さとセットで存在する。
買ってよい急落と落ちるナイフを分けるには、Funding Rate、Open Interest、
清算データ、執行を考慮したリスク管理が必要である。
```

## 記事との対応

現在の記事・計画ファイルは以下である。

| ファイル | 役割 |
|---|---|
| [仮想通貨市場のエッジはどこに潜むのか？──BTC・ETH・SOLの分布・急変動・Funding Rateから検証する](https://qiita.com/tikeda123/items/8975139eb3ffcc0a7d5a) | 公開済み日本語Qiita記事 |
| `BTC_ETH_SOL_crypto_quant_article_plan.docx.md` | 記事計画と構成案 |
| `crypto_crash_rebound_experiment_plan.md` | フェーズ別の実験計画書 |
| `outputs/article_materials/README.md` | 記事素材パッケージのガイド |
| `outputs/article_materials/report_index.csv` | レポート索引 |
| `outputs/article_materials/table_index.csv` | 表索引 |
| `outputs/article_materials/figure_index.csv` | 図表索引 |

記事の中心メッセージは、次の境界に合わせる。

```text
暗号資産の急落後リバウンドは測定できる。
一部の高ボラ急落レジームでは、正の平均回帰も見える。
しかし「急落したから買い」は粗すぎる。
重要なのは、清算後の反発候補なのか、まだレバレッジ解消の途中なのかを分けることである。
```
