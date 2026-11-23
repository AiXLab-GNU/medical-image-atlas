"""Paths and canonical G-table readers for the pathology atlas (prostate H&E: PRECISE, SICAPv2)."""
from __future__ import annotations

import csv
import hashlib
import re
from functools import lru_cache
from pathlib import Path

DOMAIN = Path(__file__).resolve().parents[1]
ROOT = DOMAIN.parents[1]
CATALOG = DOMAIN / 'docs/surveys/pathology_atlas_catalog'
DATASETS = ROOT / 'resources/datasets'
PRECISE = DATASETS / 'public_pathology/precise'
SICAP = DATASETS / 'public_pathology/sicapv2/SICAPv2'
MASKED_DIR = DATASETS / 'pathology_atlas_masked_figures'
EXAMPLE_DIR = DATASETS / 'pathology_atlas_measurement_examples'
WEB_DATA = DOMAIN / 'packages/pathology-atlas-web/src/pathology_atlas_web/data'
MEASURES_SRC = DOMAIN / 'packages/pathology-measures/src'

PRECISE_CLASSES = {0: 'background', 1: 'tumor', 2: 'benign_gland', 3: 'artifact', 4: 'hgpin',
                   5: 'intraductal_carcinoma', 6: 'atypical_intraductal_proliferation', 7: 'stroma'}
SICAP_CLASSES = {0: 'non_cancerous', 3: 'gleason_3', 4: 'gleason_4', 5: 'gleason_5'}   # actual mask values (readme says 1·2·3)


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


# ------------------------------------------------------------------ PRECISE

@lru_cache(maxsize=1)
def precise_participants() -> dict[str, dict[str, str]]:
    with (PRECISE / 'participants.csv').open(encoding='utf-8', newline='') as handle:
        return {row['IMAGE_NAME']: row for row in csv.DictReader(handle)}


def precise_paths(image_name: str) -> dict[str, Path]:
    sub, ses = image_name.split('_')
    base = PRECISE / 'extracted/data' / sub / ses
    return {'image': base / 'wsi_h-e' / f'{image_name}_h-e.ome.tif', 'mask': base / 'wsi_h-e' / f'{image_name}_h-e_mask.ome.tif',
            'ihc': base / 'wsi_hmwck-amacr' / f'{image_name}_hmwck-amacr.ome.tif',
            'ihc_mask': base / 'wsi_hmwck-amacr' / f'{image_name}_hmwck-amacr_mask.ome.tif'}


def precise_mpp(image_name: str) -> float:
    import tifffile
    with tifffile.TiffFile(precise_paths(image_name)['image']) as tif:
        match = re.search(r'PhysicalSizeX="([0-9.]+)"', tif.ome_metadata or '')
    if not match:
        raise ValueError(f'{image_name}: no PhysicalSizeX in OME metadata')
    return float(match.group(1))


def precise_level(image_name: str, level: int, kind: str = 'image', window=None):
    """Pyramid level as an array; window = (r0, r1, c0, c1) in that level's pixels reads only that region."""
    import tifffile
    import zarr
    store = tifffile.imread(precise_paths(image_name)[kind], aszarr=True, level=level)
    try:
        arr = zarr.open(store, mode='r')
        return arr[:] if window is None else arr[window[0]:window[1], window[2]:window[3]]
    finally:
        store.close()


def precise_level_shape(image_name: str, level: int, kind: str = 'image'):
    import tifffile
    with tifffile.TiffFile(precise_paths(image_name)[kind]) as tif:
        return tif.series[0].levels[level].shape


# ------------------------------------------------------------------ SICAPv2

def sicap_paths(patch: str) -> dict[str, Path]:
    return {'image': SICAP / 'images' / f'{patch}.jpg', 'mask': SICAP / 'masks' / f'{patch}.png'}


@lru_cache(maxsize=1)
def sicap_table() -> list[dict]:
    """Test-split patch labels (majority Gleason label and cribriform flag)."""
    import pandas as pd
    rows = []
    for name in ('Test.xlsx',):
        t = pd.read_excel(SICAP / 'partition/Test' / name)
        rows += t.to_dict('records')
    return rows


@lru_cache(maxsize=1)
def sicap_cribriform() -> list[dict]:
    import pandas as pd
    return pd.read_excel(SICAP / 'partition/Test/TestCribfriform.xlsx').to_dict('records')
