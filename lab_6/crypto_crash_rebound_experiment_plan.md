# lab_6 実験計画書: BTC/ETH/SOL 急落後リバウンド検証

作成日: 2026-05-30

参照企画書: `BTC_ETH_SOL_crypto_quant_article_plan.docx.md`

## 1. 実験の目的

この実験の中心テーマは、単なる「BTC/ETH/SOL のモーメント比較」ではない。

主目的は、次の問いを実データで検証することである。

> BTC・ETH・SOL の急落後は本当に買いなのか。
> それとも、買ってはいけない急落も存在するのか。

暗号資産市場では、急落の意味が一つではない。一時的な投げ売りであれば短期反発の候補になり得るが、ロング過熱、Open Interest の積み上がり、清算連鎖の途中であれば、急落後ロングは危険な「落ちるナイフ」になり得る。

したがって、本実験では最終的に以下を区別する検証フレームを作る。

- 買ってよい可能性がある急落
- 待つべき急落
- 買ってはいけない急落

ただし、最初から完成した売買戦略を作ることは目的にしない。`lab_1` と同じく、本実験は記事用のエッジ候補探索であり、結果は後続の正式バックテスト、WFO、Holdout 検証の前段階として扱う。

## 2. lab_1 から踏襲する実験思想

`lab_1` は、FX 240分足データで以下の順に分析している。

1. 終値ベース対数リターンのモーメント比較
2. 最大上昇・最大下落の確認
3. リターン分布の可視化
4. 上昇足後・下落足後の未来リターン分析
5. 上位・下位テール急変後の平均回帰分析
6. ボラティリティ階層別の未来リターン分析
7. 年別安定性と次足始値ベースの簡易リスク確認

`lab_6` では、この型を BTCUSDT / ETHUSDT / SOLUSDT に移植する。

ただし、暗号資産では以下を追加で重視する。

- 24時間市場であるため、4H / 8H / 12H / 24H / 48H / 72H の保有期間を見る
- 平均リターンだけでなく、MAE / MFE / Profit Factor / 最大DDを見る
- Perpetual Futures である場合、Funding Rate の影響を無視しない
- Open Interest と清算データが取得できる場合、急落の構造を分類する

## 3. 現時点の入力データ

`lab_6` 直下には、現時点で以下の 4時間足 OHLCV CSV がある。

| ファイル | 銘柄 | 現時点の行数 | 開始 | 終了 |
|---|---|---:|---|---|
| `BTCUSDT240.csv` | BTCUSDT | 19227 | `2017-08-17 04:00` | `2026-05-29 12:00` |
| `ETHUSDT240.csv` | ETHUSDT | 19227 | `2017-08-17 04:00` | `2026-05-29 12:00` |
| `SOLUSDT240.csv` | SOLUSDT | 12704 | `2020-08-11 04:00` | `2026-05-29 12:00` |

3銘柄を横比較する場合の共通期間は以下である。

| 項目 | 内容 |
|---|---|
| 共通開始 | `2020-08-11 04:00` |
| 共通終了 | `2026-05-29 12:00` |
| 足種 | 240分足 |
| 入力形式 | ヘッダーなし、タブ区切り、`timestamp, open, high, low, close, volume` |

注意点:

- 記事内で Binance USD-M Perpetual と書く場合は、現在の CSV が spot 由来か futures/perp 由来かを確認する。
- 出来高が base volume か quote volume かも確認する。
- Funding / OI / 清算を扱う段階では、価格CSVと時刻を揃える必要がある。

## 4. フェーズ構成

最初の実装対象は Phase 0 から Phase 5 までとする。これは現在ある OHLCV だけで再現可能である。

Funding Rate、Open Interest、清算データを使う分析は Phase 6 以降に分離する。

## 5. Phase 0: データ確認

目的は、入力CSVを実験に使える状態として確認することである。

確認項目:

- ヘッダーなし・タブ区切りとして正しく読めるか
- timestamp が `%Y-%m-%d %H:%M` として解釈できるか
- OHLCV の数値変換に失敗する行がないか
- 欠損 timestamp がないか
- OHLC 欠損がないか
- 重複 timestamp がないか
- 時刻飛びがあるか
- 3銘柄の共通期間
- 銘柄ごとの実データ開始日と終了日

出力:

- `outputs/crypto_crash_rebound_ohlcv/data_profile.csv`
- `outputs/crypto_crash_rebound_ohlcv/article_experiment_summary.md` の Data Profile 節

## 6. Phase 1: 分布・モーメント比較

目的は、BTC / ETH / SOL を同じ暗号資産として一括りにせず、銘柄ごとの性格を確認することである。

計算するリターン:

```text
log_return_pct = log(close_t / close_{t-1}) * 100
```

集計項目:

- 件数
- 平均
- 中央値
- 分散
- 標準偏差
- 歪度
- 超過尖度
- 最大上昇
- 最大下落

図表:

