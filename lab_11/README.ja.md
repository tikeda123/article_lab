# lab_11: FX 2年金利差トレンドフィルター

English: [README.md](README.md)

このラボは、Qiita記事「[FXは2年金利差でどこまで説明できるのか？ ― 水準ではなく「変化の向き」で見るトレンドフィルター](https://qiita.com/tikeda123/items/2bf3c18cbec6b4f3527a)」に対応する実験パッケージである。

EURUSD と USDJPY を対象に、2年国債利回り差が価格トレンドをどこまで説明できるかを検証する。中心テーマは、2年金利差を単独の売買シグナルとして使えるかではなく、価格トレンドが金利市場に支えられている局面と、追随を疑うべき局面を切り分けるフィルターとして使えるかである。

このラボは投資助言ではなく、本番運用可能な売買システムでもない。記事用の根拠を再現可能な形で確認するための教育用診断パッケージである。

## 構成

`lab_11` の出力はこのディレクトリ内に保存する。ただし再生成には、ローカルの FX Nexus DuckDB と財務省の historical JGB CSV が必要である。

| 種類 | 場所 |
|---|---|
| 公開記事 | [FXは2年金利差でどこまで説明できるのか？ ― 水準ではなく「変化の向き」で見るトレンドフィルター](https://qiita.com/tikeda123/items/2bf3c18cbec6b4f3527a) |
| 記事ベースメモ | `article_base.md` |
| 実験設計メモ | `lab_base.md` |
| 実験コード | `run_yield_spread_experiment.py` |
| 正本出力 | `outputs/yield_spread_filter/` |
| 主レポート | `outputs/yield_spread_filter/report/analysis_report.ja.md` |

## データ依存

| ソース | 用途 |
|---|---|
| FX Nexus `ohlcv` | EURUSD / USDJPY の日次終値 |
| FX Nexus `sovereign_yields` | USD / EUR の2年国債利回り |
| 財務省 historical JGB CSV | JPY 2年国債利回り履歴 |
| FX Nexus `regime_features` | トレンド、レンジ、ボラティリティ、キャリー局面 |
| FX Nexus `market_distortion_features` | ペア残差、フェアバリュー乖離、歪み |
| FX Nexus `inefficiency_features` | コスト、候補ステータス、イベントリスク |

リーク防止として、T日の金利特徴量は価格データへ結合するときにT+1以降にだけ使う。

## 実験内容

| 実験 | ファイル | 問い |
|---|---|---|
| データカバレッジ | `tables/data_coverage.csv` | どの通貨、ペア、期間が使えるか |
| 金利差水準 | `tables/experiment1_yield_level_bucket.csv` | 高金利通貨を買うだけでよいのか |
| 金利差変化 | `tables/experiment2_spread_change_bucket.csv` | 水準より変化方向のほうが効くのか |
| 価格と金利差の一致 | `tables/experiment3_alignment_trend_follow.csv` | 価格と金利差が同方向ならトレンドフォローしやすいか |
| 乖離 | `tables/experiment4_divergence_mean_reversion.csv` | 価格と金利差の乖離は逆張り材料か、警告信号か |
| レジーム別 | `tables/experiment5_regime_robustness.csv` | ボラティリティや局面で効き方が変わるか |
| 最新状態 | `tables/latest_snapshot.csv` | 最新時点のペア状態はどうなっているか |

## 実験環境

必要な外部パッケージは以下である。

```text
duckdb
numpy
pandas
requests
```

## 再現コマンド

リポジトリルートから実行する。

```bash
python3 lab_11/run_yield_spread_experiment.py
```

FX Nexus DB が既定位置にない場合は、環境変数で明示する。

```bash
FX_NEXUS_ROOT=/path/to/fx_nexus \
FX_NEXUS_DB=/path/to/fx_nexus/var/fx_nexus.duckdb \
python3 lab_11/run_yield_spread_experiment.py
```

現在のスクリプトは `lab_11/outputs/yield_spread_filter/` に直接出力する。

## 主な出力

| ファイル | 内容 |
|---|---|
| `outputs/yield_spread_filter/data/master_daily.csv` | T+1シフト後の日次ペア別マスターデータ |
| `outputs/yield_spread_filter/data/experiment_sample_daily.csv` | 5日、10日、20日先リターンを計算できる検証サンプル |
| `outputs/yield_spread_filter/data/raw/*.csv` | 検査用に保存した金利・金利差のソースデータ |
| `outputs/yield_spread_filter/tables/data_coverage.csv` | データ期間、行数、品質の確認表 |
| `outputs/yield_spread_filter/tables/experiment1_yield_level_bucket.csv` | 金利差水準別の結果 |
| `outputs/yield_spread_filter/tables/experiment2_spread_change_bucket.csv` | 金利差変化別の結果 |
| `outputs/yield_spread_filter/tables/experiment3_alignment_trend_follow.csv` | 価格と金利差の一致局面におけるトレンド追随結果 |
| `outputs/yield_spread_filter/tables/experiment4_divergence_mean_reversion.csv` | 乖離局面の平均回帰診断 |
| `outputs/yield_spread_filter/tables/experiment5_regime_robustness.csv` | レジーム・ボラティリティ別の結果 |
| `outputs/yield_spread_filter/figures/*.svg` | 記事説明用の図表 |
| `outputs/yield_spread_filter/report/analysis_report.ja.md` | 記事根拠として使う日本語分析レポート |
| `outputs/yield_spread_filter/experiment_metadata.json` | データソース、期間、リーク防止、行数のメタデータ |

## 主要結果

この実験は、2年金利差を直接のエントリーシグナルではなく、相場環境フィルターとして扱う記事の主張に沿う結果になっている。

現在の出力では、金利差の拡大局面が両ペアで最も強い10日コスト控除後リターンを示した。EURUSD の `spread_expanding` は +28.09bp、USDJPY の `spread_expanding` は +56.98bp である。一方、金利差の水準だけを見ると安定性は弱い。EURUSD は高金利差バケットが良いが、USDJPY は低位から中低位のほうが強く、最高位バケットは悪化している。

価格と金利差の一致では、USDJPY が最も明確である。`aligned_long_base` は10日で +42.83bp、20日で +74.09bp だった。一方、EURUSD の一致効果は限定的で、より複数要因が混ざるペアとして扱う必要がある。乖離は即逆張りの合図ではなく、価格トレンドを金利差で説明しにくいという警告信号として読むのが実務的である。

## 解釈上の注意

- サンプルは2021年6月以降であり、コロナ後から利上げ局面に偏った短い期間である。
- USDJPY の JPY 2Y 履歴は、ローカル FX Nexus の履歴不足を補うため、財務省CSVから補助した。
- 表中の最大DDは、イベントリターンを累積した診断値であり、実運用ポートフォリオの最大DDではない。
- 価格と金利差の一致は、トレンドを信じやすいかを見るためのフィルターであり、単独のエントリールールではない。
- ペア構造の差は大きい。今回のサンプルでは USDJPY のほうが2年金利差フィルターに素直に反応している。
