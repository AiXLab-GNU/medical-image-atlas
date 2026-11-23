#!/usr/bin/env python3
"""Generate the retinal vessel schematic macros for retinal-atlas-web.

Writes ``templates/_vessel_schematic.html`` with two Jinja macros:

- ``vessel_face(hl, kids)``: en-face view of a right eye (disc on the right) with central retinal
  artery/vein on the disc, temporal and nasal arteries (red) and veins (blue), a cilioretinal artery,
  artery–vein crossings (computed from the drawn paths), the radial peripapillary capillary zone, the
  parafoveal capillary ring and the foveal avascular zone.
- ``vessel_depth(hl, kids)``: a disc-to-fovea cross-section showing where the radial peripapillary,
  superficial, intermediate and deep capillary plexuses lie, the vessel-free foveal centre and the
  central vessels in the optic nerve head.

Geometry is illustrative, not to scale. Every element links to its atlas item page.
"""
from __future__ import annotations

import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/templates/_vessel_schematic.html'

SLUG = {
    'cra': 'central-retinal-artery', 'crv': 'central-retinal-vein', 'art': 'retinal-arterioles',
    'ven': 'retinal-venules', 'arc': 'vascular-arcades', 'cilio': 'cilioretinal-artery', 'avx': 'av-crossing',
    'rpc': 'radial-peripapillary-capillaries', 'scp': 'superficial-capillary-plexus',
    'icp': 'intermediate-capillary-plexus', 'dcp': 'deep-capillary-plexus', 'faz': 'foveal-avascular-zone',
}
IDS = {
    'cra': ['ana_central_retinal_artery'], 'crv': ['ana_central_retinal_vein'],
    'art': ['ana_retinal_arterioles', 'ana_retinal_vasculature', 'ana_vascular_tree'],
    'ven': ['ana_retinal_venules', 'ana_retinal_vasculature', 'ana_vascular_tree'],
    'arc': ['ana_vascular_arcades'], 'cilio': ['ana_cilioretinal_artery'], 'avx': ['ana_av_crossing'],
    'rpc': ['ana_radial_peripapillary_capillaries'], 'scp': ['ana_superficial_capillary_plexus'],
    'icp': ['ana_intermediate_capillary_plexus'], 'dcp': ['ana_deep_capillary_plexus'],
    'faz': ['ana_foveal_avascular_zone'],
}


def rc(key: str) -> str:
    return "{{ rc(%r) }}" % IDS[key]


