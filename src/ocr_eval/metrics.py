"""CER v3：固定参考、顺序编辑距离，格式与文字分离"""
from collections import Counter
from html.parser import HTMLParser
import json
import sys
import unicodedata

import regex
from rapidfuzz.distance import Levenshtein

POLICY = 'v3.1 (Docling list markers): NFC graphemes; remove whitespace; preserve case, punctuation, width and order'


def units(text, mode='primary'):
  text = unicodedata.normalize('NFC', text)
  text = text.translate(dict.fromkeys(map(ord, '\ufeff\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069')))
  if mode == 'han':
    text = ''.join(regex.findall(r'\p{Script=Han}\p{M}*', text))
  elif mode == 'alnum':
    text = ''.join(c for c in text if unicodedata.category(c)[0] in 'LNM')
  elif mode == 'primary':
    text = ''.join(text.split())
  elif mode == 'spaces':
    text = ' '.join(text.split())
  else:
    raise ValueError(mode)
  return regex.findall(r'\X', text)


def score(reference, prediction, mode='primary'):
  a, b = units(reference, mode), units(prediction, mode)
  counts = Counter(op.tag for op in Levenshtein.editops(a, b))
  s, d, i = counts['replace'], counts['delete'], counts['insert']
  return dict(reference_chars=len(a), prediction_chars=len(b), substitutions=s,
    deletions=d, insertions=i, errors=s+d+i, cer=(s+d+i)/len(a) if a else None,
    exact=a == b)


class TableText(HTMLParser):
  def __init__(self):
    super().__init__(convert_charrefs=True)
    self.parts = []

  def handle_data(self, data):
    self.parts.append(data)

  def handle_endtag(self, tag):
    if tag in ['td', 'th', 'tr', 'p', 'div']:
      self.parts.append('\n')

  def handle_starttag(self, tag, attrs):
    if tag == 'br':
      self.parts.append('\n')


def plain_text(engine, result):
  """读取结构化文字节点，绝不以正则删除正文中的 #、*、数字"""
  if engine in ['rapid', 'apple']:
    return result['text']
  raw = result['raw']
  parts = []
  if engine == 'mineru':
    def visit(node):
      if isinstance(node, list):
        for item in node:
          visit(item)
      elif isinstance(node, dict):
        content = node.get('content')
        if isinstance(content, (dict, list)):
          visit(content)
        elif isinstance(content, str):
          kind = node.get('type')
          if kind in ['text', 'inline_equation', 'interline_equation', 'equation', 'equation_inline', 'equation_interline']:
            parts.append(content)
          elif kind == 'table_body':
            parser = TableText()
            parser.feed(content)
            parts.append(''.join(parser.parts))
          elif kind not in ['image', 'image_body'] and content.strip():
            raise ValueError(f'未支持的MinerU文字节点：{kind}')
    for page in raw['pages']:
      visit(page.get('blocks', []))
  elif engine == 'docling':
    visited = set()
    def visit(ref):
      if ref in visited:
        return
      visited.add(ref)
      node = raw
      for key in ref.removeprefix('#/').split('/'):
        node = node[int(key)] if isinstance(node, list) else node[key]
      if 'text' in node:
        text = node['text']
        marker = node.get('marker', '').strip()
        # 枚举编号或orig中真实存在的符号；不补生成的Markdown项目符号
        literal = node.get('enumerated') or node.get('orig', '').lstrip().startswith(marker)
        if node.get('label') == 'list_item' and marker and literal and not text.lstrip().startswith(marker):
          text = marker + ' ' + text
        parts.append(text)
      if node.get('label') == 'table':
        cells = node['data']['table_cells']
        for cell in sorted(cells, key=lambda c: (c['start_row_offset_idx'], c['start_col_offset_idx'])):
          parts.append(cell['text'])
      for child in node.get('children', []):
        visit(child['$ref'])
      for key in ['captions', 'footnotes']:
        for child in node.get(key, []):
          visit(child['$ref'])
    visit('#/body')
    visit('#/furniture')
  else:
    raise ValueError(engine)
  return '\n'.join(parts)


if __name__ == '__main__':
  args = json.load(sys.stdin)
  prediction = plain_text(args['engine'], args['result'])
  print(json.dumps({'plain_text': prediction, 'policy': POLICY,
    **score(args['reference'], prediction)}, ensure_ascii=False))
