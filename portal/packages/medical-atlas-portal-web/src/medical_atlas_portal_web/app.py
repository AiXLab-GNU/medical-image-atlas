"""Front page of the medical image atlas: one entry for the retinal, mammography and prostate-pathology atlases.

Each domain atlas is its own web service (own port, own home page). This page only reads their published data
(``data/*.json`` of each domain web package and ``DOMAIN.yaml``) to show what each atlas holds, and links to the
domain home. Domain URLs are built from the host of the current request with the domain's port, so the links work
through an SSH tunnel that keeps the port numbers; ``MEDICAL_ATLAS_URL_<DOMAIN>`` overrides them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, abort, render_template, request, send_from_directory

REPO = Path(os.environ.get('MEDICAL_ATLAS_ROOT', Path(__file__).resolve().parents[5]))
PORTAL_PORT = 8875

DOMAINS = [
    {'id': 'retinal', 'area': '안과', 'name': '망막 영상 지도', 'port': 8877, 'web': 'retinal-atlas-web', 'module': 'retinal_atlas_web',
     'modalities': '안저 사진 · OCT · OCTA · 형광안저조영 등', 'lead': '망막의 해부 구조와 병변, 측정할 수 있는 특징과 관련 질병(당뇨망막병증·황반변성·녹내장·근시 등).',
     'previews': ['fundus_optic_disc', 'fundus_ex', 'oct_irf'], 'accent': '#c4562e'},
    {'id': 'mammography', 'area': '유방', 'name': '유방촬영 영상 지도', 'port': 8879, 'web': 'mammography-atlas-web', 'module': 'mammography_atlas_web',
     'modalities': '2D 유방촬영 · DBT · CEM', 'lead': '유방의 해부 구조와 종괴·석회화·구조 왜곡 등 병변, BI-RADS 기술 항목과 측정, 관련 질병.',
     'previews': ['mass_spiculated_1', 'calc_cluster_1'], 'accent': '#7c3aed'},
    {'id': 'pathology', 'area': '전립선', 'name': '병리 영상 지도', 'port': 8881, 'web': 'pathology-atlas-web', 'module': 'pathology_atlas_web',
     'modalities': 'H&E · HMWCK–AMACR IHC', 'lead': '전립선 조직의 샘·간질 구조와 글리슨 패턴·관내암·암 모방 병변, 측정과 등급 판정의 재현성.',
     'previews': ['tumor_hpf', 'cribriform'], 'accent': '#9b7fc4'},
]


def _web_data(d: dict) -> Path:
    return REPO / 'domains' / d['id'] / 'packages' / d['web'] / 'src' / d['module'] / 'data'


def _masked_dir(d: dict) -> Path:
    return REPO / 'resources' / 'datasets' / f"{d['id']}_atlas_masked_figures"


def _status(d: dict) -> str:
    path = REPO / 'domains' / d['id'] / 'DOMAIN.yaml'
    if not path.is_file():
        return ''
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('status:'):
            return line.split(':', 1)[1].strip()
    return ''


def load_domain(d: dict) -> dict:
    data = _web_data(d)
    atlas = json.loads((data / 'atlas.json').read_text(encoding='utf-8'))
    figures = json.loads((data / 'masked_figures.json').read_text(encoding='utf-8'))['figures']
    examples = json.loads((data / 'measurement_examples.json').read_text(encoding='utf-8'))['examples']
    items = atlas['items'].values()
    by_id = {f['id']: f for f in figures}
    previews = []
    for fid in d['previews']:
        f = by_id.get(fid)
        if f and (_masked_dir(d) / f['base']).is_file():
            previews.append({'base': f['base'], 'overlay': f.get('overlay') or '', 'label': f['mask_label'],
                             'width': f['width'], 'height': f['height'], 'credit': f['credit'], 'license': f['license']})
    status = _status(d)
    return dict(d, counts={
        'anatomy': sum(1 for i in items if i.get('section') == 'anatomy'),
        'lesions': sum(1 for i in items if i.get('section') == 'lesions'),
        'features': len(atlas.get('features', {})), 'diseases': len(atlas.get('diseases', {})),
        'imaging': len(atlas.get('imaging', {})), 'figures': len(figures), 'examples': len(examples)},
        previews=previews, review_pending='EXPERT_REVIEW_PENDING' in status, files={p['base'] for p in previews} |
        {p['overlay'] for p in previews if p['overlay']})


def domain_url(d: dict) -> str:
    env = os.environ.get(f"MEDICAL_ATLAS_URL_{d['id'].upper()}")
    if env:
        return env.rstrip('/') + '/'
    host = request.host.rsplit(':', 1)[0] if request.host.count(':') == 1 else request.host.split(']')[0] + ']'
    return f"{request.scheme}://{host}:{d['port']}/"


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)
    domains = [load_domain(d) for d in DOMAINS]
    by_id = {d['id']: d for d in domains}

    @app.get('/')
    def index():
        cards = [dict(d, url=domain_url(d)) for d in domains]
        totals = {k: sum(d['counts'][k] for d in domains) for k in ('anatomy', 'lesions', 'features', 'diseases', 'figures', 'examples')}
        return render_template('index.html', domains=cards, totals=totals)

    @app.get('/preview/<domain>/<path:name>')
    def preview(domain, name):
        d = by_id.get(domain)
        if not d or name not in d['files']:
            abort(404)
        return send_from_directory(_masked_dir(d), name, max_age=3600)

    @app.get('/go/<domain>')
    def go(domain):
        from flask import redirect
        d = by_id.get(domain)
        if not d:
            abort(404)
        return redirect(domain_url(d))

    @app.get('/health')
    def health():
        return {'status': 'ok', 'site': 'medical_atlas_portal_web', 'domains': [d['id'] for d in domains]}

    return app