def bezier(points, n=80):
    """Sample a chain of cubic Bézier segments given as [p0, c1, c2, p1, c1, c2, p2, ...]."""
    out = []
    for i in range(0, len(points) - 1, 3):
        p0, c1, c2, p1 = points[i:i + 4]
        for k in range(n + 1):
            t = k / n
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t ** 2 * c2[0] + t ** 3 * p1[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t ** 2 * c2[1] + t ** 3 * p1[1]
            out.append((x, y))
    return out


def d_attr(points):
    s = f'M{points[0][0]},{points[0][1]}'
    for i in range(1, len(points), 3):
        c1, c2, p = points[i:i + 3]
        s += f' C{c1[0]},{c1[1]} {c2[0]},{c2[1]} {p[0]},{p[1]}'
    return s


def intersections(a, b):
    hits = []
    for (x1, y1), (x2, y2) in zip(a, a[1:]):
        for (x3, y3), (x4, y4) in zip(b, b[1:]):
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-9:
                continue
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                hits.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
    return hits


# ---------------------------------------------------------------- en-face geometry (right eye)
DISC = (600, 262)
FOVEA = (330, 272)
ARTERIES = {  # temporal arcade arteries are the 'arc' + 'art' items; nasal/macular branches are 'art'
    'st': [(598, 244), (575, 176), (470, 150), (340, 160), (275, 165), (215, 186), (150, 222)],
    'it': [(598, 280), (575, 352), (470, 382), (340, 376), (275, 372), (215, 352), (150, 318)],
    'sn': [(606, 244), (645, 196), (700, 166), (760, 148)],
    'in': [(606, 280), (645, 330), (700, 362), (760, 382)],
    'sm': [(586, 252), (540, 228), (470, 222), (402, 238)],
    'im': [(586, 274), (540, 300), (470, 312), (402, 304)],
}
VEINS = {
    'st': [(594, 240), (560, 150), (450, 122), (340, 134), (270, 140), (215, 176), (160, 248)],
    'it': [(594, 284), (560, 378), (450, 408), (340, 400), (270, 394), (215, 362), (160, 292)],
    'sn': [(612, 242), (655, 184), (705, 142), (760, 118)],
    'in': [(612, 282), (655, 344), (705, 388), (760, 410)],
}
CILIO = [(563, 258), (540, 250), (498, 252), (452, 264)]


def face_macro() -> str:
    art = {k: bezier(v) for k, v in ARTERIES.items()}
    ven = {k: bezier(v) for k, v in VEINS.items()}
    crossings = []
    for a in art.values():
        for v in ven.values():
            for p in intersections(a, v):
                if math.dist(p, DISC) > 60 and all(math.dist(p, q) > 12 for q in crossings):
                    crossings.append(p)
    lines = []
    w = lines.append
    w('{% macro vessel_face(hl=\'\', kids=()) -%}')
    w("{%- macro rc(ids) -%}{% if hl in ids %} hl{% elif ids|select('in', kids)|list %} child{% endif %}{%- endmacro -%}")
    w('<figure class="schematic vessel-schematic">')
    w('<svg viewBox="0 0 800 520" role="img" aria-labelledby="vs-face-title">')
    w('  <title id="vs-face-title">망막 혈관 모식도(오른눈, 정면): 중심망막동·정맥, 동맥·정맥 가지, 섬모체망막동맥, 동정맥 교차, 유두주위 방사상 모세혈관, 중심와 무혈관 구역</title>')
    w('  <ellipse class="vs-bg" cx="430" cy="265" rx="390" ry="250"/>')
    w(f'  <circle class="vs-macula" cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="95"/>')
    # radial peripapillary capillaries
    rpc = []
    for k in range(48):
        ang = 2 * math.pi * k / 48
        r0, r1 = 46, 78 + 8 * (abs(math.sin(ang)))  # longer above and below the disc
        rpc.append(f'M{DISC[0] + r0 * math.cos(ang):.1f},{DISC[1] + r0 * math.sin(ang):.1f} '
                   f'L{DISC[0] + r1 * math.cos(ang):.1f},{DISC[1] + r1 * math.sin(ang):.1f}')
    w(f'  <a href="/anatomy/{SLUG["rpc"]}/" aria-label="유두주위 방사상 모세혈관"><g class="vs-grp vs-rpc{rc("rpc")}">'
      f'<path class="vs-halo" d="{" ".join(rpc)}"/><path class="vs-cap" d="{" ".join(rpc)}"/></g></a>')
    # parafoveal capillary ring (plexuses) and FAZ
    ring = []
    for k in range(72):
        ang = 2 * math.pi * k / 72
        r0 = 16 + 3 * math.sin(5 * ang)
        r1 = 70 + 6 * math.cos(3 * ang)
        ring.append(f'M{FOVEA[0] + r0 * math.cos(ang):.1f},{FOVEA[1] + r0 * math.sin(ang):.1f} '
                    f'Q{FOVEA[0] + (r0 + r1) / 2 * math.cos(ang + 0.05):.1f},{FOVEA[1] + (r0 + r1) / 2 * math.sin(ang + 0.05):.1f} '
                    f'{FOVEA[0] + r1 * math.cos(ang):.1f},{FOVEA[1] + r1 * math.sin(ang):.1f}')
    plex_ids = IDS['scp'] + IDS['icp'] + IDS['dcp']
    w(f'  <a href="/anatomy/{SLUG["scp"]}/" aria-label="황반 모세혈관망"><g class="vs-grp vs-plexus'
      "{{ rc(%r) }}" % plex_ids + f'"><path class="vs-halo" d="{" ".join(ring)}"/><path class="vs-cap" d="{" ".join(ring)}"/></g></a>')
    w(f'  <a href="/anatomy/{SLUG["faz"]}/" aria-label="중심와 무혈관 구역"><g class="vs-grp vs-faz{rc("faz")}">'
      f'<circle class="vs-faz-shape" cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="15"/></g></a>')
    # veins under arteries
    for key, pts in VEINS.items():
        temporal = key in ('st', 'it')
        cls_ids = IDS['ven'] + (IDS['arc'] if temporal else [])
        w(f'  <a href="/anatomy/{SLUG["arc" if temporal else "ven"]}/" aria-label="망막 소정맥"><g class="vs-grp vs-vein'
          "{{ rc(%r) }}" % cls_ids + f'"><path class="vs-halo" d="{d_attr(pts)}"/><path class="vs-v" d="{d_attr(pts)}"/></g></a>')
    for key, pts in ARTERIES.items():
        temporal = key in ('st', 'it')
        cls_ids = IDS['art'] + (IDS['arc'] if temporal else [])
        w(f'  <a href="/anatomy/{SLUG["arc" if temporal else "art"]}/" aria-label="망막 소동맥"><g class="vs-grp vs-art'
          "{{ rc(%r) }}" % cls_ids + f'"><path class="vs-halo" d="{d_attr(pts)}"/><path class="vs-a{" thin" if key in ("sm", "im") else ""}" d="{d_attr(pts)}"/></g></a>')
    w(f'  <a href="/anatomy/{SLUG["cilio"]}/" aria-label="섬모체망막동맥"><g class="vs-grp vs-cilio{rc("cilio")}">'
      f'<path class="vs-halo" d="{d_attr(CILIO)}"/><path class="vs-a thin" d="{d_attr(CILIO)}"/></g></a>')
    # disc, cup and central vessels
    w(f'  <ellipse class="vs-disc" cx="{DISC[0]}" cy="{DISC[1]}" rx="36" ry="42"/>')
    w(f'  <ellipse class="vs-cup" cx="{DISC[0] + 3}" cy="{DISC[1]}" rx="16" ry="20"/>')
    w(f'  <a href="/anatomy/{SLUG["crv"]}/" aria-label="중심망막정맥"><g class="vs-grp vs-vein{rc("crv")}">'
      f'<path class="vs-halo" d="M594,240 L596,262 L594,284"/><path class="vs-v" d="M594,240 L596,262 L594,284"/>'
      f'<circle class="vs-trunk-v" cx="596" cy="262" r="5"/></g></a>')
    w(f'  <a href="/anatomy/{SLUG["cra"]}/" aria-label="중심망막동맥"><g class="vs-grp vs-art{rc("cra")}">'
      f'<path class="vs-halo" d="M598,244 L603,262 L598,280"/><path class="vs-a" d="M598,244 L603,262 L598,280"/>'
      f'<circle class="vs-trunk-a" cx="603" cy="262" r="4"/></g></a>')
    # artery–vein crossings
    marks = ''.join(f'<circle class="vs-x" cx="{x:.1f}" cy="{y:.1f}" r="9"/>' for x, y in crossings)
    w(f'  <a href="/anatomy/{SLUG["avx"]}/" aria-label="동정맥 교차부"><g class="vs-grp vs-cross{rc("avx")}">{marks}</g></a>')
    # labels
    w(f'  <text class="vs-lbl" x="{DISC[0]}" y="{DISC[1] + 62}">시신경유두</text>')
    w(f'  <text class="vs-lbl" x="{FOVEA[0]}" y="{FOVEA[1] + 34}">중심와</text>')
    w('  <text class="vs-lbl small" x="520" y="244">섬모체망막동맥</text>')
    w('  <g class="vs-legend"><line class="vs-a" x1="300" y1="482" x2="330" y2="482"/><text x="336" y="486">동맥</text>'
      '<line class="vs-v" x1="382" y1="482" x2="412" y2="482"/><text x="418" y="486">정맥</text>'
      '<circle class="vs-x" cx="474" cy="482" r="7"/><text x="486" y="486">동정맥 교차</text></g>')
    w('</svg>')
    w('<figcaption>오른눈 정면 모식도. 중심망막동·정맥은 유두 중앙에서 위·아래로 갈라지고, 이측 큰 가지가 황반을 둘러싸는 혈관 아케이드를 이룹니다. 크기·위치는 설명용입니다.</figcaption>')
    w('</figure>')
    w('{%- endmacro %}')
    return '\n'.join(lines), len(crossings)


# ---------------------------------------------------------------- disc-to-fovea cross-section
X0, X1, XF, XB = 40, 640, 150, 640   # left edge, BMO (disc margin), fovea centre, disc margin
RPE_TOP = 230


def gauss(x, w):
    return math.exp(-((x - XF) / w) ** 2)


def layers(x):
    """Thickness of each retinal layer at x (px), outer to inner."""
    toward_disc = max(0.0, min(1.0, (x - XF) / (XB - XF)))
    return {
        'ps': 20, 'onl': 30 + 16 * gauss(x, 30), 'opl': 9 * (1 - gauss(x, 40)),
        'inl': 20 * (1 - gauss(x, 38)) * (1 - 0.3 * toward_disc), 'ipl': 15 * (1 - gauss(x, 42)),
        'gcl': 26 * (1 - gauss(x, 48)) * (1 - 0.55 * toward_disc),
        'rnfl': 3 + 62 * toward_disc ** 1.8,
    }


def depth_macro() -> str:
    xs = list(range(X0, X1 + 1, 4))
    order = ['ps', 'onl', 'opl', 'inl', 'ipl', 'gcl', 'rnfl']
    bounds = {k: [] for k in order}
    for x in xs:
        y = RPE_TOP
        for k in order:
            y -= layers(x)[k]
            bounds[k].append((x, y))
    fill = {'ps': '#3a3a3a', 'onl': '#2a2a2a', 'opl': '#9a9a9a', 'inl': '#4a4a4a', 'ipl': '#a8a8a8',
            'gcl': '#7c7c7c', 'rnfl': '#d6d6d6'}
    names = {'rnfl': 'RNFL', 'gcl': 'GCL', 'ipl': 'IPL', 'inl': 'INL', 'opl': 'OPL', 'onl': 'ONL', 'ps': '시세포'}
    lines = []
    w = lines.append
    w('{% macro vessel_depth(hl=\'\', kids=()) -%}')
    w("{%- macro rc(ids) -%}{% if hl in ids %} hl{% elif ids|select('in', kids)|list %} child{% endif %}{%- endmacro -%}")
    w('<figure class="schematic vessel-schematic">')
    w('<svg viewBox="0 0 800 330" role="img" aria-labelledby="vs-depth-title">')
    w('  <title id="vs-depth-title">망막 모세혈관망의 깊이: 중심와에서 시신경유두까지의 단면</title>')
    w(f'  <rect class="vs-vitreous" x="0" y="0" width="800" height="{RPE_TOP + 60}"/>')
    prev = [(x, RPE_TOP) for x in xs]
    for k in order:
        top = bounds[k]
        poly = ' '.join(f'{x},{y:.1f}' for x, y in prev) + ' ' + ' '.join(f'{x},{y:.1f}' for x, y in reversed(top))
        w(f'  <polygon points="{poly}" fill="{fill[k]}"/>')
        prev = top
    w(f'  <rect x="{X0}" y="{RPE_TOP}" width="{X1 - X0}" height="7" fill="#f2f2f2"/>')
    w(f'  <rect x="{X0}" y="{RPE_TOP + 7}" width="{X1 - X0}" height="40" fill="#6b6b6b"/>')
    # optic nerve head with central vessels
    w(f'  <path class="vs-onh" d="M{X1},{bounds["rnfl"][-1][1]:.1f} C{X1 + 30},{bounds["rnfl"][-1][1] + 40:.1f} {X1 + 20},{RPE_TOP + 47} {X1 + 40},{RPE_TOP + 80} L790,{RPE_TOP + 80} L790,90 C760,92 720,96 {X1},{bounds["rnfl"][-1][1]:.1f} Z"/>')
    w(f'  <a href="/anatomy/{SLUG["cra"]}/" aria-label="중심망막동맥"><g class="vs-grp vs-art{rc("cra")}">'
      f'<path class="vs-halo" d="M712,120 L712,{RPE_TOP + 80}"/><path class="vs-a" d="M712,120 L712,{RPE_TOP + 80}"/></g></a>')
    w(f'  <a href="/anatomy/{SLUG["crv"]}/" aria-label="중심망막정맥"><g class="vs-grp vs-vein{rc("crv")}">'
      f'<path class="vs-halo" d="M730,118 L730,{RPE_TOP + 80}"/><path class="vs-v" d="M730,118 L730,{RPE_TOP + 80}"/></g></a>')

    def dots(key, layer_lo, layer_hi, frac, min_thick, label, step=14, xmin=X0, r=3.2):
        pts = []
        for i, x in enumerate(xs):
            if x % step or x < xmin or x > X1 - 6 or (key != 'rpc' and 548 <= x <= 600):
                continue
            lo = bounds[layer_lo][i][1]
            hi = bounds[layer_hi][i][1]
            thick = lo - hi
            if thick < min_thick:
                continue
            pts.append(f'<circle cx="{x}" cy="{lo - frac * thick:.1f}" r="{r}"/>')
        w(f'  <a href="/anatomy/{SLUG[key]}/" aria-label="{label}"><g class="vs-grp vs-plx vs-{key}{rc(key)}">{"".join(pts)}</g></a>')

    dots('dcp', 'onl', 'opl', 0.9, 4, '심층 모세혈관망')          # INL/OPL border
    dots('icp', 'inl', 'ipl', 0.95, 4, '중간 모세혈관망')          # IPL/INL border
    dots('scp', 'ipl', 'gcl', 0.55, 6, '표층 모세혈관망')          # within GCL
    dots('rpc', 'gcl', 'rnfl', 0.6, 30, '유두주위 방사상 모세혈관', step=10, r=2.6)  # within thick RNFL
    # FAZ bracket
    y_ilm = min(y for x, y in bounds['rnfl'] if abs(x - XF) < 4)
    w(f'  <a href="/anatomy/{SLUG["faz"]}/" aria-label="중심와 무혈관 구역"><g class="vs-grp vs-faz{rc("faz")}">'
      f'<path class="vs-faz-bracket" d="M{XF - 34},{y_ilm - 30} L{XF - 34},{y_ilm - 22} L{XF + 34},{y_ilm - 22} L{XF + 34},{y_ilm - 30}"/>'
      f'<text class="vs-lbl" x="{XF}" y="{y_ilm - 36}">중심와 무혈관 구역</text></g></a>')
    # layer names at the left edge and plexus labels at the right of the retina
    i0 = 1
    prev_y = RPE_TOP
    for k in order:
        y = bounds[k][i0][1]
        if prev_y - y > 9:
            w(f'  <text class="vs-layer" x="{X0 - 4}" y="{(prev_y + y) / 2 + 3:.1f}">{names[k]}</text>')
        prev_y = y
    ix = xs.index(572)
    for key, lo, hi, frac, label in [('scp', 'ipl', 'gcl', 0.55, 'SCP'), ('icp', 'inl', 'ipl', 0.95, 'ICP'),
                                     ('dcp', 'onl', 'opl', 0.9, 'DCP')]:
        y = bounds[lo][ix][1] - frac * (bounds[lo][ix][1] - bounds[hi][ix][1])
        w(f'  <text class="vs-plx-lbl vs-{key}" x="574" y="{y + 4:.1f}">{label}</text>')
    w(f'  <text class="vs-plx-lbl vs-rpc" x="575" y="{bounds["rnfl"][-8][1] - 6:.1f}">RPC</text>')
    w(f'  <text class="vs-lbl" x="{XF}" y="{RPE_TOP + 72}">중심와</text>')
    w(f'  <text class="vs-lbl" x="725" y="{RPE_TOP + 98}">시신경유두(중심망막동·정맥)</text>')
    w(f'  <text class="vs-lbl small" x="{(X0 + X1) // 2}" y="{RPE_TOP + 30}">RPE · 맥락막</text>')
    w('</svg>')
    w('<figcaption>중심와에서 시신경유두까지의 단면 모식도. 점은 단면으로 잘린 모세혈관입니다. 유두 가까이 두꺼운 신경섬유층에는 방사상 모세혈관(RPC), 그 아래 신경절세포층에 표층(SCP), 내망상층–내핵층 경계에 중간(ICP), 내핵층–외망상층 경계에 심층(DCP) 모세혈관망이 있고, 중심와 가운데는 혈관이 없습니다.</figcaption>')
    w('</figure>')
    w('{%- endmacro %}')
    return '\n'.join(lines)


def main():
    face, n_cross = face_macro()
    text = ('{#- Generated by code/build_vessel_schematic.py — do not edit by hand. -#}\n'
            + face + '\n\n' + depth_macro() + '\n')
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote {OUT.relative_to(PROJECT)} ({n_cross} artery–vein crossings)')


if __name__ == '__main__':
    main()
