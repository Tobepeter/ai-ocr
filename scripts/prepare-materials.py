"""固定来源的小规模物料采集，不运行 OCR 模型"""
import argparse
import hashlib
import json
import random
import subprocess
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/input/pilot-20261030'
META = BASE / 'metadata'
PLAN = ROOT / 'data/manifests/pilot-plan.json'
SEED = 20261030


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def make_plan():
    if PLAN.exists():
        raise SystemExit('计划已冻结；不要覆盖现有名单')
    rng = random.Random(SEED)
    cases = []
    omni = json.loads((META / 'omni-download.json').read_text())
    revision = json.loads((META / 'OmniDocBench-info.json').read_text())['sha']
    groups = defaultdict(list)
    for page in omni:
        attr = page['page_info']['page_attribute']
        groups[(attr['data_source'], attr['language'])].append(page)
    # 每轮每层一个；类别与语言共同覆盖，页面原始文档未知时不伪造独立性
    for pages in groups.values():
        pages.sort(key=lambda p: p['page_info']['image_path'])
        rng.shuffle(pages)
    keys = sorted(groups)
    picked = []
    while len(picked) < 30:
        progressed = False
        for key in keys:
            if groups[key] and len(picked) < 30:
                picked.append(groups[key].pop())
                progressed = True
        if not progressed:
            break
    for i, page in enumerate(picked):
        info = page['page_info']
        cases.append(dict(case_id=f'omni-{i+1:03}', dataset='OmniDocBench',
                          revision=revision, source_split='benchmark',
                          source_item_id=info['image_path'],
                          language=info['page_attribute']['language'],
                          stratum=info['page_attribute']['data_source'],
                          document_id='unknown', annotation_type='layout-text-table-formula-order',
                          license='upstream-copyright-statement; local research only',
                          url=f'https://huggingface.co/datasets/opendatalab/OmniDocBench/resolve/{revision}/images/{info["image_path"]}',
                          suffix=Path(info['image_path']).suffix, reference=page))
    archive = META / 'funsd-official.zip'
    with zipfile.ZipFile(archive) as z:
        names = sorted(n for n in z.namelist() if n.startswith('dataset/testing_data/annotations/') and n.endswith('.json'))
        pool = list(names)
        rng.shuffle(names)
        for name in names[:12]:
            item = Path(name).stem
            cases.append(dict(case_id=f'funsd-{item}', dataset='FUNSD',
                              revision='archive-sha256:' + sha(archive), source_split='test',
                              source_item_id=item, language='english', stratum='form',
                              document_id=item, annotation_type='word-box-entity-relation',
                              license='non-commercial research/education; official terms',
                              url='https://raw.githubusercontent.com/guillaumejaume/FUNSD/8905aca92b3181853307e2880e3d6f71dee8e9f3/dataset.zip',
                              archive_member=f'dataset/testing_data/images/{item}.png',
                              suffix='.png', reference=json.loads(z.read(name))))
    annotations = [json.loads(s) for s in (META / 'olmOCR-bench-annotations.json').read_text().splitlines()]
    by_pdf = defaultdict(list)
    for a in annotations:
        by_pdf[a['pdf']].append(a)
    names = sorted(by_pdf)
    rng.shuffle(names)
    revision = json.loads((META / 'olmOCR-bench-info.json').read_text())['sha']
    # 同一原始条目只选一页，来源 URL 缺失时按 PDF 标识分组
    origins = set()
    for name in names:
        refs = by_pdf[name]
        origin = next((a.get('url') for a in refs if a.get('url')), name)
        # LOC 的条目目录作为聚类线索，完整 URL 仍保留于原始标注
        group = origin.rsplit('/', 2)[0] if origin.startswith('http') else origin
        if group in origins:
            continue
        origins.add(group)
        cases.append(dict(case_id='olm-' + Path(name).stem, dataset='olmOCR-bench',
                          revision=revision, source_split='old_scans', source_item_id=name,
                          language='english', stratum='old-scan', document_id=group,
                          annotation_type='assertions', license='ODC-BY-1.0; original document rights retained',
                          url=f'https://huggingface.co/datasets/allenai/olmOCR-bench/resolve/{revision}/bench_data/pdfs/{name}',
                          suffix='.pdf', reference=refs))
        if len(origins) == 8:
            break
    for case in cases:
        write_json(BASE / case['case_id'] / 'reference.json', case.pop('reference'))
    snapshot = dict(seed=SEED, selection='round-robin source/language + seeded test sampling; no model output',
                    pool_counts=dict(omni=len(omni), funsd_test=len(pool), olm_pdfs=len(by_pdf)),
                    metadata_hashes={f.name: sha(f) for f in META.iterdir() if f.is_file() and f.name in ['omni-download.json', 'funsd-official.zip', 'olmOCR-bench-annotations.json']},
                    cases=cases)
    write_json(PLAN, snapshot)
    print('计划已冻结', len(cases), flush=True)


