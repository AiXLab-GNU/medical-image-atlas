#!/usr/bin/env python3
"""Generate per-item schematic SVGs for lesions and the anatomy items without a drawn schematic.

Each item gets one or two small panels drawn on shared bases:

- ``face``  posterior pole of a right eye (disc on the right), as a fundus photograph shows it
- ``wide``  wide-field fundus (posterior pole, equator, ora serrata, vortex veins)
- ``disc``  close-up of the optic disc
- ``oct``   macular OCT B-scan through the fovea
- ``onh``   OCT cross-section through the optic nerve head

Lesions are drawn with simple glyphs and pointed to by a yellow call-out. Drawings are explanatory,
not to scale. Output: static SVG files (presentation attributes only, no inline style) and a JSON
manifest read by retinal-atlas-web.
"""
from __future__ import annotations

import json
import math
import random
from xml.sax.saxutils import escape
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
WEB = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web'
OUT_DIR = WEB / 'static/schematics'
MANIFEST = WEB / 'data/item_schematics.json'

W, H = 400, 300
HW = 400
OH = 230                      # OCT panel height
CALL = '#ffd34d'
FONT = 'font-family="Pretendard, Noto Sans KR, sans-serif"'


class Svg:
    def __init__(self, w=W, h=H, bg='#0f141a'):
        self.w, self.h = w, h
        self.defs, self.parts = [], []
        self.parts.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, t, size=11, fill='#fff', anchor='start', weight=600, halo='#0f141a'):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" stroke="{halo}" stroke-width="3" paint-order="stroke" {FONT}>{escape(str(t))}</text>')

    def callout(self, target, label, at=None):
        tx, ty = target
        if at is None:
            at = (tx + (70 if tx < self.w * 0.6 else -70), max(18, ty - 55))
        lx, ly = at
        self.add(f'<line x1="{lx:.1f}" y1="{ly + (4 if ly < ty else -12):.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                 f'stroke="{CALL}" stroke-width="1.6"/>')
        self.add(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3" fill="{CALL}"/>')
        self.text(lx, ly, label, 12, CALL, 'middle', 700)

    def svg(self):
        defs = f'<defs>{"".join(self.defs)}</defs>' if self.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}">{defs}{"".join(self.parts)}</svg>\n')


def rng(seed):
    return random.Random(seed)


# ------------------------------------------------------------------ bases
FOVEA, DISC = (165, 152), (292, 148)
CENTRE, RADIUS = (205, 150), 142


def bez(p0, c1, c2, p1, t):
    return tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d
                 for a, b, c, d in zip(p0, c1, c2, p1))


ARC_SUP_V = ((288, 128), (262, 70), (170, 58), (70, 92))
ARC_INF_V = ((288, 168), (262, 228), (170, 242), (70, 210))
ARC_SUP_A = ((292, 130), (268, 82), (180, 72), (80, 104))
ARC_INF_A = ((292, 166), (268, 216), (180, 228), (80, 198))
NAS = [((300, 132), (320, 105), (340, 88), (360, 72)), ((300, 164), (320, 192), (340, 210), (360, 226)),
       ((306, 140), (330, 132), (345, 128), (365, 122)), ((306, 158), (330, 168), (345, 172), (365, 178))]
NAS_V = [((298, 130), (316, 98), (332, 78), (352, 60)), ((298, 166), (316, 200), (332, 220), (352, 238))]


def path_d(c):
    return f'M{c[0][0]},{c[0][1]} C{c[1][0]},{c[1][1]} {c[2][0]},{c[2][1]} {c[3][0]},{c[3][1]}'


def face_base(s: Svg, *, vessels=True, disc_fill='#f6d79c', tint=None, artery_w=2.6, vein_w=3.6, macula=True):
    s.defs.append('<radialGradient id="fg" cx="48%" cy="50%" r="60%"><stop offset="0" stop-color="#d8743e"/>'
                  '<stop offset=".72" stop-color="#b4512a"/><stop offset="1" stop-color="#70301a"/></radialGradient>'
                  '<clipPath id="fc"><circle cx="205" cy="150" r="142"/></clipPath>')
    s.add(f'<circle cx="{CENTRE[0]}" cy="{CENTRE[1]}" r="{RADIUS}" fill="url(#fg)"/>')
    if tint:
        s.add(f'<circle cx="{CENTRE[0]}" cy="{CENTRE[1]}" r="{RADIUS}" fill="{tint[0]}" opacity="{tint[1]}"/>')
    if macula:
        s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="38" fill="#7a2c14" opacity=".35"/>'
              f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="12" fill="#6a2410" opacity=".55"/>'
              f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="2" fill="#ffe7c2" opacity=".8"/>')
    if vessels:
        g = '<g fill="none" stroke-linecap="round" clip-path="url(#fc)">'
        for c in (ARC_SUP_V, ARC_INF_V, *NAS_V):
            g += f'<path d="{path_d(c)}" stroke="#7d1a12" stroke-width="{vein_w}"/>'
        for c in (ARC_SUP_A, ARC_INF_A, *NAS):
            g += f'<path d="{path_d(c)}" stroke="#c2402a" stroke-width="{artery_w}"/>'
        g += ('<path d="M286,140 C255,132 220,128 195,136" stroke="#c2402a" stroke-width="1.3"/>'
              '<path d="M286,156 C255,166 220,170 195,164" stroke="#c2402a" stroke-width="1.3"/></g>')
        s.add(g)
    s.add(f'<ellipse cx="{DISC[0]}" cy="{DISC[1]}" rx="17" ry="21" fill="{disc_fill}"/>'
          f'<ellipse cx="{DISC[0] + 2}" cy="{DISC[1]}" rx="7" ry="9" fill="#fff6dc" opacity=".9"/>')


def wide_base(s: Svg, *, ora=True, vortex=True):
    s.defs.append('<radialGradient id="wg" cx="50%" cy="50%" r="55%"><stop offset="0" stop-color="#cf6b37"/>'
                  '<stop offset=".8" stop-color="#a9502c"/><stop offset="1" stop-color="#5b2716"/></radialGradient>')
    s.add('<circle cx="200" cy="150" r="140" fill="url(#wg)"/>')
    s.add('<circle cx="200" cy="150" r="88" fill="none" stroke="#f4d3b5" stroke-width="1" stroke-dasharray="4 4" opacity=".7"/>')
    if ora:
        pts = []
        for k in range(73):
            a = 2 * math.pi * k / 72
            r = 128 + 3 * math.sin(18 * a)
            pts.append(f'{200 + r * math.cos(a):.1f},{150 + r * math.sin(a):.1f}')
        s.add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#f9e0c4" stroke-width="1.2" opacity=".75"/>')
    g = '<g fill="none" stroke-linecap="round">'
    for k, ang in enumerate([-60, -25, 25, 60, 120, 155, 205, 240]):
        a = math.radians(ang)
        x0, y0 = 214 + 4 * math.cos(a), 150 + 4 * math.sin(a)
        x1, y1 = 200 + 120 * math.cos(a), 150 + 120 * math.sin(a)
        mx, my = 200 + 60 * math.cos(a + 0.25), 150 + 60 * math.sin(a + 0.25)
        g += f'<path d="M{x0:.1f},{y0:.1f} Q{mx:.1f},{my:.1f} {x1:.1f},{y1:.1f}" stroke="{"#7d1a12" if k % 2 else "#c2402a"}" stroke-width="{1.8 if k % 2 else 1.3}"/>'
    s.add(g + '</g>')
    s.add('<circle cx="186" cy="151" r="5" fill="#6a2410" opacity=".6"/>')
    s.add('<ellipse cx="214" cy="150" rx="5" ry="6" fill="#f6d79c"/>')
    if vortex:
        for ang in (45, 135, 225, 315):
            a = math.radians(ang)
            x, y = 200 + 92 * math.cos(a), 150 + 92 * math.sin(a)
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#4a1a10" opacity=".55"/>')


def disc_base(s: Svg, *, disc_fill='#f6d79c', cup=(30, 36), rim='#f2b773'):
    s.defs.append('<radialGradient id="dg" cx="50%" cy="50%" r="60%"><stop offset="0" stop-color="#c95e33"/>'
                  '<stop offset="1" stop-color="#8a3a1e"/></radialGradient>')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#dg)"/>')
    s.add(f'<ellipse cx="200" cy="150" rx="70" ry="80" fill="{rim}"/>')
    s.add(f'<ellipse cx="204" cy="150" rx="{cup[0]}" ry="{cup[1]}" fill="#fff4d9"/>')
    g = '<g fill="none" stroke-linecap="round">'
    for sx, ex, ey, col, wd in [(206, 120, -10, '#7d1a12', 7), (206, 300, -10, '#7d1a12', 6), (206, 120, 310, '#7d1a12', 7),
                                (206, 300, 310, '#7d1a12', 6), (200, 90, -10, '#c2402a', 5), (200, 330, 20, '#c2402a', 4),
                                (200, 90, 310, '#c2402a', 5), (200, 330, 280, '#c2402a', 4)]:
        my = 150 + (ey - 150) * 0.35
        g += f'<path d="M{sx},150 Q{sx + (ex - sx) * 0.15:.0f},{my:.0f} {ex},{ey}" stroke="{col}" stroke-width="{wd}"/>'
    s.add(g + '</g>')


# OCT layer model: boundaries from inner to outer, symmetric pit at x = 200
B_ORDER = ['ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL', 'ELM', 'EZ', 'IZ', 'RPE', 'BM', 'CSI']
LAYER_FILL = {'NFL': '#cfcfcf', 'GCL': '#858585', 'IPL': '#a8a8a8', 'INL': '#474747', 'OPL': '#9c9c9c',
              'ONL': '#262626', 'MZ': '#353535', 'OS': '#5a5a5a', 'IZ_RPE': '#7a7a7a', 'RPE': '#f2f2f2',
              'CHOROID': '#666666'}
RPE_Y = 160


def oct_bounds(x, fx=200, pit=1.0, ret_scale=1.0, choroid=48):
    g = math.exp(-((x - fx) / 34) ** 2) * pit
    th = {  # thickness of each layer (outer to inner) in px
        'IZ_RPE': 4, 'OS': 8, 'MZ': 7, 'ONL': (26 + 10 * g) * ret_scale, 'OPL': 7 * (1 - g) * ret_scale,
        'INL': 15 * (1 - g) * ret_scale, 'IPL': 11 * (1 - g) * ret_scale, 'GCL': 15 * (1 - 0.98 * g) * ret_scale,
        'NFL': (3 + 4 * abs(x - fx) / 200) * (1 - g) * ret_scale + 1}
    y = RPE_Y
    b = {'RPE': y, 'BM': y + 5, 'CSI': y + 5 + choroid}
    b['IZ'] = y - th['IZ_RPE']
    b['EZ'] = b['IZ'] - th['OS']
    b['ELM'] = b['EZ'] - th['MZ']
    b['OPL'] = b['ELM'] - th['ONL']
    b['INL'] = b['OPL'] - th['OPL']
    b['IPL'] = b['INL'] - th['INL']
    b['GCL'] = b['IPL'] - th['IPL']
    b['NFL'] = b['GCL'] - th['GCL']
    b['ILM'] = b['NFL'] - th['NFL']
    return b


class Cols(dict):
    """Column boundaries keyed by x; any x snaps to the nearest sampled column."""
    def __missing__(self, x):
        return dict.__getitem__(self, min(self.keys(), key=lambda k: abs(k - x)))


