"""统一图像输入，PDF光栅化，原图不修改"""
import hashlib
import json
import subprocess
import time
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[1]
out=root/'data/outputs/bench-20261030'
out.mkdir(parents=True,exist_ok=True)
start=time.perf_counter()
selected=json.loads((root/'data/manifests/balanced60.json').read_text())['cases']
dev_manifest=root/'data/manifests/development6.json'
old=json.loads((dev_manifest if dev_manifest.exists() else root/'data/manifests/pilot-downloads.json').read_text())
dev={'omni-003','omni-007','omni-022','funsd-82573104','funsd-86263525','olm-24'}
cases=[]
for row in selected+[r for r in old if r['case_id'] in dev]:
 path=root/row['input_path'];case=row['case_id'];target=out/'inputs'/f'{case}.png';target.parent.mkdir(exist_ok=True)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
 if path.suffix=='.pdf':
  subprocess.run(['pdftoppm','-f','1','-singlefile','-scale-to','2000','-png',str(path),str(target.with_suffix(''))],check=True,capture_output=True)
 else:
  with Image.open(path) as im:
   im=im.convert('RGB');im.thumbnail((2000,2000),Image.Resampling.LANCZOS);im.save(target)
 with Image.open(target) as im:size=im.size
 cases.append(dict(row,prepared_path=str(target.relative_to(root)),prepared_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),size=size,phase='preflight' if case in dev else 'full'))
(out/'inputs.json').write_text(json.dumps({'created':'2026-10-30','policy':'RGB; longest side <=2000; no upscale; PDF first page image only; no native text extraction','seconds':time.perf_counter()-start,'cases':cases},ensure_ascii=False,indent=2)+'\n')
print(len(cases),round(time.perf_counter()-start,2))
