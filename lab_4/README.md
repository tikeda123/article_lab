# USDJPY 60分足 簡易PBO検証 提出物

## 実験概要

アップロードされた `USDJPY60(29).csv` を使い、2020-01-01 00:00 以上、2026-01-01 00:00 未満のUSDJPY 60分足を対象に、移動平均クロス戦略144候補のバックテストと簡易PBO検証を実施しました。

- 短期MA: 5, 10, 20, 30
- 長期MA: 50, 100, 150, 200
- 損切り: なし, ATR 1.0倍, ATR 1.5倍
- 利確: なし, ATR 1.5倍, ATR 2.0倍
- 取引コスト: 往復1.0 pips
- 約定: 終値確定後にシグナル判定、次足始値で約定
- 検証: 8ブロック、4ブロックIS / 4ブロックOOS、全70通り

## 主要結果

- 簡易PBO: 5.71%
- OOS損失確率: 35.71%
- 選択戦略の平均IS Sharpe: 0.7474
- 選択戦略の平均OOS Sharpe: 0.1187
- 平均OOS順位: 32.43 / 144
- フルサンプルSharpe最良戦略: `ma_s20_l50_sl_none_tp_none`

## ファイル一覧

- `run_backtest_overfitting_experiment.py`: 実験再現用コード
- `create_summary_workbook.py`: Excelサマリー生成用コード
- `experiment_summary.xlsx`: 結果サマリー、候補一覧、PBO結果、データ品質をまとめたExcel
- `candidate_summary.csv`: 144戦略候補のフルサンプル評価
- `pbo_results.csv`: 70通りのIS/OOS検証結果
- `pnl_matrix.csv.gz`: T×Nの損益行列。gzip圧縮CSV
- `best_strategy_timeseries.csv`: フルサンプルSharpe最良戦略の損益時系列
- `results_summary.json`: 実験条件とKPI
- `experiment_report.md`: 短い文章レポート
- `figures/`: 記事用図表6点

## 再現方法

Python 3で以下を実行してください。必要な外部パッケージは `numpy` と `matplotlib` です。

```bash
python run_backtest_overfitting_experiment.py \
  --input /path/to/USDJPY60\(29\).csv \
  --outdir ./backtest_overfitting_submission
```

Excelサマリーはこの環境では `artifact_tool` で生成しています。標準的なPython環境では、まず上記コードでCSVと図表を再生成してください。
