"""用户级uv工具环境定位，复用全局CLI的Python依赖"""
import json
import subprocess
from pathlib import Path


def tool_python(name):
  root = Path(subprocess.check_output(['uv', 'tool', 'dir'], text=True).strip())
  python = root / name / 'bin/python'
  if not python.exists():
    raise RuntimeError(f'缺少用户级工具 {name}，参见 docs/cli-setup.md')
  return str(python)


def rapid_models():
  code = 'import json,rapidocr;from pathlib import Path;print(json.dumps(str(Path(rapidocr.__file__).parent/"models")))'
  return Path(json.loads(subprocess.check_output([tool_python('rapidocr'), '-c', code], text=True)))
