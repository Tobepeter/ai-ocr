"""主测完成后追加单行模式诊断；不替换固定主测结果"""
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path
from ocr_runtime import rapid_models
os.environ.update(OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',VECLIB_MAXIMUM_THREADS='4')
from rapidocr import RapidOCR
root=Path(__file__).resolve().parents[1];base=root/'data/outputs/bench-20261030'
s=importlib.util.spec_from_file_location('score',root/'scripts/bench-score.py');sc=importlib.util.module_from_spec(s);s.loader.exec_module(sc)
cache=rapid_models()
model=RapidOCR(params={'EngineConfig.onnxruntime.intra_op_num_threads':4,'EngineConfig.onnxruntime.inter_op_num_threads':1,'Det.model_path':str(cache/'ch_PP-OCRv4_det_infer.onnx'),'Rec.model_path':str(cache/'ch_PP-OCRv4_rec_infer.onnx'),'Cls.model_path':str(cache/'ch_ppocr_mobile_v2.0_cls_infer.onnx')})
rows=[r for r in json.loads((root/'data/manifests/balanced60.json').read_text())['cases'] if r['dataset']=='ReCTS'];out=[]
for row in rows:
 path=base/'inputs'/(row['case_id']+'.png');truth=json.loads((root/row['reference_path']).read_text())['row']['answers']
 for engine in ['rapid-rec-only','tesseract-psm7']:
  t=time.perf_counter()
  if engine=='rapid-rec-only':
   r=model(str(path),use_det=False,use_cls=False,use_rec=True);pred='\n'.join(r.txts or [])
  else:pred=subprocess.check_output(['tesseract',str(path),'stdout','-l','chi_sim+eng','--psm','7'],stderr=subprocess.DEVNULL,text=True,timeout=30)
  out.append(dict(engine=engine,case_id=row['case_id'],text=pred,reference=truth,seconds=time.perf_counter()-t,errors=sc.distance(sc.norm(truth),sc.norm(pred)),reference_chars=len(sc.norm(truth))))
(base/'cropped-diagnostic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for e in ['rapid-rec-only','tesseract-psm7']:
 rs=[r for r in out if r['engine']==e];print(e,sum(r['errors'] for r in rs)/sum(r['reference_chars'] for r in rs),[(r['reference'],r['text']) for r in rs])
