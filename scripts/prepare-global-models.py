"""初始化用户级Rapid权重并验证冻结哈希，兼容历史模型名"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from ocr_runtime import rapid_models, tool_python

ROOT = Path(__file__).resolve().parents[1]


def main():
  python = tool_python('rapidocr')
  config = json.loads((ROOT / 'configs/rapid-models.json').read_text())
  subprocess.run([python, '-c', 'from importlib.metadata import version; import sys; assert version("rapidocr")==sys.argv[1], "RapidOCR版本不符"', config['rapidocr_version']], check=True)
  models = rapid_models()
  if any(not (models / row['name']).is_file() for row in config['models']):
    # 首次由官方包下载默认PP-OCRv4 mobile模型；只落用户工具缓存
    subprocess.run([python, '-c', 'from rapidocr import RapidOCR; RapidOCR()'], check=True)
  for row in config['models']:
    source = models / row['name']
    if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
      raise ValueError(f'模型哈希与基准不同，未修改：{source}')
    alias = models / row['legacy_alias']
    if alias.exists():
      if hashlib.sha256(alias.read_bytes()).hexdigest() != row['sha256']:
        raise ValueError(f'已有模型不同，未覆盖：{alias}')
    elif alias.is_symlink():
      raise ValueError(f'已有失效链接，未覆盖：{alias}')
    else:
      alias.symlink_to(source.name)
  subprocess.run([sys.executable, str(ROOT / 'scripts/link-ocr-models.py')], check=True)
  print('用户级模型已核对，历史模型名和Docling共享路径已就绪')


if __name__ == '__main__':
  main()
