"""从冻结上游来源恢复当前66份；历史采集包只是中间文件，完成后清理"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
selected=json.loads((root/'data/manifests/balanced60.json').read_text())['cases']
devpath=root/'data/manifests/development6.json'
dev=json.loads(devpath.read_text()) if devpath.exists() else []
valid=bool(dev) and all((root/r[k]).exists() and hashlib.sha256((root/r[k]).read_bytes()).hexdigest()==r[h] for r in selected+dev for k,h in [('input_path','sha256'),('reference_path','reference_sha256')])
if valid:print('当前60份与开发6份哈希均一致，无需下载')
else:
 for script in ['prepare-materials.py','expand-chinese.py']:
  subprocess.run([sys.executable,str(root/'scripts'/script),'--restore'],cwd=root,check=True)
 subprocess.run([sys.executable,str(root/'scripts/consolidate-materials.py'),'--clean'],cwd=root,check=True)
