1. 記事で検証すべき中心仮説

記事の主張は、次の3つに絞るのがよいです。

仮説1：
2年金利差の「水準」だけでは、FXトレードの根拠として弱い。

仮説2：
2年金利差の「変化」と「傾き」は、価格トレンドの説明力を持つ可能性がある。

仮説3：
価格トレンドと2年金利差トレンドが一致している局面はトレンドフォロー向き、
乖離している局面は平均回帰・警戒・見送り向きになりやすい。

つまり、実験の目的は、

2年金利差は売買シグナルではなく、トレンドフォロー・平均回帰・見送りを分けるフィルターとして有効か

を検証することです。

2. FX Nexusから取得すべきデータ
A. 2年金利差データ

最重要です。
取得すべき列は以下です。

項目	用途
pair	通貨ペア
observation_date	金利データの日付
base_currency	base通貨
quote_currency	quote通貨
base_yield_percent	base通貨の2年金利
quote_yield_percent	quote通貨の2年金利
yield_spread_bp	2年金利差の水準
spread_change_1d_bp	1日変化
spread_change_5d_bp	5日変化
spread_change_20d_bp	20日変化
spread_slope_20d_bp_per_day	20日傾き
spread_z_252	過去1年比の極端度
price_return_20d_bp	20日価格リターン
price_trend_confirmation	価格と金利差の方向確認
rate_trend_bias	long_base / short_base / neutral
quality_status	データ品質

これらは pair_yield_spread_features に相当する中核列です。FX Nexus側でも、金利差水準、1日・5日・20日変化、20日傾き、252日zスコア、価格20日リターン、価格確認、金利バイアス、品質ステータスが特徴量として定義されています。

取得元は以下です。

DuckDB:
pair_yield_spread_features

API:
GET /api/rates/yield-spreads?tenor=2Y&limit=10000

Runbook上でも、金利差特徴量は pair_yield_spread_features table に保存され、APIでは /api/rates/yield-spreads から取得できる設計です。

B. 通貨別2年金利データ

記事内で「なぜこのペアの金利差が拡大したのか」を説明するには、ペアの金利差だけでなく、通貨別の2年金利も必要です。

項目	用途
currency	通貨
observation_date	観測日
yield_percent	2年金利
source	データソース
quality_status	データ品質
loaded_at	取得時刻

取得元は以下です。

DuckDB:
sovereign_yields

API:
GET /api/rates/sovereign-yields?tenor=2Y&limit=10000

これは記事の図表で、例えば

USD 2Y
JPY 2Y
USDJPY 2Y spread

を並べるために使います。

C. 価格データ

2年金利差だけでは記事になりません。
必ず価格データと結合します。

取得すべき価格データは以下です。

項目	用途
pair	通貨ペア
timestamp	時刻
open	始値
high	高値
low	安値
close	終値
timeframe	60m / 1d など
return_1d	1日リターン
return_5d	5日リターン
return_10d	10日リターン
return_20d	20日リターン
forward_return_5d	5日後リターン
forward_return_10d	10日後リターン
forward_return_20d	20日後リターン
MFE	最大順行幅
MAE	最大逆行幅

時間足は、記事用にはまず 1d がよいです。
2年金利は日次データなので、最初から60分足に細かく落とすと、読者にとって実験意図が見えにくくなります。

ただし、実運用寄りにするなら 60mにforward fill して、日次金利差が60分足トレードの環境認識に使えるかを検証します。

おすすめは2段構えです。

実験1：
1d価格 × 日次2年金利差

実験2：
60m価格 × 日次2年金利差をforward fill
D. 価格と金利差の一致・乖離データ

記事で最も重要なのはここです。

取得すべき分類は以下です。

分類	意味
aligned_long_base	価格上昇、金利差拡大、傾き上向き
aligned_short_base	価格下落、金利差縮小、傾き下向き
divergent	価格と金利差が逆方向
neutral	判定不能または条件不足

FX Nexus上でも、価格リターン、5日金利差変化、20日傾きの符号によって aligned_long_base、aligned_short_base、divergent、neutral を判定しています。

取得元は以下です。

API:
GET /api/graph/alignment?tenor=2Y&date=latest

または、過去時系列として使うなら pair_yield_spread_features から自前で同じ分類を再計算します。

記事では、この分類を使って以下を検証します。

aligned_long_base の後、base通貨は上がりやすいか
aligned_short_base の後、base通貨は下がりやすいか
divergent の後、価格は反転しやすいか
neutral は本当に優位性が弱いか
E. レジーム・ボラティリティ・歪み・流動性データ

2年金利差だけで検証すると、記事が浅くなります。
「効く局面」と「効かない局面」を分けるために、以下も取得します。

データ	用途
regime_map_60m.json	トレンド相場かレンジ相場か
graph_network_60m.json	通貨強弱
inefficiency_ranking_60m.json	フェアバリュー乖離
factor_neutral_60m.json	ファクター中立後の歪み
lead_lag_60m.json	リード・ラグ
session_liquidity_60m.json	流動性・時間帯
executable_triangles_60m.json	三角裁定・相対価値
strategy_bias_evidence_60m.json	日次戦略バイアス用の統合証跡

