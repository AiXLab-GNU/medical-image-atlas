"""Export the one-channel atlas (portal + three domains) as a static site.

The dynamic service stays the source: this module runs the same Flask app in-process, follows every internal link
from ``/`` and writes what it gets. Differences from the dynamic service, all handled here:

* pages become ``<path>/index.html``; every root or same-host link becomes a relative link, so the site works under
  any base path (GitHub Pages project site, a sub-folder of another web server) and needs no configuration;
* filter pages reached through a query string (``?cat=``, ``?img=``, ``?level=``…, a finite set) are written as their
  own pages under ``<path>/_q/<params>/`` and the links point there — same content as the dynamic filter;
* free-text search (``/<domain>/search/?q=`` and the name filters on the anatomy/lesion lists) runs in the browser
  from ``_static/search_<domain>.json`` (same matching rule: every word must occur in name, English name,
  abbreviation, definition or location);
* code downloads (``?download=1``) become plain files with a ``download`` attribute on the link;
* redirects become small pages that forward; ``404.html`` and ``.nojekyll`` are added.

    .venv/bin/medical-atlas-export-static --out ../../../build/static_site
"""
from __future__ import annotations

import argparse
import collections
import json
import posixpath
import re
import shutil
from importlib import import_module
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit

from .app import DOMAINS, REPO, create_app

HOST = 'http://localhost'
ATTR = re.compile(r'(?P<attr>\b(?:href|src|action))="(?P<url>[^"]*)"')
STATIC_DIR = '_static'


def slug(query: str) -> str:
    pairs = sorted(parse_qsl(query, keep_blank_values=True))
    return '_'.join(f"{k}-{quote(v, safe='')}".replace('%', '~') for k, v in pairs) or 'all'


def target_of(url: str, page: str) -> tuple[str, str, str] | None:
    """(path, query, fragment) of an internal link, resolved against ``page``; None for external links."""
    full = urlsplit(urljoin(HOST + page, url.replace('&amp;', '&')))
    if full.scheme not in ('http', 'https') or full.netloc != 'localhost':
        return None
    return full.path or '/', full.query, full.fragment


def file_for(path: str, query: str, html: bool) -> str:
    """Site-relative file a URL is written to."""
    path = path.lstrip('/')
    if 'download' in dict(parse_qsl(query)):
        return path
    if html:
        base = path if (path.endswith('/') or not path) else path + '/'
        if query:
            base += f'_q/{slug(query)}/'
        return base + 'index.html'
    return path


def relative(from_file: str, to_file: str) -> str:
    rel = posixpath.relpath(to_file, posixpath.dirname(from_file) or '.')
    if rel.endswith('index.html'):
        rel = rel[:-len('index.html')] or './'
    return rel