def oct_base(s: Svg, *, xs=range(0, HW + 1, 4), mods=None, choroid=48, haller=True, **kw):
    """Draw layered B-scan. ``mods(x, b)`` may edit the boundary dict per column."""
    s.add(f'<rect width="{HW}" height="{OH}" fill="#0b0d10"/>')
    cols = []
    for x in xs:
        b = oct_bounds(x, choroid=choroid, **kw)
        if mods:
            mods(x, b)
        cols.append((x, b))
    seq = [('NFL', 'ILM', 'GCL'), ('GCL', 'GCL', 'IPL'), ('IPL', 'IPL', 'INL'), ('INL', 'INL', 'OPL'),
           ('OPL', 'OPL', 'ELM_top'), ('ONL', 'ELM_top', 'ELM'), ('MZ', 'ELM', 'EZ'), ('OS', 'EZ', 'IZ'),
           ('IZ_RPE', 'IZ', 'RPE'), ('RPE', 'RPE', 'BM'), ('CHOROID', 'BM', 'CSI')]
    for name, top, bot in seq:
        def y(b, key):
            if key == 'ELM_top':
                return b['OPL'] + (b['ELM'] - b['OPL']) * 0.0 if False else b['OPL'] + max(0, (b['INL'] - b['OPL'])) * 0
            return b[key]
        if name == 'OPL':
            up = [(x, b['INL']) for x, b in cols]
            dn = [(x, b['OPL']) for x, b in cols]
        elif name == 'ONL':
            up = [(x, b['OPL']) for x, b in cols]
            dn = [(x, b['ELM']) for x, b in cols]
        elif name == 'INL':
            up = [(x, b['IPL']) for x, b in cols]
            dn = [(x, b['INL']) for x, b in cols]
        elif name == 'IPL':
            up = [(x, b['GCL']) for x, b in cols]
            dn = [(x, b['IPL']) for x, b in cols]
        elif name == 'GCL':
            up = [(x, b['NFL']) for x, b in cols]
            dn = [(x, b['GCL']) for x, b in cols]
        elif name == 'NFL':
            up = [(x, b['ILM']) for x, b in cols]
            dn = [(x, b['NFL']) for x, b in cols]
        else:
            up = [(x, b[top]) for x, b in cols]
            dn = [(x, b[bot]) for x, b in cols]
        pts = ' '.join(f'{x},{v:.1f}' for x, v in up) + ' ' + ' '.join(f'{x},{v:.1f}' for x, v in reversed(dn))
        s.add(f'<polygon points="{pts}" fill="{LAYER_FILL[name]}"/>')
    for key, col, wd in (('ELM', '#bdbdbd', 0.8), ('EZ', '#ececec', 1.6), ('IZ', '#b9b9b9', 1)):
        s.add(f'<polyline points="{" ".join(f"{x},{b[key]:.1f}" for x, b in cols)}" fill="none" stroke="{col}" stroke-width="{wd}"/>')
    if haller:
        r = rng(7)
        for k in range(9):
            x = 20 + k * 45 + r.uniform(-8, 8)
            b = dict(cols[min(len(cols) - 1, int(x / 4))][1])
            yc = (b['BM'] + b['CSI']) / 2 + 6
            s.add(f'<ellipse cx="{x:.0f}" cy="{yc:.0f}" rx="{14 + r.uniform(-3, 4):.0f}" ry="{8 + r.uniform(-2, 3):.0f}" fill="#3a3a3a"/>')
    s.add(f'<rect y="{OH - 14}" width="{HW}" height="14" fill="#8a8a8a" opacity=".9"/>')
    return Cols(cols)


def onh_base(s: Svg, *, cup_depth=40):
    """OCT through the optic nerve head: retina ending at Bruch's membrane opening, lamina cribrosa."""
    s.add(f'<rect width="{HW}" height="{OH}" fill="#0b0d10"/>')
    left = [(x, 150 - 26 - 18 * max(0, 1 - abs(x - 140) / 60)) for x in range(0, 141, 4)]
    right = [(x, 150 - 26 - 18 * max(0, 1 - abs(x - 260) / 60)) for x in range(260, 401, 4)]
    cup = f'M140,{left[-1][1]:.1f} C165,{left[-1][1] + cup_depth * 0.8:.1f} 235,{right[0][1] + cup_depth * 0.8:.1f} 260,{right[0][1]:.1f}'
    s.add(f'<path d="M0,{left[0][1]:.1f} L' + ' L'.join(f'{x},{y:.1f}' for x, y in left) +
          f' {cup[cup.index("C"):]} L' + ' L'.join(f'{x},{y:.1f}' for x, y in right) +
          ' L400,150 L260,150 L250,200 L150,200 L140,150 L0,150 Z" fill="#9a9a9a"/>')
    s.add('<path d="M0,150 L140,150 M260,150 L400,150" stroke="#f2f2f2" stroke-width="5"/>')
    s.add('<rect x="0" y="153" width="140" height="40" fill="#666"/><rect x="260" y="153" width="140" height="40" fill="#666"/>')
    s.add('<rect x="150" y="185" width="100" height="45" fill="#7d7d7d"/>')
    s.add(f'<rect y="{OH - 14}" width="{HW}" height="14" fill="#8a8a8a" opacity=".9"/>')


# ------------------------------------------------------------------ glyph helpers (face)
def spots(s, centre, n, spread, r, fill, seed=1, stroke=None, shape='circle', opacity=1.0):
    g = rng(seed)
    pts = []
    for _ in range(n):
        a, d = g.uniform(0, 2 * math.pi), spread * math.sqrt(g.random())
        x, y = centre[0] + d * math.cos(a), centre[1] + d * math.sin(a)
        rr = r * g.uniform(0.7, 1.3)
        st = f' stroke="{stroke}" stroke-width="1"' if stroke else ''
        if shape == 'blot':
            s.add(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rr:.1f}" ry="{rr * g.uniform(.7, 1):.1f}" fill="{fill}" opacity="{opacity}"{st}/>')
        else:
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" opacity="{opacity}"{st}/>')
        pts.append((x, y))
    return pts


def blob(s, c, rx, ry, fill, seed=3, jitter=0.25, opacity=1.0, stroke=None, sw=1.5, dash=None):
    g = rng(seed)
    pts = []
    for k in range(24):
        a = 2 * math.pi * k / 24
        f = 1 + g.uniform(-jitter, jitter)
        pts.append((c[0] + rx * f * math.cos(a), c[1] + ry * f * math.sin(a)))
    if jitter > 0.15 and max(rx, ry) > 40:
        jitter = 0.12
        pts = [(c[0] + rx * (1 + g.uniform(-jitter, jitter)) * math.cos(2 * math.pi * k / 24),
                c[1] + ry * (1 + g.uniform(-jitter, jitter)) * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pts, pts[1:] + pts[:1])]
    d = f'M{mids[-1][0]:.1f},{mids[-1][1]:.1f}' + ''.join(f' Q{p[0]:.1f},{p[1]:.1f} {m[0]:.1f},{m[1]:.1f}' for p, m in zip(pts, mids)) + ' Z'
    st = f' stroke="{stroke}" stroke-width="{sw}"' + (f' stroke-dasharray="{dash}"' if dash else '') if stroke else ''
    s.add(f'<path d="{d}" fill="{fill}" opacity="{opacity}"{st} stroke-linejoin="round"/>')


def flame(s, c, ang, length=16, width=5, fill='#7a0f0b'):
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    p0 = (c[0] - dx * length / 2, c[1] - dy * length / 2)
    p1 = (c[0] + dx * length / 2, c[1] + dy * length / 2)
    s.add(f'<path d="M{p0[0]:.1f},{p0[1]:.1f} Q{c[0] + px * width:.1f},{c[1] + py * width:.1f} {p1[0]:.1f},{p1[1]:.1f} '
          f'Q{c[0] - px * width * .6:.1f},{c[1] - py * width * .6:.1f} {p0[0]:.1f},{p0[1]:.1f} Z" fill="{fill}"/>')


def radial_angle(p):
    return math.degrees(math.atan2(p[1] - DISC[1], p[0] - DISC[0]))


# ------------------------------------------------------------------ face glyph library
def f_ma(s):
    pts = spots(s, (175, 140), 14, 42, 1.8, '#8a0c0c', seed=2)
    return pts[0], '미세동맥류'


def f_dot_blot(s):
    pts = spots(s, (170, 150), 9, 50, 4.5, '#6d0d0a', seed=4, shape='blot')
    return pts[1], '점·얼룩 출혈'


def f_flame(s):
    g = rng(5)
    last = None
    for k in range(7):
        a = g.uniform(-60, 60) + (180 if k % 2 else 0)
        r = g.uniform(34, 70)
        c = (DISC[0] + r * math.cos(math.radians(a)), DISC[1] + r * math.sin(math.radians(a)))
        flame(s, c, a, 18, 4.5)
        last = c
    return last, '화염상 출혈'


def f_preretinal(s):
    s.add('<path d="M120,180 Q165,228 210,180 Z" fill="#6a0b08"/><path d="M120,180 L210,180" stroke="#9a2a1c" stroke-width="1.5"/>')
    return (165, 195), '망막앞 출혈(수평 경계)'


def f_vitreous(s):
    s.add('<circle cx="205" cy="150" r="142" fill="#5a1010" opacity=".45"/>')
    for k, (x, y, rx, ry) in enumerate([(150, 120, 60, 25), (240, 190, 70, 30), (190, 160, 40, 50)]):
        blob(s, (x, y), rx, ry, '#4a0a08', seed=30 + k, opacity=.55)
    return (190, 160), '유리체 출혈(가림)'


def f_subretinal_hem(s):
    blob(s, (175, 160), 42, 30, '#5a0b0a', seed=6, opacity=.92)
    return (175, 160), '망막하 출혈'


def f_sub_rpe_hem(s):
    blob(s, (175, 160), 40, 28, '#2e2418', seed=7, opacity=.9, stroke='#4a3a26')
    return (175, 160), 'RPE 아래 출혈(검푸른색)'


def vein_curve(s, c, mod):
    pts = [bez(*c, t / 40) for t in range(41)]
    out = []
    for i, (x, y) in enumerate(pts):
        out.append(mod(i, x, y))
    return out


def f_beading(s):
    pts = [bez(*ARC_SUP_V, t / 40) for t in range(41)]
    for i, (x, y) in enumerate(pts[6:30]):
        if i % 4 == 0:
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#7d1a12"/>')
    return pts[18], '정맥 구슬모양'


def f_dilation(s):
    pts = [bez(*ARC_INF_V, t / 40) for t in range(41)]
    d = 'M' + ' L'.join(f'{x:.1f},{y + 5 * math.sin(i / 1.6):.1f}' for i, (x, y) in enumerate(pts))
    s.add(f'<path d="{d}" stroke="#6a120c" stroke-width="7" fill="none" stroke-linecap="round"/>')
    return pts[20], '정맥 확장·구불거림'


def f_loop(s):
    x, y = bez(*ARC_SUP_V, 0.45)
    s.add(f'<path d="M{x - 12},{y} C{x - 10},{y - 22} {x + 14},{y - 22} {x + 10},{y} C{x + 6},{y + 12} {x - 4},{y + 10} {x - 12},{y}" stroke="#7d1a12" stroke-width="3" fill="none"/>')
    return (x, y - 12), '정맥 고리'


