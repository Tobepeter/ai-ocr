"""串行运行引擎，保存退出状态；预检耗时可控才扩至60份"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from ocr_runtime import tool_python

root=Path(__file__).resolve().parents[1]
base=root/'data/outputs/bench-20261030'
def engine_python(engine):
 if engine in ['rapid','paddle','docling']:return tool_python({'rapid':'rapidocr','paddle':'paddleocr','docling':'docling'}[engine])
 return sys.executable


def run(engine,phase):
 folder=base/engine/phase;folder.mkdir(parents=True,exist_ok=True)
 done=folder/'exit.json';summary=folder/'summary.json'
 if done.exists() and summary.exists() and json.loads(done.read_text())['exit_code']==0 and json.loads(summary.read_text()).get('complete'):
  return True
 start=time.time()
 with (folder/'process.log').open('w') as log:
  try:
   r=subprocess.run([engine_python(engine),str(root/'scripts/bench-worker.py'),engine,'--phase',phase],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=1200 if phase=='full' else 420)
   code=r.returncode
  except subprocess.TimeoutExpired:code=124
 done.write_text(json.dumps({'exit_code':code,'wall_seconds':time.time()-start},indent=2)+'\n')
 print(engine,phase,'exit',code,'seconds',round(time.time()-start,2),flush=True)
 return code==0 and summary.exists()


def main():
 p=argparse.ArgumentParser();p.add_argument('engines',nargs='+');args=p.parse_args()
 for engine in args.engines:
  if not run(engine,'preflight'):continue
  result=json.loads((base/engine/'preflight/summary.json').read_text())
  items=result['results'];median=statistics.median(x['seconds'] for x in items)
  if sum(x['status']=='ok' for x in items)>=5 and median<=30:
   run(engine,'full')
  else:print('PREFLIGHT_ONLY',engine,'median',median,flush=True)


if __name__=='__main__':main()
