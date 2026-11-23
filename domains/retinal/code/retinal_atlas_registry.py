"""Canonical image-provenance registry of the retinal atlas (read by every figure / example builder).

Two hand-authored tables in ``docs/surveys/retinal_atlas_catalog/`` are the single source of truth:

* ``g_image_sources_v01.csv`` – datasets and articles that supply images (licence, citation, local path)
* ``g_provider_figures_v01.csv`` – published article figure files kept once under
  ``resources/datasets/retinal_atlas_modality_figures/provider_figures/`` with their pinned SHA-256

The builders used to carry their own dictionaries; they now call the functions below so that a source,
licence or checksum is written in exactly one place.
"""
from __future__ import annotations

import csv
import hashlib
from functools import lru_cache
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
CATALOG = PROJECT / 'docs/surveys/retinal_atlas_catalog'
IMAGE_SOURCES = CATALOG / 'g_image_sources_v01.csv'
PROVIDER_FIGURES = CATALOG / 'g_provider_figures_v01.csv'
PROVIDER_DIR = ROOT / 'resources/datasets/retinal_atlas_modality_figures/provider_figures'
USERS = {'masked_figures', 'modality_figures', 'measurement_examples'}


def _read(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def image_sources() -> dict[str, dict]:
    """source_id → row of ``g_image_sources_v01.csv``."""
    rows = _read(IMAGE_SOURCES)
    out = {r['source_id']: r for r in rows}
    if len(out) != len(rows):
        raise ValueError('duplicate source_id in g_image_sources_v01.csv')
    return out


def source_record(source_id: str) -> dict:
    """Credit record in the shape the builders write into their manifests."""
    r = image_sources()[source_id]
    return {'name': r['name'], 'credit': r['credit'], 'url': r['url'], 'license': r['license'],
            'license_url': r['license_url']}


def source_records() -> dict[str, dict]:
    return {k: source_record(k) for k in image_sources()}


def article_record(source_id: str) -> dict:
    """Panel-free citation used by the modality-figure crops (the panel is written separately)."""
    r = image_sources()[source_id]
    return {'credit': r['citation'], 'title': r['title'], 'url': r['url']}


@lru_cache(maxsize=1)
def provider_figures() -> dict[str, dict]:
    """provider file → row of ``g_provider_figures_v01.csv`` (``used_by`` split into a set)."""
    rows = _read(PROVIDER_FIGURES)
    out = {}
    for r in rows:
        r = dict(r, used_by=set(filter(None, r['used_by'].split(';'))))
        if r['file'] in out:
            raise ValueError(f"duplicate provider figure {r['file']}")
        if not r['used_by'] <= USERS:
            raise ValueError(f"unknown used_by for {r['file']}: {r['used_by'] - USERS}")
        out[r['file']] = r
    return out


def provider_figures_for(user: str) -> dict[str, dict]:
    return {k: v for k, v in provider_figures().items() if user in v['used_by']}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provider_path(name: str, *, check: bool = True) -> Path:
    """Path of a registered provider figure; the file must match its pinned checksum."""
    row = provider_figures()[name]
    path = PROVIDER_DIR / name
    if check and sha256(path) != row['sha256']:
        raise ValueError(f'provider figure changed: {name}')
    return path
