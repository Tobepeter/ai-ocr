"""复用UI配置、每个引擎独立常驻进程，固定预热后顺序推理"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import signal
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ocr_ui.worker import load_engine


def run(engine, run_dir):
  inputs = json.loads((run_dir / 'inputs.json').read_text())
  out = run_dir / engine
  out.mkdir(exist_ok=True)
  if any(out.glob('*.json')):
    raise FileExistsError(f'引擎目录已有结果，拒绝覆盖：{out}')
  with (out / '.worker-started').open('x') as file:
    file.write(engine)
  def write(name, data):
    temp = out / (name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, default=lambda v: v.tolist() if hasattr(v, 'tolist') else str(v)))
    temp.replace(out / (name + '.json'))
  def alarm(*_):
    raise TimeoutError('case timeout 175s')
  infer, loaded = load_engine(engine)
  packages = {'rapid': ['rapidocr', 'onnxruntime'], 'mineru': ['mineru', 'onnxruntime'], 'docling': ['docling', 'rapidocr', 'onnxruntime', 'torch']}[engine]
  write('setup', {'load_seconds': loaded, 'versions': {p: importlib.metadata.version(p) for p in packages}})
  t = time.perf_counter()
  infer(str(ROOT / inputs['warmup_path']))
  write('warmup', {'seconds': time.perf_counter() - t})
  rows = inputs['cases']
  results = []
  signal.signal(signal.SIGALRM, alarm)
  for row in rows:
    write('current', {'case_id': row['case_id']})
    t = time.perf_counter()
    signal.alarm(175)
    try:
      data = infer(str(ROOT / row['prepared_path']))
      data['status'] = 'ok'
    except Exception as error:
      data = {'status': 'error', 'text': '', 'error': repr(error)}
    finally:
      signal.alarm(0)
    data.update(case_id=row['case_id'], seconds=time.perf_counter()-t, prepared_sha256=row['prepared_sha256'])
    write(row['case_id'], data)
    results.append({k: data[k] for k in ['case_id', 'status', 'seconds']})
    print(engine, row['case_id'], data['status'], round(data['seconds'], 2), flush=True)
  write('summary', {'complete': True, 'count': len(results), 'results': results})

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('engine', choices=['rapid', 'mineru', 'docling'])
  parser.add_argument('--run-dir', required=True, type=Path)
  args = parser.parse_args()
  run(args.engine, args.run_dir.resolve())


if __name__ == '__main__':
  main()
