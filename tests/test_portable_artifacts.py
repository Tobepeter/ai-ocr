import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
  spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


exporter, restore = load('export-report-summary'), load('restore-derived')


class PortableArtifactsTest(unittest.TestCase):
  def test_summary_drops_raw_text_and_local_commands(self):
    data = {'policy': 'test', 'models': {'rapid': {'groups': {'english': {'cer': .1}},
      'setup': {'versions': {'rapidocr': '3.8.1'}, 'path': 'PRIVATE'},
      'exit': {'exit_code': 0, 'command': ['PRIVATE'], 'case_peak_tree_rss_bytes': {'PRIVATE': 10}}}},
      'cases': [{'reference': 'PRIVATE', 'plain_text': 'PRIVATE'}]}
    text = json.dumps(exporter.summarize(data))
    self.assertNotIn('PRIVATE', text)
    self.assertIn('3.8.1', text)
    self.assertIn('0.1', text)

  def test_restore_is_idempotent_and_refuses_changed_file(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder)/'test.png'
      expected = restore.digest(b'fixed')
      self.assertTrue(restore.restore(path, expected, lambda: b'fixed'))
      self.assertFalse(restore.restore(path, expected, lambda: self.fail('不应重新生成')))
      path.write_bytes(b'changed')
      with self.assertRaises(ValueError):
        restore.restore(path, expected, lambda: b'fixed')
      self.assertEqual(path.read_bytes(), b'changed')

  def test_wrong_regeneration_does_not_write(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder)/'test.png'
      with self.assertRaises(ValueError):
        restore.restore(path, restore.digest(b'fixed'), lambda: b'different')
      self.assertFalse(path.exists())


if __name__ == '__main__':
  unittest.main()
