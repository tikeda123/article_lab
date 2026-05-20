# USDJPY 60分足 簡易PBO検証 実験レポート

## 実験条件

- instrument: USDJPY
- timeframe: 60 minutes
- source_file: USDJPY60(29).csv
- experiment_period: 2020-01-01 00:00 <= timestamp < 2026-01-01 00:00
- strategy_family: Moving-average cross, long if short MA > long MA, short if short MA < long MA
- short_ma: 5, 10, 20, 30
- long_ma: 50, 100, 150, 200
- sl_options: none, ATR 1.0, ATR 1.5
- tp_options: none, ATR 1.5, ATR 2.0
- atr_period: 14
- candidate_count: 144
- entry_timing: Signal at confirmed close; execution at next bar open
- position_rule: Single position; long/short; reverse on opposite signal; re-enter allowed after SL/TP on next bar
- intrabar_sl_tp_rule: If both SL and TP are touched in one bar, stop-loss is prioritized conservatively
- transaction_cost: Round trip 1.0 pip; side cost 0.0050 JPY
- annualization_bars: 6048
- cscv_blocks: 8
- is_blocks_per_combo: 4
- oos_blocks_per_combo: 4
- combo_count: 70

## データ品質

### 入力全体
- rows: 100000
- start: 2010-03-18 18:00
- end: 2026-04-02 12:00
- duplicate_timestamps: 0
- non_monotonic_steps: 0
- ohlc_invalid_rows: 0
- gaps_over_1h_count: 859
- max_gap_hours: 73.0
- note: Forex weekend/holiday gaps are counted as gaps; no interpolation was applied.

### 実験対象期間
- rows: 37430
- start: 2020-01-01 22:00
- end: 2025-12-31 21:00
- duplicate_timestamps: 0
- non_monotonic_steps: 0
- ohlc_invalid_rows: 0
- gaps_over_1h_count: 318
- max_gap_hours: 73.0
- note: Forex weekend/holiday gaps are counted as gaps; no interpolation was applied.

## 主要結果

- 戦略候補数: 144
- CSCV組み合わせ数: 70
- 簡易PBO（IS最良がOOS中央値以下）: 5.71%
- OOS損失確率: 35.71%
- 選択戦略の平均IS Sharpe: 0.7474
- 選択戦略の平均OOS Sharpe: 0.1187
- 選択戦略のOOS順位平均: 32.43 / 144

## フルサンプル上位5戦略

| rank | strategy_id | Sharpe | CumReturn | MaxDD | Trades | WinRate |
|---:|---|---:|---:|---:|---:|---:|
| 1 | ma_s20_l50_sl_none_tp_none | 0.5717 | 35.4514% | -10.1280% | 786 | 38.17% |
| 2 | ma_s20_l50_sl_atr1_5_tp_none | 0.5396 | 31.9305% | -10.2501% | 1659 | 30.08% |
| 3 | ma_s10_l50_sl_atr1_5_tp_none | 0.5088 | 29.4069% | -11.2661% | 1715 | 29.15% |
| 4 | ma_s10_l50_sl_none_tp_none | 0.4990 | 29.8721% | -17.2286% | 938 | 34.97% |
| 5 | ma_s10_l50_sl_atr1_0_tp_none | 0.4543 | 25.3168% | -12.2720% | 2271 | 24.39% |

## 解釈

簡易PBOは50%未満でした。ただし、PBOが低いだけで将来の収益性が保証されるわけではありません。別期間のHoldout、WFO、DryRun、コスト・スリッページ再評価が必要です。

## 生成ファイル

- candidate_summary.csv: 144戦略のフルサンプル評価
- pbo_results.csv: 70通りのIS/OOS検証結果
- pnl_matrix.csv.gz: T×Nの損益行列
- best_strategy_timeseries.csv: フルサンプルSharpe最良戦略の時系列
- figures/*.png: 記事用図表
- results_summary.json: KPIと実験条件