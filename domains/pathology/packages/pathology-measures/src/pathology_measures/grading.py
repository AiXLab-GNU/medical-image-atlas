"""Gleason score and ISUP grade group from Gleason-pattern areas, and inter-reader agreement.

Rules follow the ISUP 2014 consensus: on needle biopsy the score is the most extensive pattern plus the highest
remaining pattern (any amount); on radical prostatectomy it is the most and the second most extensive pattern,
where a second pattern below 5 % is ignored unless it is of higher grade. Grade groups: ≤6 → 1, 3+4 → 2, 4+3 → 3,
8 → 4, 9–10 → 5.
"""
from __future__ import annotations

import numpy as np

from ._common import Measurement


def gleason_from_areas(areas: dict[int, float], specimen: str = 'biopsy', minor_cutoff: float = 0.05) -> Measurement:
    """``areas`` maps pattern (3, 4, 5) to area (any unit). Returns 'p+s' or not_observed when no tumour."""
    present = {p: float(a) for p, a in areas.items() if p in (3, 4, 5) and a > 0}
    total = sum(present.values())
    if total == 0:
        return Measurement('ft_gleason_score', None, 'category', 'not_observed', '종양 패턴 없음')
    ordered = sorted(present, key=lambda p: (-present[p], -p))
    primary = ordered[0]
    rest = [p for p in present if p != primary]
    if not rest:
        secondary = primary
    elif specimen == 'biopsy':
        secondary = max(rest)                                   # highest remaining pattern, any amount
    else:
        second = max(rest, key=lambda p: present[p])
        if present[second] / total < minor_cutoff and second < primary:
            secondary = primary
        else:
            secondary = second
    shares = {p: round(100 * a / total, 1) for p, a in present.items()}
    return Measurement('ft_gleason_score', f'{primary}+{secondary}', 'category',
                       note='생검 규칙(가장 많은 패턴 + 가장 높은 나머지 패턴)' if specimen == 'biopsy' else '절제 규칙',
                       detail={'pattern_percent': shares, 'primary': primary, 'secondary': secondary})


def grade_group(score: str | None) -> Measurement:
    if not score:
        return Measurement('ft_isup_grade_group', None, 'category', 'not_observed')
    p, s = (int(x) for x in score.split('+'))
    total = p + s
    if total <= 6:
        gg = 1
    elif total == 7:
        gg = 2 if p == 3 else 3
    elif total == 8:
        gg = 4
    else:
        gg = 5
    return Measurement('ft_isup_grade_group', gg, 'category')


def kappa(a, b, categories, weights: str | None = None) -> float:
    """Cohen's kappa between two raters; ``weights`` None, 'linear' or 'quadratic'."""
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    m = np.zeros((k, k))
    for x, y in zip(a, b):
        m[idx[x], idx[y]] += 1
    n = m.sum()
    if n == 0:
        return float('nan')
    i, j = np.indices((k, k))
    if weights == 'quadratic':
        w = ((i - j) / max(k - 1, 1)) ** 2
    elif weights == 'linear':
        w = np.abs(i - j) / max(k - 1, 1)
    else:
        w = (i != j).astype(float)
    expected = np.outer(m.sum(1), m.sum(0)) / n
    denom = (w * expected).sum()
    return float(1 - (w * m).sum() / denom) if denom else float('nan')


def confusion(a, b, categories) -> list[list[int]]:
    idx = {c: i for i, c in enumerate(categories)}
    m = [[0] * len(categories) for _ in categories]
    for x, y in zip(a, b):
        m[idx[x]][idx[y]] += 1
    return m
