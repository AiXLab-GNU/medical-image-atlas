"""Check service measurements against provider annotations (PRECISE) and write ``data/validation.json``.

Checks
  glands      glands.segment_glands vs PRECISE benign-gland annotation (each gland drawn separately, lumen
              included): pixel Dice inside annotated tissue (benign gland + stroma) and gland-level match
              (IoU ≥ 0.5), on windows around the three largest benign-gland regions of each slide.
  stain       the same with Macenko normalisation first (stain.macenko_normalise) — adopted only if it helps.
  basal       ihc.basal_fragments / basal_cell_presence on PRECISE IHC: cut-off chosen on the largest region of
              each class per slide (tuning), checked on the 2nd–4th largest regions (held out, same slides).
  nucleoli    nuclei.nucleolus_prominence (experimental) at level 0: share of nuclei with a prominent nucleolus in
              tumour vs benign glands — adopted only if tumour is clearly higher (AUC ≥ 0.75).
  register    register.align: tissue overlap of H&E and the serial IHC section before and after alignment.

Run after ``build_pathology_figures.py``; takes a few minutes on many cores. ``export_pathology_atlas_registry.py``
turns the result into ``i_measure_validation``.
"""
from __future__ import annotations

import json
import os
import warnings
from multiprocessing import Pool

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

import pathology_atlas_registry as registry
from pathology_measures import glands, ihc, nuclei, register, stain, tissue

warnings.filterwarnings('ignore')
IOU = 0.5
IHC_CLASSES = {1: 'tumour', 2: 'benign', 4: 'hgpin', 5: 'idc', 6: 'aip'}


# ------------------------------------------------------------------ windows

def class_windows(name, cls, k, level=1, side=1400, kind='image'):
    """Up to ``k`` non-overlapping windows centred on the largest components of ``cls`` (rank 0 = largest)."""
    mask_kind = 'ihc_mask' if kind == 'ihc' else 'mask'
    coarse = registry.precise_level(name, 4, mask_kind)
    lab, n = ndi.label(coarse == cls)
    if n == 0:
        return []
    sizes = np.bincount(lab.ravel())[1:]
    f = 2 ** (4 - level)
    H, W = registry.precise_level_shape(name, level, kind)[:2]
    out, used = [], []
    for rank, i in enumerate(np.argsort(sizes)[::-1]):
        if sizes[i] < 20:
            break
        cy, cx = (v * f for v in ndi.center_of_mass(lab == i + 1))
        if any(abs(cy - a) < side and abs(cx - b) < side for a, b in used):
            continue
        used.append((cy, cx))
        r0 = int(min(max(cy - side / 2, 0), H - side))
        c0 = int(min(max(cx - side / 2, 0), W - side))
        out.append((len(out), (r0, r0 + side, c0, c0 + side)))
        if len(out) == k:
            break
    return out


# ------------------------------------------------------------------ gland segmentation

def match(pred_labels, gt, region, min_px):
    """Pixel Dice and gland-level counts; predicted glands mostly outside the annotated area are ignored."""
    keep = np.zeros(pred_labels.max() + 1, bool)
    for p in measure.regionprops(pred_labels):
        if p.area >= min_px and region[pred_labels == p.label].mean() >= 0.5:
            keep[p.label] = True
    pl = np.where(keep[pred_labels], pred_labels, 0)
    g = gt & region
    p = pl > 0
    dice = 2 * (p & g).sum() / max(p.sum() + g.sum(), 1)
    gl = measure.label(g)
    truth = [q for q in measure.regionprops(gl) if q.area >= min_px]
    tp = 0
    for q in truth:
        one = gl == q.label
        ids, counts = np.unique(pl[one], return_counts=True)
        best = max((c / (one | (pl == i)).sum() for i, c in zip(ids, counts) if i), default=0)
        tp += best >= IOU
    preds = [q for q in measure.regionprops(pl)]
    merged = sum((np.unique(gl[pl == q.label]) > 0).sum() >= 2 for q in preds)
    return {'dice': float(dice), 'truth': len(truth), 'pred': len(preds), 'tp': int(tp), 'merged': int(merged)}