- 4時間足リターン分布ヒストグラム
- 標準偏差・歪度・超過尖度の比較
- 最大上昇・最大下落の比較
- QQプロット、または正規分布との差が分かる代替図

出力:

- `moment_summary.csv`
- `fig_01_moment_std_skew_kurtosis.png`
- `fig_02_extreme_returns.png`
- `fig_03_return_distribution_histograms.png`

## 7. Phase 2: 急落・急騰イベントスタディ

記事の中心実験である。

急落を下位分位、急騰を上位分位として定義し、その後の未来リターンを銘柄別・保有期間別に比較する。

急落条件:

- 下位5%
- 下位2.5%
- 下位1%

急騰条件:

- 上位5%
- 上位2.5%
- 上位1%

見るホライズン:

| 本数 | 時間 |
|---:|---:|
| 1 | 4H |
| 2 | 8H |
| 3 | 12H |
| 6 | 24H |
| 12 | 48H |
| 18 | 72H |

評価項目:

- 件数
- 現在足リターン平均
- 未来リターン平均
- 未来リターン中央値
- 平均回帰リターン平均
- 平均回帰リターン中央値
- 勝率
- t値

符号定義:

```text
急落後ロング平均回帰 = +future_return
急騰後ショート平均回帰 = -future_return
```

出力:

- `direction_return_summary.csv`
- `shock_mean_reversion_summary.csv`
- `fig_04_direction_future_returns.png`
- `fig_05_shock_mean_reversion_by_horizon.png`

## 8. Phase 3: ボラティリティ階層別分析

目的は、急落後反発が低ボラ・中ボラ・高ボラでどう変わるかを確認することである。

`lab_1` と同様に、過去20本の4時間足リターン標準偏差を `vol20_pct` として計算し、5分位に分ける。

ボラティリティ階層:

| ラベル | 内容 |
|---|---|
| `Q1_low` | 低ボラ |
| `Q2_lower` | やや低ボラ |
| `Q3_mid` | 中ボラ |
| `Q4_higher` | やや高ボラ |
| `Q5_high` | 高ボラ |

確認する問い:

- 高ボラ時の急落は本当に反発しやすいか
- 反発幅が大きくても MAE が大きすぎないか
- SOL の結果が外れ値依存になっていないか
- BTC / ETH / SOL で同じ構造が見えるか

出力:

- `vol_regime_summary.csv`
- `shock_mean_reversion_by_vol_summary.csv`
- `fig_06_vol_regime_future_abs_return_h6.png`
- `fig_07_lower5_mr_by_vol.png`

## 9. Phase 4: 次足始値エントリーと MAE/MFE

終値で急落を判定し、同じ終値で買うことは実売買では再現できない。

そのため、実売買寄りの簡易確認では以下を標準にする。

| 項目 | 内容 |
|---|---|
| シグナル | 4時間足終値で急落判定 |
| エントリー | 次の4時間足始値 |
| 決済 | 24H / 48H / 72H の時間決済 |
| 方向 | 急落後ロングを中心に検証 |

評価項目:

- 次足始値ベースのリターン
- 勝率
- Profit Factor
- MAE
- MFE
- 最大DD
- 簡易エクイティカーブ
- ドローダウン曲線

この段階では、平均リターンがプラスでも途中逆行が大きすぎる候補を落とす。

出力:

- `path_risk_summary.csv`
- `path_risk_events.csv`
- `simple_backtest_summary.csv`
- `simple_backtest_events.csv`
- `fig_08_path_risk_mae_mfe.png`
- `fig_09_simple_equity_curve.png`
- `fig_10_simple_drawdown_curve.png`

## 10. Phase 5: 年別安定性

目的は、特定年だけの外れ値依存を避けることである。

年別に確認する対象:

- 急落後ロング候補
- 急騰後ショート候補
- ボラティリティ階層付き候補
- 次足始値エントリー候補

対象年:

- 2020
- 2021
- 2022
- 2023
- 2024
- 2025
- 2026

注意点:

- SOL は 2020年途中からなので、2020年の件数は少ない。
- 2026年も 2026-05-29 までの途中年として扱う。
- 年別成績が極端に偏る候補は、記事では強く主張しない。

出力:

- `annual_condition_summary.csv`
- `fig_11_annual_condition_summary.png`

## 11. Phase 6: Funding Rate 拡張

Funding データが取得できた後に実施する。

目的は、急落後ロングを Funding 状態で分類し、ロング過熱崩壊と悲観過剰を分けることである。

分類:

| 分類 | 条件例 | 仮説 |
|---|---|---|
| Funding高い + 急落 | Funding 上位20% かつ下位5%急落 | ロング過熱の巻き戻し。急落後ロングは危険な可能性 |
| Funding低い/マイナス + 急落 | Funding 下位20%またはマイナス、かつ下位5%急落 | ショート過熱または悲観過剰。反発しやすい可能性 |
| Funding中立 + 急落 | 中央60%かつ下位5%急落 | 価格ショック単体の平均回帰を観察 |

追加出力:

