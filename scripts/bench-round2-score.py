"""第二轮沿用冻结参考口径，失败与截断不剔除；新旧运行分开保存"""
import csv,importlib.util,json,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/outputs/bench-20261030b'
spec=importlib.util.spec_from_file_location('oldscore',ROOT/'scripts/bench-score.py');sc=importlib.util.module_from_spec(spec);spec.loader.exec_module(sc)
rows=json.loads((ROOT/'data/manifests/balanced60.json').read_text())['cases'];output={};cases=[]
for engine in ['vision','glm','paddlevl','mineru','tesseract']:
 folder=BASE/engine/'full'
 if not (folder/'summary.json').exists():continue
 summary=json.loads((folder/'summary.json').read_text());rs=[]
 for row in rows:
  result=json.loads((folder/(row['case_id']+'.json')).read_text())
  # 图片字节不是识别文字，保留原始输出，仅在评分前剥离内嵌图片
  if engine=='mineru':result={**result,'text':re.sub(r'data:image/[^;\s]+;base64,[A-Za-z0-9+/=\r\n]+','',result['text'])}
  quality=sc.score(row,result)
  item=dict(engine=engine,case_id=row['case_id'],dataset=row['dataset'],status=result['status'],seconds=result['seconds'],**quality);rs.append(item)
  cases.append({k:item[k] for k in ['engine','case_id','dataset','status','seconds','metric','value']})
 groups={}
 for dataset in dict.fromkeys(r['dataset'] for r in rows):
  xs=[r for r in rs if r['dataset']==dataset];v=dict(n=len(xs),metric=xs[0]['metric'],macro_mean=statistics.mean(r['value'] for r in xs))
  if dataset=='ReCTS':v.update(micro_cer=sum(r['errors'] for r in xs)/sum(r['reference_chars'] for r in xs),exact_count=sum(r['exact'] for r in xs))
  if dataset=='olmOCR-bench':v['by_type']={t:dict(passed=sum(c['pass'] for r in xs for c in r['checks'] if c['type']==t),total=sum(c['type']==t for r in xs for c in r['checks'])) for t in ['present','order','absent']}
  groups[dataset]=v
 times=sorted(r['seconds'] for r in rs)
 output[engine]=dict(quality=groups,timing=dict(inference_seconds=sum(times),median=statistics.median(times),p95=times[56],success=sum(r['status']=='ok' for r in rs)),resources=json.loads((folder/'exit.json').read_text()),setup=json.loads((folder/'setup.json').read_text()))
 print(engine,output[engine]['timing'],{k:round(v.get('micro_cer',v['macro_mean']),3) for k,v in groups.items()})
(ROOT/'data/reports/benchmark-round2.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
with (ROOT/'data/reports/benchmark-round2.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['engine','case_id','dataset','status','seconds','metric','value']);w.writeheader();w.writerows(cases)