def acquire(case):
    folder = BASE / case['case_id']
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ('input' + case['suffix'])
    reference = folder / 'reference.json'
    if not reference.exists():
        if case['dataset'] == 'OmniDocBench':
            pages = json.loads((META / 'omni-download.json').read_text())
            ref = next(p for p in pages if p['page_info']['image_path'] == case['source_item_id'])
        elif case['dataset'] == 'FUNSD':
            with zipfile.ZipFile(META / 'funsd-official.zip') as z:
                ref = json.loads(z.read(case['archive_member'].replace('/images/', '/annotations/').replace('.png', '.json')))
        else:
            ref = [json.loads(line) for line in (META / 'olmOCR-bench-annotations.json').read_text().splitlines() if json.loads(line)['pdf'] == case['source_item_id']]
        write_json(reference, ref)
    if not target.exists():
        partial = target.with_suffix('.part')
        if 'archive_member' in case:
            with zipfile.ZipFile(META / 'funsd-official.zip') as z:
                partial.write_bytes(z.read(case['archive_member']))
        else:
            result = subprocess.run(['curl', '-fL', '--retry', '1', '--max-time', '50', '--max-filesize', '10000000', '-sS', case['url'], '-o', str(partial)], capture_output=True, text=True)
            if result.returncode:
                return dict(case_id=case['case_id'], status='download-failed', error=result.stderr[-500:])
        partial.replace(target)
    result = {k: v for k, v in case.items() if k != 'reference'}
    result.update(status='downloaded', input_path=str(target.relative_to(ROOT)),
                  reference_path=str(reference.relative_to(ROOT)), sha256=sha(target),
                  reference_sha256=sha(reference), bytes=target.stat().st_size,
                  reference_status='upstream-not-locally-verified')
    print(case['case_id'], target.stat().st_size, flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if args.restore:
        META.mkdir(parents=True, exist_ok=True)
        resources = json.loads((ROOT / 'data/manifests/pilot-resources.json').read_text())
        for item in resources:
            target = META / item['name']
            if target.exists() and sha(target) == item['sha256']:
                continue
            partial = target.with_suffix('.part')
            subprocess.run(['curl', '-fL', '--retry', '2', '--max-time', '180', '--max-filesize', str(item['bytes'] + 1), '-sS', item['url'], '-o', str(partial)], check=True)
            if sha(partial) != item['sha256']:
                raise ValueError('源文件哈希不一致: ' + item['name'])
            partial.replace(target)
    if args.plan:
        make_plan()
    plan = json.loads(PLAN.read_text())
    previous = ROOT / 'data/manifests/pilot-downloads.json'
    expected = {r['case_id']: r for r in json.loads(previous.read_text()) if r['status'] == 'downloaded'} if previous.exists() else {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(acquire, plan['cases']))
    for result in results:
        old = expected.get(result['case_id'])
        if old and result['status'] == 'downloaded':
            if result['sha256'] != old['sha256'] or result['reference_sha256'] != old['reference_sha256']:
                raise ValueError('冻结物料已变化: ' + result['case_id'])
    if all(r['status'] == 'downloaded' for r in results):
        write_json(ROOT / 'data/manifests/pilot-downloads.json', results)
    else:
        write_json(ROOT / 'data/manifests/pilot-failures.json', results)
    print('完成', sum(r['status'] == 'downloaded' for r in results), '/', len(results))


if __name__ == '__main__':
    main()