class Exporter:
    def __init__(self, out: Path):
        self.out = out
        self.client = create_app({'TESTING': True}).test_client()
        self.kind: dict[str, str] = {}             # url → 'html' | 'file' | 'redirect' | 'missing'
        self.redirects: dict[str, str] = {}
        self.pages: dict[str, bytes] = {}
        self.files: dict[str, bytes] = {}

    @staticmethod
    def key(path, query):
        q = urlencode(sorted(parse_qsl(query, keep_blank_values=True)))
        return path + ('?' + q if q else '')

    def crawl(self):
        queue = collections.deque(['/'] + [f"/{d['id']}/search/" for d in DOMAINS])   # search pages: reached by forms
        while queue:
            url = queue.popleft()
            if url in self.kind:
                continue
            r = self.client.get(url, base_url=HOST)
            if r.status_code in (301, 302, 308):
                t = target_of(r.headers['Location'], url)
                self.kind[url] = 'redirect'
                if t:
                    self.redirects[url] = self.key(t[0], t[1])
                    queue.append(self.redirects[url])
                continue
            if r.status_code != 200:
                self.kind[url] = 'missing'
                continue
            if r.mimetype != 'text/html':
                self.kind[url] = 'file'
                self.files[url] = r.get_data()
                continue
            self.kind[url] = 'html'
            html = r.get_data(as_text=True)
            self.pages[url] = html.encode('utf-8')
            for m in ATTR.finditer(html):
                t = target_of(m.group('url'), url)
                if not t:
                    continue
                path, query, _ = t
                q = dict(parse_qsl(query, keep_blank_values=True))
                if m.group('attr') == 'action' or 'q' in q:     # free-text forms: handled in the browser
                    continue
                queue.append(self.key(path, query))

    def file_of(self, url: str) -> str:
        path, _, query = url.partition('?')
        return file_for(path, query, self.kind.get(url) in ('html', 'redirect'))

    def rewrite(self, url: str, html: str) -> str:
        here = self.file_of(url)

        def sub(m):
            raw = m.group('url')
            t = target_of(raw, url)
            if not t or raw.startswith('#'):
                return m.group(0)
            path, query, frag = t
            q = dict(parse_qsl(query, keep_blank_values=True))
            extra = ''
            if m.group('attr') == 'action' or 'q' in q:            # browser search keeps its query
                target = file_for(path, '', True)
                link = relative(here, target) + (('?' + query) if query and m.group('attr') != 'action' else '')
            else:
                k = self.key(path, query)
                kind = self.kind.get(k)
                if kind is None and 'download' in q:
                    kind = self.kind.get(path)
                if 'download' in q:
                    extra = ' download'
                html_like = kind in ('html', 'redirect') or (kind is None and path.endswith('/'))
                target = file_for(path, query, html_like)
                link = relative(here, target)
            if frag:
                link += '#' + frag
            return f'{m.group("attr")}="{link}"{extra}'
        html = ATTR.sub(sub, html)
        domain = url.strip('/').split('/')[0] if url.strip('/') else ''
        script = relative(here, f'{STATIC_DIR}/static_site.js')
        tag = (f'<script src="{script}" data-root="{relative(here, "index.html")}" '
               f'data-domain="{domain if domain in {d["id"] for d in DOMAINS} else ""}" defer></script>')
        return html.replace('</body>', tag + '</body>', 1) if '</body>' in html else html + tag

    def search_index(self, d: dict) -> list[dict]:
        mod = import_module(d['module'] + '.app')
        atlas = json.loads((REPO / 'domains' / d['id'] / 'packages' / d['web'] / 'src' / d['module'] / 'data' /
                            'atlas.json').read_text(encoding='utf-8'))
        out = []
        for item in atlas['items'].values():
            if item.get('section') not in ('anatomy', 'lesions'):
                continue
            out.append({'name': item.get('name', ''), 'name_en': item.get('name_en', ''), 'abbr': item.get('abbr', ''),
                        'definition': item.get('definition', ''), 'location': item.get('location', ''),
                        'section': item['section'], 'path': f"{d['id']}{mod.item_path(item)}"})
        return sorted(out, key=lambda i: (i['section'] != 'anatomy', i['name']))

    def write(self):
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        for url, body in self.files.items():
            p = self.out / self.file_of(url)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
        for url, body in self.pages.items():
            p = self.out / self.file_of(url)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.rewrite(url, body.decode('utf-8')), encoding='utf-8')
        for url, target in self.redirects.items():
            here = self.file_of(url)
            p = self.out / here
            if p.exists():
                continue
            link = relative(here, self.file_of(target))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={link}">'
                         f'<link rel="canonical" href="{link}"><a href="{link}">이동</a>', encoding='utf-8')
        static = self.out / STATIC_DIR
        static.mkdir(exist_ok=True)
        shutil.copy(Path(__file__).with_name('static') / 'static_site.js', static / 'static_site.js')
        for d in DOMAINS:
            (static / f"search_{d['id']}.json").write_text(json.dumps(self.search_index(d), ensure_ascii=False),
                                                           encoding='utf-8')
        (self.out / '.nojekyll').write_text('')
        (self.out / '404.html').write_text(
            '<!doctype html><html lang="ko"><meta charset="utf-8"><title>페이지 없음 · 의료영상 지도</title>'
            '<body style="font-family:system-ui,sans-serif;padding:40px"><h1>페이지를 찾을 수 없습니다</h1>'
            '<p><a href="./">의료영상 지도 첫 페이지로</a></p></body></html>', encoding='utf-8')
        missing = [u for u, k in self.kind.items() if k == 'missing']
        return {'pages': len(self.pages), 'files': len(self.files), 'redirects': len(self.redirects),
                'filter_pages': sum(1 for u in self.pages if '?' in u), 'missing': missing}


def main():
    parser = argparse.ArgumentParser(description='Export the medical image atlas as a static site.')
    parser.add_argument('--out', type=Path, default=REPO / 'build' / 'static_site')
    args = parser.parse_args()
    ex = Exporter(args.out.resolve())
    ex.crawl()
    report = ex.write()
    size = sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file())
    print(f"static site: {args.out} · pages {report['pages']} (filter pages {report['filter_pages']}) · files "
          f"{report['files']} · redirects {report['redirects']} · {size / 1e6:.1f} MB")
    if report['missing']:
        print('missing:', *report['missing'][:20], sep='\n  ')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
