"""独立报告目录：字符错误、执行覆盖率、成功延时与失败耗时"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ocr_eval.metrics import POLICY, plain_text, score

NAMES = {'rapid': 'RapidOCR', 'apple': 'Apple Vision', 'mineru': 'MinerU Basic', 'docling': 'Docling + RapidOCR'}


def aggregate(rows, key='primary'):
  metrics = [r[key] for r in rows]
  sums = {k: sum(m[k] for m in metrics) for k in ['reference_chars', 'errors', 'substitutions', 'deletions', 'insertions']}
  valid = [m['cer'] for m in metrics if m['cer'] is not None]
  return {**sums, 'cer': sums['errors']/sums['reference_chars'] if sums['reference_chars'] else None,
    'macro_cer': statistics.mean(valid) if valid else None,
    'exact_count': sum(m['exact'] for m in metrics), 'count': len(rows)}


def ci(rows):
  if not rows:
    return [None, None]
  groups = defaultdict(list)
  for row in rows:
    groups[row['parent_case_id']].append(row)
  rng = random.Random(20261030)
  values = list(groups.values())
  samples = [aggregate([r for group in rng.choices(values, k=len(values)) for r in group])['cer'] for _ in range(2000)]
  samples = sorted(x for x in samples if x is not None)
  return [samples[max(0, math.ceil(len(samples)*.025)-1)], samples[math.ceil(len(samples)*.975)-1]] if samples else [None, None]


def timing(rows):
  measured = [r for r in rows if r.get('seconds') is not None and r['status'] != 'missing']
  values = sorted(r['seconds'] for r in measured if r['status'] == 'ok')
  return {'expected_count': len(rows), 'attempted_count': sum(r['status'] != 'missing' for r in rows),
    'count': len(values), 'missing_count': sum(r['status'] == 'missing' for r in rows),
    'failed_count': sum(r['status'] not in ['ok', 'missing'] for r in rows),
    'sum_seconds': sum(r['seconds'] for r in measured),
    'failed_seconds': sum(r['seconds'] for r in measured if r['status'] != 'ok'),
    'mean_seconds': statistics.mean(values) if values else None,
    'p50_seconds': statistics.median(values) if values else None,
    'p95_seconds': values[math.ceil(len(values)*.95)-1] if values else None}


def read(path, default):
  return json.loads(path.read_text()) if path.exists() else default


def collect(run_dir):
  inputs = read(run_dir / 'inputs.json', None)
  if inputs is None:
    raise FileNotFoundError(run_dir / 'inputs.json')
  # 兼容旧轮只读重评；新轮始终使用批次内参考快照
  manifest = run_dir / 'reference.json'
  if not manifest.exists():
    manifest = ROOT / 'data/manifests/recognition60-v3.json'
  if inputs['reference_manifest_sha256'] != hashlib.sha256(manifest.read_bytes()).hexdigest():
    raise ValueError('冻结参考哈希不一致')
  references = {r['case_id']: r for r in read(manifest, {})['cases']}
  ids = [r['case_id'] for r in inputs['cases']]
  if len(ids) != len(set(ids)):
    raise ValueError('输入含重复样本')
  for row in inputs['cases']:
    if row['suite'] == 'region':
      frozen = references[row['case_id']]
      if row['reference'] != frozen['reference'] or row['prepared_sha256'] != frozen['sha256']:
        raise ValueError(f'输入中的参考/哈希与冻结快照不一致：{row["case_id"]}')
  all_rows, models = [], {}
  engines = inputs.get('engines', list(NAMES))
  for engine in engines:
    folder = run_dir / engine
    exit_data = read(folder / 'exit.json', {'exit_code': None, 'stop_reason': 'missing_exit', 'case_peak_tree_rss_bytes': {}})
    summary = read(folder / 'summary.json', {})
    rows, pages = [], []
    for item in inputs['cases']:
      data = read(folder / (item['case_id'] + '.json'), {'status': 'missing', 'text': '', 'seconds': None})
      if data['status'] != 'missing' and data['prepared_sha256'] != item['prepared_sha256']:
        raise ValueError(f'{engine}/{item["case_id"]}输入哈希不一致')
      seconds = data.get('seconds')
      if seconds is not None and (not math.isfinite(seconds) or seconds < 0):
        raise ValueError('耗时必须是非负有限数或null')
      # 提取器错误不能归罪于模型；中止评分而非计算伪漏字
      text = plain_text(engine, data) if data['status'] == 'ok' else ''
      row = {'engine': engine, 'case_id': item['case_id'], 'dataset': item['dataset'],
        'language_group': item['language_group'], 'status': data['status'], 'seconds': seconds,
        'empty': not text.strip(), 'plain_text': text,
        'peak_tree_rss_bytes': exit_data.get('case_peak_tree_rss_bytes', {}).get(item['case_id'])}
      if item['suite'] == 'region':
        row.update(parent_case_id=item['parent_case_id'], reference=item['reference'])
        for mode in ['primary', 'alnum', 'spaces', 'han']:
          row[mode] = score(item['reference'], text, mode)
        rows.append(row)
      else:
        pages.append(row)
    groups = {}
    for group in ['chinese-or-mixed', 'english']:
      selected = [r for r in rows if r['language_group'] == group]
      groups[group] = {**aggregate(selected), 'ci95_parent_bootstrap': ci(selected),
        **{key: aggregate(selected, key) for key in ['alnum', 'spaces', 'han']}}
    complete = (exit_data.get('exit_code') == 0 and not exit_data.get('stop_reason')
      and summary.get('complete') is True and summary.get('count') == len(inputs['cases'])
      and all(r['status'] != 'missing' for r in rows + pages))
    models[engine] = {'complete': complete, 'groups': groups,
      'by_dataset': {d: aggregate([r for r in rows if r['dataset'] == d]) for d in sorted({r['dataset'] for r in rows})},
      'region_timing': timing(rows), 'page_timing': timing(pages), 'exit': exit_data,
      'setup': read(folder / 'setup.json', {}), 'warmup': read(folder / 'warmup.json', {}),
      'region_failed': sum(r['status'] != 'ok' for r in rows), 'region_empty': sum(r['empty'] for r in rows),
      'page_failed': sum(r['status'] != 'ok' for r in pages), 'page_empty': sum(r['empty'] for r in pages)}
    all_rows.extend(rows + pages)
  return {'run_id': inputs.get('run_id', run_dir.name), 'complete': all(m['complete'] for m in models.values()),
    'policy': POLICY, 'reference_sha256': inputs['reference_manifest_sha256'],
    'metric_code_sha256': hashlib.sha256((ROOT / 'src/ocr_eval/metrics.py').read_bytes()).hexdigest(),
    'models': models, 'cases': all_rows}


def fmt(value, percent=False):
  return '—' if value is None else (f'{value:.2%}' if percent else f'{value:.3f}')


def markdown(report, report_dir):
  models = report['models']
  attempted = sum(r['status'] != 'missing' for r in report['cases'])
  planned = len(report['cases'])
  protocol = os.path.relpath(ROOT / 'docs/ocr-evaluation-v3.md', report_dir)
  lines = ['# OCR 评测报告', '', f"批次：{report['run_id']} · {'执行完整' if report['complete'] else '未完成（incomplete）'} · 已有结果 {attempted}/{planned} 项", '',
    f'文字区域CER与整图耗时分别统计，不代表整页准确率。[评价协议]({protocol})', '',
    '| 方案 | 状态 | 中混CER↓ | 英文CER↓ | 区域成功均秒 | 整图成功均秒/P95 | 峰值GiB |', '|---|---|---:|---:|---:|---:|---:|']
  for engine, model in models.items():
    groups, page = model['groups'], model['page_timing']
    peak = model['exit'].get('peak_tree_rss_bytes')
    # 中止批次保留JSON诊断，不把局部耗时摆进可比较的主表
    avg = model['region_timing']['mean_seconds'] if model['complete'] else None
    mean, p95 = (page['mean_seconds'], page['p95_seconds']) if model['complete'] else (None, None)
    lines.append(f"| {NAMES[engine]} | {'完整' if model['complete'] else '未完成'} | {fmt(groups['chinese-or-mixed']['cer'], True)} | {fmt(groups['english']['cer'], True)} | {fmt(avg)} | {fmt(mean)}/{fmt(p95)} | {fmt(peak/1024**3 if peak is not None else None)} |")
  lines += ['', 'CER为忽略空白的微平均；失败和缺失按全部漏字计入分母。缺失耗时为null，均值/P50/P95只统计成功且有耗时的样本；中止批次不参与主表速度比较。原始运行时间、预热及逐图数据见report.json', '',
    '| 方案/组 | 参考字数 | S错字 | D漏字 | I多字 | CER区间 | 完全正确 |', '|---|---:|---:|---:|---:|---|---:|']
  for engine, model in models.items():
    for key, group in model['groups'].items():
      lo, hi = group['ci95_parent_bootstrap']
      lines.append(f"| {NAMES[engine]}/{key} | {group['reference_chars']} | {group['substitutions']} | {group['deletions']} | {group['insertions']} | {fmt(lo, True)}–{fmt(hi, True)} | {group['exact_count']}/{group['count']} |")
  lines += ['', '| 方案/输入 | 成功计时/计划 | 失败/缺失 | 已记录总秒 | 失败耗时秒 |', '|---|---:|---:|---:|---:|']
  for engine, model in models.items():
    for key in ['region_timing', 'page_timing']:
      t = model[key]
      lines.append(f"| {NAMES[engine]}/{key} | {t['count']}/{t['expected_count']} | {t['failed_count']}/{t['missing_count']} | {fmt(t['sum_seconds'])} | {fmt(t['failed_seconds'])} |")
  lines += ['', '参考为上游标注与AI目视复核，未经独立双人裁决。语言组按来源页；分来源、纯汉字等辅助指标见JSON。区间按父页bootstrap 2000次，不含参考系统性误差。RSS为50ms进程树采样之和，不等于净物理内存；未测表格结构、公式与整页阅读顺序准确率', '']
  return '\n'.join(lines)


def write_report(report, report_dir):
  report_dir.parent.mkdir(parents=True, exist_ok=True)
  report_dir.mkdir()  # 独占报告目录，不覆写旧评分版本
  (report_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
  with (report_dir / 'cases.csv').open('x') as file:
    fields = ['engine', 'case_id', 'dataset', 'language_group', 'status', 'seconds', 'empty', 'reference_chars', 'substitutions', 'deletions', 'insertions', 'errors', 'cer']
    writer = csv.DictWriter(file, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in report['cases']:
      writer.writerow({**row, **row.get('primary', {})})
  (report_dir / 'report.md').write_text(markdown(report, report_dir))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--run-dir', required=True, type=Path)
  parser.add_argument('--report-dir', type=Path)
  args = parser.parse_args()
  run_dir = args.run_dir.resolve()
  report_dir = args.report_dir.resolve() if args.report_dir else run_dir / 'report'
  if report_dir.exists():
    raise FileExistsError(f'报告目录已存在，拒绝覆盖：{report_dir}')
  report = collect(run_dir)
  write_report(report, report_dir)
  print(report_dir / 'report.md')


if __name__ == '__main__':
  main()