def gland_case(name):
    out = []
    mpp = registry.precise_mpp(name) * 2
    for _, win in class_windows(name, 2, 3):
        rgb = registry.precise_level(name, 1, 'image', win)[..., :3]
        lab = registry.precise_level(name, 1, 'mask', win)
        if (lab == 2).sum() < 2000:
            continue
        region = np.isin(lab, (2, 7))
        row = {'slide': name}
        for key, im in (('raw', rgb), ('macenko', stain.macenko_normalise(rgb))):
            ref = tissue.tissue_mask(im)
            seg = glands.segment_glands(im, ref, mpp, reference=ref)
            row[key] = match(measure.label(seg), lab == 2, region, int(150 / mpp / mpp))
        out.append(row)
    return out


def summarise_glands(rows, key):
    t = sum(r[key]['truth'] for r in rows)
    p = sum(r[key]['pred'] for r in rows)
    tp = sum(r[key]['tp'] for r in rows)
    per_slide = {}
    for r in rows:
        per_slide.setdefault(r['slide'], []).append(r[key]['dice'])
    return {'windows': len(rows), 'slides': len(per_slide), 'dice': round(float(np.mean([r[key]['dice'] for r in rows])), 3),
            'dice_slide_sd': round(float(np.std([np.mean(v) for v in per_slide.values()])), 3),
            'truth': t, 'pred': p, 'tp': tp, 'recall': round(tp / max(t, 1), 3), 'precision': round(tp / max(p, 1), 3),
            'f1': round(2 * tp / max(t + p, 1), 3), 'merged': sum(r[key]['merged'] for r in rows)}


# ------------------------------------------------------------------ IHC basal fragments

def basal_case(name):
    out = []
    mpp = registry.precise_mpp(name, 'ihc') * 2
    for cls in IHC_CLASSES:
        for rank, win in class_windows(name, cls, 4, side=1200, kind='ihc'):
            rgb = registry.precise_level(name, 1, 'ihc', win)[..., :3]
            m = registry.precise_level(name, 1, 'ihc_mask', win) == cls
            if m.sum() < 2000:
                continue
            f = ihc.basal_fragments(rgb, m, mpp)
            if f.status == 'ok':
                out.append({'slide': name, 'cls': cls, 'rank': rank, 'value': f.value})
    return out


def summarise_basal(rows):
    tune = [r for r in rows if r['rank'] == 0]
    held = [r for r in rows if r['rank'] > 0]
    t_max = max(r['value'] for r in tune if r['cls'] == 1)
    n_min = min(r['value'] for r in tune if r['cls'] != 1)
    cut = round((t_max + n_min) / 2, 2)

    def rates(rs):
        t = [r['value'] for r in rs if r['cls'] == 1]
        n = [r['value'] for r in rs if r['cls'] != 1]
        auc = float(np.mean([(a < b) + 0.5 * (a == b) for a in t for b in n])) if t and n else float('nan')
        return {'tumour': len(t), 'tumour_absent': int(sum(v < cut for v in t)), 'other': len(n),
                'other_present': int(sum(v >= cut for v in n)), 'auc': round(auc, 3)}
    by_class = {IHC_CLASSES[c]: [round(r['value'], 2) for r in sorted(rows, key=lambda r: r['value']) if r['cls'] == c]
                for c in IHC_CLASSES}
    return {'cutoff': cut, 'tune_tumour_max': round(t_max, 2), 'tune_other_min': round(n_min, 2),
            'tune': rates(tune), 'held_out': rates(held), 'slides': len({r['slide'] for r in rows}), 'by_class': by_class}


# ------------------------------------------------------------------ nucleoli

def nucleoli_case(name):
    out = []
    mpp = registry.precise_mpp(name)
    for cls in (1, 2):
        for _, win in class_windows(name, cls, 2, level=0, side=1500):
            rgb = registry.precise_level(name, 0, 'image', win)[..., :3]
            m = registry.precise_level(name, 0, 'mask', win) == cls
            if m.sum() < 20000:
                continue
            v = nuclei.nucleolus_prominence(rgb, m, mpp)
            if v.status == 'ok':
                out.append({'slide': name, 'cls': cls, 'value': v.value, 'nuclei': v.detail['nuclei']})
    return out


