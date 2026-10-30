import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]


def load(name):
  spec = importlib.util.spec_from_file_location(name, ROOT / f'scripts/{name}.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


runner, worker, report = [load(name) for name in ['bench-v3-run', 'bench-v3-worker', 'bench-v3-report']]


class BenchmarkTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.image = self.root / 'image.png'
    self.image.write_bytes(b'fixed input')
    self.sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
    regions = [{'case_id': 'zh', 'parent_case_id': 'parent-zh', 'dataset': 'XFUND',
      'language_group': 'chinese-or-mixed', 'reference': '中文', 'input_path': str(self.image), 'sha256': self.sha},
      {'case_id': 'en', 'parent_case_id': 'parent-en', 'dataset': 'FUNSD',
      'language_group': 'english', 'reference': 'AB', 'input_path': str(self.image), 'sha256': self.sha}]
    self.manifest = self.root / 'regions.json'
    self.manifest.write_text(json.dumps({'cases': regions}))
    self.pages = self.root / 'pages.json'
    self.pages.write_text(json.dumps({'cases': [{'case_id': 'omni-003', 'phase': 'preflight',
      'prepared_path': str(self.image), 'prepared_sha256': self.sha}]}))
    self.run = self.root / 'new-run'

  def prepare(self):
    return runner.prepare(self.run, self.manifest, self.pages, ['rapid'])

  def test_refuse_existing_before_any_write(self):
    self.run.mkdir()
    sentinel = self.run / 'inputs.json'
    sentinel.write_text('old evidence')
    with self.assertRaises(FileExistsError):
      self.prepare()
    self.assertEqual(sentinel.read_text(), 'old evidence')
    self.assertEqual(list(self.run.iterdir()), [sentinel])

  def test_bad_hash_does_not_create_run(self):
    self.image.write_bytes(b'changed')
    with self.assertRaises(ValueError):
      self.prepare()
    self.assertFalse(self.run.exists())

  def test_worker_uses_new_run_and_refuses_repeat(self):
    self.prepare()
    old = self.root / 'data/outputs/bench-20261030c/rapid'
    old.mkdir(parents=True)
    sentinel = old / 'zh.json'
    sentinel.write_text('old evidence')
    with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'load_engine', return_value=(lambda p: {'text': '中文'}, 0)), patch.object(worker.importlib.metadata, 'version', return_value='test'), contextlib.redirect_stdout(io.StringIO()):
      worker.run('rapid', self.run)
      with self.assertRaises(FileExistsError):
        worker.run('rapid', self.run)
    self.assertEqual(sentinel.read_text(), 'old evidence')
    self.assertEqual(json.loads((self.run / 'rapid/zh.json').read_text())['prepared_sha256'], self.sha)
    self.assertEqual(json.loads((self.run / 'rapid/summary.json').read_text())['count'], 2)

  def test_missing_and_failures_not_zero_latency(self):
    t = report.timing([{'status': 'ok', 'seconds': 2}, {'status': 'error', 'seconds': 9}, {'status': 'missing', 'seconds': None}])
    self.assertEqual(t['mean_seconds'], 2)
    self.assertEqual(t['p50_seconds'], 2)
    self.assertEqual(t['failed_seconds'], 9)
    self.assertEqual(t['count'], 1)
    self.assertEqual(t['missing_count'], 1)
    self.assertIsNone(report.timing([{'status': 'missing', 'seconds': None}])['mean_seconds'])

  def test_incomplete_report_is_explicit_and_immutable(self):
    self.prepare()
    engine = self.run / 'rapid'
    engine.mkdir()
    (engine / 'zh.json').write_text(json.dumps({'text': '中文', 'status': 'ok', 'seconds': 2, 'prepared_sha256': self.sha}))
    # 没有exit/summary/第二条结果也能输出诚实的中止诊断
    result = report.collect(self.run)
    self.assertFalse(result['complete'])
    self.assertEqual(result['models']['rapid']['region_timing']['mean_seconds'], 2)
    self.assertEqual(result['models']['rapid']['groups']['english']['cer'], 1)
    text = report.markdown(result, self.root)
    self.assertIn('已有结果 1/2 项', text)
    self.assertIn('incomplete', text)
    self.assertNotIn('480', text)
    self.assertIn('| — | —/— |', text)
    out = self.root / 'report'
    report.write_report(result, out)
    before = (out / 'report.json').read_bytes()
    with self.assertRaises(FileExistsError):
      report.write_report(result, out)
    self.assertEqual((out / 'report.json').read_bytes(), before)

  def test_keyboard_interrupt_cleans_process_group(self):
    out = self.root / 'process'
    out.mkdir()
    child_file = self.root / 'child.pid'
    grand_file = self.root / 'grand.pid'
    child_code = f"import os,sys,time,subprocess;from pathlib import Path;Path({str(child_file)!r}).write_text(str(os.getpid()));p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);Path({str(grand_file)!r}).write_text(str(p.pid));time.sleep(60)"
    wrapper = self.root / 'wrapper.py'
    wrapper.write_text(f"import sys,importlib.util;from pathlib import Path\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\ns=importlib.util.spec_from_file_location('runner',{str(ROOT / 'scripts/bench-v3-run.py')!r});m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.run_command([sys.executable,'-c',{child_code!r}],Path({str(out)!r}))\n")
    proc = subprocess.Popen([sys.executable, str(wrapper)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    child = None
    try:
      deadline = time.monotonic()+5
      while not grand_file.exists() and time.monotonic() < deadline:
        time.sleep(.02)
      self.assertTrue(grand_file.exists())
      child, grand = int(child_file.read_text()), int(grand_file.read_text())
      os.kill(proc.pid, signal.SIGINT)
      proc.communicate(timeout=8)
      for pid in [child, grand]:
        self.assertTrue(not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE)
      self.assertEqual(json.loads((out / 'exit.json').read_text())['stop_reason'], 'interrupted')
    finally:
      if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
      if child:
        try:
          os.killpg(child, signal.SIGKILL)
        except ProcessLookupError:
          pass


if __name__ == '__main__':
  unittest.main()
