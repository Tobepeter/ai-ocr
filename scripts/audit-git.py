"""在临时Git目录审计候选文件，不初始化项目或改动全局配置"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output', type=Path)
  args = parser.parse_args()
  with tempfile.TemporaryDirectory(prefix='ocr-git-audit-') as folder:
    subprocess.run(['git', 'init', '-q', folder], check=True)
    git = ['git', '--git-dir', str(Path(folder)/'.git'), '--work-tree', str(ROOT)]
    result = subprocess.check_output([*git, 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    names = sorted(x for x in result.decode().split('\0') if x)
    if args.output:
      output = args.output.resolve()
      names = [n for n in names if (ROOT/n).resolve() != output]
    probes = ['.temp/notes.md', '.venv/bin/python', 'data/input/customer.png', 'data/outputs/run/report.json',
      'data/reports/benchmark-v3.json', 'data/reports/shareable/benchmark-v3-summary.json',
      'data/fixtures/synthetic-mixed/input.png', 'uv.lock', 'configs/rapid-models.json', '.env', 'model.onnx']
    policies = {}
    for name in probes:
      checked = subprocess.run([*git, 'check-ignore', '--no-index', '-q', name], cwd=ROOT)
      if checked.returncode not in [0, 1]:
        raise RuntimeError(f'git check-ignore失败：{name}')
      policies[name] = 'ignored' if checked.returncode == 0 else 'candidate'
  files = [{'path': name, 'bytes': (ROOT/name).stat().st_size} for name in names if (ROOT/name).is_file()]
  report = {'scope': 'candidate files under current project and global ignore rules; not staged or committed',
    'count': len(files), 'bytes': sum(f['bytes'] for f in files), 'ignore_probes': policies, 'files': files}
  if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
  print(json.dumps({k: report[k] for k in ['count', 'bytes', 'ignore_probes']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
  main()