- `funding_profile.csv`
- `shock_mr_by_funding_summary.csv`
- `fig_12_lower5_mr_by_funding.png`

## 12. Phase 7: Open Interest / 清算拡張

Open Interest と清算データが取得できた後に実施する。

目的は、急落を「投げ売り完了」と「清算連鎖の途中」に分けることである。

OI分類:

| 価格変化 | OI変化 | 解釈仮説 |
|---|---|---|
| 上昇 | OI増加 | 新規ロング流入。上昇継続の可能性 |
| 上昇 | OI減少 | ショートカバー。上昇一服の可能性 |
| 下落 | OI増加 | 新規ショート増加、またはロング捕まり。下落継続リスク |
| 下落 | OI減少 | デレバレッジや清算後。反発余地の可能性 |

清算分類:

| 条件 | 仮説 |
|---|---|
| 急落 + ロング清算急増 + OI減少 | 強制売りが一巡し、短期反発しやすい可能性 |
| 急落 + ロング清算急増 + OI増加 | 新規ショートも入り、下落継続リスク |
| 急騰 + ショート清算急増 + OI減少 | ショートカバー一巡で反落しやすい可能性 |
| 急騰 + ショート清算急増 + OI増加 | 新規ロング流入で上昇継続の可能性 |

追加出力:

- `oi_profile.csv`
- `liquidation_profile.csv`
- `shock_mr_by_oi_summary.csv`
- `shock_mr_by_liquidation_summary.csv`
- `fig_13_lower5_mr_by_oi.png`
- `fig_14_liquidation_regime_summary.png`

## 13. 実装予定ファイル

最初に作るべきファイル:

- `run_crypto_crash_rebound_experiment.py`
- `README.md`
- `README.ja.md`

最初に作るべき出力ディレクトリ:

- `outputs/crypto_crash_rebound_ohlcv/`
- `outputs/crypto_crash_rebound_ohlcv/figures/`

記事用の図表を別途整理する場合:

- `save_article_figures.py`
- `outputs/article_figures/`
- `outputs/article_figures/figure_index.md`
- `outputs/article_figures/figure_index.csv`

## 14. 初回実装のスコープ

初回実装では、以下だけを対象にする。

- Phase 0: データ確認
- Phase 1: 分布・モーメント比較
- Phase 2: 急落・急騰イベントスタディ
- Phase 3: ボラティリティ階層別分析
- Phase 4: 次足始値エントリーと MAE/MFE
- Phase 5: 年別安定性

Funding / OI / 清算は、データソースと保存形式を確認してから追加する。

理由:

- 現在の `lab_6` には OHLCV CSV だけがある
- まず無料で再現可能な価格ベース分析を確立する
- Perp 固有データは取得制約、履歴制限、API制限、時刻合わせの問題がある
- 記事としても、Phase 1 で価格だけの限界を示した後に Phase 2 以降の必要性を説明しやすい

## 15. 判定基準

記事で「候補」として扱える条件:

- 件数が極端に少なすぎない
- 平均だけでなく中央値も極端に悪くない
- 勝率または Profit Factor に一定の改善がある
- 年別で特定年だけに依存しすぎない
- 次足始値エントリーでも大きく崩れない
- MAE が想定リターンに対して過大すぎない
- BTC / ETH / SOL のどれか単独の偶然に見えない説明がある

記事で強く主張しない条件:

- 件数が少ない
- 平均が一部の外れ値だけで良い
- 2021年または特定ショック年だけで良い
- 終値エントリーでは良いが次足始値で消える
- SOL 専用の過剰最適化に見える
- コスト、スリッページ、Funding を入れると消えそうな小さい優位性

## 16. 注意点

全期間分位は探索分析としては使えるが、そのまま売買ルールに使うと未来情報を含む。

実売買寄りの検証では、以下のどちらかを使う。

- 過去365日ローリング分布
- 過去1000本ローリング分布

また、終値シグナルと同時終値エントリーは禁止する。標準は、シグナル足確定後の次足始値エントリーとする。

Perpetual Futures として記事を書く場合は、最終的に Funding を損益に入れる必要がある。特に24時間以上保有する検証では Funding の影響を無視しない。

## 17. 想定される記事結論の型

実験前の段階では、結論を断定しない。

想定される結論の型は以下である。

> BTC・ETH・SOL の急落後リターンを比較すると、価格だけでも平均回帰の候補が見つかる可能性はある。
> しかし、暗号資産市場では急落の意味が一つではない。
> Funding Rate が高い状態での急落、Open Interest が積み上がったままの急落、清算が連鎖している急落は、単なる押し目ではなく、レバレッジ解消の途中かもしれない。
> したがって、暗号資産のクオンツ分析では、価格分布だけでなく、Funding Rate・Open Interest・清算を組み合わせて「買ってよい急落」と「買ってはいけない急落」を分ける必要がある。

この計画書の次の作業は、`run_crypto_crash_rebound_experiment.py` を作成し、Phase 0 から Phase 5 までの OHLCV ベース出力を再生成可能にすることである。
