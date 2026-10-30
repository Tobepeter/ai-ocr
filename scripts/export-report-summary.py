"""从详细评测证据导出可版本管理的数值汇总，不复制原文和本机路径"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summarize(report):
  models = {}
  for name, row in report['models'].items():
    setup, exit_data = row.get('setup', {}), row.get('exit', {})
    models[name] = {key: row[key] for key in ['complete', 'groups', 'by_dataset', 'region_timing', 'page_timing', 'region_failed', 'region_empty', 'page_failed', 'page_empty'] if key in row}
    models[name]['runtime'] = {
      'versions': setup.get('versions', {}), 'os': setup.get('os'),
      'vision_revision': setup.get('revision'), 'load_seconds': setup.get('load_seconds'),
      'warmup_seconds': row.get('warmup', {}).get('seconds'),
      **{key: exit_data.get(key) for key in ['exit_code', 'wall_seconds', 'peak_tree_rss_bytes', 'sampling_interval_seconds', 'stop_reason']}}
  return {key: report[key] for key in ['run_id', 'date', 'complete', 'policy', 'reference_sha256', 'metric_code_sha256'] if key in report} | {
    'scope': 'aggregate metrics only; no reference text, prediction text, raw outputs or local commands',
    'models': models}


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('input', type=Path)
  parser.add_argument('output', type=Path)
  args = parser.parse_args()
  result = summarize(json.loads(args.input.read_text()))
  args.output.parent.mkdir(parents=True, exist_ok=True)
  with args.output.open('x') as file:
    file.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
  print(args.output)


if __name__ == '__main__':
  main()
