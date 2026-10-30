"""在用户级工具环境识别单图，结果写文件，日志与文本分离"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from ocr_runtime import rapid_models


def load_engine(engine):
  for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '4'
  os.environ['MINERU_MODEL_SMALL_BACKEND'] = 'onnx'
  os.environ['MINERU_MODEL_ONNX_DEVICE'] = 'cpu'
  start = time.perf_counter()
  if engine == 'rapid':
    from rapidocr import RapidOCR
    cache = rapid_models()
    model = RapidOCR(params={
      'Det.model_path': str(cache / 'ch_PP-OCRv4_det_infer.onnx'),
      'Rec.model_path': str(cache / 'ch_PP-OCRv4_rec_infer.onnx'),
      'Cls.model_path': str(cache / 'ch_ppocr_mobile_v2.0_cls_infer.onnx'),
      'EngineConfig.onnxruntime.intra_op_num_threads': 4,
      'EngineConfig.onnxruntime.inter_op_num_threads': 1,
    })
    def infer(source):
      result = model(source)
      return {'text': '\n'.join(result.txts or []), 'boxes': result.boxes, 'scores': result.scores}
  elif engine == 'mineru':
    from mineru.parser import parse
    def infer(source):
      result = parse(source, tier='basic', ocr_mode='ocr')
      return {'text': result.markdown(), 'raw': result.to_dict()}
  else:
    import torch
    torch.set_num_threads(4)
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.document_converter import DocumentConverter, ImageFormatOption
    cache = rapid_models()
    opts = PdfPipelineOptions(do_ocr=True, do_table_structure=True)
    opts.ocr_options = RapidOcrOptions(force_full_page_ocr=True,
      det_model_path=str(cache/'ch_PP-OCRv4_det_infer.onnx'),
      rec_model_path=str(cache/'ch_PP-OCRv4_rec_infer.onnx'),
      cls_model_path=str(cache/'ch_ppocr_mobile_v2.0_cls_infer.onnx'))
    opts.accelerator_options = AcceleratorOptions(num_threads=4, device=AcceleratorDevice.CPU)
    model = DocumentConverter(format_options={InputFormat.IMAGE: ImageFormatOption(pipeline_options=opts)})
    def infer(source):
      result = model.convert(source)
      if result.status.value != 'success':
        raise RuntimeError(f'Docling转换状态：{result.status}')
      return {'text': result.document.export_to_markdown(), 'raw': result.document.export_to_dict()}
  return infer, time.perf_counter() - start


def main():
  engine, source, dest = sys.argv[1:]
  infer, loaded = load_engine(engine)
  start = time.perf_counter()
  result = infer(source)
  result.update(seconds=time.perf_counter()-start, load_seconds=loaded)
  def serial(value):
    return value.tolist() if hasattr(value, 'tolist') else str(value)
  Path(dest).write_text(json.dumps(result, ensure_ascii=False, default=serial))


if __name__ == '__main__':
  main()
