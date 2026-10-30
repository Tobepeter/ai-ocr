import json,time
from pathlib import Path
from huggingface_hub import snapshot_download
start=time.time();results=[]
for repo,rev in [('docling-project/docling-models','v2.3.0'),('docling-project/docling-layout-heron','main')]:
 t=time.time()
 try:
  path=snapshot_download(repo,revision=rev,max_workers=3)
  results.append(dict(repo=repo,revision=rev,path=path,seconds=time.time()-t,status='ok'))
 except Exception as e:results.append(dict(repo=repo,seconds=time.time()-t,status='error',error=repr(e)))
 print(results[-1],flush=True)
Path('data/outputs/bench-20261030/setup/docling-download.json').write_text(json.dumps(dict(seconds=time.time()-start,results=results),indent=2))
