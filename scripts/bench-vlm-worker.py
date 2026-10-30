"""MLX文档视觉模型裸模型对照；固定提示词，不假称完整布局流水线"""
import importlib.metadata,json,os,signal,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/outputs/bench-20261030b'
engine,phase=sys.argv[1:];out=BASE/engine/phase;out.mkdir(parents=True,exist_ok=True)
def write(name,data):
 p=out/(name+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n');tmp.replace(p)
def alarm(*_):raise TimeoutError('case timeout 180s')
started=time.time();t=time.perf_counter()
import mlx.core as mx
mx.set_memory_limit(16*1024**3)
mx.set_cache_limit(1024**3)
from mlx_vlm import load,generate
from mlx_vlm.prompt_utils import apply_chat_template
spec=next(r for r in json.loads((BASE/'setup/vlm-models.json').read_text()) if r['engine']==engine and r['status']=='ok')
model,processor=load(spec['path'])
prompt='Text Recognition:' if engine=='glm' else 'OCR:'
formatted=apply_chat_template(processor,model.config,prompt,num_images=1)
config=dict(mlx_memory_limit_gib=16,mlx_cache_limit_gib=1,engine=engine,model=spec,device='Metal GPU',prompt=prompt,max_tokens=8192,temperature=0,clear_mlx_cache_after_case=True,mode='whole-image standalone model; no external layout detector')
write('setup',dict(config=config,versions={p:importlib.metadata.version(p) for p in ['mlx-vlm','mlx','transformers']},init_seconds=time.perf_counter()-t))
signal.signal(signal.SIGALRM,alarm)
def infer(path):
 mx.reset_peak_memory()
 r=generate(model,processor,formatted,image=[str(path)],max_tokens=8192,temperature=0,verbose=False)
 tokens=getattr(r,'generation_tokens',None)
 result=dict(text=r.text,status='truncated' if tokens and tokens>=8192 else 'ok',generation_tokens=tokens,prompt_tokens=getattr(r,'prompt_tokens',None),generation_tps=getattr(r,'generation_tps',None),mlx_peak_bytes=mx.get_peak_memory())
 mx.clear_cache();return result
warm=time.perf_counter();signal.alarm(180)
try:r=infer(ROOT/'data/outputs/bench-20261030/inputs/omni-003.png');write('warmup',dict(seconds=time.perf_counter()-warm,status=r['status']))
finally:signal.alarm(0)
rows=[r for r in json.loads((BASE/'inputs.json').read_text())['cases'] if r['phase']==phase];summaries=[]
for row in rows:
 write('current',{'case_id':row['case_id']});t=time.perf_counter();signal.alarm(175)
 try:r=infer(ROOT/row['prepared_path'])
 except Exception as e:r=dict(text='',status='error',error=repr(e));mx.clear_cache()
 finally:signal.alarm(0)
 r.update(case_id=row['case_id'],seconds=time.perf_counter()-t,prepared_sha256=row['prepared_sha256']);write(row['case_id'],r)
 summaries.append({k:r[k] for k in ['case_id','seconds','status']});print(engine,row['case_id'],r['status'],round(r['seconds'],2),len(r['text']),flush=True)
write('summary',dict(engine=engine,complete=True,count=len(rows),total_seconds=time.time()-started,results=summaries))