def summarise_nucleoli(rows):
    t = [r['value'] for r in rows if r['cls'] == 1]
    b = [r['value'] for r in rows if r['cls'] == 2]
    auc = float(np.mean([(x > y) + 0.5 * (x == y) for x in t for y in b])) if t and b else float('nan')
    paired = {}
    for r in rows:
        paired.setdefault(r['slide'], {}).setdefault(r['cls'], []).append(r['value'])
    pairs = [(np.mean(v[1]), np.mean(v[2])) for v in paired.values() if 1 in v and 2 in v]
    return {'tumour_windows': len(t), 'benign_windows': len(b), 'tumour_median': round(float(np.median(t)), 1) if t else None,
            'benign_median': round(float(np.median(b)), 1) if b else None, 'auc': round(auc, 3),
            'paired_slides': len(pairs), 'paired_tumour_higher': int(sum(x > y for x, y in pairs))}


# ------------------------------------------------------------------ registration

def register_case(name):
    L = 5
    r = register.align(registry.precise_level(name, L, 'image')[..., :3], registry.precise_mpp(name) * 2 ** L,
                       registry.precise_level(name, L, 'ihc')[..., :3], registry.precise_mpp(name, 'ihc') * 2 ** L)
    return {'slide': name, 'before': r['dice_before'], 'global': r['dice_global'], 'cores': r['dice_cores'],
            'pieces': len(r['cores'])}


def summarise_register(rows):
    med = lambda k: round(float(np.median([r[k] for r in rows])), 3)  # noqa: E731
    return {'slides': len(rows), 'before': med('before'), 'global': med('global'), 'cores': med('cores'),
            'good_slides': int(sum(r['cores'] >= 0.7 for r in rows)), 'rows': rows}


# ------------------------------------------------------------------ main

