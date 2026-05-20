# -*- coding: utf-8 -*-
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
from artifact_tool import Workbook, SpreadsheetFile

OUTDIR = Path('/mnt/data/backtest_overfitting_submission')
XLSX_PATH = OUTDIR / 'experiment_summary.xlsx'

def clean(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if math.isfinite(v):
            return v
        return str(v)
    if v is None:
        return ''
    s = str(v)
    # convert numeric-looking values from csv
    if s.lower() in ('true','false'):
        return s.upper() == 'TRUE'
    if s == 'none':
        return s
    try:
        if any(ch in s for ch in ['.', 'e', 'E']) and not s.startswith('0'):
            f = float(s)
            return f if math.isfinite(f) else s
        # Keep timestamp-like strings and semicolon lists intact
        if '-' in s or ':' in s or ';' in s:
            return s
        return int(s)
    except Exception:
        try:
            f = float(s)
            return f if math.isfinite(f) else s
        except Exception:
            return s

def read_csv(path):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    return rows

def rows_to_matrix(rows, fields=None):
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    matrix = [fields]
    for r in rows:
        matrix.append([clean(r.get(k, '')) for k in fields])
    return matrix

def set_header_format(sheet, address):
    r = sheet.get_range(address)
    r.format = {
        'fill': '#1F4E78',
        'font': {'bold': True, 'color': '#FFFFFF'},
        'horizontal_alignment': 'center',
        'vertical_alignment': 'center',
        'wrap_text': True,
    }

def main():
    summary = json.loads((OUTDIR / 'results_summary.json').read_text(encoding='utf-8'))
    candidates = read_csv(OUTDIR / 'candidate_summary.csv')
    pbo = read_csv(OUTDIR / 'pbo_results.csv')

    wb = Workbook.create()
    ws = wb.worksheets.add('Summary')
    cand_ws = wb.worksheets.add('CandidateSummary')
    pbo_ws = wb.worksheets.add('PBOResults')
    dq_ws = wb.worksheets.add('DataQuality')
    files_ws = wb.worksheets.add('OutputFiles')

    # Summary sheet
    ws.get_range('A1:R1').merge()
    ws.get_range('A1').values = [['USDJPY 60分足 簡易PBO検証 サマリー']]
    ws.get_range('A1').format = {
        'fill': '#17365D',
        'font': {'bold': True, 'color': '#FFFFFF', 'size': 16},
        'horizontal_alignment': 'center',
        'vertical_alignment': 'center',
        'row_height': 28,
    }

    kpis = [
        ['KPI', 'Value', 'Notes'],
        ['戦略候補数', summary['n_strategies'], 'MA×SL×TP = 144'],
        ['CSCV組み合わせ数', summary['combinations'], '8ブロックから4ブロックISを選択'],
        ['簡易PBO', summary['pbo_median_or_worse_rate'], 'IS最良がOOS中央値以下になった割合'],
        ['OOS損失確率', summary['oos_loss_probability'], '選択戦略のOOS累積リターンがマイナスの割合'],
        ['平均IS Sharpe', summary['mean_selected_is_sharpe'], 'ISで選ばれた戦略'],
        ['平均OOS Sharpe', summary['mean_selected_oos_sharpe'], '同じ選択戦略のOOS'],
        ['平均OOS順位', summary['mean_oos_rank'], '1=最良、144=最下位'],
    ]
    ws.get_range('A3:C10').values = kpis
    set_header_format(ws, 'A3:C3')
    ws.get_range('B6:B7').format.number_format = '0.00%'
    ws.get_range('B4:B5').format.number_format = '0'
    ws.get_range('B8:B10').format.number_format = '0.0000'
    ws.get_range('A3:C10').format.wrap_text = True

    best = summary['full_sample_best_strategy']
    best_rows = [
        ['Full-sample best strategy', 'Value'],
        ['strategy_id', best['strategy_id']],
        ['Sharpe', best['sharpe']],
        ['Cumulative return', best['cum_return']],
        ['Max drawdown', best['max_drawdown']],
        ['Trade count', best['trade_count']],
        ['Win rate', best['win_rate']],
    ]
    ws.get_range('E3:F9').values = best_rows
    set_header_format(ws, 'E3:F3')
    ws.get_range('F5:F7').format.number_format = '0.00%'
    ws.get_range('F4').format.number_format = '0.0000'
    ws.get_range('F8').format.number_format = '0'
    ws.get_range('F9').format.number_format = '0.00%'

    cond = summary['experiment_conditions']
    cond_items = list(cond.items())
    cond_matrix = [['Condition', 'Value']] + [[k, clean(v)] for k, v in cond_items]
    end_row = 13 + len(cond_matrix) - 1
    ws.get_range(f'A13:B{end_row}').values = cond_matrix
    set_header_format(ws, 'A13:B13')
    ws.get_range(f'A13:B{end_row}').format.wrap_text = True

    top_fields = ['full_sample_rank','strategy_id','full_sample_sharpe','full_sample_cum_return','full_sample_max_drawdown','trade_count','win_rate']
    top_matrix = [['Rank','Strategy','Sharpe','CumReturn','MaxDD','Trades','WinRate']]
    for r in candidates[:10]:
        top_matrix.append([clean(r[f]) for f in top_fields])
    ws.get_range('D13:J23').values = top_matrix
    set_header_format(ws, 'D13:J13')
    ws.get_range('F14:H23').format.number_format = '0.00%'
    ws.get_range('E14:E23').format.number_format = '0.0000'
    ws.get_range('I14:I23').format.number_format = '0'
    ws.get_range('J14:J23').format.number_format = '0.00%'

    # Candidate Summary sheet
    cand_fields = list(candidates[0].keys())
    cand_matrix = rows_to_matrix(candidates, cand_fields)
    cand_ws.get_range_by_indexes(0, 0, len(cand_matrix), len(cand_fields)).values = cand_matrix
    set_header_format(cand_ws, f'A1:O1')
    cand_ws.freeze_panes.freeze_rows(1)
    cand_ws.tables.add(f'A1:O{len(cand_matrix)}', True, 'CandidateSummaryTable')
    cand_ws.get_range('G2:J145').format.number_format = '0.0000'
    cand_ws.get_range('K2:K145').format.number_format = '0'
    cand_ws.get_range('L2:L145').format.number_format = '0.00%'
    cand_ws.get_range('M2:O145').format.number_format = '0.0000'

    # PBO Results sheet
    pbo_fields = list(pbo[0].keys())
    pbo_matrix = rows_to_matrix(pbo, pbo_fields)
    pbo_ws.get_range_by_indexes(0, 0, len(pbo_matrix), len(pbo_fields)).values = pbo_matrix
    set_header_format(pbo_ws, 'A1:T1')
    pbo_ws.freeze_panes.freeze_rows(1)
    pbo_ws.tables.add(f'A1:T{len(pbo_matrix)}', True, 'PBOResultsTable')
    pbo_ws.get_range('J2:M71').format.number_format = '0.0000'
    pbo_ws.get_range('N2:O71').format.number_format = '0.0000'
    pbo_ws.get_range('P2:P71').format.number_format = '0.0000'
    pbo_ws.get_range('Q2:R71').format.number_format = 'General'
    pbo_ws.get_range('T2:T71').format.number_format = '0.0000'

    # Data Quality sheet
    dq_rows = [['Scope', 'Metric', 'Value']]
    for scope_key, label in [('data_quality_full', 'Input full data'), ('data_quality_experiment', 'Experiment period')]:
        for k, v in summary[scope_key].items():
            dq_rows.append([label, k, clean(v)])
    dq_ws.get_range_by_indexes(0, 0, len(dq_rows), 3).values = dq_rows
    set_header_format(dq_ws, 'A1:C1')
    dq_ws.tables.add(f'A1:C{len(dq_rows)}', True, 'DataQualityTable')
    dq_ws.freeze_panes.freeze_rows(1)

    # Output files sheet
    files = [
        ['File', 'Description'],
        ['candidate_summary.csv', '144戦略候補のフルサンプル評価'],
        ['pbo_results.csv', '70通りのIS/OOS検証結果'],
        ['pnl_matrix.csv.gz', 'T×N損益行列（gzip圧縮CSV）'],
        ['best_strategy_timeseries.csv', 'フルサンプルSharpe最良戦略の時系列'],
        ['results_summary.json', '主要KPIと実験条件'],
        ['experiment_report.md', '提出用の文章サマリー'],
        ['figures/*.png', '記事用図表6点'],
        ['run_backtest_overfitting_experiment.py', '再現用コード'],
    ]
    files_ws.get_range_by_indexes(0, 0, len(files), 2).values = files
    set_header_format(files_ws, 'A1:B1')
    files_ws.tables.add(f'A1:B{len(files)}', True, 'OutputFilesTable')

    # Basic visual formatting and widths.
    for sheet in [ws, cand_ws, pbo_ws, dq_ws, files_ws]:
        used = sheet.get_range('A1:R200')
        used.format.wrap_text = True
        used.format.vertical_alignment = 'top'
        used.format.autofit_columns()
        used.format.autofit_rows()

    ws.get_range('A:A').format.column_width = 24
    ws.get_range('B:B').format.column_width = 24
    ws.get_range('C:C').format.column_width = 48
    ws.get_range('E:E').format.column_width = 24
    ws.get_range('F:F').format.column_width = 28
    ws.get_range('D:J').format.column_width = 17
    cand_ws.get_range('B:B').format.column_width = 36
    pbo_ws.get_range('H:H').format.column_width = 36
    pbo_ws.get_range('S:S').format.column_width = 36
    dq_ws.get_range('A:C').format.column_width = 32
    files_ws.get_range('A:A').format.column_width = 34
    files_ws.get_range('B:B').format.column_width = 58

    # Figures are saved as PNG files in the figures/ directory; no embedded chart is added here.

    # Verification snippets
    print(wb.inspect({'kind': 'table', 'range': 'Summary!A1:R25', 'include': 'values,formulas', 'table_max_rows': 25, 'table_max_cols': 18}).ndjson[:2000])
    errors = wb.inspect({'kind': 'match', 'search_term': '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A', 'options': {'use_regex': True, 'max_results': 300}, 'summary': 'final formula error scan'})
    print(errors.ndjson[:1000])
    # Render summary preview for QA
    blob = wb.render({'sheet_name': 'Summary', 'range': 'A1:R25', 'scale': 1})
    blob.save(str(OUTDIR / 'experiment_summary_preview.png'))
    SpreadsheetFile.export_xlsx(wb).save(str(XLSX_PATH))
    print(str(XLSX_PATH))

if __name__ == '__main__':
    main()
