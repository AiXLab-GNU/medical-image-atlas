"""Feature ID → measurement function registry (pathology atlas, prostate H&E).

Input kinds
  image          H&E image only (tissue found automatically)
  label_map      H&E image with a provider annotation label map (classes per pixel)
  region_mask    H&E image with one region mask (lesion, gland or tumour annotation)
  pattern_mask   Gleason-pattern label map together with the tumour area
  ihc_region     HMWCK–AMACR IHC image with a gland or region mask
  reader_labels  slide grades from two or more readers
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

INPUT_LABELS = {
    'image': 'H&E 영상(조직 자동 검출)',
    'label_map': 'H&E 영상과 화소별 주석 지도',
    'region_mask': 'H&E 영상과 영역 mask(병변·샘·종양 주석)',
    'pattern_mask': '글리슨 패턴 주석과 종양 범위',
    'ihc_region': 'HMWCK·AMACR IHC 영상과 샘·영역 mask',
    'reader_labels': '판독의별 슬라이드 등급',
}


@dataclass(frozen=True)
class Entry:
    feature_id: str
    function: str
    input: str
    method: str
    reference: str = ''

    def load(self):
        module, name = self.function.rsplit('.', 1)
        return getattr(import_module(f'pathology_measures.{module}'), name)


_ROWS = [
    ('ft_tissue_area', 'tissue.tissue_area', 'image', 'saturation and luminance threshold against glass, holes filled'),
    ('ft_tumor_fraction', 'tissue.tumor_fraction', 'label_map', 'tumour pixels ÷ tissue pixels'),
    ('ft_tumor_area', 'tissue.tumor_area', 'label_map', 'tumour pixels × pixel area'),
    ('ft_tumor_extent', 'tissue.tumor_extent', 'label_map', 'maximum distance between tumour pixels'),
    ('ft_stroma_fraction', 'tissue.stroma_fraction', 'label_map', 'stroma pixels ÷ tissue pixels'),
    ('ft_benign_gland_fraction', 'tissue.benign_gland_fraction', 'label_map', 'benign-gland pixels ÷ tissue pixels'),
    ('ft_artifact_fraction', 'tissue.artifact_fraction', 'label_map', 'artifact pixels ÷ tissue pixels'),
    ('ft_pattern3_percent', 'tissue.pattern_percent', 'pattern_mask', 'pattern-3 pixels ÷ tumour pixels', 'ISUP 2019'),
    ('ft_pattern4_percent', 'tissue.pattern_percent', 'pattern_mask', 'pattern-4 pixels ÷ tumour pixels', 'ISUP 2019'),
    ('ft_pattern5_percent', 'tissue.pattern_percent', 'pattern_mask', 'pattern-5 pixels ÷ tumour pixels', 'ISUP 2019'),
    ('ft_gland_count', 'glands.count', 'region_mask', 'connected components of the gland mask'),
    ('ft_gland_density', 'glands.gland_density', 'region_mask', 'glands per tissue area'),
    ('ft_gland_area', 'glands.mean_area', 'region_mask', 'mean component area'),
    ('ft_gland_circularity', 'glands.circularity', 'region_mask', 'median 4π·area/perimeter² per gland'),
    ('ft_lumen_fraction', 'glands.lumen_fraction', 'region_mask', 'bright low-saturation pixels inside glands ÷ gland area'),
    ('ft_lumina_per_gland', 'glands.lumina_per_gland', 'region_mask', 'lumen components per gland (cribriform proxy)', 'ISUP 2021 cribriform definition'),
    ('ft_nuclear_density', 'nuclei.density', 'region_mask', 'haematoxylin Otsu + distance-transform watershed, size window', 'Ruifrok 2001'),
    ('ft_nuclear_area', 'nuclei.mean_area', 'region_mask', 'mean nucleus-candidate area', 'Ruifrok 2001'),
    ('ft_nuclear_area_variation', 'nuclei.area_variation', 'region_mask', 'coefficient of variation of nucleus area'),
    ('ft_hematoxylin_od', 'nuclei.hematoxylin_od', 'region_mask', 'mean haematoxylin OD after HED separation', 'Ruifrok 2001'),
    ('ft_texture_contrast', 'texture.glcm_contrast', 'region_mask', 'normalised GLCM contrast, 32 levels, 4 directions'),
    ('ft_basal_cell_coverage', 'ihc.basal_coverage', 'ihc_region', 'brown (DAB OD > 0.03) share of a 30-px gland rim, median over glands'),
    ('ft_basal_cell_presence', 'ihc.basal_cell_presence', 'ihc_region', 'basal coverage ≥ 5 % (service cut-off)'),
    ('ft_amacr_fraction', 'ihc.amacr_fraction', 'ihc_region', 'red-chromogen pixels ÷ region pixels'),
    ('ft_amacr_positivity', 'ihc.amacr_positivity', 'ihc_region', 'AMACR fraction ≥ 5 % (service cut-off)'),
    ('ft_gleason_score', 'grading.gleason_from_areas', 'pattern_mask', 'ISUP 2014 biopsy rule from pattern areas', 'ISUP 2014'),
    ('ft_isup_grade_group', 'grading.grade_group', 'pattern_mask', 'Gleason score → grade group 1–5', 'Epstein 2016'),
    ('ft_lesion_generic_presence', 'tissue.presence', 'region_mask', 'any annotated pixel'),
    ('ft_lesion_generic_area', 'tissue.lesion_area', 'region_mask', 'pixel area × calibration'),
    ('ft_lesion_generic_fraction', 'tissue.lesion_fraction', 'region_mask', 'lesion pixels ÷ tissue pixels'),
    ('ft_lesion_generic_count', 'tissue.lesion_count', 'region_mask', 'connected components'),
]

REGISTRY: dict[str, Entry] = {row[0]: Entry(*row) for row in _ROWS}
