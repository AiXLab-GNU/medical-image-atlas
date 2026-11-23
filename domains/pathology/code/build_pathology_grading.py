"""Slide-level Gleason grading from SICAPv2 pattern annotations, and inter-reader agreement on PAR.

SICAPv2: patches (512 px at 10×, 50 % overlap; xini/yini in 40× pixels) are put back on a per-slide canvas at
2.5×; every canvas pixel takes the label most patches give it. Pattern areas → Gleason score by the ISUP 2014
biopsy rule → grade group, compared with the provider's slide label (Gleason primary/secondary).

PAR (Sci Data 2026, CC BY 4.0): Gleason/ISUP of up to three pathologists per slide → Cohen kappa (unweighted and
quadratic), exact agreement and confusion matrices; one slide per grade group where all readers agree is shown.

Called from ``build_pathology_figures.py``; writes web ``data/grading.json`` and returns figures/examples.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import pathology_atlas_registry as registry
from pathology_measures import grading, tissue

PATCH_RE = re.compile(r'(.+?)_Block_Region_(\d+)_(\d+)_(\d+)_xini_(\d+)_yini_(\d+)')
SCALE = 16          # 40× pixels per canvas pixel (canvas at 2.5×)
PATCH = 512 * 4 // SCALE
PAR_LABELS = registry.DATASETS / 'public_pathology/par/slide_labels.tsv'
PAR_SLIDES = registry.DATASETS / 'public_pathology/par/hamamatsu'
GG_CATS = [0, 1, 2, 3, 4, 5]


# ------------------------------------------------------------------ SICAPv2

def sicap_patches():
    out = defaultdict(list)
    for path in sorted((registry.SICAP / 'images').glob('*.jpg')):
        m = PATCH_RE.match(path.stem)
        if m:
            out[m.group(1)].append((path.stem, int(m.group(5)), int(m.group(6))))
    return out


def sicap_slide_map(patches, with_rgb=False):
    xs = [x for _, x, _ in patches]
    ys = [y for _, _, y in patches]
    x0, y0 = min(xs), min(ys)
    w = (max(xs) - x0) // SCALE + PATCH
    h = (max(ys) - y0) // SCALE + PATCH
    votes = np.zeros((4, h, w), np.uint16)          # non-cancer, pattern 3, 4, 5
    rgb = np.full((h, w, 3), 245, np.uint8) if with_rgb else None
    code = {0: 0, 3: 1, 4: 2, 5: 3}
    for name, x, y in patches:
        m = np.asarray(Image.open(registry.sicap_paths(name)['mask']))
        if m.ndim == 3:
            m = m[..., 0]
        small = np.asarray(Image.fromarray(m).resize((PATCH, PATCH), Image.NEAREST))
        r, c = (y - y0) // SCALE, (x - x0) // SCALE
        for v, k in code.items():
            votes[k, r:r + PATCH, c:c + PATCH] += (small == v)
        if with_rgb:
            im = np.asarray(Image.open(registry.sicap_paths(name)['image']).convert('RGB').resize((PATCH, PATCH), Image.BILINEAR))
            rgb[r:r + PATCH, c:c + PATCH] = im
    covered = votes.sum(0) > 0
    label = np.where(covered, np.array([0, 3, 4, 5])[votes.argmax(0)], -1)
    return label, rgb


def sicap_grading():
    import pandas as pd
    truth = pd.read_excel(registry.SICAP / 'wsi_labels.xlsx')
    truth = {str(r.slide_id): (int(r.Gleason_primary), int(r.Gleason_secondary)) for r in truth.itertuples()}
    rows = []
    for slide, patches in sicap_patches().items():
        if slide not in truth:
            continue
        label, _ = sicap_slide_map(patches)
        areas = {p: int((label == p).sum()) for p in (3, 4, 5)}
        derived = grading.gleason_from_areas(areas)
        p, s = truth[slide]
        provider = f'{p}+{s}' if p else None
        gg_d = grading.grade_group(derived.value).value or 0
        gg_p = grading.grade_group(provider).value if provider else 0
        tumour = sum(areas.values())
        rows.append({'slide': slide, 'patches': len(patches), 'provider': provider or '0',
                     'derived': derived.value or '0', 'gg_provider': gg_p, 'gg_derived': gg_d,
                     **{f'p{k}': round(100 * v / tumour, 1) if tumour else 0.0 for k, v in areas.items()}})
    a = [r['gg_provider'] for r in rows]
    b = [r['gg_derived'] for r in rows]
    return {
        'n': len(rows), 'exact_score': round(100 * np.mean([r['provider'] == r['derived'] for r in rows]), 1),
        'exact_gg': round(100 * np.mean([x == y for x, y in zip(a, b)]), 1),
        'within_one_gg': round(100 * np.mean([abs(x - y) <= 1 for x, y in zip(a, b)]), 1),
        'kappa': round(grading.kappa(a, b, GG_CATS), 3), 'kappa_quadratic': round(grading.kappa(a, b, GG_CATS, 'quadratic'), 3),
        'confusion': grading.confusion(a, b, GG_CATS), 'categories': GG_CATS, 'rows': rows,
    }


def sicap_example(gr, helpers):
    """Whole-slide reconstruction card for one slide whose derived grade differs from 3+3 and matches the provider."""
    overlay, resize_mask, save, val, reading, example_head, layer, masked, SRC_S = helpers
    candidates = sorted((r for r in gr['rows'] if r['provider'] == r['derived'] and r['gg_provider'] >= 2
                         and 40 <= r['patches'] <= 160 and r['p3'] > 0 and r['p4'] > 0), key=lambda r: -r['patches'])
    pick = candidates[0]
    label, rgb = sicap_slide_map(sicap_patches()[pick['slide']], with_rgb=True)
    im = Image.fromarray(rgb)
    s = min(820 / im.width, 820 / im.height, 2.0)
    size = (max(int(im.width * s), 1), max(int(im.height * s), 1))
    base = im.resize(size, Image.LANCZOS)
    ex = example_head('ex_he_slide_grading', '슬라이드 단위 판정', '슬라이드 단위 글리슨 판정',
                      f"SICAPv2 슬라이드 {pick['slide']}의 패치 {pick['patches']}장을 원래 위치에 다시 붙인 2.5× 영상입니다. "
                      '겹치는 패치의 주석은 다수결로 합쳤습니다. 패턴 면적으로 ISUP 2014 생검 규칙에 따라 글리슨 점수와 등급군을 계산해 '
                      '공급자 판정과 비교했습니다. 화소 단위입니다.', base, SRC_S, f"images/{pick['slide']}_*.jpg", 'sicap_slide_example')
    tumour = np.isin(label, (3, 4, 5))
    fills = [(resize_mask(label == k, size), t, 120) for k, t in ((3, 'green'), (4, 'orange'), (5, 'red'))]
    layer(ex, 'patterns', '슬라이드 전체 패턴 비율', 'orange', 'tissue.pattern_percent', '다시 붙인 주석에서 종양 면적 중 패턴별 비율',
          [val(tissue.pattern_percent(label == 3, tumour, 3)), val(tissue.pattern_percent(label == 4, tumour, 4)),
           val(tissue.pattern_percent(label == 5, tumour, 5))], overlay(size, fills=fills))
    score = grading.gleason_from_areas({p: int((label == p).sum()) for p in (3, 4, 5)})
    gg = grading.grade_group(score.value)
    layer(ex, 'grade', '계산한 글리슨 점수·등급군', 'red', 'grading.gleason_from_areas',
          '가장 많은 패턴 + 가장 높은 나머지 패턴(생검 규칙) → 등급군',
          [val(score), val(gg)], overlay(size, texts=[((10, 10), f'계산 {score.value} · 등급군 {gg.value}', 'white')],
                                         outlines=[(resize_mask(tumour, size), 'red', 2)]))
    layer(ex, 'provider', '공급자 판정(판독)', 'white', '', 'SICAPv2 wsi_labels의 primary·secondary',
          [reading('ft_gleason_score', f"{pick['provider']} (공급자)"), reading('ft_isup_grade_group', f"{pick['gg_provider']} (공급자)")],
          overlay(size, texts=[((10, 40), f"공급자 {pick['provider']} · 등급군 {pick['gg_provider']}", 'white')]))
    fig = masked('slide_patterns', ['les_gleason_pattern_4', 'les_gleason_pattern_3'], '글리슨 패턴 지도(전문가 주석을 다시 붙임)',
                 f"SICAPv2 슬라이드 {pick['slide']}의 패턴 주석을 슬라이드 전체로 다시 붙였습니다(초록 3 · 주황 4 · 빨강 5).",
                 base, resize_mask(tumour, size), 'orange', SRC_S, f"images/{pick['slide']}_*.jpg", f'패치 {pick["patches"]}장을 2.5×로 다시 붙임')
    return ex, fig


# ------------------------------------------------------------------ PAR

def par_rows():
    with PAR_LABELS.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def _gg(v):
    return int(v) if v not in ('', None) else None


def par_agreement():
    rows = par_rows()
    pairs = {}
    for a, b, name in (('isup_1', 'isup_r2', '판독의 1–2'), ('isup_1', 'isup_r3', '판독의 1–3'), ('isup_r2', 'isup_r3', '판독의 2–3')):
        x = [(_gg(r[a]), _gg(r[b])) for r in rows if _gg(r[a]) is not None and _gg(r[b]) is not None]
        xa, xb = [p for p, _ in x], [q for _, q in x]
        pairs[name] = {
            'n': len(x), 'exact': round(100 * np.mean([p == q for p, q in x]), 1),
            'within_one': round(100 * np.mean([abs(p - q) <= 1 for p, q in x]), 1),
            'cancer_agree': round(100 * np.mean([(p > 0) == (q > 0) for p, q in x]), 1),
            'kappa': round(grading.kappa(xa, xb, GG_CATS), 3),
            'kappa_quadratic': round(grading.kappa(xa, xb, GG_CATS, 'quadratic'), 3),
            'confusion': grading.confusion(xa, xb, GG_CATS)}
    counts = {name: [sum(1 for r in rows if _gg(r[c]) == g) for g in GG_CATS] for c, name in
              (('isup_1', '판독의 1'), ('isup_r2', '판독의 2'), ('isup_r3', '판독의 3'))}
    return {'n_slides': len(rows), 'pairs': pairs, 'counts': counts, 'categories': GG_CATS}


def par_unanimous():
    """Slides where every reader gave the same grade group (and Gleason score), one per grade group 0–5."""
    picks = {}
    for r in par_rows():
        ggs = [_gg(r[c]) for c in ('isup_1', 'isup_r2', 'isup_r3') if _gg(r[c]) is not None]
        scores = {r[c] for c in ('gleason_r1', 'gleason_r2', 'gleason_r3') if r[c]}
        if len(ggs) >= 2 and len(set(ggs)) == 1 and len(scores) == 1 and ggs[0] not in picks:
            picks[ggs[0]] = (r['slide_id'], next(iter(scores)), len(ggs))
    return picks


def par_figures(helpers):
    overlay, resize_mask, save, val, reading, example_head, layer, masked, SRC_PAR = helpers
    import tifffile
    figs = []
    for gg, (slide, score, n) in sorted(par_unanimous().items()):
        path = PAR_SLIDES / f'{slide.lower()}_hamamatsu.ndpi'
        if not path.is_file():
            continue
        with tifffile.TiffFile(path) as tif:
            levels = tif.series[0].levels
            lv = next((l for l in levels if max(l.shape[:2]) <= 3000), levels[-1])
            arr = lv.asarray()[..., :3]
        tis_full = tissue.tissue_mask(arr, min_object_px=500)
        rows, cols = np.nonzero(tis_full)
        if rows.size:
            pad = int(0.03 * max(arr.shape[:2]))
            arr = arr[max(rows.min() - pad, 0):rows.max() + pad, max(cols.min() - pad, 0):cols.max() + pad]
        im = Image.fromarray(np.ascontiguousarray(arr))
        s = min(900 / im.width, 520 / im.height, 1.0)
        size = (max(int(im.width * s), 1), max(int(im.height * s), 1))
        base = im.resize(size, Image.LANCZOS)
        tis = resize_mask(tissue.tissue_mask(np.asarray(base), min_object_px=300), size)
        label = '양성' if gg == 0 else f'ISUP 등급군 {gg}'
        figs.append(masked(f'par_gg{gg}', ['les_adenocarcinoma'] if gg else ['ana_benign_gland'], f'{label}(판독의 {n}명 일치)',
                           f'PAR 슬라이드 {slide}: 판독의 {n}명이 모두 {"양성" if gg == 0 else f"글리슨 {score}"}으로 판정한 생검입니다. '
                           '윤곽은 서비스가 찾은 조직 범위입니다.', base, tis, 'blue', SRC_PAR, f'hamamatsu/{path.name}',
                           f'NDPI 피라미드 저해상도 층({lv.shape[1]}×{lv.shape[0]})에서 조직 범위를 잘라 {size[0]} px로 축소', outline_only=True))
        figs[-1]['grade_group'] = gg
        figs[-1]['score'] = score
    return figs


def build(helpers_sicap, helpers_par):
    sicap = sicap_grading()
    ex, fig = sicap_example(sicap, helpers_sicap)
    par = par_agreement()
    par_figs = par_figures(helpers_par)
    payload = {'generated_by': 'domains/pathology/code/build_pathology_grading.py',
               'sicap': {k: v for k, v in sicap.items() if k != 'rows'}, 'sicap_rows': sicap['rows'],
               'par': par, 'par_examples': [{'figure': f['id'], 'grade_group': f['grade_group'], 'score': f['score']} for f in par_figs]}
    (registry.WEB_DATA / 'grading.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for f in par_figs:
        f.pop('grade_group', None)
        f.pop('score', None)
    return [ex], [fig] + par_figs, payload