def f_irma(s):
    g = rng(9)
    for k in range(4):
        x0, y0 = 200 + g.uniform(-30, 30), 115 + g.uniform(-15, 15)
        d = f'M{x0:.0f},{y0:.0f}' + ''.join(f' q{g.uniform(-6, 6):.0f},{g.uniform(-6, 6):.0f} {g.uniform(-8, 8):.0f},{g.uniform(-8, 8):.0f}' for _ in range(6))
        s.add(f'<path d="{d}" stroke="#a3271b" stroke-width="1.3" fill="none"/>')
    spots(s, (200, 115), 3, 25, 3.5, '#6d0d0a', seed=10, shape='blot')
    return (200, 115), '망막내 미세혈관 이상'


def nv_net(s, c, r, seed):
    g = rng(seed)
    for k in range(14):
        a = g.uniform(0, 2 * math.pi)
        rr = r * g.uniform(.4, 1)
        s.add(f'<path d="M{c[0]:.1f},{c[1]:.1f} q{rr * .6 * math.cos(a + .6):.1f},{rr * .6 * math.sin(a + .6):.1f} '
              f'{rr * math.cos(a):.1f},{rr * math.sin(a):.1f}" stroke="#d1442e" stroke-width="1" fill="none"/>')
    s.add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{r:.1f}" fill="#d1442e" opacity=".18"/>')


def f_nvd(s):
    nv_net(s, DISC, 22, 11)
    return DISC, '유두 신생혈관'


def f_nve(s):
    c = bez(*ARC_SUP_V, 0.55)
    nv_net(s, c, 18, 12)
    return c, '망막 신생혈관'


def f_nonperfusion(s):
    blob(s, (110, 110), 38, 30, '#b9a38c', seed=13, opacity=.55, stroke='#e8d8c8', dash='3 3')
    return (110, 110), '무관류 영역(FA)'


def f_faz(s):
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="30" fill="none" stroke="#e9d2bf" stroke-width="1.5" stroke-dasharray="3 2"/>')
    blob(s, FOVEA, 18, 15, '#2a0f08', seed=14, opacity=.7, stroke='#ffd34d', sw=1.4)
    return (FOVEA[0] + 12, FOVEA[1] - 10), 'FAZ 확대·불규칙'


def f_narrowing(s):
    for c in (ARC_SUP_A, ARC_INF_A):
        s.add(f'<path d="{path_d(c)}" stroke="#e7a06a" stroke-width="1.1" fill="none"/>')
    return bez(*ARC_SUP_A, .5), '소동맥 협착(가늘어짐)'


def f_av_nick(s):
    x, y = bez(*ARC_SUP_V, .5)
    s.add(f'<path d="M{x - 24},{y + 14} L{x + 24},{y - 14}" stroke="#c2402a" stroke-width="3"/>')
    s.add(f'<rect x="{x - 7}" y="{y - 7}" width="14" height="14" fill="#c0612e"/>')
    return (x, y), '교차부 정맥 눌림'