日次戦略バイアス用テンプレートでも、これらのファイル群を証跡として参照し、2Y金利差はトレンドフォロー、キャリー継続、乖離監視の文脈として使う設計になっています。

3. 実験用マスターデータの作り方

最終的には、以下のような1行1観測のテーブルを作ります。

基本単位
pair × date

または、60m検証なら、

pair × timestamp
マスターテーブル例
列	内容
pair	通貨ペア
date	日付
close_t	当日終値
ret_5d_past	過去5日リターン
ret_20d_past	過去20日リターン
fwd_ret_5d	5日後リターン
fwd_ret_10d	10日後リターン
fwd_ret_20d	20日後リターン
yield_spread_bp	2年金利差
spread_change_5d_bp	5日金利差変化
spread_change_20d_bp	20日金利差変化
spread_slope_20d_bp_per_day	20日傾き
spread_z_252	252日zスコア
alignment	aligned / divergent / neutral
rate_trend_bias	long_base / short_base / neutral
quality_status	ok / stale / missing
regime	trend / range / high_vol など
vol_percentile	ボラティリティ水準
residual_z	フェアバリュー乖離
cost_bp	取引コスト
event_flag	重要イベント前後か

このテーブルが作れれば、記事に必要な検証はほぼできます。

4. 実験設計
実験1：2年金利差の「水準」は効くのか
目的

高金利通貨を買えばよい、という単純な考えを検証します。

方法

yield_spread_bp を分位で分けます。

低金利差
中立
高金利差
極端な高金利差

それぞれについて、将来リターンを比較します。

5日後リターン
10日後リターン
20日後リターン
見る指標
平均リターン
中央値リターン
勝率
Sharpe
最大DD
外れ値依存
想定される記事上の結論

おそらく、水準だけでは安定しない可能性が高いです。

記事では、

高金利通貨を買うだけでは遅い。市場はすでにその金利差を織り込んでいる可能性がある。

という結論に使えます。

実験2：2年金利差の「変化」は効くのか
目的

金利差の水準より、変化のほうが価格トレンドと関係するかを検証します。

方法

以下の指標を使います。

spread_change_1d_bp
spread_change_5d_bp
spread_change_20d_bp
spread_slope_20d_bp_per_day

特に中心にするのは、

spread_change_5d_bp
spread_slope_20d_bp_per_day

です。

分類例
金利差が5日で+10bp以上拡大
金利差が5日で-10bp以下縮小
それ以外
見る指標
その後5日・10日・20日の価格リターン
価格トレンド継続率
最大逆行幅
最大順行幅
記事上の結論候補

FXで効きやすいのは、金利差の絶対水準よりも、金利差の変化方向である。

実験3：価格と金利差が一致している局面はトレンドフォロー向きか
目的

記事の中心仮説を検証します。

分類
aligned_long_base
aligned_short_base
neutral
ルール例
aligned_long_base:
  base通貨ロング

aligned_short_base:
  base通貨ショート

neutral:
  ノーポジション
保有期間
5日
10日
20日
見る指標
平均リターン
勝率
Sharpe
最大DD
損益分布
MFE
MAE
記事上の見せ方

ここは図表にすると強いです。

分類	5日後平均	10日後平均	20日後平均	勝率	最大DD
aligned_long_base	TODO	TODO	TODO	TODO	TODO
aligned_short_base	TODO	TODO	TODO	TODO	TODO
neutral	TODO	TODO	TODO	TODO	TODO
結論候補

価格と金利差が同じ方向を向く局面では、トレンドフォローの説明力が高まる。

実験4：価格と金利差が乖離している局面は平均回帰向きか
目的

divergent が逆張り・警戒・見送りの材料になるかを検証します。

分類
価格上昇 + 金利差縮小
価格下落 + 金利差拡大
検証パターン
パターンA：単純逆張り
価格上昇 + 金利差縮小
→ short base

価格下落 + 金利差拡大
→ long base
パターンB：フェアバリュー乖離を追加
divergent
+ residual_z が極端
+ レンジまたは低ボラ
→ 平均回帰候補
見る指標
反転率
平均回帰までの日数
最大逆行幅
勝率
損益分布
イベント時の失敗率
重要な注意

ここは、単独では弱い可能性があります。
記事ではむしろ、

乖離は即逆張りではなく、「トレンドフォローで追うには疑いが必要」という警告信号である。

と書くと実務的です。

実験5：キャリー継続・キャリー巻き戻しの判定に使えるか
目的

2年金利差が、キャリー継続と巻き戻しのフィルターになるかを検証します。

条件例
キャリー継続候補
yield_spread_bp がプラス
spread_change_5d_bp もプラス
価格も上昇
ボラティリティが低〜中程度
キャリー巻き戻し候補
yield_spread_bp はまだプラス
しかし spread_change_5d_bp がマイナス
価格も下落
ボラティリティ上昇
見る指標
高金利通貨ロングの継続成績
金利差縮小後のドローダウン
ボラティリティ上昇時の崩れ方
記事上の結論候補

キャリーで重要なのは、いま高金利かどうかではなく、その金利優位が市場に維持されると見られているかである。

