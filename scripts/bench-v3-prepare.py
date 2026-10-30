"""从冻结输入按标注裁剪60个识字区域，选样不读取任何模型输出"""
import hashlib,json,random,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/outputs/bench-20261030c'
BASE.mkdir(parents=True,exist_ok=True)
rows=json.loads((ROOT/'data/manifests/balanced60.json').read_text())['cases']
rng=random.Random(20261030);chosen=[];rejections=[]

def candidates(row):
 ref=json.loads((ROOT/row['reference_path']).read_text())
 if row['dataset']=='ReCTS':return [{'text':ref['row']['answers'],'box':None,'id':'full'}]
 if row['dataset']=='OmniDocBench':
  items=[]
  for x in ref['layout_dets']:
   t=x.get('text','')
   if x.get('ignore') or x['category_type'] not in ['text_block','title','header','footer']:continue
   t=re.sub(r'^#{1,6}\s+','',t)
   if not 20<=len(t)<=600 or any(c in t for c in ['$','\\','<','>']):continue
   poly=x['poly'];items.append({'text':t,'box':[min(poly[::2]),min(poly[1::2]),max(poly[::2]),max(poly[1::2])],'id':x['anno_id']})
 else:
  items=[{'text':x['text'],'box':x['box'],'id':x['id']} for x in ref.get('document',ref.get('form',[])) if 10<=len(x['text'])<=240 and x['text'].strip()]
 rng.shuffle(items)
 return items

def take(row,n):
 items=candidates(row)
 if len(items)<n:return False
 for item in items[:n]:chosen.append((row,item))
 return True

for row in rows:
 if row['dataset'] in ['ReCTS','XFUND','FUNSD']:
  if not take(row,1):raise ValueError(row['case_id'])
for group,target in [('chinese-or-mixed',40),('english',20)]:
 pages=[r for r in rows if r['dataset']=='OmniDocBench' and r['language_group']==group]
 # 覆盖尽可能多的不同原页，按清单顺序轮转，每页最多3段
 pools={r['case_id']:candidates(r)[:3] for r in pages}
 for j in range(3):
  for row in pages:
   if sum(r['language_group']==group for r,_ in chosen)>=target:break
   if len(pools[row['case_id']])>j:chosen.append((row,pools[row['case_id']][j]))
 if group=='english':
  for row in [r for r in rows if r['dataset']=='FUNSD']:
   if sum(r['language_group']==group for r,_ in chosen)>=target:break
   used={x['id'] for r,x in chosen if r['case_id']==row['case_id']}
   extra=[x for x in candidates(row) if x['id'] not in used]
   if extra:chosen.append((row,extra[0]))
 assert sum(r['language_group']==group for r,_ in chosen)==target


out=[]
for idx,(row,item) in enumerate(chosen):
 case=f'region-{idx+1:03d}';original=ROOT/row['input_path']
 with Image.open(original) as image:
  image=image.convert('RGB');box=item['box']
  if box:
   box=[max(0,int(box[0])-2),max(0,int(box[1])-2),min(image.width,int(box[2])+3),min(image.height,int(box[3])+3)]
   image=image.crop(box)
  image.thumbnail((2000,2000));path=BASE/'regions'/f'{case}.png';path.parent.mkdir(exist_ok=True);image.save(path)
 out.append(dict(case_id=case,parent_case_id=row['case_id'],dataset=row['dataset'],language_group=row['language_group'],stratum=row['stratum'],annotation_id=item['id'],crop_box=box,input_path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reference=item['text'],review_status='pending_visual_review'))
manifest={'seed':20261030,'scope':'known-region recognition; not whole-page layout or text detection benchmark','cases':out}
(BASE/'region-draft.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',22)
for start in range(0,60,5):
 sheet=Image.new('RGB',(1500,2600),'#dddddd');d=ImageDraw.Draw(sheet)
 for i,r in enumerate(out[start:start+5]):
  y=i*520;d.text((10,y+5),f"{r['case_id']} | {r['parent_case_id']} | {r['annotation_id']}",font=font,fill='black')
  im=Image.open(ROOT/r['input_path']);im.thumbnail((1450,245));sheet.paste(im,(10,y+40))
  text=r['reference'];lines=[text[j:j+60] for j in range(0,len(text),60)]
  for j,line in enumerate(lines):d.text((10,y+290+24*j),line,font=font,fill='black')
 sheet.save(BASE/f'review-{start//5+1:02d}.png')
print('regions',len(out),'reference chars',sum(len(r['reference']) for r in out))
