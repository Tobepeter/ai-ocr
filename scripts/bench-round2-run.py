"""串行运行第二轮，采样进程树RSS并保留资源中止原因"""
import json,os,statistics,subprocess,sys,time
from pathlib import Path
import psutil
from ocr_runtime import tool_python
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/outputs/bench-20261030b';INPUT=ROOT/'data/outputs/bench-20261030/inputs.json'

def run(engine,phase):
 out=BASE/engine/phase;out.mkdir(parents=True,exist_ok=True)
 if (out/'exit.json').exists() and json.loads((out/'exit.json').read_text())['exit_code']==0 and (out/'summary.json').exists():return True
 if engine=='vision':cmd=[str(BASE/'setup/vision-ocr'),str(INPUT),str(out),str(ROOT),phase]
 elif engine in ['glm','paddlevl']:cmd=[str(ROOT/'.venv-mlx/bin/python'),str(ROOT/'scripts/bench-vlm-worker.py'),engine,phase]
 elif engine=='mineru':cmd=[tool_python('mineru'),str(ROOT/'scripts/bench-mineru-worker.py'),phase]
 else:cmd=[sys.executable,str(ROOT/'scripts/bench-worker.py'),engine,'--phase',phase]
 env=os.environ.copy();env.update(OCR_BENCH_DIR='data/outputs/bench-20261030b',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',VECLIB_MAXIMUM_THREADS='4',MINERU_MODEL_SMALL_BACKEND='onnx',MINERU_MODEL_ONNX_DEVICE='cpu')
 t=time.time();peak=0;case_peaks={};reason=None;case_id='setup';case_start=t;lastfile=None
 with (out/'process.log').open('w') as log:
  p=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);proc=psutil.Process(p.pid)
  while p.poll() is None:
   try:
    tree=[proc]+proc.children(recursive=True);rss=sum(x.memory_info().rss for x in tree if x.is_running());peak=max(peak,rss)
    marker=out/'current.json'
    if marker.exists():
     key=json.loads(marker.read_text()).get('case_id','setup')
     if key!=case_id:case_id=key;case_start=time.time()
    case_peaks[case_id]=max(case_peaks.get(case_id,0),rss)
    if rss>24*1024**3:reason='process_tree_rss_over_24GiB'
    elif case_id!='setup' and time.time()-case_start>180:reason='case_over_180s'
    elif time.time()-t>(2400 if phase=='full' else 1200):reason='phase_wall_timeout'
    if reason:
     import signal
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=8)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL)
     break
   except (psutil.NoSuchProcess,psutil.AccessDenied,json.JSONDecodeError):pass
   time.sleep(.2)
  code=p.wait()
 data=dict(exit_code=code,wall_seconds=time.time()-t,peak_tree_rss_bytes=peak,case_peak_tree_rss_bytes=case_peaks,stop_reason=reason,sampling_interval_seconds=.2)
 (out/'exit.json').write_text(json.dumps(data,indent=2)+'\n');print(engine,phase,data['exit_code'],round(data['wall_seconds'],2),round(peak/1024**3,2),reason,flush=True)
 return code==0 and (out/'summary.json').exists()

for engine in sys.argv[1:]:
 if not run(engine,'preflight'):continue
 s=json.loads((BASE/engine/'preflight/summary.json').read_text());rs=s['results']
 if sum(r['status']=='ok' for r in rs)>=5 and statistics.median(r['seconds'] for r in rs)<=30:run(engine,'full')
 else:print('PREFLIGHT_ONLY',engine,flush=True)
