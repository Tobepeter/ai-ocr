"""冻结中文40/英文20试评测名单，并核验输入、标注和开发集排除"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / 'data/manifests'
ZH_OMNI = {f'omni-{n:03}' for n in [1,4,6,9,11,13,14,16,19,24,25,27,29,30]}
EN_OMNI = {f'omni-{n:03}' for n in [2,8,12,28]}
EN_OLM = {f'olm-{n}' for n in [31,55,65,67,74,84]}
DEV = {'omni-003','omni-007','omni-022','funsd-82573104','funsd-86263525','olm-24'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old = json.loads((MAN / 'pilot-downloads.json').read_text())
    new = json.loads((MAN / 'chinese-downloads.json').read_text())
    chosen = ZH_OMNI | EN_OMNI | EN_OLM | {r['case_id'] for r in old if r['dataset']=='FUNSD' and r['case_id'] not in DEV} | {r['case_id'] for r in new}
    assert len(chosen)==60 and not chosen.intersection(DEV)
    selected = []
    fingerprints = []
    hashes = set()
    for r in old+new:
        if r['case_id'] not in chosen:
            continue
        path = ROOT / r['input_path']
        reference = ROOT / r['reference_path']
        assert digest(path)==r['sha256'] and digest(reference)==r['reference_sha256']
        assert r['sha256'] not in hashes
        hashes.add(r['sha256'])
        ref = json.loads(reference.read_text())
        preview = path.parent / 'preview.png' if path.suffix=='.pdf' else path
        with Image.open(preview) as im:
            im.load()
            if r['dataset']=='XFUND':
                assert im.size==(ref['img']['width'],ref['img']['height'])
                assert ref['document'] and any('\u4e00'<=c<='\u9fff' for x in ref['document'] for c in x['text'])
            if r['dataset'] in ['ESTVQA','ReCTS']:
                assert im.size==(ref['width'],ref['height'])
                assert ref['row']['answers'].strip()
            thumb=im.convert('L').resize((9,8))
            h=sum((thumb.getpixel((x,y))>thumb.getpixel((x+1,y))) << (y*8+x) for y in range(8) for x in range(8))
            fingerprints.append((r['case_id'],h,im.width/im.height))
        selected.append(dict(r,selection='balanced60-v1',language_group='english' if r['language']=='english' else 'chinese-or-mixed',
                             original_source=r.get('original_source',r['dataset']), reference_status='upstream-not-locally-verified'))
    languages=Counter(r['language_group'] for r in selected)
    sources=Counter(r['original_source'] for r in selected)
    assert languages=={'chinese-or-mixed':40,'english':20}
    assert max(sources.values())<=18
    near=[]
    for i,(a,ha,ra) in enumerate(fingerprints):
        for b,hb,rb in fingerprints[i+1:]:
            distance=(ha^hb).bit_count()
            if distance<=5 and abs(ra-rb)<.05:
                near.append(dict(a=a,b=b,distance=distance))
    result=dict(selection='balanced60-v1',count=60,language_counts=dict(languages),source_counts=dict(sources),
                bytes=sum(r['bytes'] for r in selected),unique_hashes=len(hashes),near_duplicate_candidates=near,
                development_excluded=sorted(DEV),cases=selected)
    out=MAN/'balanced60.json'
    if out.exists():
        prev=json.loads(out.read_text())
        assert [(r['case_id'],r['sha256'],r['reference_sha256']) for r in prev['cases']]==[(r['case_id'],r['sha256'],r['reference_sha256']) for r in selected], '冻结名单发生变化，请创建新版本'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    fields=['case_id', 'task', 'language', 'input_path', 'page', 'sha256', 'source', 'revision', 'license', 'reference_path', 'reference_status', 'storage', 'restore', 'dataset_id', 'source_item_id', 'source_split', 'stratum', 'document_id', 'template_id', 'site_id', 'writer_id', 'group_id', 'eval_split', 'annotation_type', 'reference_sha256', 'parent_case_id', 'synthetic', 'sampling_seed', 'original_source', 'language_group']
    for name, records in [('materials.csv',old+new),('balanced60.csv',selected)]:
        with (MAN/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for r in records:
                case=r['case_id']
                writer.writerow(dict(task='scene-qa' if r['dataset']=='ESTVQA' else 'line-recognition' if r['dataset']=='ReCTS' else 'document-parsing', page=1, group_id=r['document_id'], site_id='unknown', synthetic='false', case_id=case,dataset_id=r['dataset'],original_source=r.get('original_source',r['dataset']),language=r['language'],
                                     language_group='english' if r['language']=='english' else 'other' if r['language']=='other' else 'chinese-or-mixed',
                                     stratum=r['stratum'],annotation_type=r['annotation_type'],eval_split='pilot-evaluation' if case in chosen else 'development' if case in DEV else 'reserve',
                                     source_split=r['source_split'],source_item_id=r['source_item_id'],revision=r['revision'],input_path=r['input_path'],sha256=r['sha256'],
                                     reference_path=r['reference_path'],reference_sha256=r['reference_sha256'],reference_status='upstream-not-locally-verified',source=r['url'],license=r['license'],
                                     storage='local',document_id=r['document_id'],template_id='unknown',writer_id='unknown',sampling_seed=20261030,
                                     restore='python3 scripts/expand-chinese.py --restore' if r in new else 'python3 scripts/prepare-materials.py --restore'))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
