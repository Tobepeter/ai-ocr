"""为Docling默认RapidOCR模型名链接已有用户级权重"""
import json
import subprocess
from pathlib import Path
from ocr_runtime import rapid_models, tool_python


def main():
  source = rapid_models()
  code = 'import json,rapidocr;from pathlib import Path;print(json.dumps(str(Path(rapidocr.__file__).parent/"models")))'
  target = Path(json.loads(subprocess.check_output([tool_python('docling'), '-c', code], text=True)))
  for name in ['ch_PP-OCRv4_det_mobile.onnx', 'ch_PP-OCRv4_rec_mobile.onnx', 'ch_ppocr_mobile_v2.0_cls_mobile.onnx']:
    src, dst = source / name, target / name
    if not src.is_file():
      raise SystemExit(f'已有RapidOCR模型缺失：{src}')
    if dst.is_symlink():
      if dst.resolve() != src.resolve():
        raise SystemExit(f'已有不同链接，未覆盖：{dst}')
    elif dst.exists():
      print(f'保留已有文件：{dst}')
      continue
    else:
      dst.symlink_to(src)
    print(f'{dst.name} -> {src}')


if __name__ == '__main__':
  main()
