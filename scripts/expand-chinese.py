"""补充固定随机索引的中文小样本，来源包和原始标注保留本地"""
import hashlib
import argparse
import json
import random
import subprocess
import urllib.parse
import urllib.request
import zipfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/input/zh-expansion-20261030'
META = BASE / 'metadata'
REV = '857e91af744e05b234c504caf900f932f236de71'
SEED = 20261030


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def fetch_row(spec):
    family, index = spec
    folder = BASE / f'{family.lower()}-{index:04}'
    folder.mkdir(parents=True, exist_ok=True)
    ref_path = folder / 'reference.json'
    image_path = folder / 'input.jpg'
    endpoint = 'https://datasets-server.huggingface.co/rows?' + urllib.parse.urlencode(dict(dataset='SWHL/ChineseOCRBench', config='default', split='test', offset=index, length=1))
    if not (image_path.exists() and ref_path.exists()):
        for attempt in range(3):
            try:
                payload = json.load(urllib.request.urlopen(endpoint, timeout=30))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
        entry = payload['rows'][0]
        assert not entry['truncated_cells'] and entry['row_idx'] == index
        row = entry['row']
        assert row['dataset_name'].lower().startswith(family.lower()), row['dataset_name']
        src = row.pop('image')
        assert REV in src['src'], 'Viewer 版本已变化，请使用已冻结物料'
        target = image_path.with_suffix('.part')
        subprocess.run(['curl', '-fL', '--retry', '1', '--max-time', '45', '--max-filesize', '5000000', '-sS', src['src'], '-o', str(target)], check=True)
        target.replace(image_path)
        write(ref_path, dict(row=row, viewer_index=index, viewer_revision=REV,
                             width=src['width'], height=src['height']))
    ref = json.loads(ref_path.read_text())
    assert ref['row']['answers'].strip()
    print(folder.name, image_path.stat().st_size, flush=True)
    return dict(case_id=folder.name, dataset=family, original_source='LSVT' if family=='ESTVQA' else 'ReCTS',
                revision=REV, source_split='ChineseOCRBench/test; original split not verified',
                source_item_id=str(ref['row']['id']), language='simplified_chinese',
                stratum='scene-question-answer' if family=='ESTVQA' else 'scene-text',
                annotation_type='question-answer; not full-image transcript' if family=='ESTVQA' else 'cropped-line-transcript',
                document_id='unknown', license='mirror card Apache-2.0; upstream image rights not inferred',
                url=endpoint, input_path=str(image_path.relative_to(ROOT)), reference_path=str(ref_path.relative_to(ROOT)),
                sha256=digest(image_path), reference_sha256=digest(ref_path), bytes=image_path.stat().st_size,
                reference_status='upstream-not-locally-verified')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if args.restore:
        resources = json.loads((ROOT / 'data/manifests/chinese-resources.json').read_text())
        for item in resources:
            target = ROOT / item['path']
            if target.exists() and digest(target) == item['sha256']:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix('.part')
            subprocess.run(['curl','-fL','-C','-','--max-time','360','--max-filesize',str(item['bytes']+1),'-sS',item['url'],'-o',str(partial)],check=True)
            assert digest(partial)==item['sha256'], '上游文件已变化'
            partial.replace(target)
    rng = random.Random(SEED)
    specs = [('ESTVQA', i) for i in sorted(rng.sample(range(709), 6))]
    specs += [('ReCTS', i) for i in sorted(rng.sample(range(709, 3410), 6))]
    write(ROOT / 'data/manifests/chinese-sampling.json', dict(seed=SEED, ranges={'ESTVQA': [0,708], 'ReCTS':[709,3409]}, selected_indices=specs, revision=REV))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch_row, specs))
    write(ROOT / 'data/manifests/chinese-scene-downloads.json', results)
    archive = META / 'zh.val.zip'
    annotation = META / 'zh.val.json'
    if not archive.exists() or not zipfile.is_zipfile(archive):
        print('街景采集完成，XFUND 包尚未就绪', flush=True)
        return
    data = json.loads(annotation.read_text())['documents']
    candidates = sorted(data, key=lambda x:str(x['id']))
    picked = rng.sample(candidates, 14)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for doc in picked:
            case = 'xfund-' + str(doc['id'])
            folder = BASE / case
            folder.mkdir(parents=True, exist_ok=True)
            image_name = doc['img']['fname']
            matches = [n for n in z.namelist() if Path(n).name == Path(image_name).name]
            assert len(matches) == 1, matches
            image_path = folder / ('input' + Path(image_name).suffix)
            image_path.write_bytes(z.read(matches[0]))
            ref_path = folder / 'reference.json'
            write(ref_path, doc)
            results.append(dict(case_id=case, dataset='XFUND', original_source='XFUND', revision='v1.0; archive-sha256:' + digest(archive),
                                source_split='zh.val (official evaluation)', source_item_id=str(doc['id']), language='chinese',
                                stratum='form', annotation_type='text-box-entity-relation', document_id=str(doc['id']),
                                license='CC-BY-NC-SA-4.0', url='https://github.com/doc-analysis/XFUND/releases/download/v1.0/zh.val.zip',
                                archive_member=matches[0], input_path=str(image_path.relative_to(ROOT)), reference_path=str(ref_path.relative_to(ROOT)),
                                sha256=digest(image_path), reference_sha256=digest(ref_path), bytes=image_path.stat().st_size,
                                reference_status='upstream-not-locally-verified'))
            print(case, image_path.stat().st_size, flush=True)
    target = ROOT / 'data/manifests/chinese-downloads.json'
    if target.exists():
        old = {r['case_id']: r for r in json.loads(target.read_text())}
        for r in results:
            if r['case_id'] in old:
                assert r['sha256'] == old[r['case_id']]['sha256'] and r['reference_sha256'] == old[r['case_id']]['reference_sha256']
    write(target, results)
    write(ROOT / 'data/manifests/chinese-resources.json', [dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,sha256=digest(f),url='https://github.com/doc-analysis/XFUND/releases/download/v1.0/'+f.name) for f in [archive,annotation]])
    print('新增物料',len(results),flush=True)


if __name__ == '__main__':
    main()
