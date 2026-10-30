"""检查已下载物料并输出候选分流，不运行识别模型"""
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/input/pilot-20261030'
MAN = ROOT / 'data/manifests'
SMOKE = {'omni-003', 'omni-007', 'omni-022', 'funsd-82573104', 'funsd-86263525', 'olm-24'}
CHALLENGE = {'omni-018', 'omni-019', 'omni-025', 'omni-027', 'olm-44', 'olm-55', 'olm-74', 'olm-84'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = json.loads((MAN / 'pilot-downloads.json').read_text())
    hashes = set()
    summaries = []
    fingerprints = []
    for row in rows:
        assert row['status'] == 'downloaded', row
        path = ROOT / row['input_path']
        ref_path = ROOT / row['reference_path']
        assert digest(path) == row['sha256']
        assert digest(ref_path) == row['reference_sha256']
        assert row['sha256'] not in hashes, row['case_id']
        hashes.add(row['sha256'])
        ref = json.loads(ref_path.read_text())
        if path.suffix == '.pdf':
            info = subprocess.check_output(['pdfinfo', str(path)], text=True)
            pages = int(next(s.split(':')[1] for s in info.splitlines() if s.startswith('Pages:')))
            assert all(1 <= r['page'] <= pages for r in ref)
            prefix = path.parent / 'preview'
            subprocess.run(['pdftoppm', '-f', '1', '-singlefile', '-scale-to', '450', '-png', str(path), str(prefix)], check=True, capture_output=True)
            image_path = prefix.with_suffix('.png')
            count = len(ref)
        else:
            image_path = path
            pages = 1
            count = len(ref.get('layout_dets', ref.get('form', [])))
        with Image.open(image_path) as im:
            im.load()
            width, height = im.size
            assert width > 0 and height > 0 and count > 0
            if row['dataset'] == 'OmniDocBench':
                assert (width, height) == (ref['page_info']['width'], ref['page_info']['height'])
            thumb = im.convert('L').resize((9, 8))
            small = [thumb.getpixel((x, y)) for y in range(8) for x in range(9)]
            bits = sum((small[y*9+x] > small[y*9+x+1]) << (y*8+x) for y in range(8) for x in range(8))
            fingerprints.append((row['case_id'], bits, width/height))
        case = row['case_id']
        purpose = 'development' if case in SMOKE else 'challenge' if case in CHALLENGE else 'exploratory' if case == 'omni-021' else 'sparse-text' if case == 'omni-026' else 'pilot-evaluation'
        summaries.append(dict(case_id=case, use=purpose, annotation_count=count, width=width, height=height, pages=pages,
                              visually_screened=True, reference_fully_verified=False))
    near = []
    for i, (a, ha, ra) in enumerate(fingerprints):
        for b, hb, rb in fingerprints[i+1:]:
            dist = (ha ^ hb).bit_count()
            if dist <= 5 and abs(ra-rb) < .05:
                near.append(dict(a=a, b=b, distance=dist, status='needs-review; not automatically excluded'))
    result = dict(count=len(rows), unique_hashes=len(hashes), bytes=sum(r['bytes'] for r in rows),
                  source_counts=dict(Counter(r['dataset'] for r in rows)),
                  use_counts=dict(Counter(r['use'] for r in summaries)), near_duplicate_candidates=near, cases=summaries)
    (MAN / 'pilot-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    target = MAN / 'pilot-materials.csv'
    fields = ['case_id', 'task', 'language', 'input_path', 'page', 'sha256', 'source', 'revision', 'license', 'reference_path', 'reference_status', 'storage', 'restore', 'dataset_id', 'source_item_id', 'source_split', 'stratum', 'document_id', 'template_id', 'site_id', 'writer_id', 'group_id', 'eval_split', 'annotation_type', 'reference_sha256', 'parent_case_id', 'synthetic', 'sampling_seed']
    with target.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row, audit in zip(rows, summaries):
            writer.writerow(dict(case_id=row['case_id'], task='document-parsing' if row['dataset']=='OmniDocBench' else 'form-understanding' if row['dataset']=='FUNSD' else 'document-assertions',
                                 language=row['language'], input_path=row['input_path'], page=1,
                                 sha256=row['sha256'], source=row['url'], revision=row['revision'], license=row['license'],
                                 reference_path=row['reference_path'], reference_status='upstream-not-locally-verified', storage='local',
                                 restore='python3 scripts/prepare-materials.py --restore', dataset_id=row['dataset'], source_item_id=row['source_item_id'],
                                 source_split=row['source_split'], stratum=row['stratum'], document_id=row['document_id'],
                                 template_id='unknown', site_id='unknown', writer_id='unknown', group_id=row['document_id'],
                                 eval_split=audit['use'], annotation_type=row['annotation_type'], reference_sha256=row['reference_sha256'], synthetic='false', sampling_seed=20261030))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
