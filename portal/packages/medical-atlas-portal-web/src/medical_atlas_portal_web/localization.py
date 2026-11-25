"""Deterministic English views of the atlas; source data and provider bytes stay canonical.

Catalogs are checked in under data/english. No translation service is called at
build or request time. Domain factories receive ``localize`` through app config.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from werkzeug.wrappers import Request, Response

HANGUL = re.compile('[가-힣]')
CATALOG_DIR = Path(__file__).with_name('data') / 'english'


class EnglishCatalog:
    def __init__(self, directory: Path = CATALOG_DIR, domain: str = ''):
        self.messages = {}
        for path in sorted(directory.glob('*.json'), key=lambda p: (p.name == 'interface.json', p.name)):
            if path.name == 'contexts.json':
                continue
            messages = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(messages, dict):
                raise ValueError(f'English catalog must be a mapping: {path.name}')
            self.messages.update({unescape(source): unescape(target) for source, target in messages.items()})
        contexts = directory / 'contexts.json'
        if domain and contexts.is_file():
            self.messages.update(json.loads(contexts.read_text(encoding='utf-8')).get(domain, {}))
        # One-character replacements inside words corrupt untranslated medical terms.
        phrases = sorted((s for s in self.messages if len(s) > 1 and HANGUL.search(s)), key=len, reverse=True)
        # A short label must not consume a prefix of a longer Korean medical term.
        patterns = [re.escape(s) + (r'(?![가-힣])' if HANGUL.fullmatch(s[-1]) else '') for s in phrases]
        self.phrases = re.compile('|'.join(patterns)) if patterns else None
        self.originals = {target: source for source, target in self.messages.items()
                          if len(target) >= 3 and HANGUL.search(source)}
        targets = sorted(self.originals, key=len, reverse=True)
        self.reverse_phrases = re.compile('|'.join(map(re.escape, targets))) if targets else None

    @lru_cache(maxsize=32768)
    def translate(self, value: str) -> str:
        if not HANGUL.search(value):
            return value
        core = value.strip()
        if core in self.messages:
            return value.replace(core, self.messages[core], 1)
        # Jinja can combine an already-localized data field with literal interface text.
        # Recover a source sentence only when it has a complete checked-in translation.
        if self.reverse_phrases:
            original = self.reverse_phrases.sub(lambda m: self.originals[m.group()], core)
            if original in self.messages:
                return value.replace(core, self.messages[original], 1)
        out = self.phrases.sub(lambda m: self.messages[m.group()], value) if self.phrases else value
        # Counts are composed by templates, not stored as complete source sentences.
        out = re.sub(r'(\d+)\s*개(?=\s|[·/(),.:]|$)', r'\1 items', out)
        out = re.sub(r'(\d+)\s*장(?=\s|[·/(),.:]|$)', r'\1 images', out)
        return out

    def localize(self, value):
        if isinstance(value, str):
            return self.translate(value)
        if isinstance(value, dict):
            return {key: self.localize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.localize(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.localize(item) for item in value)
        return value


@lru_cache(maxsize=4)
def english_catalog(domain: str = '') -> EnglishCatalog:
    return EnglishCatalog(domain=domain)


def english_url(value: str, host: str, base: str = '') -> str:
    """Keep internal navigation within English; leave external/citation URLs intact."""
    parts = urlsplit(value)
    if parts.scheme and parts.scheme not in ('http', 'https'):
        return value
    if parts.netloc and parts.netloc != host:
        return value
    if not parts.path.startswith('/'):
        return value
    base = base.rstrip('/')
    path = parts.path
    if base and (path == base or path.startswith(base + '/')):
        path = path[len(base):] or '/'
    if path != '/en' and not path.startswith('/en/'):
        path = '/en' + path
    return urlunsplit((parts.scheme, parts.netloc, base + path, parts.query, parts.fragment))


class EnglishHTML(HTMLParser):
    """Translate text, accessible labels and viewer JSON, never executable code.

    Original start-tag spelling is retained (including case-sensitive inline SVG).
    URLs, IDs and code literals are not passed through the text catalog.
    """
    ATTR = re.compile(r'(?P<name>[\w:-]+)(?P<eq>\s*=\s*)(?P<q>[\"\x27])(?P<value>.*?)(?P=q)', re.S)
    TEXT_ATTRS = {'alt', 'title', 'placeholder', 'aria-label', 'content', 'data-label', 'data-name'}

    def __init__(self, catalog: EnglishCatalog, host: str, base: str = ''):
        super().__init__(convert_charrefs=True)
        self.catalog = catalog
        self.host = host
        self.base = base
        self.output = []
        self.protected = []
        self.json_script = False
        self.source_lines = []

    def render(self, source: str) -> str:
        self.source_lines = source.splitlines(keepends=True)
        self.feed(source)
        self.close()
        return ''.join(self.output)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in ('script', 'style', 'pre', 'code'):
            self.protected.append(tag)
        if tag == 'script':
            self.json_script = values.get('type', '').lower() == 'application/json'

        def attribute(m):
            name = m['name'].lower()
            value = unescape(m['value'])
            if name in ('href', 'src', 'action'):
                value = english_url(value, self.host, self.base)
            elif name in self.TEXT_ATTRS:
                value = self.catalog.translate(value)
            elif name == 'lang' and tag == 'html':
                value = 'en'
            else:
                return m.group()
            return m['name'] + m['eq'] + m['q'] + escape(value, quote=True) + m['q']

        raw = self.get_starttag_text()
        raw = self.ATTR.sub(attribute, raw)
        if tag == 'html':
            raw = re.sub(r'\blang=(?![\"\x27])[^\s>]+', 'lang="en"', raw)
            if 'lang=' not in raw:
                raw = raw[:-1] + ' lang="en">'
        self.output.append(raw)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.protected and self.protected[-1] == tag:
            self.protected.pop()

    def handle_endtag(self, tag):
        line, offset = self.getpos()
        # HTMLParser lowercases tag names; preserve SVG closing-tag case.
        raw = self.source_lines[line - 1][offset:]
        self.output.append(raw[:raw.index('>') + 1])
        if self.protected and self.protected[-1] == tag:
            self.protected.pop()
        if tag == 'script':
            self.json_script = False

    def handle_data(self, data):
        if self.json_script:
            try:
                value = self.catalog.localize(json.loads(data))
            except (ValueError, TypeError):
                self.output.append(data)
            else:
                # JSON embedded in HTML must not introduce a closing script tag.
                self.output.append(json.dumps(value, ensure_ascii=True).replace('<', '\\u003c'))
        elif self.protected:
            self.output.append(data if self.protected[-1] in ('script', 'style') else escape(data, quote=False))
        else:
            self.output.append(escape(self.catalog.translate(data), quote=False))

    def handle_entityref(self, name):
        self.output.append('&' + name + ';')

    def handle_charref(self, name):
        self.output.append('&#' + name + ';')

    def handle_comment(self, data):
        self.output.append('<!--' + data + '-->')

    def handle_decl(self, decl):
        self.output.append('<!' + decl + '>')

    def handle_pi(self, data):
        self.output.append('<?' + data + '>')


def language_controls(source: str, request: Request, english: bool) -> str:
    path = request.path
    korean_path = path[3:] or '/' if english else path
    english_path = '/en' + korean_path
    query = ('?' + request.query_string.decode('latin1')) if request.query_string else ''
    base = request.script_root
    ko = escape(base + korean_path + query, quote=True)
    en = escape(base + english_path + query, quote=True)
    current = 'en' if english else 'ko'
    assets = base + ('/en' if english else '')
    head = (f'<link rel="alternate" hreflang="ko" href="{ko}">'
            f'<link rel="alternate" hreflang="en" href="{en}">'
            f'<link rel="stylesheet" href="{assets}/static/language.css">'
            f'<script defer src="{assets}/static/language.js"></script>')
    switch = ('<nav class="atlas-language" aria-label="Language" data-language-selector>'
              f'<a href="{ko}" lang="ko" hreflang="ko" data-language-switch'
              + (' aria-current="true"' if current == 'ko' else '') + '>한국어</a>'
              f'<a href="{en}" lang="en" hreflang="en" data-language-switch'
              + (' aria-current="true"' if current == 'en' else '') + '>English</a></nav>')
    # Load the language-switch behavior before the domain's deferred viewer scripts.
    if '<head>' in source:
        source = source.replace('<head>', '<head>' + head, 1)
    elif '</head>' in source:
        source = source.replace('</head>', head + '</head>', 1)
    else:
        source = head + source
    if '<!-- atlas-language-switch -->' in source:
        return source.replace('<!-- atlas-language-switch -->', switch, 1)
    return source.replace('</body>', switch + '</body>', 1) if '</body>' in source else source + switch


class BilingualApplication:
    """Route /en to independent English app instances; stream binary responses unchanged."""
    def __init__(self, korean_app, english_app, catalog: EnglishCatalog):
        self.korean_app = korean_app
        self.english_app = english_app
        self.catalog = catalog

    def __call__(self, environ, start_response):
        request = Request(environ)
        english = request.path == '/en' or request.path.startswith('/en/')
        if request.path == '/en':
            query = ('?' + request.query_string.decode('latin1')) if request.query_string else ''
            return Response('', status=308, headers={'Location': request.script_root + '/en/' + query})(environ, start_response)
        domain = request.path.split('/')[2] if english and len(request.path.split('/')) > 2 else ''
        catalog = english_catalog(domain) if domain in ('retinal', 'mammography', 'pathology') else self.catalog
        selected = self.english_app if english else self.korean_app
        inner = environ.copy()
        # Render the GET representation so HEAD advertises its actual translated length.
        if request.method == 'HEAD':
            inner['REQUEST_METHOD'] = 'GET'
        schematic = english and '/static/schematics/' in request.path and request.path.endswith('.svg')
        if schematic:
            # Source file validators and byte offsets do not describe the translated SVG.
            for header in ('HTTP_IF_NONE_MATCH', 'HTTP_IF_MODIFIED_SINCE', 'HTTP_RANGE', 'HTTP_IF_RANGE'):
                inner.pop(header, None)
        if english:
            inner['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + '/en'
            inner['PATH_INFO'] = request.path[3:] or '/'
        response = Response.from_app(selected, inner, buffered=False)
        if english and response.location:
            response.location = english_url(response.location, request.host, request.script_root)
        if schematic and response.mimetype == 'image/svg+xml' and response.status_code == 200:
            response.set_data(EnglishHTML(catalog, request.host, request.script_root).render(response.get_data(as_text=True)))
            for header in ('ETag', 'Last-Modified', 'Content-Range', 'Accept-Ranges'):
                response.headers.pop(header, None)
            response.set_etag(hashlib.sha256(response.get_data()).hexdigest())
            response.headers['Content-Language'] = 'en'
            response.make_conditional(environ, accept_ranges=False)
        if response.mimetype == 'text/html':
            source = response.get_data(as_text=True)
            if english:
                source = EnglishHTML(catalog, request.host, request.script_root).render(source)
            response.set_data(language_controls(source, request, english))
            response.headers['Content-Language'] = 'en' if english else 'ko'
        return response(environ, start_response)


class EnglishTextAudit(HTMLParser):
    """Find untranslated visible prose; original source-code listings are exempt."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.protected = []
        self.untranslated = set()

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'pre', 'code'):
            self.protected.append(tag)
        if not self.protected:
            for name, value in attrs:
                if name in EnglishHTML.TEXT_ATTRS and value and HANGUL.search(value):
                    self.untranslated.add(value.strip())

    def handle_endtag(self, tag):
        if self.protected and self.protected[-1] == tag:
            self.protected.pop()

    def handle_data(self, data):
        text = data.strip()
        if not self.protected and text != '한국어' and HANGUL.search(text):
            self.untranslated.add(text)


def untranslated_text(source: str) -> list[str]:
    audit = EnglishTextAudit()
    audit.feed(source)
    audit.close()
    return sorted(audit.untranslated)