def f_sheathing(s):
    pts = [bez(*ARC_INF_V, t / 30) for t in range(8, 22)]
    s.add(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" stroke="#f3efe6" stroke-width="7" fill="none" opacity=".85"/>')
    s.add(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" stroke="#7d1a12" stroke-width="2.5" fill="none"/>')
    return pts[6], '혈관 백선화'


def f_embolus(s):
    x, y = bez(*ARC_SUP_A, .18)
    s.add(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="4" ry="3" fill="#fff2a6" stroke="#e6c34a"/>')
    return (x, y), '색전(밝은 판)'


def f_whitening(s):
    blob(s, FOVEA, 95, 80, '#efe6da', seed=15, opacity=.7)
    return (FOVEA[0] - 50, FOVEA[1] - 30), '허혈성 백색 부종'


def f_cherry(s):
    blob(s, FOVEA, 95, 80, '#efe6da', seed=15, opacity=.75)
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="9" fill="#c0281c"/>')
    return FOVEA, '체리 적색 반점'


def f_pamm_face(s):
    for k in range(6):
        a = 2 * math.pi * k / 6
        blob(s, (FOVEA[0] + 26 * math.cos(a), FOVEA[1] + 26 * math.sin(a)), 9, 6, '#e8d9c7', seed=16 + k, opacity=.55)
    return (FOVEA[0] + 26, FOVEA[1]), '중심주위 회백색 병변'


def f_mnv_face(s):
    blob(s, (FOVEA[0], FOVEA[1] + 4), 22, 18, '#5d6b4c', seed=17, opacity=.85)
    blob(s, (FOVEA[0] + 18, FOVEA[1] + 20), 10, 6, '#6d0d0a', seed=18)
    return (FOVEA[0], FOVEA[1] + 4), '회녹색 신생혈관 병변'


def f_polyp_face(s):
    for k, (dx, dy) in enumerate([(-8, -4), (6, 2), (0, 12)]):
        s.add(f'<circle cx="{FOVEA[0] + 30 + dx}" cy="{FOVEA[1] + dy}" r="5" fill="#e3621e" stroke="#ffb27a"/>')
    return (FOVEA[0] + 30, FOVEA[1]), '주황색 결절'


def f_exudates(s):
    pts = spots(s, (178, 150), 22, 45, 2.4, '#f3d34a', seed=19)
    return pts[2], '경성삼출물'


def f_circinate(s):
    c = (195, 120)
    for k in range(26):
        a = 2 * math.pi * k / 26
        s.add(f'<circle cx="{c[0] + 26 * math.cos(a):.1f}" cy="{c[1] + 22 * math.sin(a):.1f}" r="2.4" fill="#f3d34a"/>')
    s.add(f'<circle cx="{c[0]}" cy="{c[1]}" r="3" fill="#8a0c0c"/>')
    return (c[0] + 26, c[1]), '환상 삼출물'


def f_star(s):
    for k in range(14):
        a = 2 * math.pi * k / 14
        s.add(f'<path d="M{FOVEA[0] + 8 * math.cos(a):.1f},{FOVEA[1] + 8 * math.sin(a):.1f} L{FOVEA[0] + 34 * math.cos(a):.1f},{FOVEA[1] + 34 * math.sin(a):.1f}" stroke="#f3d34a" stroke-width="2.4" stroke-dasharray="3 2"/>')
    return (FOVEA[0] + 30, FOVEA[1] - 10), '별모양 삼출물'


def f_cws(s):
    pts = []
    for k, (x, y) in enumerate([(250, 110), (230, 185), (205, 95), (262, 175)]):
        blob(s, (x, y), 9, 6, '#f6f2ea', seed=20 + k, opacity=.92)
        pts.append((x, y))
    return pts[0], '면화반'


def f_drusen(size):
    def draw(s):
        n, r, spread = {'small': (26, 1.6, 40), 'medium': (16, 3.2, 38), 'large': (10, 6.2, 34),
                        'any': (18, 3.5, 40)}[size]
        pts = spots(s, FOVEA, n, spread, r, '#f2d57a', seed=21, stroke='#e0b848')
        label = {'small': '소형 드루젠(≤63 µm)', 'medium': '중형 드루젠(63–125 µm)', 'large': '대형 드루젠(>125 µm)',
                 'any': '드루젠'}[size]
        return pts[0], label
    return draw


def f_cuticular(s):
    pts = spots(s, FOVEA, 60, 70, 1.2, '#f7e6a6', seed=22)
    return pts[3], '작은 드루젠이 무수히(별이 뜬 밤)'


def f_sdd_face(s):
    g = rng(23)
    for k in range(40):
        x, y = 120 + g.uniform(-40, 60), 95 + g.uniform(-25, 25)
        s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="none" stroke="#f7e6c0" stroke-width="1.1"/>')
    return (130, 95), '망막하 드루젠양 침착물(그물 모양)'


def f_lipid(s):
    blob(s, (175, 168), 30, 18, '#f0c94a', seed=24, opacity=.9)
    return (175, 168), '망막하 지질'


def f_elevation(s, c, rx, ry, label, col='#c87a52', stroke='#ffd9b8', seed=25):
    blob(s, c, rx, ry, col, seed=seed, jitter=.06, opacity=.55, stroke=stroke, sw=1.4)
    s.add(f'<ellipse cx="{c[0] - rx * .3:.1f}" cy="{c[1] - ry * .35:.1f}" rx="{rx * .35:.1f}" ry="{ry * .2:.1f}" fill="#fff" opacity=".25"/>')
    return c, label


def f_serous_rd(s):
    return f_elevation(s, FOVEA, 38, 30, '장액성 박리(둥근 융기)')


def f_csme(s):
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="20" fill="none" stroke="#9fd8ff" stroke-width="1.2" stroke-dasharray="3 3"/>')
    blob(s, (FOVEA[0] + 10, FOVEA[1] - 4), 22, 16, '#d38a62', seed=26, opacity=.5)
    spots(s, (FOVEA[0] + 14, FOVEA[1]), 8, 14, 2, '#f3d34a', seed=27)
    return (FOVEA[0] + 10, FOVEA[1] - 4), '중심 500 µm 안의 부종·삼출물'


def f_thick_face(s):
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="36" fill="#d38a62" opacity=".35" stroke="#ffd9b8" stroke-dasharray="4 3"/>')
    return (FOVEA[0] + 30, FOVEA[1] - 18), '황반 두꺼워짐'


def f_pigment(s, n=10, c=FOVEA, spread=30, label='과색소 덩어리', col='#24140c', r=2.8, seed=28):
    pts = spots(s, c, n, spread, r, col, seed=seed, shape='blot')
    return pts[0], label


def f_hypo(s):
    blob(s, FOVEA, 30, 24, '#e7b38b', seed=29, opacity=.55)
    return FOVEA, '탈색 반점'


def f_atrophy(s, c=(170, 150), rx=34, ry=26, label='지도모양위축', seed=31, vessels_vis=True):
    blob(s, c, rx, ry, '#f1cfa9', seed=seed, jitter=.2)
    if vessels_vis:
        g = rng(seed)
        for k in range(5):
            y = c[1] - ry * .6 + k * ry * .3
            s.add(f'<path d="M{c[0] - rx * .7:.1f},{y:.1f} q{rx * .7:.1f},{g.uniform(-6, 6):.1f} {rx * 1.4:.1f},0" stroke="#c46a45" stroke-width="2.2" fill="none" opacity=".75"/>')
    return c, label


def f_erm(s):
    for k in range(8):
        a = 2 * math.pi * k / 8
        s.add(f'<path d="M{FOVEA[0] + 10 * math.cos(a):.1f},{FOVEA[1] + 10 * math.sin(a):.1f} L{FOVEA[0] + 42 * math.cos(a):.1f},{FOVEA[1] + 42 * math.sin(a):.1f}" stroke="#fdf4e2" stroke-width="1" opacity=".75"/>')
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="44" fill="#fff6e8" opacity=".22"/>')
    return (FOVEA[0] + 30, FOVEA[1] - 25), '망막전막(셀로판 광택·주름)'


def f_mh_face(s, label='황반원공', cuff=True):
    if cuff:
        s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="16" fill="#c9895e" opacity=".55"/>')
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="9" fill="#a3170f" stroke="#e6b08a"/>')
    return FOVEA, label


def f_fvp(s):
    pts = [bez(*ARC_SUP_V, t / 30) for t in range(4, 24)]
    s.add(f'<polyline points="{" ".join(f"{x:.1f},{y + 4:.1f}" for x, y in pts)}" stroke="#f5efe4" stroke-width="12" fill="none" opacity=".75" stroke-linecap="round"/>')
    nv_net(s, pts[10], 12, 33)
    return pts[10], '섬유혈관 증식막'


def f_trd(s):
    f_fvp(s)
    f_elevation(s, (150, 112), 40, 22, '', seed=34)
    return (150, 112), '견인 박리'


def f_pvr(s):
    c = (130, 200)
    for k in range(6):
        a = 2 * math.pi * k / 6
        s.add(f'<path d="M{c[0]},{c[1]} L{c[0] + 26 * math.cos(a):.1f},{c[1] + 26 * math.sin(a):.1f}" stroke="#f5efe4" stroke-width="1.6"/>')
    s.add(f'<circle cx="{c[0]}" cy="{c[1]}" r="5" fill="#f5efe4"/>')
    return c, '별모양 주름(PVR)'


def f_scar(s, kind):
    if kind == 'laser':
        g = rng(35)
        for k in range(60):
            a, d = g.uniform(0, 2 * math.pi), g.uniform(60, 130)
            x, y = 205 + d * math.cos(a), 150 + d * math.sin(a)
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#2a170d" stroke="#f0d2a8" stroke-width="1"/>')
        return (205 + 90, 150 + 60), '레이저 반흔(범망막 광응고)'
    if kind == 'fibrotic':
        blob(s, FOVEA, 30, 24, '#f4efe6', seed=36, jitter=.25)
        f_pigment(s, 6, FOVEA, 24, '', seed=37)
        return FOVEA, '섬유성 반흔'
    blob(s, (110, 175), 24, 18, '#f1e2c8', seed=38, jitter=.3)
    s.add('<ellipse cx="110" cy="175" rx="26" ry="20" fill="none" stroke="#2a170d" stroke-width="3" stroke-dasharray="5 3"/>')
    return (110, 175), '맥락망막 흉터'


def f_tessellated(s):
    g = rng(39)
    for k in range(18):
        x = 70 + k * 15
        s.add(f'<path d="M{x},{40 + g.uniform(-10, 10):.0f} q{g.uniform(-25, 25):.0f},110 {g.uniform(-15, 15):.0f},220" stroke="#e98a55" stroke-width="5" fill="none" opacity=".55"/>')
    return (120, 110), '맥락막 혈관이 비침(호피 모양)'


def f_myopic_diffuse(s):
    blob(s, (215, 150), 95, 70, '#e8b27c', seed=40, jitter=.12, opacity=.6)
    return (215, 120), '미만성 위축(노란 빛)'


def f_myopic_patchy(s):
    for k, c in enumerate([(130, 110), (150, 190), (110, 160)]):
        f_atrophy(s, c, 16, 12, '', seed=41 + k, vessels_vis=False)
    return (130, 110), '반점형 위축'


def f_myopic_macular(s):
    return f_atrophy(s, FOVEA, 30, 24, '황반 위축', seed=44)


def f_lacquer(s):
    for d in ['M130,130 q20,-6 50,4 q20,8 40,0', 'M140,170 q25,10 55,-2', 'M150,145 q10,-12 30,-10']:
        s.add(f'<path d="{d}" stroke="#f6e0a6" stroke-width="2.2" fill="none"/>')
    return (180, 134), '래커 균열(노란 선)'


def f_fuchs(s):
    blob(s, FOVEA, 10, 9, '#1c120a', seed=45)
    return FOVEA, '푹스 반점'


def f_staph_face(s):
    s.add('<ellipse cx="205" cy="150" rx="110" ry="85" fill="none" stroke="#ffe2bf" stroke-width="2" stroke-dasharray="6 4"/>')
    return (115, 150), '후포도종 경계'


def f_pachy_face(s):
    for k, y in enumerate((120, 150, 180)):
        s.add(f'<path d="M80,{y} q60,{-10 + 10 * k} 140,0" stroke="#d76a3f" stroke-width="9" fill="none" opacity=".55"/>')
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="26" fill="none" stroke="#f1d7b6" stroke-width="1.5" stroke-dasharray="3 2"/>')
    return (140, 150), '두꺼운 맥락막·대혈관(배경)'


def f_gravitational(s):
    s.add('<path d="M168,152 C175,180 190,215 205,262 L216,262 C200,215 186,180 178,152 Z" fill="#e9b88e" opacity=".75"/>')
    return (195, 220), 'RPE 중력 궤적(아래로 흐른 띠)'


def f_nevus(s):
    blob(s, (110, 190), 26, 20, '#4a4a4f', seed=46, jitter=.1, opacity=.92)
    spots(s, (110, 190), 5, 14, 1.6, '#f2d57a', seed=47)
    return (110, 190), '맥락막 모반(회색 평평한 반)'


def f_vasculitis(s):
    for c in (ARC_SUP_V, ARC_INF_V):
        pts = [bez(*c, t / 30) for t in range(6, 26)]
        s.add(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" stroke="#f3efe6" stroke-width="8" fill="none" opacity=".55"/>')
    spots(s, (120, 110), 4, 20, 4, '#6d0d0a', seed=48, shape='blot')
    return bez(*ARC_SUP_V, .55), '혈관 주위 백선(혈관염)'


def f_telangiectasia(s):
    g = rng(49)
    for k in range(10):
        a = g.uniform(math.pi * .6, math.pi * 1.4)
        r0 = g.uniform(8, 14)
        s.add(f'<path d="M{FOVEA[0] + r0 * math.cos(a):.1f},{FOVEA[1] + r0 * math.sin(a):.1f} q{g.uniform(-6, 6):.1f},{g.uniform(-6, 6):.1f} {14 * math.cos(a):.1f},{14 * math.sin(a):.1f}" stroke="#d1442e" stroke-width="1.6" fill="none"/>')
    s.add(f'<circle cx="{FOVEA[0] - 12}" cy="{FOVEA[1]}" r="18" fill="#d9c3b0" opacity=".3"/>')
    return (FOVEA[0] - 16, FOVEA[1]), '측두 중심와 주위 모세혈관확장'


def f_ram(s):
    x, y = bez(*ARC_INF_A, .4)
    s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#d2231a" stroke="#ff8a72"/>')
    for k in range(18):
        a = 2 * math.pi * k / 18
        s.add(f'<circle cx="{x + 18 * math.cos(a):.1f}" cy="{y + 15 * math.sin(a):.1f}" r="2" fill="#f3d34a"/>')
    blob(s, (x + 10, y - 16), 10, 7, '#6d0d0a', seed=50)
    return (x, y), '동맥 대동맥류(둥근 확장)'


def f_flecks(s):
    g = rng(51)
    for k in range(26):
        x, y = FOVEA[0] + g.uniform(-75, 85), FOVEA[1] + g.uniform(-60, 60)
        a = g.uniform(0, 180)
        s.add(f'<path d="M{x:.1f},{y:.1f} l{5 * math.cos(math.radians(a)):.1f},{5 * math.sin(math.radians(a)):.1f} l{3 * math.cos(math.radians(a + 140)):.1f},{3 * math.sin(math.radians(a + 140)):.1f} z" fill="#f6e3a0" stroke="#f6e3a0" stroke-width="1.6" stroke-linejoin="round"/>')
    return (FOVEA[0] + 40, FOVEA[1] - 30), '물고기꼬리 모양 반점(fleck)'


def f_vitelliform_face(s):
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="20" fill="#f2b52a" stroke="#ffe08a" stroke-width="1.5"/>'
          f'<ellipse cx="{FOVEA[0] - 6}" cy="{FOVEA[1] - 7}" rx="7" ry="4" fill="#fff" opacity=".35"/>')
    return FOVEA, '난황모양 병변'


def f_bulls_eye(s):
    s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="30" fill="#efc59c" opacity=".7"/>'
          f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="30" fill="none" stroke="#3a2214" stroke-width="2" opacity=".6"/>'
          f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="12" fill="#8a3418"/>')
    return (FOVEA[0] + 22, FOVEA[1] - 12), '중심와 주위 고리(중심 보존)'


def f_white_dots(s):
    pts = spots(s, (200, 150), 30, 105, 2.6, '#f5f1e6', seed=52, opacity=.9)
    return pts[4], '다발성 흰 점'


def f_angioid(s):
    g = rng(53)
    for k in range(9):
        a = 2 * math.pi * k / 9 + .2
        x0, y0 = DISC[0] + 26 * math.cos(a), DISC[1] + 30 * math.sin(a)
        x1, y1 = DISC[0] + 90 * math.cos(a + g.uniform(-.2, .2)), DISC[1] + 90 * math.sin(a + g.uniform(-.2, .2))
        s.add(f'<path d="M{x0:.1f},{y0:.1f} Q{(x0 + x1) / 2 + g.uniform(-8, 8):.1f},{(y0 + y1) / 2 + g.uniform(-8, 8):.1f} {x1:.1f},{y1:.1f}" stroke="#4a1c12" stroke-width="3.2" fill="none" stroke-linecap="round"/>')
    s.add(f'<ellipse cx="{DISC[0]}" cy="{DISC[1]}" rx="26" ry="30" fill="none" stroke="#4a1c12" stroke-width="2.5"/>')
    return (DISC[0] - 70, DISC[1] - 40), '유두에서 뻗는 어두운 띠'


def f_hemangioma(s):
    return f_elevation(s, (FOVEA[0] + 40, FOVEA[1] - 30), 30, 26, '주황색 융기 종괴', col='#ef7a2c', stroke='#ffc38a', seed=54)


def f_chrpe(s):
    blob(s, (100, 200), 26, 22, '#140c08', seed=55, jitter=.08)
    for c in [(95, 196), (106, 206)]:
        s.add(f'<circle cx="{c[0]}" cy="{c[1]}" r="4" fill="#d7a679"/>')
    s.add('<ellipse cx="100" cy="200" rx="30" ry="26" fill="none" stroke="#e7c39a" stroke-width="2"/>')
    return (100, 200), 'CHRPE(경계 분명한 흑색 반)'


def f_bone_spicule(s):
    g = rng(56)
    for k in range(26):
        a = g.uniform(0, 2 * math.pi)
        r = g.uniform(95, 125)
        x, y = 205 + r * math.cos(a), 150 + r * math.sin(a)
        d = f'M{x:.1f},{y:.1f}' + ''.join(f' l{g.uniform(-6, 6):.1f},{g.uniform(-6, 6):.1f}' for _ in range(4))
        s.add(f'<path d="{d}" stroke="#140c08" stroke-width="1.8" fill="none"/>')
    return (205 + 110 * math.cos(-0.6), 150 + 110 * math.sin(-0.6)), '골소체 모양 색소(주변부)'


def f_ped_face(s, label='색소상피박리(돔 모양 융기)'):
    return f_elevation(s, (FOVEA[0] + 6, FOVEA[1]), 26, 22, label, col='#d4744a', stroke='#ffcf9e', seed=57)


def f_subrpe_ring_face(s):
    s.add(f'<circle cx="{FOVEA[0] + 34}" cy="{FOVEA[1] + 4}" r="10" fill="none" stroke="#e3621e" stroke-width="3"/>')
    return (FOVEA[0] + 34, FOVEA[1] + 4), 'RPE 아래 고리'


# ------------------------------------------------------------------ OCT glyphs (operate via modifiers + overlays)
def oct_mark(s, target, label, at=None):
    s.callout(target, label, at)


def pit_x(cols, x):
    return cols[min(cols, key=lambda k: abs(k - x))]


def o_cysts(s, cols, label='망막내액(낭포)', big=False):
    g = rng(60)
    for k in range(9 if not big else 6):
        x = 200 + g.uniform(-70, 70)
        b = pit_x(cols, x)
        y = (b['INL'] + b['OPL']) / 2 if k % 2 else (b['OPL'] + b['ELM']) / 2 - 4
        rx = g.uniform(5, 9) * (1.6 if big else 1)
        s.add(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{rx * .8:.1f}" fill="#050607"/>')
    b = pit_x(cols, 230)
    return (230, (b['INL'] + b['OPL']) / 2), label


def mods_thick(extra):
    def m(x, b):
        g = math.exp(-((x - 200) / 60) ** 2)
        for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL'):
            b[k] -= extra * g
    return m


def mods_srf(h, w=60, cx=200):
    def m(x, b):
        g = max(0.0, 1 - ((x - cx) / w) ** 2)
        lift = h * g ** 0.7
        for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL', 'ELM', 'EZ', 'IZ'):
            b[k] -= lift
        b['_srf'] = lift
    return m


def o_srf_fill(s, cols, fill='#050607'):
    pts_top = [(x, b['IZ'] + 0.5) for x, b in sorted(cols.items()) if b.get('_srf', 0) > 0.5]
    if not pts_top:
        return
    pts_bot = [(x, b['RPE']) for x, b in sorted(cols.items()) if b.get('_srf', 0) > 0.5]
    s.add(f'<polygon points="{" ".join(f"{x},{y:.1f}" for x, y in pts_top)} {" ".join(f"{x},{y:.1f}" for x, y in reversed(pts_bot))}" fill="{fill}"/>')


def mods_ped(h, w=45, cx=200, peaked=False):
    def m(x, b):
        t = 1 - ((x - cx) / w) ** 2
        if t <= 0:
            return
        lift = h * (t ** (2.2 if peaked else 0.6))
        for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL', 'ELM', 'EZ', 'IZ', 'RPE'):
            b[k] -= lift
        b['_ped'] = lift
    return m


def o_ped_fill(s, cols, fill):
    pts = sorted((x, b) for x, b in cols.items() if b.get('_ped', 0) > 0.5)
    if not pts:
        return
    top = ' '.join(f'{x},{b["RPE"] + 4:.1f}' for x, b in pts)
    bot = ' '.join(f'{x},{b["BM"]:.1f}' for x, b in reversed(pts))
    s.add(f'<polygon points="{top} {bot}" fill="{fill}"/>')
    s.add(f'<polyline points="{" ".join(f"{x},{b["RPE"] + 2:.1f}" for x, b in pts)}" fill="none" stroke="#f2f2f2" stroke-width="4"/>')


def mods_drusen(sizes):
    def m(x, b):
        lift = 0
        for cx, w, h in sizes:
            t = 1 - ((x - cx) / w) ** 2
            if t > 0:
                lift = max(lift, h * t ** 0.8)
        for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL', 'ELM', 'EZ', 'IZ', 'RPE'):
            b[k] -= lift
        b['_ped'] = lift
    return m


def mods_vmt(kind):
    def m(x, b):
        if kind == 'vmt':
            g = max(0, 1 - ((x - 200) / 28) ** 2)
            for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL'):
                b[k] -= 22 * g ** 1.5
    return m


def o_hyaloid(s, cols, attach=(176, 224), lift=40, label='후유리체막'):
    left = [(x, cols[x]['ILM'] - lift * min(1, (attach[0] - x) / 60)) for x in sorted(cols) if x <= attach[0]]
    mid = [(x, cols[x]['ILM'] - 1) for x in sorted(cols) if attach[0] < x < attach[1]]
    right = [(x, cols[x]['ILM'] - lift * min(1, (x - attach[1]) / 60)) for x in sorted(cols) if x >= attach[1]]
    pts = left + mid + right
    s.add(f'<polyline points="{" ".join(f"{x},{y:.1f}" for x, y in pts)}" fill="none" stroke="#e6e6e6" stroke-width="1.6"/>')
    return (attach[0] - 40, cols[min(cols, key=lambda k: abs(k - (attach[0] - 40)))]['ILM'] - 24), label


def o_hole(s, cols, full=True):
    b = cols[200]
    bottom = b['RPE'] if full else (b['INL'] + b['OPL']) / 2
    top = min(cols[176]['ILM'], cols[224]['ILM'])
    w_top, w_bot = (12, 26) if full else (16, 10)
    s.add(f'<polygon points="{200 - w_top},{top - 2} {200 + w_top},{top - 2} {200 + w_bot},{bottom} {200 - w_bot},{bottom}" fill="#0b0d10"/>')
    if full:
        for dx in (-34, -24, 24, 34):
            s.add(f'<ellipse cx="{200 + dx}" cy="{(cols[200 + dx]["INL"] + cols[200 + dx]["OPL"]) / 2:.1f}" rx="5" ry="4" fill="#050607"/>')
    return (200, (top + bottom) / 2), '전층 황반원공' if full else '층판 원공(내층 결손)'


def o_erm(s, cols, label='망막전막'):
    pts = [(x, cols[x]['ILM'] - 2 + 1.5 * math.sin(x / 7)) for x in sorted(cols) if 60 <= x <= 340]
    s.add(f'<polyline points="{" ".join(f"{x},{y:.1f}" for x, y in pts)}" fill="none" stroke="#fafafa" stroke-width="2.4"/>')
    return pts[12], label


def o_band(s, cols, key_top, key_bot, x0, x1, fill, frac=(0, 1), opacity=1.0):
    xs = [x for x in sorted(cols) if x0 <= x <= x1]
    top = [(x, cols[x][key_top] + (cols[x][key_bot] - cols[x][key_top]) * frac[0]) for x in xs]
    bot = [(x, cols[x][key_top] + (cols[x][key_bot] - cols[x][key_top]) * frac[1]) for x in xs]
    s.add(f'<polygon points="{" ".join(f"{x},{y:.1f}" for x, y in top)} {" ".join(f"{x},{y:.1f}" for x, y in reversed(bot))}" fill="{fill}" opacity="{opacity}"/>')
    mid = xs[len(xs) // 2]
    return (mid, (top[len(xs) // 2][1] + bot[len(xs) // 2][1]) / 2)


def o_gap(s, cols, key, x0, x1, width=3):
    xs = [x for x in sorted(cols) if x0 <= x <= x1]
    s.add(f'<polyline points="{" ".join(f"{x},{cols[x][key]:.1f}" for x in xs)}" fill="none" stroke="#353535" stroke-width="{width}"/>')
    return ((x0 + x1) / 2, cols[xs[len(xs) // 2]][key])


def o_hypertd(s, cols, x0, x1):
    o_gap(s, cols, 'RPE', x0, x1, 5)
    o_gap(s, cols, 'EZ', x0 - 6, x1 + 6, 3)
    xs = [x for x in sorted(cols) if x0 <= x <= x1]
    top = ' '.join(f'{x},{cols[x]["BM"]:.1f}' for x in xs)
    bot = ' '.join(f'{x},{cols[x]["CSI"] + 10:.1f}' for x in reversed(xs))
    s.add(f'<polygon points="{top} {bot}" fill="#e6e6e6" opacity=".55"/>')
    return ((x0 + x1) / 2, cols[xs[len(xs) // 2]]['CSI'] - 10)


def o_dots(s, cols, key_top, key_bot, n, x0, x1, r, fill, seed=61, shadow=False):
    g = rng(seed)
    pts = []
    for _ in range(n):
        x = g.uniform(x0, x1)
        b = cols[min(cols, key=lambda k: abs(k - x))]
        y = b[key_top] + (b[key_bot] - b[key_top]) * g.uniform(.2, .8)
        if shadow:
            s.add(f'<rect x="{x - r:.1f}" y="{y:.1f}" width="{2 * r:.1f}" height="{OH - y:.1f}" fill="#000" opacity=".35"/>')
        s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}"/>')
        pts.append((x, y))
    return pts


# ------------------------------------------------------------------ panel builders
def face_panel(glyph, base_kw=None, label=None):
    s = Svg()
    face_base(s, **(base_kw or {}))
    target, lab = glyph(s)
    if lab or label:
        s.callout(target, label or lab)
    return s


def wide_panel(glyph):
    s = Svg()
    wide_base(s)
    target, lab = glyph(s)
    s.callout(target, lab)
    return s


def disc_panel(glyph, base_kw=None):
    s = Svg()
    disc_base(s, **(base_kw or {}))
    target, lab = glyph(s)
    if lab:
        s.callout(target, lab)
    return s


def oct_panel(draw, mods=None, base_kw=None):
    s = Svg(HW, OH)
    cols = oct_base(s, mods=mods, **(base_kw or {}))
    out = draw(s, cols) if draw else None
    if out:
        s.callout(*out)
    return s


# wide-field glyphs
def w_lattice(s):
    for a in (-35, -20):
        r = math.radians(a)
        x, y = 200 + 112 * math.cos(r), 150 + 112 * math.sin(r)
        s.add(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="16" ry="6" transform="rotate({a + 90:.0f} {x:.1f} {y:.1f})" fill="#e8c9a8" opacity=".7" stroke="#2a170d"/>')
        s.add(f'<path d="M{x - 8:.1f},{y - 3:.1f} l16,6 M{x - 8:.1f},{y + 3:.1f} l16,-6" stroke="#f8f2e8" stroke-width="1" transform="rotate({a + 90:.0f} {x:.1f} {y:.1f})"/>')
    r = math.radians(-28)
    return (200 + 112 * math.cos(r), 150 + 112 * math.sin(r)), '격자변성(주변부)'


def w_break(s):
    x, y = 200 + 110 * math.cos(math.radians(-50)), 150 + 110 * math.sin(math.radians(-50))
    s.add(f'<path d="M{x - 9:.1f},{y + 6:.1f} Q{x:.1f},{y - 14:.1f} {x + 9:.1f},{y + 6:.1f} Q{x:.1f},{y - 2:.1f} {x - 9:.1f},{y + 6:.1f} Z" fill="#a3170f" stroke="#f4e3cf"/>')
    return (x, y), '말굽 모양 열공'


def w_rrd(s):
    w_break(s)
    s.add('<path d="M330,150 A130,130 0 0 0 200,20 L210,95 Q260,110 300,150 Z" fill="#c4b6aa" opacity=".6" stroke="#efe6dc"/>')
    for k in range(4):
        s.add(f'<path d="M{240 + k * 18},{60 + k * 14} q10,10 20,0" stroke="#efe6dc" stroke-width="1" fill="none"/>')
    return (265, 90), '열공성 망막박리(회색 융기)'


def w_np(s):
    blob(s, (110, 90), 40, 34, '#b9a38c', seed=70, opacity=.6, stroke='#efe2d2', dash='3 3')
    blob(s, (300, 215), 36, 26, '#b9a38c', seed=71, opacity=.6, stroke='#efe2d2', dash='3 3')
    return (110, 90), '주변부 무관류'


def w_ora(s):
    return (200 + 128 * math.cos(-1.0), 150 + 128 * math.sin(-1.0)), '거상연(톱니 모양 경계)'


def w_far(s):
    s.add('<path fill-rule="evenodd" d="M60,150 a140,140 0 1 0 280,0 a140,140 0 1 0 -280,0 Z M112,150 a88,88 0 1 0 176,0 a88,88 0 1 0 -176,0 Z" fill="#ffd34d" opacity=".22"/>')
    return (200, 38), '적도부 바깥 ~ 거상연'


def w_vortex(s):
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        x, y = 200 + 92 * math.cos(a), 150 + 92 * math.sin(a)
        s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="none" stroke="#ffd34d" stroke-width="2"/>')
    return (200 + 92 * math.cos(math.radians(315)), 150 + 92 * math.sin(math.radians(315))), '와정맥 팽대부(4곳)'


def w_zones(s):
    for r, lab in ((40, '후극부'), (88, '중간 주변부'), (128, '원주변부')):
        s.add(f'<circle cx="200" cy="150" r="{r}" fill="none" stroke="#ffd34d" stroke-width="1.4" stroke-dasharray="5 4"/>')
        s.text(200, 150 - r + 13, lab, 10.5, '#ffd34d', 'middle')
    return (200, 150 - 88), ''


def w_seven(s):
    for k, (dx, dy) in enumerate([(0, 0), (-38, 0), (38, 0), (-20, -36), (20, -36), (-20, 36), (20, 36)]):
        s.add(f'<circle cx="{205 + dx}" cy="{150 + dy}" r="26" fill="none" stroke="#ffd34d" stroke-width="1.4"/>')
        s.text(205 + dx, 154 + dy, str(k + 1), 11, '#ffd34d', 'middle')
    return (205, 92), ''


# ------------------------------------------------------------------ specs
P = {}  # item_id -> list of (panel_key, svg, label)


def add(item, key, svg, label):
    P.setdefault(item, []).append((key, svg, label))


def face(item, glyph, base_kw=None, label=None):
    add(item, 'face', face_panel(glyph, base_kw, label), '모식도 · 안저')


def octp(item, draw, mods=None, base_kw=None):
    add(item, 'oct', oct_panel(draw, mods, base_kw), '모식도 · OCT')


def build_specs():
    # haemorrhage / vascular
    face('les_microaneurysm', f_ma)
    octp('les_microaneurysm', lambda s, c: (o_dots(s, c, 'IPL', 'INL', 3, 150, 260, 3.5, '#d9d9d9', seed=62)[0], '미세동맥류(INL 고반사 고리)'))
    face('les_hemorrhage_dot_blot', f_dot_blot)
    face('les_hemorrhage_flame', f_flame)
    face('les_hemorrhage_preretinal', f_preretinal)
    def preretinal(s, c):
        xs = [x for x in sorted(c) if 120 <= x <= 280]
        top = ' '.join(f'{x},{c[x]["ILM"] - 16 * (1 - ((x - 200) / 80) ** 2) ** .5:.1f}' for x in xs)
        bot = ' '.join(f'{x},{c[x]["ILM"] - 1:.1f}' for x in reversed(xs))
        s.add(''.join(f'<rect x="{x - 2}" y="{c[x]["ILM"]:.1f}" width="4" height="{OH - c[x]["ILM"]:.1f}" fill="#000" opacity=".4"/>' for x in xs))
        s.add(f'<polygon points="{top} {bot}" fill="#d4d4d4"/>')
        return (200, c[200]['ILM'] - 10), '망막앞 출혈(아래 그림자)'
    octp('les_hemorrhage_preretinal', preretinal)
    face('les_hemorrhage_vitreous', f_vitreous)
    face('les_hemorrhage_subretinal', f_subretinal_hem)
    octp('les_hemorrhage_subretinal', lambda s, c: (o_srf_fill(s, c, '#bdbdbd'), ((200, c[200]['RPE'] - 10), '망막하 출혈(고반사)'))[1], mods_srf(18))
    face('les_hemorrhage_sub_rpe', f_sub_rpe_hem)
    octp('les_hemorrhage_sub_rpe', lambda s, c: (o_ped_fill(s, c, '#9a9a9a'), ((200, c[200]['BM'] - 10), 'RPE 아래 출혈'))[1], mods_ped(26, 60))
    face('les_venous_beading', f_beading)
    face('les_venous_dilation_tortuosity', f_dilation)
    face('les_venous_loop_reduplication', f_loop)
    face('les_irma', f_irma)
    face('les_nv_disc', f_nvd)
    face('les_nv_elsewhere', f_nve)
    add('les_nv_elsewhere', 'wide', wide_panel(lambda s: (nv_net(s, (285, 85), 14, 72), ((285, 85), '주변부 신생혈관'))[1]), '모식도 · 광각')
    face('les_neovascularization_pooled', lambda s: (f_nvd(s), f_nve(s))[1][0:1] + ('NVD + NVE',))
    face('les_nonperfusion', f_nonperfusion)
    add('les_nonperfusion', 'wide', wide_panel(w_np), '모식도 · 광각')
    face('les_faz_enlargement', f_faz)
    face('les_arteriolar_narrowing', f_narrowing)
    face('les_av_nicking', f_av_nick)
    face('les_vessel_sheathing', f_sheathing)
    face('les_retinal_embolus', f_embolus)
    face('les_retinal_whitening', f_whitening)
    octp('les_retinal_whitening', lambda s, c: (o_band(s, c, 'ILM', 'OPL', 40, 360, '#d9d9d9', opacity=.7), 'x')[0:1] and ((120, (c[120]['GCL'] + c[120]['INL']) / 2), '내망막 고반사·두꺼워짐'), mods_thick(8))
    face('les_cherry_red_spot', f_cherry)
    face('les_paracentral_amn', f_pamm_face)
    octp('les_paracentral_amn', lambda s, c: (o_band(s, c, 'IPL', 'OPL', 110, 170, '#e0e0e0', (0.05, 1)), '')[0:1] and ((140, (c[140]['INL'] + c[140]['IPL']) / 2), 'INL 띠 모양 고반사'))
    face('les_hemorrhage_pooled', lambda s: (f_dot_blot(s), f_flame(s))[0][0:1] + ('출혈(층위 미구분)',))
    face('les_red_lesion_pooled', lambda s: (f_ma(s), f_dot_blot(s))[1][0:1] + ('미세동맥류 + 출혈',))
    face('les_retinal_telangiectasia', f_telangiectasia)
    face('les_arterial_macroaneurysm', f_ram)
    face('les_retinal_vasculitis_signs', f_vasculitis)
    # neovascular AMD / PCV
    face('les_macular_neovascularization', f_mnv_face)
    octp('les_macular_neovascularization', lambda s, c: (o_ped_fill(s, c, '#8f8f8f'), o_srf_fill(s, c), ((200, c[200]['BM'] - 6), '1형 MNV(RPE 아래 불균일 반사)'))[2], lambda x, b: (mods_ped(14, 55)(x, b), mods_srf(10, 70)(x, b)))
    face('les_polypoidal_lesion', f_polyp_face)
    octp('les_polypoidal_lesion', lambda s, c: (o_ped_fill(s, c, '#3a3a3a'), s.add(f'<ellipse cx="236" cy="{c[236]["RPE"] + 10:.1f}" rx="6" ry="5" fill="none" stroke="#d9d9d9" stroke-width="2"/>'), ((236, c[236]['RPE'] + 10), '뾰족한 PED + 고리 모양 결절'))[2], mods_ped(24, 24, cx=236, peaked=True))
    face('les_sub_rpe_ring_lesion', f_subrpe_ring_face)
    octp('les_sub_rpe_ring_lesion', lambda s, c: (s.add(f'<ellipse cx="236" cy="{c[236]["RPE"] + 9:.1f}" rx="7" ry="6" fill="#1a1a1a" stroke="#e0e0e0" stroke-width="2.2"/>'), ((236, c[236]['RPE'] + 9), 'RPE 아래 고리 모양 병변'))[1], mods_ped(20, 22, cx=236, peaked=True))
    octp('les_sharp_peaked_ped', lambda s, c: (o_ped_fill(s, c, '#080808'), ((200, c[200]['RPE'] - 4), '뾰족한 PED'))[1], mods_ped(40, 26, peaked=True))
    face('les_sharp_peaked_ped', lambda s: f_ped_face(s, '작고 뾰족한 융기'))
    octp('les_enface_complex_rpe_elevation', lambda s, c: (o_ped_fill(s, c, '#7a7a7a'), ((200, c[200]['RPE'] + 4), '얕고 불규칙한 RPE 융기(평평한 PED)'))[1], lambda x, b: mods_drusen([(150, 50, 7), (205, 45, 9), (255, 40, 6)])(x, b))
    # exudates & deposits
    face('les_hard_exudate', f_exudates)
    octp('les_hard_exudate', lambda s, c: (o_dots(s, c, 'INL', 'ELM', 6, 120, 280, 3.2, '#f2f2f2', seed=63, shadow=True)[0], '고반사 점(아래 그림자)'))
    face('les_circinate_exudate', f_circinate)
    face('les_macular_star', f_star)
    face('les_cotton_wool_spot', f_cws)
    octp('les_cotton_wool_spot', lambda s, c: (o_band(s, c, 'ILM', 'NFL', 266, 334, '#f5f5f5'), ((300, c[300]['NFL'] - 4), '신경섬유층 고반사 융기'))[1], lambda x, b: b.__setitem__('ILM', b['ILM'] - 10 * max(0, 1 - ((x - 300) / 34) ** 2) ** .7))
    for size, lid in (('small', 'les_drusen_small'), ('medium', 'les_drusen_medium'), ('large', 'les_drusen_large'), ('any', 'les_drusen_unspecified')):
        face(lid, f_drusen(size))
    octp('les_drusen_small', lambda s, c: (o_ped_fill(s, c, '#8a8a8a'), ((150, c[150]['RPE']), '작은 RPE 융기'))[1], mods_drusen([(150, 6, 3), (230, 6, 3), (270, 6, 3)]))
    octp('les_drusen_medium', lambda s, c: (o_ped_fill(s, c, '#8a8a8a'), ((150, c[150]['RPE']), 'RPE 아래 중간 융기'))[1], mods_drusen([(150, 12, 7), (240, 12, 7)]))
    octp('les_drusen_large', lambda s, c: (o_ped_fill(s, c, '#8a8a8a'), ((170, c[170]['RPE']), '큰 드루젠(RPE 아래 돔)'))[1], mods_drusen([(170, 24, 14), (240, 20, 11)]))
    octp('les_drusen_unspecified', lambda s, c: (o_ped_fill(s, c, '#8a8a8a'), ((170, c[170]['RPE']), 'RPE 아래 침착물'))[1], mods_drusen([(130, 8, 4), (170, 18, 10), (240, 12, 7)]))
    face('les_drusen_cuticular', f_cuticular)
    octp('les_drusen_cuticular', lambda s, c: (o_ped_fill(s, c, '#8a8a8a'), ((150, c[150]['RPE']), '톱니 모양 RPE 융기'))[1], mods_drusen([(x, 5, 4) for x in range(40, 361, 14)]))
    face('les_subretinal_drusenoid_deposit', f_sdd_face)
    octp('les_subretinal_drusenoid_deposit', lambda s, c: (s.add(''.join(f'<path d="M{x - 6},{c[x]["RPE"]:.1f} L{x},{c[x]["EZ"] - 2:.1f} L{x + 6},{c[x]["RPE"]:.1f} Z" fill="#bdbdbd"/>' for x in range(60, 340, 28))), ((116, c[116]['IZ']), 'RPE 위 삼각형 침착물'))[1])
    face('les_lipid_subretinal', f_lipid)
    face('les_flecks', f_flecks)
    face('les_vitelliform_lesion', f_vitelliform_face)
    octp('les_vitelliform_lesion', lambda s, c: (o_srf_fill(s, c, '#d6d6d6'), ((200, c[200]['RPE'] - 8), 'EZ–RPE 사이 고반사 물질'))[1], mods_srf(20, 32))
    # fluid & elevation
    octp('les_intraretinal_fluid', lambda s, c: o_cysts(s, c), mods_thick(10))
    face('les_intraretinal_fluid', f_thick_face, label='망막내액(정면에선 두꺼워짐으로 보임)')
    octp('les_cystoid_macular_edema', lambda s, c: o_cysts(s, c, '꽃잎 모양 낭포', big=True), mods_thick(18))
    face('les_cystoid_macular_edema', lambda s: (s.add(''.join(f'<ellipse cx="{FOVEA[0] + 16 * math.cos(2 * math.pi * k / 8):.1f}" cy="{FOVEA[1] + 16 * math.sin(2 * math.pi * k / 8):.1f}" rx="7" ry="4.5" transform="rotate({45 * k} {FOVEA[0] + 16 * math.cos(2 * math.pi * k / 8):.1f} {FOVEA[1] + 16 * math.sin(2 * math.pi * k / 8):.1f})" fill="#e9b892" opacity=".7"/>' for k in range(8))), (FOVEA, '꽃잎 모양 부종'))[1])
    octp('les_subretinal_fluid', lambda s, c: (o_srf_fill(s, c), ((200, c[200]['RPE'] - 8), '망막하액'))[1], mods_srf(24))
    face('les_subretinal_fluid', f_serous_rd, label='망막하액(둥근 융기)')
    octp('les_serous_retinal_detachment', lambda s, c: (o_srf_fill(s, c), ((200, c[200]['RPE'] - 10), '장액성 망막박리'))[1], mods_srf(34, 90))
    face('les_serous_retinal_detachment', f_serous_rd)
    for lid, fill, label, kw in (('les_ped_serous', '#060606', '장액성 PED(속이 검음)', {}), ('les_ped_drusenoid', '#8f8f8f', '드루젠양 PED(중간 반사)', {}),
                                 ('les_ped_fibrovascular', '#6a6a6a', '섬유혈관성 PED(불균일)', {}), ('les_ped_unspecified', '#4a4a4a', '색소상피박리', {})):
        octp(lid, (lambda fill, label: lambda s, c: (o_ped_fill(s, c, fill), ((200, c[200]['RPE'] + 10), label))[1])(fill, label), mods_ped(30, 50))
        face(lid, lambda s, l=label: f_ped_face(s, l))
    octp('les_macular_thickening', lambda s, c: ((200, c[200]['ILM'] - 2), '망막 두께 증가'), mods_thick(22))
    face('les_macular_thickening', f_thick_face)
    face('les_csme', f_csme)
    octp('les_csme', lambda s, c: o_cysts(s, c, '중심 침범 부종'), mods_thick(14))
    # reflectivity / outer retina
    octp('les_hyperreflective_foci', lambda s, c: (o_dots(s, c, 'GCL', 'ELM', 10, 100, 300, 2.6, '#ffffff', seed=64)[0], '고반사 점'))
    octp('les_shrm', lambda s, c: (o_srf_fill(s, c, '#c8c8c8'), ((200, c[200]['RPE'] - 8), '망막하 고반사 물질'))[1], mods_srf(16, 55))
    octp('les_dril', lambda s, c: (o_band(s, c, 'GCL', 'OPL', 240, 330, '#6f6f6f'), ((285, (c[285]['IPL'] + c[285]['INL']) / 2), '내층 경계 소실'))[1])
    octp('les_ez_disruption', lambda s, c: (o_gap(s, c, 'EZ', 170, 230, 3), ((200, c[200]['EZ']), 'EZ 단절'))[1])
    octp('les_elm_disruption', lambda s, c: (o_gap(s, c, 'ELM', 175, 225, 2.5), ((200, c[200]['ELM']), 'ELM 단절'))[1])
    octp('les_outer_retinal_tubulation', lambda s, c: (s.add(f'<ellipse cx="230" cy="{(c[230]["OPL"] + c[230]["ELM"]) / 2:.1f}" rx="8" ry="6" fill="#111" stroke="#e8e8e8" stroke-width="2"/>'), ((230, (c[230]['OPL'] + c[230]['ELM']) / 2), '외망막 관상 구조(고리)'))[1])
    octp('les_hypertransmission', lambda s, c: o_hypertd(s, c, 170, 240) and ((205, c[205]['CSI'] - 10), '맥락막 쪽 과투과'))
    octp('les_rpe_attenuation_disruption', lambda s, c: (o_gap(s, c, 'RPE', 180, 230, 3), ((205, c[205]['RPE']), 'RPE 약화·단절'))[1])
    face('les_rpe_hyperpigmentation', lambda s: f_pigment(s, 12, FOVEA, 26, 'RPE 과색소'))
    octp('les_rpe_hyperpigmentation', lambda s, c: (o_dots(s, c, 'IZ', 'RPE', 4, 160, 240, 3, '#ffffff', seed=65, shadow=True)[0], 'RPE 수준 고반사·그림자'))
    face('les_rpe_hypopigmentation', f_hypo)
    octp('les_intraretinal_hyperreflective_pigment', lambda s, c: (o_dots(s, c, 'INL', 'ELM', 4, 160, 250, 3.2, '#ffffff', seed=66, shadow=True)[0], '망막 안으로 이동한 색소'))
    face('les_intraretinal_hyperreflective_pigment', lambda s: f_pigment(s, 8, FOVEA, 22, '망막 내 색소 덩어리'))
    octp('les_atrophy_incomplete', lambda s, c: (o_gap(s, c, 'RPE', 185, 215, 3), o_hypertd(s, c, 188, 212), ((200, c[200]['CSI'] - 10), 'iRORA(<250 µm, 불완전)'))[2])
    octp('les_atrophy_complete', lambda s, c: (o_hypertd(s, c, 165, 240), ((200, c[200]['CSI'] - 10), 'cRORA(≥250 µm 과투과+RPE 소실)'))[1], lambda x, b: [b.__setitem__(k, b[k] + 9 * max(0, 1 - ((x - 202) / 40) ** 2)) for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL', 'ELM', 'EZ', 'IZ')])
    face('les_atrophy_complete', lambda s: f_atrophy(s, FOVEA, 22, 18, '완전 위축(맥락막 혈관 노출)', seed=73))
    face('les_geographic_atrophy', f_atrophy)
    octp('les_geographic_atrophy', lambda s, c: (o_hypertd(s, c, 140, 260), ((200, c[200]['CSI'] - 10), '넓은 RPE 소실·과투과'))[1], lambda x, b: [b.__setitem__(k, b[k] + 10 * max(0, 1 - ((x - 200) / 62) ** 2)) for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL', 'OPL', 'ELM', 'EZ', 'IZ')])
    face('les_bulls_eye_maculopathy', f_bulls_eye)
    octp('les_bulls_eye_maculopathy', lambda s, c: (o_gap(s, c, 'EZ', 140, 175, 3), o_gap(s, c, 'EZ', 225, 260, 3), ((158, c[158]['EZ']), '중심와 주위 EZ 소실·중심 보존'))[2])
    face('les_white_dots', f_white_dots)
    octp('les_white_dots', lambda s, c: (o_gap(s, c, 'EZ', 120, 140, 3), o_gap(s, c, 'EZ', 250, 270, 3), ((130, c[130]['EZ']), '점에 대응하는 EZ 단절'))[2])
    # vitreoretinal interface
    face('les_epiretinal_membrane', f_erm)
    octp('les_epiretinal_membrane', lambda s, c: o_erm(s, c), mods_thick(12))
    octp('les_erm_foveoschisis', lambda s, c: (o_erm(s, c), s.add(''.join(f'<rect x="{x}" y="{(c[x]["INL"] + c[x]["OPL"]) / 2 - 3:.1f}" width="2.4" height="9" fill="#050607"/>' for x in range(140, 262, 6) if abs(x - 200) > 12)), ((240, (c[240]['INL'] + c[240]['OPL']) / 2), '헨레층 층간분리'))[2], mods_thick(10))
    octp('les_macular_pseudohole', lambda s, c: (o_erm(s, c, '망막전막'), ((200, c[200]['ILM'] - 2), '가파른 중심와 가장자리(가성원공)'))[1], lambda x, b: [b.__setitem__(k, b[k] - 16 * max(0, min(1, (abs(x - 200) - 14) / 20)) * math.exp(-((x - 200) / 70) ** 2)) for k in ('ILM', 'NFL', 'GCL', 'IPL', 'INL')])
    face('les_macular_pseudohole', lambda s: (f_erm(s), f_mh_face(s, '원공처럼 보이는 중심와', cuff=False))[1])
    octp('les_vitreomacular_adhesion', lambda s, c: o_hyaloid(s, c, (182, 218), 30, '유리체 부착(형태 변화 없음)'))
    octp('les_vitreomacular_traction', lambda s, c: o_hyaloid(s, c, (186, 214), 46, '견인으로 들린 중심와'), mods_vmt('vmt'))
    octp('les_macular_hole_full_thickness', lambda s, c: o_hole(s, c, True))
    face('les_macular_hole_full_thickness', f_mh_face, label='전층 황반원공')
    octp('les_macular_hole_lamellar', lambda s, c: o_hole(s, c, False))
    face('les_macular_hole_lamellar', lambda s: f_mh_face(s, '층판 원공(불규칙한 중심와)', cuff=False))
    octp('les_retinal_schisis', lambda s, c: (s.add(''.join(f'<rect x="{x}" y="{c[x]["INL"] - 2:.1f}" width="2.4" height="{max(4, (c[x]["OPL"] - c[x]["INL"]) + 6):.1f}" fill="#050607"/>' for x in range(60, 340, 7))), ((120, c[120]['INL'] + 4), '층 사이 기둥 모양 분리'))[1], mods_thick(10))
    face('les_fibrovascular_proliferation', f_fvp)
    face('les_retinal_detachment_tractional', f_trd)
    octp('les_retinal_detachment_tractional', lambda s, c: (o_srf_fill(s, c), s.add(f'<path d="M140,{c[200]["ILM"] - 30:.1f} L200,{c[200]["ILM"] - 2:.1f} L260,{c[200]["ILM"] - 30:.1f}" stroke="#f2f2f2" stroke-width="2.4" fill="none"/>'), ((200, c[200]['RPE'] - 12), '막에 끌려 들린 망막'))[2], lambda x, b: mods_srf(34, 50)(x, b))
    add('les_retinal_detachment_rhegmatogenous', 'wide', wide_panel(w_rrd), '모식도 · 광각')
    octp('les_retinal_detachment_rhegmatogenous', lambda s, c: (o_srf_fill(s, c), ((120, c[120]['RPE'] - 14), '박리된 망막과 망막하액'))[1], mods_srf(46, 160, cx=120))
    add('les_retinal_break', 'wide', wide_panel(w_break), '모식도 · 광각')
    add('les_lattice_degeneration', 'wide', wide_panel(w_lattice), '모식도 · 광각')
    face('les_pvr', f_pvr)
    # optic disc
    add('les_disc_cupping', 'disc', disc_panel(lambda s: ((204, 150), '확대된 함몰(C/D 큼)'), {'cup': (52, 62)}), '모식도 · 시신경유두')
    add('les_rnfl_defect', 'disc', disc_panel(lambda s: (s.add('<path d="M190,220 L120,300 L175,300 Z" fill="#5a2010" opacity=".55"/>'), ((160, 280), '쐐기 모양 신경섬유층 결손'))[1]), '모식도 · 시신경유두')
    add('les_disc_hemorrhage', 'disc', disc_panel(lambda s: (flame(s, (150, 215), 125, 26, 6), ((150, 215), '유두 가장자리 선상 출혈'))[1]), '모식도 · 시신경유두')
    add('les_peripapillary_atrophy', 'disc', disc_panel(lambda s: (s.add('<path d="M140,85 A75,85 0 0 0 140,215 L118,225 A95,100 0 0 1 118,75 Z" fill="#f2dcc0"/>'), ((125, 150), '유두주위 위축(이측 초승달)'))[1]), '모식도 · 시신경유두')
    add('les_disc_edema', 'disc', disc_panel(lambda s: (s.add('<ellipse cx="200" cy="150" rx="92" ry="102" fill="#e89a6a" opacity=".55"/>'), flame(s, (110, 120), 200, 22, 5), ((285, 110), '흐려진 경계·부은 유두'))[2], {'cup': (8, 10)}), '모식도 · 시신경유두')
    add('les_disc_pallor', 'disc', disc_panel(lambda s: ((165, 150), '창백한 유두'), {'rim': '#f7ecd8'}), '모식도 · 시신경유두')
    add('les_tilted_disc', 'disc', disc_panel(lambda s: (s.add('<ellipse cx="200" cy="150" rx="78" ry="50" transform="rotate(-25 200 150)" fill="none" stroke="#ffd34d" stroke-width="1.5" stroke-dasharray="4 3"/><path d="M120,200 A80,52 -25 0 0 175,214 L150,236 A100,70 -25 0 1 100,214 Z" fill="#f2dcc0"/>'), ((200, 100), '기울어진 타원 유두·하측 초승달'))[1], {'cup': (24, 20)}), '모식도 · 시신경유두')
    add('les_disc_collaterals', 'disc', disc_panel(lambda s: (s.add('<path d="M170,120 q-25,25 0,50 q25,25 0,40 M230,120 q25,20 0,45" stroke="#7d1a12" stroke-width="4" fill="none"/>'), ((158, 150), '유두 위 정맥 고리(측부혈관)'))[1]), '모식도 · 시신경유두')
    octp('les_disc_edema', None)
    P['les_disc_edema'].pop()   # OCT through the macula is not informative here
    # scars / myopia / choroid / tumours / inherited
    face('les_laser_scar', lambda s: f_scar(s, 'laser'))
    face('les_fibrotic_scar', lambda s: f_scar(s, 'fibrotic'))
    face('les_chorioretinal_scar', lambda s: f_scar(s, 'chorio'))
    face('les_tessellated_fundus', f_tessellated)
    face('les_myopic_diffuse_atrophy', f_myopic_diffuse)
    face('les_myopic_patchy_atrophy', f_myopic_patchy)
    face('les_myopic_macular_atrophy', f_myopic_macular)
    face('les_lacquer_crack', f_lacquer)
    face('les_myopic_cnv', lambda s: (f_mnv_face(s)[0], '근시성 CNV(작은 회색 병변)'))
    octp('les_myopic_cnv', lambda s, c: (o_srf_fill(s, c, '#bdbdbd'), ((200, c[200]['RPE'] - 8), 'RPE 위 고반사 병변(2형)'))[1], mods_srf(14, 26), {'choroid': 16})
    face('les_fuchs_spot', f_fuchs)
    octp('les_posterior_staphyloma', lambda s, c: ((200, c[200]['CSI'] + 6), '뒤로 휘어진 공막(후포도종)'), lambda x, b: [b.__setitem__(k, b[k] + 34 * math.exp(-((x - 200) / 110) ** 2)) for k in list(b)], {'choroid': 14, 'pit': 0.7})
    face('les_posterior_staphyloma', f_staph_face)
    octp('les_myopic_traction_maculopathy', lambda s, c: (s.add(''.join(f'<rect x="{x}" y="{c[x]["INL"] - 2:.1f}" width="2.4" height="{max(4, c[x]["ELM"] - c[x]["INL"]):.1f}" fill="#050607"/>' for x in range(60, 340, 8))), ((110, c[110]['OPL']), '얇은 맥락막 위의 황반분리'))[1], lambda x, b: (mods_thick(12)(x, b), [b.__setitem__(k, b[k] + 30 * math.exp(-((x - 200) / 110) ** 2)) for k in list(b)]), {'choroid': 12})
    octp('les_dome_shaped_macula', lambda s, c: ((200, c[200]['RPE'] - 2), '안쪽으로 돌출한 황반(돔)'), lambda x, b: [b.__setitem__(k, b[k] - 16 * math.exp(-((x - 200) / 70) ** 2) + 20 * (1 - math.exp(-((x - 200) / 140) ** 2))) for k in list(b)], {'choroid': 16})
    octp('les_pachychoroid_features', lambda s, c: ((90, (c[90]['BM'] + c[90]['CSI']) / 2), '두꺼운 맥락막·확장된 대혈관'), None, {'choroid': 64})
    face('les_pachychoroid_features', f_pachy_face)
    octp('les_choroidal_hyperpermeability', lambda s, c: ((300, (c[300]['BM'] + c[300]['CSI']) / 2), '맥락막 비후(ICGA 과투과의 배경)'), None, {'choroid': 64})
    face('les_choroidal_hyperpermeability', lambda s: (blob(s, (190, 150), 60, 45, '#ffd9a0', seed=74, opacity=.35), ((190, 150), 'ICGA 후기 다발성 과형광 지역'))[1])
    face('les_rpe_gravitational_tract', f_gravitational)
    face('les_choroidal_nevus', f_nevus)
    octp('les_choroidal_nevus', lambda s, c: (o_band(s, c, 'BM', 'CSI', 90, 170, '#bdbdbd', (0.05, 0.9)), ((130, (c[130]['BM'] + c[130]['CSI']) / 2), '맥락막 안 고반사 병변'))[1])
    face('les_choroidal_hemangioma', f_hemangioma)
    octp('les_choroidal_hemangioma', lambda s, c: ((240, c[240]['BM'] + 14), '돔 모양 맥락막 종괴'), lambda x, b: [b.__setitem__(k, b[k] - 30 * max(0, 1 - ((x - 240) / 60) ** 2) ** .6) for k in list(b) if k != 'CSI'])
    face('les_chrpe', f_chrpe)
    face('les_bone_spicule_pigment', lambda s: (f_bone_spicule(s)))
    face('les_angioid_streaks', f_angioid)
    face('les_flecks', f_flecks) if 'les_flecks' not in P else None
    # anatomy items without a schematic
    add('ana_far_periphery', 'wide', wide_panel(w_far), '모식도 · 광각')
    add('ana_ora_serrata', 'wide', wide_panel(w_ora), '모식도 · 광각')
    add('ana_vortex_vein', 'wide', wide_panel(w_vortex), '모식도 · 광각')
    add('zone_retinal_periphery', 'wide', wide_panel(w_zones), '모식도 · 광각')
    add('zone_etdrs_7field', 'wide', wide_panel(w_seven), '모식도 · 광각')
    face('ana_macular_pigment', lambda s: (s.add(f'<circle cx="{FOVEA[0]}" cy="{FOVEA[1]}" r="20" fill="#f3d34a" opacity=".55"/>'), (FOVEA, '황반 색소(루테인·제아잔틴)'))[1])
    def quadrants(s):
        s.add(f'<g clip-path="url(#fc)"><path d="M40,{FOVEA[1] + 2} L380,{DISC[1] - 1} M{FOVEA[0] + 2},0 L{FOVEA[0] - 2},300" stroke="#ffd34d" stroke-width="1.6" stroke-dasharray="5 4"/></g>')
        for x, y, t in ((110, 80, '상이측'), (235, 80, '상비측'), (110, 228, '하이측'), (235, 228, '하비측')):
            s.text(x, y, t, 11.5, '#ffd34d', 'middle')
        return FOVEA, ''
    face('zone_fundus_quadrant', quadrants)
    face('zone_peripapillary', lambda s: (s.add(f'<path fill-rule="evenodd" d="M{DISC[0] - 50},{DISC[1]} a50,54 0 1 0 100,0 a50,54 0 1 0 -100,0 Z M{DISC[0] - 18},{DISC[1]} a18,22 0 1 0 36,0 a18,22 0 1 0 -36,0 Z" fill="#ffd34d" opacity=".3"/>'), ((DISC[0] - 40, DISC[1] - 30), '유두주위 구역'))[1])
    octp('zone_octa_slab', lambda s, c: (o_band(s, c, 'ILM', 'IPL', 0, 400, '#ef4444', (0, .9), .35), o_band(s, c, 'IPL', 'OPL', 0, 400, '#38bdf8', (0, 1), .35), o_band(s, c, 'OPL', 'BM', 0, 400, '#a3e635', (0, 1), .25), o_band(s, c, 'BM', 'CSI', 0, 400, '#f97316', (0, .25), .5),
                                          s.text(390, c[390]['GCL'] + 4, '표층', 10.5, '#fecaca', 'end'), s.text(390, c[390]['INL'] + 4, '심층', 10.5, '#bae6fd', 'end'), s.text(390, c[390]['ELM'] + 4, '외망막', 10.5, '#d9f99d', 'end'), s.text(390, c[390]['BM'] + 9, 'CC', 10.5, '#fed7aa', 'end'), None)[-1])
    octp('ana_premacular_bursa', lambda s, c: (s.add(f'<path d="M110,{c[110]["ILM"] - 4:.1f} Q200,{c[200]["ILM"] - 70:.1f} 290,{c[290]["ILM"] - 4:.1f}" fill="#1c2430" stroke="#9aa4b2" stroke-width="1.4"/>'), ((200, c[200]['ILM'] - 40), '황반앞 유리체 주머니'))[1])
    onh = Svg(HW, OH)
    onh_base(onh)
    onh.add('<circle cx="140" cy="150" r="5" fill="#ffd34d"/><circle cx="260" cy="150" r="5" fill="#ffd34d"/>')
    onh.callout((260, 150), '브루크막 개구부(BMO)', (330, 110))
    add('ana_bmo', 'onh', onh, '모식도 · 유두 OCT')
    onh2 = Svg(HW, OH)
    onh_base(onh2)
    onh2.add(''.join(f'<path d="M150,{y} L250,{y}" stroke="#ffd34d" stroke-width="1.4" opacity=".8"/>' for y in range(190, 214, 6)))
    onh2.callout((200, 200), '사상판(체 모양 판)', (320, 120))
    add('ana_lamina_cribrosa', 'onh', onh2, '모식도 · 유두 OCT')
    add('les_disc_cupping', 'onh', (lambda s: (onh_base(s, cup_depth=90), s.callout((200, 150), '깊어진 함몰', (320, 90)), s)[-1])(Svg(HW, OH)), '모식도 · 유두 OCT')


CAPTIONS = {'face': '오른눈 후극부 정면 모식도. 노란 선이 해당 소견을 가리킵니다. 크기·위치는 설명용입니다.',
            'wide': '광각 안저 모식도(점선: 적도부, 톱니 선: 거상연). 노란 선이 해당 부위를 가리킵니다.',
            'disc': '시신경유두 확대 모식도. 노란 선이 해당 소견을 가리킵니다.',
            'oct': '중심와를 지나는 OCT B-scan 모식도(위: 유리체, 아래: 맥락막). 노란 선이 해당 소견을 가리킵니다.',
            'onh': '시신경유두를 지나는 OCT 단면 모식도. 노란 선이 해당 구조를 가리킵니다.'}


def main():
    build_specs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob('*.svg'):
        old.unlink()
    manifest = {}
    for item, panels in sorted(P.items()):
        entries = []
        for key, svg, label in panels:
            name = f"{item}-{key}.svg"
            (OUT_DIR / name).write_text(svg.svg(), encoding='utf-8')
            entries.append({'file': f'schematics/{name}', 'label': label, 'caption': CAPTIONS[key],
                            'width': svg.w, 'height': svg.h})
        manifest[item] = entries
    MANIFEST.write_text(json.dumps({'generated_by': 'code/build_lesion_schematics.py', 'items': manifest},
                                   ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(manifest)} items, {sum(len(v) for v in manifest.values())} panels → {OUT_DIR.relative_to(PROJECT)}')


if __name__ == '__main__':
    main()
