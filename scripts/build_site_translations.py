"""Build local public-site catalogs. No translation service is called at runtime.

Only committed public copy is sent to the translation service; never render user data.
Run with Python 3: python3 scripts/build_site_translations.py
"""
import ast
import concurrent.futures
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ('en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar')

def normalize(value):
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()

class CopyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocked = []
        self.copy = set()
    def add(self, text):
        text = normalize(text)
        if text and re.search(r'[a-zA-ZçğıöşüÇĞİÖŞÜ]', text) and not re.search(r'[{}]|https?://|^[/#.\w-]+\.(js|css|png|jpg|svg)$', re.sub(r'\$\{[^}]+\}', 'GRCPLACEHOLDER', text)):
            self.copy.add(text)
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.blocked.append(tag)
        for key, value in attrs:
            if value and key in ('title', 'placeholder', 'aria-label', 'alt', 'content'):
                self.add(value)
    def handle_endtag(self, tag):
        if self.blocked and tag == self.blocked[-1]: self.blocked.pop()
    def handle_data(self, data):
        if not self.blocked: self.add(data)

def source_strings():
    parser = CopyParser()
    for path in (ROOT / 'landing/templates/landing').glob('*.html'):
        if path.name == 'traffic_dashboard.html': continue
        parser.feed(re.sub(r'{%.*?%}', '', path.read_text(), flags=re.S))
    for name in ('login.html',):
        parser.feed(re.sub(r'{%.*?%}', '', (ROOT / 'core/templates' / name).read_text(), flags=re.S))
    for path in (ROOT / 'static/js').glob('*.js'):
        if path.name == 'site-language.js': continue
        for match in re.finditer(r'''(['"`])((?:\\.|(?!\1).)*?)\1''', path.read_text(), re.S):
            value = match.group(2)
            if re.search('[çğıöşüÇĞİÖŞÜ]', value) and '<' not in value:
                parser.add(value)
    for name in ('views.py', 'legal.py', 'bootcamp_catalog.py', 'travel.py', 'curriculum.py'):
        path = ROOT / 'landing' / name
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and (name == 'curriculum.py' or re.search('[çğıöşüÇĞİÖŞÜ]', node.value)) and '\n' not in node.value:
                parser.add(node.value)
    return sorted(parser.copy)

def placeholder_copy(value):
    counter = iter(range(100))
    return re.sub(r'\$\{[^}]+\}', lambda match: 'GRCPLACEHOLDER' + str(next(counter)), value)

def translate_batch(language, batch):
    params = [('client', 'dict-chrome-ex'), ('sl', 'tr'), ('tl', language)] + [('q', placeholder_copy(value)) for value in batch]
    url = 'https://clients5.google.com/translate_a/t?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=40) as response:
                translated = json.load(response)
            if len(translated) != len(batch) or not all(isinstance(value, str) for value in translated):
                raise ValueError('Unexpected translation response')
            return dict(zip(batch, translated))
        except Exception:
            if attempt == 3: raise
            time.sleep(2 ** attempt)

def build(language, sources):
    target = ROOT / 'static/i18n' / (language + '.json')
    catalog = json.loads(target.read_text()) if target.exists() else {}
    missing = [source for source in sources if source not in catalog]
    batches, batch, size = [], [], 0
    for value in missing:
        length = len(urllib.parse.quote(value))
        if batch and size + length > 5500:
            batches.append(batch); batch, size = [], 0
        batch.append(value); size += length + 4
    if batch: batches.append(batch)
    for index, batch in enumerate(batches):
        catalog.update(translate_batch(language, batch))
        target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
        print(f'{language}: {index + 1}/{len(batches)}', flush=True)
    overrides = json.loads((ROOT / 'static/i18n/overrides.json').read_text())[language]
    catalog.update(overrides)
    if language == 'ar':
        catalog = {key: value.replace('مركز الخليج للأبحاث', 'GRC').replace('مركز أبحاث الخليج', 'GRC') for key, value in catalog.items()}
    target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    return language, len(catalog)

if __name__ == '__main__':
    sources = source_strings()
    print(f'{len(sources)} public source strings', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda language: build(language, sources), LANGUAGES): print(result, flush=True)
