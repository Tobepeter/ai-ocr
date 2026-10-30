"""将冻结60份和开发6份迁入稳定目录，校验后可清理采集批次"""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAN=ROOT/'data/manifests'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvwrite(p,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def main():
 p=argparse.ArgumentParser();p.add_argument('--clean',action='store_true');args=p.parse_args()
 m=json.loads((MAN/'balanced60.json').read_text())
 historical=json.loads((MAN/'pilot-downloads.json').read_text())+json.loads((MAN/'chinese-downloads.json').read_text())
 byid={r['case_id']:r for r in historical}
 dev=json.loads((MAN/'development6.json').read_text()) if (MAN/'development6.json').exists() else [byid[k] for k in m['development_excluded']]
 # 开发6份是本轮预检依据，保留供复跑；10份未使用候选与采集包可清理
 for row in m['cases']+dev:
  folder=ROOT/'data/input'/('balanced60-v1' if row in m['cases'] else 'development6-v1')/row['case_id'];folder.mkdir(parents=True,exist_ok=True)
  for key,hashkey,name in [('input_path','sha256','input'),('reference_path','reference_sha256','reference')]:
   source=ROOT/row[key]
   if not source.exists() or sha(source)!=row[hashkey]:source=ROOT/byid[row['case_id']][key]
   target=folder/(name+source.suffix)
   assert sha(source)==row[hashkey],source
   if source!=target:shutil.copy2(source,target)
   assert sha(target)==row[hashkey],target
   row[key]=str(target.relative_to(ROOT))
 write(MAN/'balanced60.json',m);write(MAN/'development6.json',dev)
 csvwrite(MAN/'balanced60.csv',m['cases']);csvwrite(MAN/'materials.csv',m['cases'])
 record={'selected':60,'development':6,'verified_files':132,'removed':[]}
 if args.clean:
  for name in ['pilot-20261030','zh-expansion-20261030']:
   folder=ROOT/'data/input'/name
   if folder.exists():
    count=sum(1 for p in folder.rglob('*') if p.is_file());size=sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
    shutil.rmtree(folder);record['removed'].append({'path':str(folder.relative_to(ROOT)),'files':count,'bytes':size})
 write(ROOT/'data/reports/material-cleanup.json',record)
 print(record)

if __name__=='__main__':main()
