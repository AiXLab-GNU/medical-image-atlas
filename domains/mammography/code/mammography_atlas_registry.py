"""Paths and canonical G-table readers for the mammography atlas (image sources, provider figures, DMID)."""
from __future__ import annotations

import csv
import hashlib
import re
from functools import lru_cache
from pathlib import Path

DOMAIN = Path(__file__).resolve().parents[1]
ROOT = DOMAIN.parents[1]
CATALOG = DOMAIN / 'docs/surveys/mammography_atlas_catalog'
DATASETS = ROOT / 'resources/datasets'
DMID = DATASETS / 'public_mammography/dmid'
MASKED_DIR = DATASETS / 'mammography_atlas_masked_figures'
EXAMPLE_DIR = DATASETS / 'mammography_atlas_measurement_examples'
WEB_DATA = DOMAIN / 'packages/mammography-atlas-web/src/mammography_atlas_web/data'
MEASURES_SRC = DOMAIN / 'packages/mammography-measures/src'

DMID_CLASSES = {'CALC', 'CIRC', 'SPIC', 'MISC', 'ARCH', 'ASYM', 'NORM'}


def read(name: str) -> list[dict[str, str]]:
    with (CATALOG / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def image_sources() -> dict[str, dict[str, str]]:
    return {row['source_id']: row for row in read('g_image_sources_v01.csv')}


def source_record(source_id: str) -> dict[str, str]:
    row = image_sources()[source_id]
    return {'name': row['name'], 'credit': row['credit'], 'url': row['url'], 'license': row['license'],
            'license_url': row['license_url']}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def dmid_findings() -> list[dict]:
    """One row per annotated DMID finding (normal images give one row with classes ['NORM'])."""
    import pandas as pd
    table = pd.read_excel(DMID / 'provider_archives/Metadata.xlsx', header=None)
    rows = []
    for values in table.itertuples(index=False):
        image = str(values[0]).strip()
        if not re.fullmatch(r'IMG\d{3}', image):
            continue
        view_code = str(values[1]).strip().upper()
        classes = [c for c in re.split(r'[+\s]+', str(values[3]).strip().upper()) if c]
        classes = ['CALC' if c == 'CLAC' else c for c in classes]
        unknown = set(classes) - DMID_CLASSES
        if unknown:
            raise ValueError(f'{image}: unknown DMID class {unknown}')
        def num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        rows.append({'image': image, 'view': 'CC' if view_code.startswith('CC') else 'MLO',
                     'laterality': 'R' if view_code.endswith('RT') else 'L', 'tissue': str(values[2]).strip(),
                     'classes': classes, 'severity': str(values[4]).strip() if str(values[4]) != 'nan' else '',
                     'x': num(values[5]), 'y': num(values[6]), 'r': num(values[7])})
    return rows


def dmid_paths(image: str) -> dict[str, Path]:
    base = DMID / 'extracted'
    return {'image': base / 'TIFF Images/TIFF Images' / f'{image}.tif',
            'roi': base / 'ROI Masks/ROI Masks' / f'{image}.tif',
            'pixel': base / 'Pixel-level annotation/Pixel-level annotation' / f'{image}.tif',
            'report': base / 'Reports/Reports' / f'Img{image[3:]}.txt'}


def dmid_report(image: str) -> str:
    path = dmid_paths(image)['report']
    return path.read_text(encoding='utf-8', errors='replace') if path.is_file() else ''


def dmid_composition(image: str) -> str:
    """ACR composition letter written in the provider report (e.g. 'ACR B'), or ''."""
    match = re.search(r'ACR\s*-?\s*([A-D])\b', dmid_report(image), re.I)
    return match.group(1).lower() if match else ''