実験6：レジーム別に効き方を分ける
目的

2年金利差が効く局面と効かない局面を分けます。

レジーム分類
トレンド相場
レンジ相場
高ボラ相場
リスクオフ相場
イベント前後
低流動性時間帯
比較
全期間
トレンド相場のみ
レンジ相場のみ
高ボラ除外
イベント前後除外
USDJPY除外
クロス円のみ
ドルストレートのみ
見る指標
平均リターン
Sharpe
最大DD
勝率
テール損失
記事上の結論候補

2年金利差は、平常時のトレンド説明には有効でも、リスクオフやイベント直後には機能が落ちる可能性がある。

5. 必ず入れるべきリーク防止ルール

この実験では、未来情報を使わないことが重要です。

ルール
1. observation_date の金利データは、その日の取引判断に即使わない
2. 保守的には、T日の金利データはT+1から利用する
3. 60m検証では、日次2年金利をforward fillするが、利用開始時刻を明示する
4. stale / missing / proxy のデータは別集計、または除外する
5. 価格のforward return計算に、同日終値以降の情報を混ぜない

特に quality_status は必ず使うべきです。
金利差データには stale の可能性があり、過去検証でも stale 入力は日次レポートで明示すべきとされています。

6. 記事に載せるべき図表
図表1：2年金利差と価格の時系列

対象例：

USDJPY
EURUSD
AUDJPY

表示するもの：

価格
2年金利差
金利差5日変化

目的：

価格トレンドが金利差と同方向に動く局面と、乖離する局面を視覚的に見せる。

図表2：金利差5日変化別の将来リターン

横軸：

spread_change_5d_bp の分位

縦軸：

forward_return_10d

目的：

金利差の水準よりも、変化が効くかを見せる。

図表3：alignment分類別の成績

分類：

aligned_long_base
aligned_short_base
divergent
neutral

指標：

平均リターン
勝率
Sharpe
最大DD

目的：

価格と金利差の一致・乖離が戦略選択に使えるかを示す。

図表4：divergent局面の平均回帰テスト

分類：

価格上昇 + 金利差縮小
価格下落 + 金利差拡大

指標：

5日後反転率
10日後反転率
平均損益
最大逆行幅

目的：

乖離は即逆張りではないが、追随に警戒が必要な局面であることを示す。

図表5：レジーム別の有効性

分類：

trend regime
range regime
high-vol regime
event window

目的：

2年金利差が効く局面と効かない局面を分ける。

7. 実験の最終アウトプット

記事を書くために、最終的には以下の5つを出せば十分です。

1. 2年金利差の水準だけで将来リターンを説明できるか

2. 2年金利差の5日変化・20日傾きは将来リターンと関係するか

3. 価格と金利差が一致している局面はトレンドフォローに有利か

4. 価格と金利差が乖離している局面は平均回帰・見送りに使えるか

5. レジーム、ボラティリティ、イベントリスクで有効性は変わるか
8. 実験骨子の最終形
実験タイトル：
FXにおける2年金利差はトレード戦略のフィルターとして有効か

目的：
2年金利差の水準・変化・価格トレンドとの一致/乖離が、
トレンドフォロー、平均回帰、キャリー継続、見送り判断に使えるかを検証する。

対象：
USDJPY, EURUSD, EURJPY, GBPUSD, GBPJPY, AUDUSD, AUDJPY, CADJPY, CHFJPY

期間：
2年金利データと価格データが重なる期間。
まずは2021年6月以降を基本にする。

時間足：
第1段階：1d
第2段階：60mに日次金利差をforward fill

説明変数：
yield_spread_bp
spread_change_1d_bp
spread_change_5d_bp
spread_change_20d_bp
spread_slope_20d_bp_per_day
spread_z_252
alignment
rate_trend_bias
quality_status
regime
volatility
residual_z
cost

目的変数：
forward_return_5d
forward_return_10d
forward_return_20d
MFE
MAE
drawdown

検証1：
金利差水準別の将来リターン

検証2：
金利差変化別の将来リターン

検証3：
alignment分類別のトレンドフォロー成績

検証4：
divergent分類別の平均回帰成績

検証5：
レジーム別・ボラティリティ別・イベント除外後の頑健性

評価指標：
平均リターン
中央値リターン
勝率
Sharpe
最大DD
損益分布
コスト控除後期待値
ペア別安定性
期間別安定性

リーク防止：
T日の金利データは原則T+1以降に利用
stale / missingは除外または別集計
60mでは日次金利差を保守的にforward fill
9. 記事化するときの結論パターン

結果が良ければ、こう書けます。

2年金利差の水準そのものよりも、5日変化と20日傾きの方が価格トレンドの説明に使いやすい。
特に価格トレンドと金利差トレンドが一致している局面では、トレンドフォローの監視対象として有効である。

結果が微妙でも、記事として成立します。

2年金利差だけでは安定した売買シグナルにはならない。
しかし、価格トレンドが金利市場に支えられているか、あるいは金利差では説明しづらい動きなのかを分けるフィルターとしては有用である。

むしろ後者のほうが、クオンツ記事として信頼されます。