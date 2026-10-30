"""本地同图OCR对比，复用用户级工具环境"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from ocr_runtime import tool_python
os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
os.environ.setdefault('GRADIO_TEMP_DIR', str(ROOT / '.temp/files/ocr/ui-cache'))
import gradio as gr
from PIL import Image, ImageOps

ENGINES = {'rapid': 'RapidOCR', 'mineru': 'MinerU Basic', 'docling': 'Docling', 'apple': 'Apple Vision'}
OUTPUT = ROOT / 'data/outputs/ocr-ui'


def run_process(command, log, timeout=240):
  process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
  try:
    if process.wait(timeout=timeout):
      raise RuntimeError('引擎执行失败，详见本次日志')
  except BaseException:
    if process.poll() is None:
      os.killpg(process.pid, signal.SIGTERM)
      try:
        process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    raise


def evaluate(engine, reference, data):
  command = [str(ROOT / '.venv/bin/python'), str(ROOT / 'src/ocr_eval/metrics.py')]
  return json.loads(subprocess.check_output(command,
    input=json.dumps({'engine': engine, 'reference': reference, 'result': data}), text=True, timeout=30))


def recognize(engine, image_path, folder, reference, batch_start):
  start = time.perf_counter()
  timing = {'started_offset_seconds': start - batch_start}
  try:
    target = folder/f'{engine}.json'
    with (folder/f'{engine}.log').open('w') as log:
      if engine == 'apple':
        binary = ROOT/'.temp/files/ocr/vision-cli'
        swift = ROOT/'src/ocr_ui/vision.swift'
        binary.parent.mkdir(parents=True, exist_ok=True)
        if not binary.exists() or binary.stat().st_mtime < swift.stat().st_mtime:
          run_process(['swiftc', '-O', str(swift), '-o', str(binary)], log)
        cmd = [str(binary), str(image_path), str(target)]
      else:
        cmd = [tool_python({'rapid': 'rapidocr', 'mineru': 'mineru', 'docling': 'docling'}[engine]),
               str(ROOT/'src/ocr_ui/worker.py'), engine, str(image_path), str(target)]
      run_process(cmd, log)
    data = json.loads(target.read_text())
    timing['wall_seconds'] = time.perf_counter() - start
    data['recognition_status'] = 'ok'
  except Exception as error:
    data = {'error': str(error), 'recognition_status': 'error'}
    timing['wall_seconds'] = time.perf_counter() - start
  # 评分失败不改变识别状态，不重复调用已失败的评分器
  data['scoring_status'] = 'not_requested'
  if (reference or '').strip():
    try:
      failed = data['recognition_status'] == 'error'
      data.update(evaluate('rapid' if failed else engine, reference, {'text': ''} if failed else data))
      data['scoring_status'] = 'ok' if data.get('cer') is not None else 'invalid_reference'
    except Exception as error:
      data.update(scoring_status='error', scoring_error=str(error), cer=None)
  if 'text' in data:
    data['text'] = re.sub(r'data:image/[^;\s]+;base64,[A-Za-z0-9+/=\r\n]+', '', data['text'])
  if target.exists():
    data['raw_result_path'] = str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target)
  data = {k: v for k, v in data.items() if k not in ['raw', 'boxes', 'scores']}
  timing['finished_offset_seconds'] = time.perf_counter() - batch_start
  return {**data, **timing}


def compare(source, chosen, reference, mode='parallel'):
  selected = [engine for engine in ENGINES if engine in (chosen or [])]
  if not source or not selected:
    raise gr.Error('请上传图片并至少选择一个方案')
  if mode not in ['parallel', 'sequential']:
    raise gr.Error('请选择并行或顺序模式')
  texts = ['未选择'] * 4
  stats = {}
  def view(status, report=None):
    return [status, *texts, [stats[e] for e in ENGINES if e in stats], report]
  yield view('准备同一份输入…')
  folder = OUTPUT / (time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
  folder.mkdir(parents=True)
  image_path = folder/'input.png'
  with Image.open(source) as img:
    rgb = ImageOps.exif_transpose(img).convert('RGB')
    rgb.thumbnail((2000, 2000))
    rgb.save(image_path)
  result = {'input_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
    'reference': reference, 'normalization': 'v3.1: structured text with literal list markers; NFC graphemes; remove whitespace; retain case/punctuation/width/order',
    'execution_mode': mode,
    'note': '同一RGB图，长边≤2000，各引擎独立启动；并行耗时受资源争抢影响，非热推理基准', 'models': {}}
  for i, engine in enumerate(ENGINES):
    if engine in selected:
      texts[i] = '识别中…' if mode == 'parallel' else '等待顺序处理…'
  label = '并行' if mode == 'parallel' else '顺序'
  yield view(f'{label}对比中 · 0/{len(selected)} 完成')
  batch_start = time.perf_counter()
  report = folder/'comparison.json'
  # worker只返回结果；UI和汇总文件由主线程更新，避免写入冲突
  with ThreadPoolExecutor(max_workers=len(selected) if mode == 'parallel' else 1) as pool:
    futures = {pool.submit(recognize, e, image_path, folder, reference or '', batch_start): e for e in selected}
    for future in as_completed(futures):
      engine = futures[future]
      try:
        data = future.result()
      except Exception as error:
        data = {'error': str(error), 'recognition_status': 'error', 'scoring_status': 'unavailable',
          'wall_seconds': None, 'finished_offset_seconds': time.perf_counter() - batch_start}
      i = list(ENGINES).index(engine)
      wall = round(data['wall_seconds'], 2) if data.get('wall_seconds') is not None else None
      if data.get('scoring_status') in ['error', 'unavailable']:
        score = '评分不可用'
      elif data.get('cer') is not None:
        score = f"{data['cer']:.1%}" + ('（失败按空输出）' if 'error' in data else '')
      else:
        score = '未提供有效参考'
      if 'error' in data:
        texts[i] = f"识别失败：{data['error']}"
        stats[engine] = [ENGINES[engine], '识别失败', wall, None, None, score]
      else:
        texts[i] = data['text'] or '（空输出）'
        state = '完成' if data['text'] else '空输出'
        if data.get('scoring_status') == 'error':
          state += ' · 评分失败'
        stats[engine] = [ENGINES[engine], state, wall,
          round(data['load_seconds'], 2), round(data['seconds'], 2), score]
      result['models'][engine] = data
      result['elapsed_seconds'] = time.perf_counter() - batch_start
      report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
      yield view(f"{label}对比中 · {len(result['models'])}/{len(selected)} 完成 · {ENGINES[engine]} 已处理", str(report))
  failed = sum('error' in row for row in result['models'].values())
  scoring_failed = sum(row.get('scoring_status') in ['error', 'unavailable'] for row in result['models'].values())
  status = '部分完成，请查看失败项' if failed else ('识别完成，部分评分不可用' if scoring_failed else '对比完成')
  yield view(f"{status} · {label}总用时 {result['elapsed_seconds']:.2f} 秒", str(report))


def build():
  with gr.Blocks(title='OCR 对比') as app:
    gr.Markdown('# OCR 对比\n同一张图片，比较识别结果与耗时；默认并行，先完成先显示；需要测速时可切换顺序模式')
    with gr.Row():
      source = gr.Image(type='filepath', sources=['upload', 'clipboard'], label='上传或粘贴图片')
      with gr.Column():
        engines = gr.CheckboxGroup(choices=[(v,k) for k,v in ENGINES.items()],
          value=['rapid', 'mineru', 'docling', 'apple'], label='参与对比的方案')
        mode = gr.Radio(choices=[('并行 · 减少等待', 'parallel'), ('顺序 · 用于测速', 'sequential')],
          value='parallel', label='运行方式')
        reference = gr.Textbox(label='人工参考文本（可选）', lines=5,
          placeholder='填写后计算字符错误率；请确认这是图片的完整正确文字')
        submit = gr.Button('开始对比', variant='primary')
    examples = json.loads((ROOT/'configs/ui-examples.json').read_text())
    available = [row for row in examples if (ROOT/row['path']).is_file()]
    if available:
      gr.Examples(examples=[[str(ROOT/row['path']), ''] for row in available],
        inputs=[source, reference], example_labels=[row['label'] for row in available],
        examples_per_page=20, label='默认示例 · 点击载入，选择方案后开始对比', cache_examples=False)
    if len(available) < len(examples):
      gr.Markdown('部分示例尚未恢复，当前只展示本机可用图片')
    status = gr.Markdown()
    outputs = []
    with gr.Row():
      for label in ENGINES.values():
        outputs.append(gr.Textbox(label=label, lines=15, interactive=False))
    stats = gr.Dataframe(headers=['方案','状态','总耗时秒','初始化秒','处理秒','正文CER ↓'], interactive=False)
    gr.Markdown('正文CER =（错字+漏字+多字）÷参考字数，越低越好，可超过100%。参考必须完整且阅读顺序一致；只填部分内容会把其余识别文字算成多字。按Unicode字素计数，忽略空白，保留大小写、标点、全半角和简繁；MinerU/Docling从结构化节点提取文字，不计生成的Markdown标记或图片编码。真实列表编号保留；评分异常显示不可用并保留识别结果。版面、表格、公式不由此指标评价。并行耗时受资源争抢影响；总耗时含进程启动，处理秒可能含延迟加载')
    download = gr.File(label='下载本次对比记录')
    submit.click(compare, inputs=[source, engines, reference, mode], outputs=[status,*outputs,stats,download], concurrency_limit=1)
  return app


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--port', type=int, default=7861)
  args = parser.parse_args()
  build().queue().launch(server_name='127.0.0.1', server_port=args.port, share=False,
    allowed_paths=[str(OUTPUT), str(ROOT/'data/outputs/bench-20261030/inputs'), str(ROOT/'data/fixtures')])
