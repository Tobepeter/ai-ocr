"""独立批次、顺序推理和进程树资源监控"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil
from ocr_runtime import tool_python

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ['rapid', 'apple', 'mineru', 'docling']


def prepare(run_dir, manifest, pages_manifest, engines):
  # 所有只读校验先完成；目录独占创建成功后才允许写入
  if run_dir.exists():
    raise FileExistsError(f'批次目录已存在，拒绝覆盖：{run_dir}')
  reference = manifest.read_bytes()
  regions = json.loads(reference)['cases']
  pages = json.loads(pages_manifest.read_text())['cases']
  rows = [{**r, 'prepared_path': r['input_path'], 'prepared_sha256': r['sha256'],
    'phase': 'full', 'suite': 'region'} for r in regions]
  rows += [{**r, 'suite': 'page'} for r in pages if r['phase'] == 'full']
  ids = [r['case_id'] for r in rows]
  if len(ids) != len(set(ids)) or any(Path(k).name != k or k in ['setup', 'summary', 'exit', 'current'] for k in ids):
    raise ValueError('样本ID重复或包含保留名称/路径')
  warmup = next(r for r in pages if r['case_id'] == 'omni-003')
  for row in [*rows, warmup]:
    if hashlib.sha256((ROOT / row['prepared_path']).read_bytes()).hexdigest() != row['prepared_sha256']:
      raise ValueError(f'输入哈希不一致：{row["case_id"]}')
  inputs = {'run_id': run_dir.name, 'created': time.strftime('%Y-%m-%d'), 'engines': engines,
    'reference_manifest_sha256': hashlib.sha256(reference).hexdigest(),
    'warmup_path': warmup['prepared_path'], 'cases': rows}
  run_dir.parent.mkdir(parents=True, exist_ok=True)
  run_dir.mkdir()  # 不能使用exist_ok，避免并发运行共享同一批次
  (run_dir / 'reference.json').write_bytes(reference)
  (run_dir / 'inputs.json').write_text(json.dumps(inputs, ensure_ascii=False, indent=2))
  return inputs


def stop_process(process):
  # 即使主worker已退出，也清理同组内遗留子进程
  try:
    os.killpg(process.pid, signal.SIGTERM)
  except ProcessLookupError:
    pass
  try:
    process.wait(timeout=5)
  except subprocess.TimeoutExpired:
    pass
  try:
    os.killpg(process.pid, signal.SIGKILL)
  except ProcessLookupError:
    pass
  process.wait()


def run_command(command, out, env=None):
  started = time.monotonic()
  peak, peaks, reason, process = 0, {}, None, None
  current, changed = 'setup', started
  monitor_error = None
  try:
    with (out / 'process.log').open('x') as log:
      process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True)
      proc = psutil.Process(process.pid)
      while process.poll() is None:
        now = time.monotonic()
        try:
          rss = 0
          for child in [proc, *proc.children(recursive=True)]:
            try:
              rss += child.memory_info().rss
            except psutil.NoSuchProcess:
              pass
          peak = max(peak, rss)
          marker = out / 'current.json'
          if marker.exists():
            key = json.loads(marker.read_text())['case_id']
            if key != current:
              current, changed = key, now
          peaks[current] = max(peaks.get(current, 0), rss)
          if rss > 24 * 1024**3 or now-changed > (600 if current == 'setup' else 200):
            reason = 'resource_or_timeout_limit'
            break
        except (psutil.NoSuchProcess, json.JSONDecodeError):
          pass
        time.sleep(.05)
  except KeyboardInterrupt:
    reason = 'interrupted'
    raise
  except BaseException as error:
    reason, monitor_error = 'runner_error', repr(error)
    raise
  finally:
    if process is not None:
      stop_process(process)
    data = {'exit_code': process.returncode if process else None,
      'wall_seconds': time.monotonic()-started, 'peak_tree_rss_bytes': peak,
      'case_peak_tree_rss_bytes': peaks, 'sampling_interval_seconds': .05,
      'stop_reason': reason, 'monitor_error': monitor_error, 'command': command}
    # 当前目录由main独占，退出证据即使中断也要保存
    with (out / 'exit.json').open('x') as file:
      json.dump(data, file, indent=2)
  return data


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--run-dir', required=True, type=Path)
  parser.add_argument('--regions', type=Path, default=ROOT / 'data/manifests/recognition60-v3.json')
  parser.add_argument('--pages', type=Path, default=ROOT / 'data/outputs/bench-20261030/inputs.json')
  parser.add_argument('--engines', nargs='+', choices=ENGINES, default=ENGINES)
  args = parser.parse_args()
  if len(args.engines) != len(set(args.engines)):
    parser.error('引擎不能重复')
  run_dir = args.run_dir.resolve()
  inputs = prepare(run_dir, args.regions.resolve(), args.pages.resolve(), args.engines)
  binary = run_dir / 'vision-batch'
  if 'apple' in args.engines:
    subprocess.run(['swiftc', '-O', str(ROOT / 'scripts/bench-vision.swift'), '-o', str(binary)], check=True)
  env = {**os.environ, 'OMP_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4', 'VECLIB_MAXIMUM_THREADS': '4'}
  failed = False
  for engine in args.engines:
    out = run_dir / engine
    out.mkdir()
    if engine == 'apple':
      command = [str(binary), str(run_dir / 'inputs.json'), str(out), str(ROOT), 'full', inputs['warmup_path']]
    else:
      python = tool_python({'rapid': 'rapidocr', 'mineru': 'mineru', 'docling': 'docling'}[engine])
      command = [python, str(ROOT / 'scripts/bench-v3-worker.py'), engine, '--run-dir', str(run_dir)]
    data = run_command(command, out, env)
    failed |= data['exit_code'] != 0 or data['stop_reason'] is not None
    print(engine, data['exit_code'], round(data['wall_seconds'], 2), flush=True)
  return 1 if failed else 0


if __name__ == '__main__':
  def interrupt(signum, frame):
    raise KeyboardInterrupt
  signal.signal(signal.SIGTERM, interrupt)
  try:
    sys.exit(main())
  except KeyboardInterrupt:
    sys.exit(130)
