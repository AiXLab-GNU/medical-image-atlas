"""Feature ID → measurement function registry (mammography atlas).

Input kinds
  image            one 2D mammogram view only (landmarks are found automatically)
  image_pair       CC and MLO views of the same breast, or left and right images of the same view
  lesion_mask      lesion region mask (expert annotation or validated segmentation) with the image
  lesion_landmark  lesion mask plus the nipple and posterior-nipple-line landmarks of the view
  matched_views    the same lesion located on both CC and MLO views of one breast
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

INPUT_LABELS = {
    'image': '유방촬영 한 장(자동 경계 검출)',
    'image_pair': '같은 유방 CC·MLO 또는 좌우 같은 방향 영상 쌍',
    'lesion_mask': '병변 범위 mask와 원 영상',
    'lesion_landmark': '병변 mask와 유두·후유두선(자동 검출)',
    'matched_views': 'CC·MLO에서 짝지은 같은 병변',
}


@dataclass(frozen=True)
class Entry:
    feature_id: str
    function: str          # module.function inside mammography_measures
    input: str
    method: str
    reference: str = ''

    def load(self):
        module, name = self.function.rsplit('.', 1)
        return getattr(import_module(f'mammography_measures.{module}'), name)


_ROWS = [
    ('ft_breast_area', 'breast.breast_area', 'image', 'Otsu threshold, largest component, pectoral muscle removed'),
    ('ft_percent_density', 'breast.percent_density', 'image', 'Otsu threshold of breast intensities (dense ÷ breast)', 'Byng 1994; Keller 2012'),
    ('ft_dense_area', 'breast.dense_area', 'image', 'Otsu threshold inside the eroded breast mask', 'Keller 2012'),
    ('ft_pectoral_area', 'breast.pectoral_area', 'image', 'straight-line anterior pectoral edge (RANSAC on gradient minima)', 'Kwok 2004'),
    ('ft_pectoral_angle', 'breast.pectoral_angle', 'image', 'angle of the fitted pectoral edge to the image vertical', 'Kwok 2004'),
    ('ft_pectoral_reaches_pnl', 'breast.pectoral_reaches_pnl', 'image', 'pectoral edge reaches the nipple level', 'Eklund 1992'),
    ('ft_pnl_length', 'breast.pnl_length', 'image', 'nipple → perpendicular foot on the pectoral edge (MLO) or chest edge (CC)', 'Eklund 1992'),
    ('ft_pnl_cc_mlo_difference', 'breast.pnl_cc_mlo_difference', 'image_pair', '|PNL(CC) − PNL(MLO)|', 'Eklund 1992'),
    ('ft_mass_size', 'mass.size', 'lesion_mask', 'maximum Feret diameter'),
    ('ft_mass_area', 'mass.mass_area', 'lesion_mask', 'pixel area × calibration'),
    ('ft_mass_circularity', 'mass.circularity', 'lesion_mask', '4π·area/perimeter²', 'Rangayyan 1997'),
    ('ft_mass_solidity', 'mass.solidity', 'lesion_mask', 'area ÷ convex hull area', 'Rangayyan 1997'),
    ('ft_mass_radial_sd', 'mass.radial_sd', 'lesion_mask', 'SD of the normalised radial profile (+ Fourier high-frequency share)', 'Rangayyan 1997'),
    ('ft_mass_spiculation_index', 'mass.spiculation_index', 'lesion_mask', 'share of outer-band ridges pointing to the centre', 'Karssemeijer 1996'),
    ('ft_mass_margin_sharpness', 'mass.margin_sharpness', 'lesion_mask', 'edge gradient ÷ inside–outside difference', 'Rangayyan 1997'),
    ('ft_mass_contrast', 'mass.contrast', 'lesion_mask', '(inside − outer band) ÷ outer band SD'),
    ('ft_calc_count', 'calcification.count', 'lesion_mask', 'white top-hat spots above median + 4·MAD', 'Shen 1994'),
    ('ft_calc_extent', 'calcification.extent', 'lesion_mask', 'largest centre-to-centre distance'),
    ('ft_calc_density', 'calcification.density', 'lesion_mask', 'spots per search-region area'),
    ('ft_calc_size', 'calcification.spot_size', 'lesion_mask', 'mean and maximum spot area', 'Shen 1994'),
    ('ft_calc_size_variation', 'calcification.size_variation', 'lesion_mask', 'coefficient of variation of spot area', 'Shen 1994'),
    ('ft_calc_elongation', 'calcification.elongation', 'lesion_mask', 'share of spots with eccentricity > 0.9', 'Shen 1994'),
    ('ft_calc_branching', 'calcification.branching', 'lesion_mask', 'share of spots whose skeleton has a branch point', 'Shen 1994'),
    ('ft_calc_linearity', 'calcification.linearity', 'lesion_mask', '1 − λmin/λmax of spot-centre covariance'),
    ('ft_calc_nn_distance', 'calcification.nn_distance', 'lesion_mask', 'mean nearest-neighbour distance of spot centres'),
    ('ft_calc_contrast', 'calcification.spot_contrast', 'lesion_mask', 'mean top-hat ÷ MAD of the spots'),
    ('ft_ad_convergence_index', 'distortion.convergence_index', 'lesion_mask', 'share of annulus ridges pointing to the centre', 'Karssemeijer 1996'),
    ('ft_ad_extent', 'distortion.distortion_extent', 'lesion_mask', 'maximum Feret diameter of the marked region'),
    ('ft_asym_area', 'distortion.asymmetry_area', 'lesion_mask', 'pixel area × calibration'),
    ('ft_asym_bilateral_difference', 'distortion.bilateral_difference', 'image_pair', 'left − right percent dense area', 'Youk 2009'),
    ('ft_enh_intensity_ratio', 'enhancement.intensity_ratio', 'lesion_mask', 'lesion mean ÷ surrounding ring mean on the recombined image', 'Jochelson 2021'),
    ('ft_nme_extent', 'enhancement.nme_extent', 'lesion_mask', 'maximum Feret diameter of the enhancing region'),
    ('ft_lesion_generic_presence', 'distortion.presence', 'lesion_mask', 'any marked pixel'),
    ('ft_lesion_generic_count', 'distortion.lesion_count', 'lesion_mask', 'connected components'),
    ('ft_lesion_generic_size', 'distortion.lesion_size', 'lesion_mask', 'maximum Feret diameter'),
    ('ft_lesion_distance_nipple', 'location.distance_from_nipple', 'lesion_landmark', 'Euclidean distance from the nipple point'),
    ('ft_lesion_depth_third', 'location.depth_third', 'lesion_landmark', 'projection on the posterior nipple line, split in thirds'),
    ('ft_lesion_view_half', 'location.view_half', 'lesion_landmark', 'side of the nipple–chest line (CC lateral/medial, MLO upper/lower)'),
    ('ft_lesion_quadrant', 'location.quadrant', 'matched_views', 'CC half × MLO half'),
    ('ft_lesion_clock_position', 'location.clock_position', 'matched_views', 'angle of (CC offset, MLO offset) → clock hour'),
]

REGISTRY: dict[str, Entry] = {row[0]: Entry(*row) for row in _ROWS}