def checks(res):
    g, s = res['glands']['raw'], res['glands']['macenko']
    b, nu, rg = res['basal'], res['nucleoli'], res['register']
    rows = [
        {'check_id': 'glands_pixel', 'function': 'glands.segment_glands', 'source_id': 'precise',
         'reference': '양성 샘 화소 주석(샘마다 따로, 내강 포함)', 'split': '전체(조정 없음)',
         'cases': f"{g['windows']} 창 · {g['slides']} 슬라이드", 'metric': '화소 Dice', 'value': g['dice'],
         'decision': '면적·분율 측정에 사용', 'note_ko': f"슬라이드 평균 Dice 표준편차 {g['dice_slide_sd']}"},
        {'check_id': 'glands_object', 'function': 'glands.segment_glands', 'source_id': 'precise',
         'reference': '양성 샘 화소 주석', 'split': '전체(조정 없음)', 'cases': f"주석 샘 {g['truth']} · 분할 {g['pred']}",
         'metric': f'샘 단위 F1(IoU≥{IOU})', 'value': g['f1'],
         'decision': '샘 개수·샘별 값은 참고용(주석이 있으면 주석 우선)',
         'note_ko': f"재현율 {g['recall']} · 정밀도 {g['precision']} · 주석 샘 2개 이상을 한 덩어리로 묶은 분할 {g['merged']}개"},
        {'check_id': 'stain_macenko', 'function': 'stain.macenko_normalise', 'source_id': 'precise',
         'reference': '양성 샘 화소 주석', 'split': '전체', 'cases': f"{s['windows']} 창", 'metric': '화소 Dice(정규화 후)',
         'value': s['dice'], 'decision': '채택 안 함' if s['dice'] <= g['dice'] else '채택',
         'note_ko': f"정규화 전 {g['dice']} → 후 {s['dice']} · 슬라이드 간 표준편차 {g['dice_slide_sd']} → {s['dice_slide_sd']}. "
                    '분할이 영상마다 Otsu로 기준을 다시 잡아 염색 차이를 이미 흡수함'},
        {'check_id': 'basal_cutoff', 'function': 'ihc.basal_cell_presence', 'source_id': 'precise',
         'reference': 'IHC 슬라이드 주석 class(침윤암 vs 양성 샘·HGPIN·관내암·비정형 관내 증식)', 'split': '조정(슬라이드별 가장 큰 영역)',
         'cases': f"{b['tune']['tumour']}+{b['tune']['other']} 창", 'metric': '기준값(100 µm당 조각)', 'value': b['cutoff'],
         'decision': '기준값으로 채택',
         'note_ko': f"조정 창에서 침윤암 최대 {b['tune_tumour_max']} · 나머지 최소 {b['tune_other_min']}의 중간값"},
        {'check_id': 'basal_heldout', 'function': 'ihc.basal_cell_presence', 'source_id': 'precise',
         'reference': 'IHC 슬라이드 주석 class', 'split': '검증(2–4번째 큰 영역, 같은 슬라이드)',
         'cases': f"{b['held_out']['tumour']}+{b['held_out']['other']} 창 · {b['slides']} 슬라이드", 'metric': 'AUC',
         'value': b['held_out']['auc'], 'decision': '기준 유지',
         'note_ko': f"침윤암 없음 판정 {b['held_out']['tumour_absent']}/{b['held_out']['tumour']} · "
                    f"나머지 있음 판정 {b['held_out']['other_present']}/{b['held_out']['other']}. 같은 슬라이드의 다른 영역이라 외부 검증은 아님"},
        {'check_id': 'nucleoli', 'function': 'nuclei.nucleolus_prominence', 'source_id': 'precise',
         'reference': 'H&E 주석 class(종양 vs 양성 샘)', 'split': '전체(조정 없음)',
         'cases': f"종양 {nu['tumour_windows']} · 양성 {nu['benign_windows']} 창", 'metric': 'AUC(종양 > 양성)', 'value': nu['auc'],
         'decision': '채택' if nu['auc'] >= 0.75 else '채택 안 함(핵소체 항목은 판독으로 둠)',
         'note_ko': f"뚜렷한 핵소체 핵 비율 중앙값 종양 {nu['tumour_median']}% · 양성 {nu['benign_median']}% · "
                    f"같은 슬라이드 짝 {nu['paired_slides']}개 중 종양이 높음 {nu['paired_tumour_higher']}"},
        {'check_id': 'register_tissue', 'function': 'register.align', 'source_id': 'precise',
         'reference': 'H&E·IHC 조직 범위(연속 절편)', 'split': '전체',
         'cases': f"{rg['slides']} 슬라이드", 'metric': '조직 조각 단위 정합 후 조직 Dice(중앙값)', 'value': rg['cores'],
         'decision': '조직 Dice 0.7 이상 슬라이드에서 같은 부위 비교 그림에만 사용(샘 단위 대응 아님)',
         'note_ko': f"정합 전 {rg['before']} · 슬라이드 전체 강체 {rg['global']} · 조각 단위 {rg['cores']} · 0.7 이상 {rg['good_slides']}/{rg['slides']}. "
                    '창 단위로 핵 지도를 다시 맞춰도 상관 0.09–0.15에 그쳐(sub-23) 샘 하나하나의 대응은 얻지 못함'},
    ]
    return rows


def main() -> int:
    names = sorted(registry.precise_participants())
    res = {}
    with Pool(min(len(names), os.cpu_count() or 1)) as pool:
        g = sum(pool.map(gland_case, names), [])
        res['glands'] = {'raw': summarise_glands(g, 'raw'), 'macenko': summarise_glands(g, 'macenko')}
        res['basal'] = summarise_basal(sum(pool.map(basal_case, names), []))
        res['nucleoli'] = summarise_nucleoli(sum(pool.map(nucleoli_case, names), []))
        res['register'] = summarise_register(pool.map(register_case, names))
    doc = {'generated_by': 'domains/pathology/code/evaluate_pathology_measures.py', 'iou': IOU, 'results': res,
           'checks': checks(res)}
    (registry.WEB_DATA / 'validation.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for c in doc['checks']:
        print(f"{c['check_id']:16s} {c['metric']}: {c['value']}  — {c['note_ko']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
