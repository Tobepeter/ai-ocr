import json,time
from pathlib import Path
from huggingface_hub import model_info,snapshot_download
out=[];base=Path('data/outputs/bench-20261030b/setup')
for engine,repo in [('glm','mlx-community/GLM-OCR-bf16'),('paddlevl','PaddlePaddle/PaddleOCR-VL-1.6')]:
 t=time.time()
 try:
  info=model_info(repo,files_metadata=True);size=sum(f.size or 0 for f in info.siblings if f.rfilename.endswith('.safetensors'));print(repo,info.sha,size,flush=True)
  path=snapshot_download(repo,revision=info.sha,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.jinja'],max_workers=3)
  row=dict(engine=engine,repo=repo,revision=info.sha,weight_bytes=size,path=path,seconds=time.time()-t,status='ok')
 except Exception as e:row=dict(engine=engine,repo=repo,seconds=time.time()-t,status='error',error=repr(e))
 out.append(row);(base/'vlm-models.json').write_text(json.dumps(out,indent=2)+'\n');print(row,flush=True)
