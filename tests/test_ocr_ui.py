import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ocr_ui_test_app', ROOT / 'src/ocr_ui/app.py')
app = importlib.util.module_from_spec(spec)
# 函数回归不要求项目安装Gradio；真实服务另做API验收
with patch.dict(sys.modules, {'gradio': types.SimpleNamespace(Error=RuntimeError)}):
  spec.loader.exec_module(app)


class UiFailureTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.folder = Path(self.temp.name)

  def fake_run(self, *args, **kwargs):
    (self.folder / 'rapid.json').write_text(json.dumps({'text': '正确文字', 'seconds': .1, 'load_seconds': 0, 'raw': {'keep': True}}))

  def test_scoring_error_preserves_ocr_and_does_not_retry(self):
    with patch.object(app, 'run_process', self.fake_run), patch.object(app, 'tool_python', return_value='unused'), patch.object(app, 'evaluate', side_effect=RuntimeError('unavailable')) as evaluate:
      result = app.recognize('rapid', 'unused', self.folder, '正确文字', time.perf_counter())
    self.assertEqual(evaluate.call_count, 1)
    self.assertEqual(result['text'], '正确文字')
    self.assertEqual(result['recognition_status'], 'ok')
    self.assertEqual(result['scoring_status'], 'error')
    self.assertIsNone(result['cer'])
    self.assertNotIn('error', result)
    self.assertEqual(json.loads((self.folder / 'rapid.json').read_text())['raw'], {'keep': True})

  def test_ocr_failure_can_still_score_empty(self):
    with patch.object(app, 'run_process', side_effect=RuntimeError('engine failed')), patch.object(app, 'tool_python', return_value='unused'), patch.object(app, 'evaluate', return_value={'cer': 1, 'deletions': 4}) as evaluate:
      result = app.recognize('rapid', 'unused', self.folder, '正确文字', time.perf_counter())
    self.assertEqual(result['recognition_status'], 'error')
    self.assertEqual(result['cer'], 1)
    self.assertEqual(evaluate.call_args.args[2], {'text': ''})

  def test_ocr_and_scorer_both_fail_returns_without_raising(self):
    with patch.object(app, 'run_process', side_effect=RuntimeError('engine failed')), patch.object(app, 'tool_python', return_value='unused'), patch.object(app, 'evaluate', side_effect=RuntimeError('scorer failed')):
      result = app.recognize('rapid', 'unused', self.folder, '正确文字', time.perf_counter())
    self.assertIn('error', result)
    self.assertEqual(result['scoring_status'], 'error')
    self.assertIsNone(result['cer'])

  def test_future_exception_does_not_abort_other_engine(self):
    image = self.folder / 'image.png'
    Image.new('RGB', (10, 10), 'white').save(image)
    def recognize(engine, *args):
      if engine == 'rapid':
        raise RuntimeError('unexpected worker exception')
      return {'text': '完成', 'wall_seconds': .1, 'seconds': .05, 'load_seconds': 0, 'recognition_status': 'ok', 'scoring_status': 'not_requested'}
    with patch.object(app, 'OUTPUT', self.folder / 'results'), patch.object(app, 'recognize', side_effect=recognize):
      views = list(app.compare(str(image), ['rapid', 'apple'], '', 'parallel'))
    self.assertIn('部分完成', views[-1][0])
    result = json.loads(Path(views[-1][-1]).read_text())
    self.assertEqual(result['models']['apple']['text'], '完成')
    self.assertEqual(result['models']['rapid']['scoring_status'], 'unavailable')


if __name__ == '__main__':
  unittest.main()
