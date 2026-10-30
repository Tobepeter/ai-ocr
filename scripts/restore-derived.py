"""按冻结清单恢复派生图，不重新选样，不覆盖已有证据"""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
  return hashlib.sha256(data).hexdigest()


def restore(target, expected, generate):
  if target.exists():
    if digest(target.read_bytes()) != expected:
      raise ValueError(f'现有文件哈希不同，未覆盖：{target}')
    return False
  data = generate()
  if digest(data) != expected:
    raise ValueError(f'重建哈希不同，未写入：{target}；检查Pillow/Poppler版本，不要修改冻结哈希')
  target.parent.mkdir(parents=True, exist_ok=True)
  with target.open('xb') as file:
    file.write(data)
  return True


def raster(source, box=None):
  if source.suffix.lower() == '.pdf':
    with tempfile.TemporaryDirectory(prefix='ocr-raster-') as folder:
      prefix = Path(folder) / 'page'
      subprocess.run(['pdftoppm', '-f', '1', '-singlefile', '-scale-to', '2000', '-png', str(source), str(prefix)], check=True, capture_output=True)
      return prefix.with_suffix('.png').read_bytes()
  with Image.open(source) as image:
    image = image.convert('RGB')
    if box:
      image = image.crop(box)
    image.thumbnail((2000, 2000), Image.Resampling.BICUBIC if box else Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def main():
  prepared = json.loads((ROOT / 'data/manifests/prepared66-v1.json').read_text())
  regions = json.loads((ROOT / 'data/manifests/recognition60-v3.json').read_text())['cases']
  parents = {r['case_id']: r for r in prepared['cases']}
  for row in prepared['cases']:
    source = ROOT / row['input_path']
    if digest(source.read_bytes()) != row['sha256']:
      raise ValueError(f'原始物料不同：{source}；先运行restore-current.py')
  restored = 0
  for row in prepared['cases']:
    restored += restore(ROOT / row['prepared_path'], row['prepared_sha256'], lambda r=row: raster(ROOT / r['input_path']))
  for row in regions:
    source = ROOT / parents[row['parent_case_id']]['input_path']
    # 区域初次生成采用Pillow默认thumbnail(BICUBIC)，包括无box的ReCTS
    def crop(r=row, src=source):
      with Image.open(src) as image:
        image = image.convert('RGB')
        if r['crop_box']:
          image = image.crop(r['crop_box'])
        image.thumbnail((2000, 2000))
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
    restored += restore(ROOT / row['input_path'], row['sha256'], crop)
  inputs = ROOT / 'data/outputs/bench-20261030/inputs.json'
  if inputs.exists():
    existing = json.loads(inputs.read_text())
    def signatures(rows):
      return {(r['case_id'], r['prepared_path'], r['prepared_sha256'], r['phase']) for r in rows}
    if signatures(existing['cases']) != signatures(prepared['cases']):
      raise ValueError('现有inputs.json与冻结清单不一致，未覆盖')
  else:
    inputs.parent.mkdir(parents=True, exist_ok=True)
    with inputs.open('x') as file:
      file.write(json.dumps(prepared, ensure_ascii=False, indent=2)+'\n')
  print(f'66张整图与60个区域已校验，本次重建{restored}张；已有文件未覆盖')


if __name__ == '__main__':
  main()
