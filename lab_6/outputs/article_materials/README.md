# Lab 6 Article Materials

作成日: 2026-05-30

このディレクトリは、Lab 6 の BTC/ETH/SOL 4H OHLCV 急落後リバウンド分析を記事化するための素材集です。実験計画、再現コード、元データ、各 Phase の分析レポート、要約 CSV、イベント明細、記事用に番号を付け直した図を一か所に集めています。

## Directory Layout

- `planning/`: 実験計画、記事計画、再現用 Python スクリプト
- `source_data/`: BTC/ETH/SOL の 4H OHLCV、Funding Rate、Open Interest の取得データ
- `reports/`: Phase 1 から Phase 7 までの分析レポート
- `tables/`: 記事で引用しやすい集計 CSV
- `event_tables/`: 個別イベント単位の明細 CSV
- `figures/`: 記事掲載用に `figure01` から採番した PNG

## Recommended Reading Order

1. `reports/article_experiment_summary.md`: 実験全体の要約
2. `reports/phase1_moment_analysis_report.md`: 分布、歪度、尖度、極端リターン
3. `reports/phase2_event_study_analysis_report.md`: 急落後リバウンドのイベントスタディ
4. `reports/phase3_vol_regime_interpretation_report.md`: ボラティリティ階層別の解釈
5. `reports/phase4_next_open_path_risk_interpretation_report.md`: 次足始値エントリー、MAE/MFE、簡易バックテスト
6. `reports/phase5_annual_stability_report.md`: 年次安定性
7. `reports/phase6_funding_rate_interpretation_report.md`: Funding Rate 条件の解釈
8. `reports/phase7_oi_liquidation_interpretation_report.md`: Open Interest / 清算拡張の解釈と限界

## Index Files

- `figure_index.csv`: 記事用図版の対応表
- `table_index.csv`: 主要 CSV の用途一覧
- `report_index.csv`: レポートの役割一覧
- `source_data_index.csv`: 元データの用途一覧

## Article Notes

- 急落後の平均回帰は、単純な「大きく下げたら買う」だけでは不十分で、ボラティリティ、年次安定性、執行後の MAE/MFE、Funding Rate、Open Interest を組み合わせて評価する必要がある。
- Phase 4 の次足始値エントリーは、終値ベースのイベントスタディより実運用に近いが、ドローダウンと逆行幅の確認が重要になる。
- Phase 6 の Funding Rate は先物由来のデータであり、OHLCV が現物系列の場合は市場構造の差を注記する。
- Phase 7 の Open Interest は取得期間が短いため、記事では補助材料として扱う。清算データは取得制約があり、空または限定的な結果として明記する。
