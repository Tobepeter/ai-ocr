import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ocr_eval.metrics import plain_text, score

class MetricsTest(unittest.TestCase):
  def test_edits(self):
    self.assertEqual(score('中国', '中国中国')['insertions'], 2)
    self.assertEqual(score('中国', '')['deletions'], 2)
    self.assertEqual(score('中国', '中田')['substitutions'], 1)
    self.assertGreater(score('中', '中国中国')['cer'], 1)
    self.assertIsNone(score('', '中')['cer'])
    self.assertGreater(score('春夏秋冬', '冬秋夏春')['errors'], 0)

  def test_unicode_and_punctuation(self):
    self.assertEqual(score('e\u0301', 'é')['cer'], 0)
    self.assertEqual(score('中 文\nA', '中文A')['cer'], 0)
    self.assertEqual(score('A，', 'a,')['errors'], 2)
    self.assertEqual(score('A，', 'A,', 'alnum')['cer'], 0)
    self.assertGreater(score('a b', 'ab', 'spaces')['cer'], 0)

  def test_mineru_structure(self):
    raw = {'pages': [{'blocks': [
      {'type': 'title', 'content': [{'type': 'text', 'content': '#原文'}]},
      {'type': 'image', 'content': [{'type': 'image_body', 'content': 'data:image/png;base64,xx'}]},
      {'type': 'table', 'content': [{'type': 'table_body', 'content': '<table><tr><td rowspan="2">甲</td><td>乙</td></tr><tr><td>乙</td></tr></table>'}]}]}]}
    text = plain_text('mineru', {'raw': raw, 'text': '## #原文 ![](x)'})
    self.assertEqual(''.join(text.split()), '#原文甲乙乙')

  def test_empty_mineru_page(self):
    self.assertEqual(plain_text('mineru', {'raw': {'pages': [{'page_idx': 0}]}}), '')

  def test_han_is_explicit_subset(self):
    self.assertEqual(score('中国ABC', '中国XYZ', 'han')['cer'], 0)
    self.assertGreater(score('中国ABC', '中国XYZ')['cer'], 0)

  def test_docling_literal_and_generated_markers(self):
    nodes = [
      {'label': 'list_item', 'marker': 'A.', 'enumerated': True, 'text': 'How exciting!', 'orig': 'A. How exciting!'},
      {'label': 'list_item', 'marker': '1.', 'enumerated': True, 'text': '1. Already present'},
      {'label': 'list_item', 'marker': '*', 'enumerated': False, 'text': 'Generated', 'orig': 'Generated'},
      {'label': 'list_item', 'marker': '*', 'enumerated': False, 'text': 'Literal', 'orig': '* Literal'},
    ]
    raw = {'body': {'children': [{'$ref': f'#/texts/{i}'} for i in range(len(nodes))]},
      'furniture': {'children': []}, 'texts': nodes}
    prediction = plain_text('docling', {'raw': raw})
    expected = 'A. How exciting!\n1. Already present\nGenerated\n* Literal'
    self.assertEqual(prediction, expected)
    self.assertEqual(score(expected, prediction)['cer'], 0)

  def test_docling_references_not_text_dedup(self):
    raw = {'body': {'children': [{'$ref': '#/texts/0'}, {'$ref': '#/pictures/0'}]},
      'furniture': {'children': [{'$ref': '#/texts/0'}]},
      'texts': [{'text': '相同', 'children': []}, {'text': '相同', 'children': []}],
      'pictures': [{'children': [{'$ref': '#/texts/1'}]}]}
    self.assertEqual(plain_text('docling', {'raw': raw}), '相同\n相同')

if __name__ == '__main__':
  unittest.main()
