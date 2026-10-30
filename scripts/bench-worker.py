"""单引擎进程，保留原始结果、失败、加载与逐样本时间"""
import argparse
import importlib.metadata
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path
from ocr_runtime import rapid_models

root=Path(__file__).resolve().parents[1]
base=root/os.environ.get('OCR_BENCH_DIR','data/outputs/bench-20261030')
os.environ.update(OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',VECLIB_MAXIMUM_THREADS='4',PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK='True',TOKENIZERS_PARALLELISM='false')


def serial(x):
 if hasattr(x,'tolist'):return x.tolist()
 if hasattr(x,'item'):return x.item()
 return str(x)


def write(path,data):
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=serial)+'\n')


def alarm(signum,frame):
 raise TimeoutError('单样本超过120秒')


def main():
 p=argparse.ArgumentParser();p.add_argument('engine',choices=['rapid','paddle','tesseract','easy','docling']);p.add_argument('--phase',default='preflight');args=p.parse_args()
 folder=base/args.engine/args.phase;folder.mkdir(parents=True,exist_ok=True)
 rows=[r for r in json.loads((base/'inputs.json').read_text())['cases'] if r['phase']==args.phase]
 started=time.time();t=time.perf_counter();config={'device':'cpu','threads':4};versions={}
 for pkg in ['rapidocr','paddleocr','paddlepaddle','easyocr','docling','torch','onnxruntime','Pillow']:
  try:versions[pkg]=importlib.metadata.version(pkg)
  except importlib.metadata.PackageNotFoundError:pass
 if args.engine=='rapid':
  from rapidocr import RapidOCR
  cache=rapid_models()
  params={'EngineConfig.onnxruntime.intra_op_num_threads':4,'EngineConfig.onnxruntime.inter_op_num_threads':1,'Det.model_path':str(cache/'ch_PP-OCRv4_det_infer.onnx'),'Rec.model_path':str(cache/'ch_PP-OCRv4_rec_infer.onnx'),'Cls.model_path':str(cache/'ch_ppocr_mobile_v2.0_cls_infer.onnx')}
  model=RapidOCR(params=params);config.update(params)
  def infer(path):
   r=model(str(path));return {'text':'\n'.join(r.txts or []),'boxes':r.boxes,'scores':r.scores,'engine_elapsed':r.elapse}
 elif args.engine=='paddle':
  from paddleocr import PaddleOCR
  config.update(det='PP-OCRv5_mobile_det',rec='PP-OCRv5_mobile_rec',doc_orientation=False,unwarping=False,line_orientation=False,mkldnn=False)
  model=PaddleOCR(text_detection_model_name=config['det'],text_recognition_model_name=config['rec'],text_detection_model_dir=str(Path.home()/'.paddlex/official_models'/config['det']),text_recognition_model_dir=str(Path.home()/'.paddlex/official_models'/config['rec']),use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu',enable_mkldnn=False,cpu_threads=4)
  def infer(path):
   results=list(model.predict(str(path)));raw=[r.json for r in results]
   return {'text':'\n'.join(txt for r in raw for txt in r.get('res',r).get('rec_texts',[])),'raw':raw}
 elif args.engine=='tesseract':
  versions['tesseract']=subprocess.check_output(['tesseract','--version'],text=True).splitlines()[0]
  config.update(language='chi_sim+chi_tra+eng',psm=3,oem=1)
  def infer(path):
   r=subprocess.run(['tesseract',str(path),'stdout','-l',config['language'],'--psm','3','--oem','1'],capture_output=True,text=True,timeout=120,check=True)
   return {'text':r.stdout,'stderr':r.stderr}
 elif args.engine=='easy':
  import torch
  torch.set_num_threads(4)
  import easyocr
  config.update(languages=['ch_sim','en'],model_dir=str(Path.home()/'.EasyOCR/model'),batch_size=8)
  model=easyocr.Reader(config['languages'],gpu=False,verbose=False)
  def infer(path):
   r=model.readtext(str(path),detail=1,batch_size=8,workers=0,paragraph=False)
   return {'text':'\n'.join(v[1] for v in r),'raw':r}
 else:
  import torch
  torch.set_num_threads(4)
  from docling.datamodel.base_models import InputFormat
  from docling.datamodel.pipeline_options import PdfPipelineOptions,RapidOcrOptions
  from docling.datamodel.accelerator_options import AcceleratorOptions,AcceleratorDevice
  from docling.document_converter import DocumentConverter,PdfFormatOption,ImageFormatOption
  options=PdfPipelineOptions(do_ocr=True,do_table_structure=True)
  cache=rapid_models()
  options.ocr_options=RapidOcrOptions(force_full_page_ocr=True,det_model_path=str(cache/'ch_PP-OCRv4_det_infer.onnx'),rec_model_path=str(cache/'ch_PP-OCRv4_rec_infer.onnx'),cls_model_path=str(cache/'ch_ppocr_mobile_v2.0_cls_infer.onnx'),rapidocr_params={'EngineConfig.onnxruntime.intra_op_num_threads':4,'EngineConfig.onnxruntime.inter_op_num_threads':1})
  options.accelerator_options=AcceleratorOptions(num_threads=4,device=AcceleratorDevice.CPU)
  model=DocumentConverter(format_options={InputFormat.IMAGE:ImageFormatOption(pipeline_options=options),InputFormat.PDF:PdfFormatOption(pipeline_options=options)})
  config.update(ocr='RapidOCR',tables=True)
  def infer(path):
   r=model.convert(path);doc=r.document
   return {'text':doc.export_to_markdown(),'raw':doc.export_to_dict(),'conversion_status':str(r.status),'status':'ok' if str(r.status)=='ConversionStatus.SUCCESS' else 'error','table_count':len(doc.tables)}
 load=time.perf_counter()-t
 write(folder/'setup.json',dict(engine=args.engine,versions=versions,config=config,init_seconds=load,started_unix=started))
 signal.signal(signal.SIGALRM,alarm)
 # 不在评价集中的开发图预热，首次模型下载可能包含于预热，独立记录
 warm=root/'data/outputs/bench-20261030/inputs/omni-003.png';t=time.perf_counter()
 signal.alarm(180)
 try:infer(warm);warm_status='ok'
 except Exception as e:warm_status=repr(e)
 finally:signal.alarm(0)
 warm_seconds=time.perf_counter()-t
 write(folder/'warmup.json',dict(seconds=warm_seconds,status=warm_status))
 print('READY',args.engine,round(load,2),round(warm_seconds,2),warm_status,flush=True)
 results=[]
 for row in rows:
  write(folder/'current.json',{'case_id':row['case_id']})
  t=time.perf_counter();signal.alarm(120)
  try:result=infer(root/row['prepared_path']);result.setdefault('status','ok')
  except Exception as e:result={'status':'error','error':repr(e),'text':''}
  finally:signal.alarm(0)
  result.update(case_id=row['case_id'],seconds=time.perf_counter()-t,prepared_sha256=row['prepared_sha256'])
  write(folder/(row['case_id']+'.json'),result);results.append({k:result[k] for k in ['case_id','status','seconds']})
  print(args.engine,row['case_id'],result['status'],round(result['seconds'],3),len(result['text']),flush=True)
 write(folder/'summary.json',dict(engine=args.engine,complete=True,count=len(results),init_seconds=load,warmup_seconds=warm_seconds,total_seconds=time.time()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,results=results))


if __name__=='__main__':main()
