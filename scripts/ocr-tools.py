"""调用用户级OCR CLI；不创建项目模型环境"""
import os
import shutil
import sys


def main():
  if len(sys.argv) < 2 or sys.argv[1] not in ['rapid', 'docling', 'mineru']:
    raise SystemExit('用法：python3 scripts/ocr-tools.py {rapid|docling|mineru} [CLI参数...]')
  engine = sys.argv[1]
  names = {'rapid': 'rapidocr', 'docling': 'docling', 'mineru': 'mineru-kit'}
  command = shutil.which(names[engine])
  if not command:
    raise SystemExit(f'未找到 {names[engine]}，请按 docs/cli-setup.md 安装用户级工具')
  args = sys.argv[2:]
  if engine == 'mineru':
    os.environ.setdefault('MINERU_MODEL_SMALL_BACKEND', 'onnx')
    os.environ.setdefault('MINERU_MODEL_ONNX_DEVICE', 'cpu')
    args = ['parse', *args]
    if '--tier' not in args and not any(x.startswith('--tier=') for x in args):
      args += ['--tier', 'basic']
  elif engine == 'docling':
    args = ['convert', *args]
    if '--ocr-engine' not in args and not any(x.startswith('--ocr-engine=') for x in args):
      args += ['--ocr-engine', 'rapidocr']
  os.execv(command, [command, *args])


if __name__ == '__main__':
  main()
