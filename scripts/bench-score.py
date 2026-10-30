"""分任务严格文本覆盖评价，不冒充官方 benchmark 分数"""
import collections
import json
import re
import statistics
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/outputs/bench-20261030'

def norm(s):
 return re.sub(r'\s+','',unicodedata.normalize('NFKC',s).casefold())

def distance(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  cur=[i]
  for j,y in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
  prev=cur
 return prev[-1]

class Cells(HTMLParser):
 def __init__(self):super().__init__();self.cells=[];self.current=None
 def handle_starttag(self,tag,attrs):
  if tag in ('td','th'):self.current=''
 def handle_data(self,data):
  if self.current is not None:self.current+=data
 def handle_endtag(self,tag):
  if tag in ('td','th') and self.current is not None:self.cells.append(self.current);self.current=None

def spans(row,ref):
 if row['dataset']=='FUNSD':return [x['text'] for x in ref['form'] if x['text'].strip()]
 if row['dataset']=='XFUND':return [x['text'] for x in ref['document'] if x['text'].strip()]
 out=[]
 for x in ref['layout_dets']:
  if x.get('ignore') or x['category_type'] in ('abandon','figure','equation_isolated','equation_caption'):continue
  if x.get('text'):out.append(re.sub(r'^#+\s*','',x['text']))
  elif x.get('html'):
   p=Cells();p.feed(x['html']);out.extend(p.cells)
 return [s for s in out if norm(s)]

def score(row,result):
 ref=json.loads((ROOT/row['reference_path']).read_text());pred=norm(result['text']) if result['status']=='ok' else '';out={}
 if row['dataset']=='ReCTS':
  truth=norm(ref['row']['answers']);errors=distance(truth,pred)
  out.update(metric='cer',errors=errors,reference_chars=len(truth),value=errors/len(truth),exact=truth==pred,reference=ref['row']['answers'])
 elif row['dataset']=='ESTVQA':
  answer=norm(ref['row']['answers']);out.update(metric='answer_presence',value=float(bool(answer) and answer in pred),reference=ref['row']['answers'])
 elif row['dataset']=='olmOCR-bench':
  checks=[]
  for x in ref:
   if x['type']=='order':
    a,b=pred.find(norm(x['before'])),pred.find(norm(x['after']));ok=a>=0 and b>=0 and a<b
   else:
    present=norm(x['text']) in pred;ok=present if x['type']=='present' else not present
   # 空输出不能靠 absent 获得成功：失败页全部记失败
   checks.append({'type':x['type'],'id':x['id'],'pass':bool(ok and result['status']=='ok' and pred)})
  out.update(metric='strict_assertions',value=sum(x['pass'] for x in checks)/len(checks),checks=checks)
 else:
  ss=spans(row,ref);hits=[norm(s) in pred for s in ss];weights=[len(norm(s)) for s in ss]
  out.update(metric='exact_span_coverage',value=sum(w for w,h in zip(weights,hits) if h)/sum(weights),spans=len(ss),hits=sum(hits),matched_chars=sum(w for w,h in zip(weights,hits) if h),reference_chars=sum(weights),missed=[s for s,h in zip(ss,hits) if not h])
 if result['status']!='ok':out['value']=1.0 if out['metric']=='cer' else 0.0
 return out

def main():
 rows=json.loads((ROOT/'data/manifests/balanced60.json').read_text())['cases'];engines={}
 for engine in ['rapid','paddle','tesseract','easy','docling']:
  folder=BASE/engine/'full'
  if not (folder/'summary.json').exists():continue
  summary=json.loads((folder/'summary.json').read_text());scored=[]
  for row in rows:
   result=json.loads((folder/(row['case_id']+'.json')).read_text())
   scored.append(dict(case_id=row['case_id'],dataset=row['dataset'],stratum=row['stratum'],language_group=row['language_group'],status=result['status'],seconds=result['seconds'],**score(row,result)))
  groups={}
  for dataset in dict.fromkeys(x['dataset'] for x in scored):
   rs=[x for x in scored if x['dataset']==dataset]
   g=dict(n=len(rs),metric=rs[0]['metric'],macro_mean=statistics.mean(x['value'] for x in rs),seconds=sum(x['seconds'] for x in rs))
   if dataset=='ReCTS':g.update(micro_cer=sum(x['errors'] for x in rs)/sum(x['reference_chars'] for x in rs),exact_count=sum(x['exact'] for x in rs))
   if dataset=='olmOCR-bench':
    g['by_type']={t:{'pass':sum(c['pass'] for x in rs for c in x['checks'] if c['type']==t),'total':sum(c['type']==t for x in rs for c in x['checks'])} for t in ['present','order','absent']}
   groups[dataset]=g
  times=sorted(x['seconds'] for x in scored)
  engines[engine]=dict(setup=json.loads((folder/'setup.json').read_text()),summary=summary,quality=groups,timing=dict(inference_seconds=sum(times),median=statistics.median(times),p95=times[int(.95*len(times))-1],success=sum(x['status']=='ok' for x in scored)),cases=scored)
 (BASE/'scores.json').write_text(json.dumps(engines,ensure_ascii=False,indent=2)+'\n')
 for name,data in engines.items():print(name,data['timing'],{k:round(v.get('micro_cer',v['macro_mean']),3) for k,v in data['quality'].items()})

if __name__=='__main__':main()
