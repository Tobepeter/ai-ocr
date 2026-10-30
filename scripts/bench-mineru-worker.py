"""MinerU Basic本地流水线，不启用远端服务或VLM"""
import importlib.metadata,json,os,signal,sys,time
from pathlib import Path
def main():
 ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/outputs/bench-20261030b';phase=sys.argv[1];out=BASE/'mineru'/phase;out.mkdir(parents=True,exist_ok=True)
 os.environ.update(MINERU_MODEL_SMALL_BACKEND='onnx',MINERU_MODEL_ONNX_DEVICE='cpu',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',VECLIB_MAXIMUM_THREADS='4',MINERU_MODEL_SOURCE='huggingface')
 def write(name,data):
  p=out/(name+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n');tmp.replace(p)
 def alarm(*_):raise TimeoutError('case timeout 175s')
 start=time.time();t=time.perf_counter()
 from mineru.parser import parse
 write('setup',dict(engine='mineru',versions={p:importlib.metadata.version(p) for p in ['mineru','onnxruntime']},config=dict(tier='basic',small_backend='onnx',onnx_device='cpu',threads_env=4,ocr_mode='ocr'),init_seconds=time.perf_counter()-t))
 def infer(path):
  r=parse(str(path),tier='basic',ocr_mode='ocr')
  return dict(text=r.markdown(),raw=r.to_dict(),status='ok')
 # 初次构建可含模型下载，由外层setup总超时控制
 warm=time.perf_counter();r=infer(ROOT/'data/outputs/bench-20261030/inputs/omni-003.png');write('warmup',dict(seconds=time.perf_counter()-warm,status=r['status']))
 signal.signal(signal.SIGALRM,alarm)
 rows=[r for r in json.loads((BASE/'inputs.json').read_text())['cases'] if r['phase']==phase];results=[]
 for row in rows:
  write('current',{'case_id':row['case_id']});t=time.perf_counter();signal.alarm(175)
  try:r=infer(ROOT/row['prepared_path'])
  except Exception as e:r=dict(text='',status='error',error=repr(e))
  finally:signal.alarm(0)
  r.update(case_id=row['case_id'],seconds=time.perf_counter()-t,prepared_sha256=row['prepared_sha256']);write(row['case_id'],r)
  results.append({k:r[k] for k in ['case_id','status','seconds']});print(row['case_id'],r['status'],round(r['seconds'],2),flush=True)
 write('summary',dict(engine='mineru',complete=True,count=len(rows),total_seconds=time.time()-start,results=results))

if __name__ == "__main__":
 main()
