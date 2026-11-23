"""Feature ID → measurement function registry.

Each entry names the atlas feature it computes, the function, the input it needs, the method
in one phrase and the method reference (author year; not yet verified against the paper).

Input kinds
  image          raw fundus/OCT/OCTA image only (no segmentation)
  vessel_mask    binary vessel map (fundus or OCTA)
  av_mask        separate artery and vein masks + disc centre/radius
  lesion_mask    binary lesion map, optionally fovea/disc landmarks
  disc_cup_mask  optic disc (and cup) masks
  landmarks      disc centre and fovea centre points
  oct_surfaces   segmented OCT boundary depth maps
  oct_mask       3D/2D OCT lesion or layer-visibility mask (+ surfaces when stated)
  octa_slab      OCTA en-face slab or FAZ / non-perfusion mask
  profile        1D thickness profile with a reference
  longitudinal   the same input at two visits with an interval
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class Entry:
    feature_id: str
    function: str          # module.function inside retinal_measures
    input: str
    method: str
    reference: str = ''

    def load(self):
        module, name = self.function.rsplit('.', 1)
        return getattr(import_module(f'retinal_measures.{module}'), name)


_ROWS = [
    # --- generic lesion (fundus/en-face masks) ---
    ('ft_lesion_generic_presence', 'lesions.presence', 'lesion_mask', 'any connected component ≥ min area'),
    ('ft_lesion_generic_count', 'lesions.count', 'lesion_mask', 'connected components (8-connectivity)'),
    ('ft_lesion_generic_area', 'lesions.area', 'lesion_mask', 'pixel area × calibration'),
    ('ft_lesion_size_distribution', 'lesions.size_distribution', 'lesion_mask', 'component area quantiles'),
    ('ft_lesion_generic_shape', 'lesions.shape', 'lesion_mask', 'circularity, solidity, eccentricity'),
    ('ft_lesion_generic_extent', 'lesions.extent', 'lesion_mask', 'largest Feret diameter'),
    ('ft_lesion_generic_position', 'lesions.position', 'lesion_mask', 'area-weighted centroid'),
    ('ft_lesion_fovea_distance', 'lesions.fovea_distance', 'lesion_mask', 'Euclidean distance transform to fovea'),
    ('ft_lesion_radial_position', 'lesions.radial_position', 'lesion_mask', 'radial distance of components'),
    ('ft_lesion_regional_fraction', 'lesions.regional_fraction', 'lesion_mask', 'lesion share inside a circle'),
    ('ft_lesion_spatial_dispersion', 'lesions.spatial_dispersion', 'lesion_mask', 'spread of components in fovea–disc frame'),
    ('ft_lesion_generic_distribution', 'lesions.distribution_pattern', 'lesion_mask', 'nearest-neighbour index', 'Clark & Evans 1954'),
    ('ft_lesion_vessel_relation', 'lesions.vessel_relation', 'lesion_mask', 'distance to nearest vessel pixel'),
    ('ft_lesion_generic_change', 'lesions.change', 'longitudinal', 'area difference per interval'),
    ('ft_lesion_generic_volume', 'oct_lesions.volume', 'oct_mask', 'voxel count × voxel volume'),
    ('ft_lesion_generic_height', 'oct_lesions.height', 'oct_mask', 'maximal axial extent per A-scan'),
    ('ft_vascular_change_extent', 'lesions.quadrant_occupancy', 'lesion_mask', 'quadrants containing the finding'),
    # --- lesion-specific (DR) ---
    ('ft_ma_presence', 'lesions.presence', 'lesion_mask', 'any component'),
    ('ft_ma_count', 'lesions.count', 'lesion_mask', 'connected components'),
    ('ft_ma_turnover', 'lesions.turnover', 'longitudinal', 'formation/disappearance by overlap matching', 'Nunes 2009'),
    ('ft_ma_distance_fovea', 'lesions.fovea_distance', 'lesion_mask', 'distance to fovea'),
    ('ft_hem_count_quadrant', 'lesions.quadrant_counts', 'lesion_mask', 'components per fovea-centred quadrant'),
    ('ft_hem_area', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_flame_hem_count', 'lesions.count', 'lesion_mask', 'connected components'),
    ('ft_prh_area', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_vb_quadrants', 'lesions.quadrant_occupancy', 'lesion_mask', 'quadrants containing beading'),
    ('ft_vb_caliber_variation', 'vessels.caliber_variation', 'vessel_mask', 'coefficient of variation of width along vein'),
    ('ft_irma_presence', 'lesions.presence', 'lesion_mask', 'any component'),
    ('ft_irma_quadrants', 'lesions.quadrant_occupancy', 'lesion_mask', 'quadrants containing IRMA'),
    ('ft_nvd_presence', 'lesions.presence', 'lesion_mask', 'any component'),
    ('ft_nvd_area', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_nve_presence', 'lesions.presence', 'lesion_mask', 'any component'),
    ('ft_nve_area', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_he_area', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_he_distance_fovea', 'lesions.fovea_distance', 'lesion_mask', 'minimum distance to fovea'),
    ('ft_cws_count', 'lesions.count', 'lesion_mask', 'connected components'),
    ('ft_cws_area', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_laser_scar_extent', 'lesions.count', 'lesion_mask', 'connected scar components'),
    ('ft_disc_hem_location', 'lesions.clock_hour', 'lesion_mask', 'clock hour around disc centre'),
    # --- AMD / macula ---
    ('ft_drusen_max_size', 'lesions.extent', 'lesion_mask', 'largest component diameter'),
    ('ft_drusen_area', 'lesions.area', 'lesion_mask', 'pixel area within the grid'),
    ('ft_drusen_volume', 'oct_lesions.volume', 'oct_mask', 'RPE–BM elevation volume', 'Gregori 2011'),
    ('ft_drusen_height', 'oct_lesions.height', 'oct_mask', 'maximal RPE elevation'),
    ('ft_sdd_extent', 'lesions.area', 'lesion_mask', 'pixel area'),
    ('ft_irf_presence', 'oct_lesions.presence', 'oct_mask', 'any voxel'),
    ('ft_irf_volume', 'oct_lesions.volume', 'oct_mask', 'voxel volume'),
    ('ft_irf_bscan_area', 'oct_lesions.bscan_area', 'oct_mask', 'largest B-scan cross-section'),
    ('ft_irf_layer', 'oct_lesions.layer_location', 'oct_mask', 'voxel share between surfaces'),
    ('ft_irf_center_involvement', 'oct_lesions.center_involvement', 'oct_mask', 'projection inside central 1 mm'),
    ('ft_srf_presence', 'oct_lesions.presence', 'oct_mask', 'any voxel'),
    ('ft_srf_height', 'oct_lesions.height', 'oct_mask', 'maximal axial extent'),
    ('ft_srf_volume', 'oct_lesions.volume', 'oct_mask', 'voxel volume'),
    ('ft_ped_height', 'oct_lesions.height', 'oct_mask', 'maximal axial extent'),
    ('ft_ped_diameter', 'oct_lesions.lateral_diameter', 'oct_mask', 'widest lateral extent'),
    ('ft_ped_volume', 'oct_lesions.volume', 'oct_mask', 'voxel volume'),
    ('ft_ped_internal_reflectivity', 'oct_lesions.internal_reflectivity', 'oct_mask', 'mean intensity ratio to reference'),
    ('ft_drusen_reflectivity', 'oct_lesions.internal_reflectivity', 'oct_mask', 'mean intensity ratio to reference'),
    ('ft_mnv_type', 'oct_lesions.depth_category', 'oct_mask', 'voxel share above/below RPE'),
    ('ft_mnv_lesion_area', 'oct_lesions.enface_area', 'oct_mask', 'en-face projection area'),
    ('ft_polyp_count', 'oct_lesions.lesion_count', 'oct_mask', '3D connected components'),
    ('ft_hrf_count', 'oct_lesions.lesion_count', 'oct_mask', 'connected components'),
    ('ft_shrm_thickness', 'oct_lesions.height', 'oct_mask', 'maximal axial extent'),
    ('ft_dril_extent', 'oct_lesions.lateral_diameter', 'oct_mask', 'widest horizontal extent', 'Sun 2014'),
    ('ft_ez_continuity', 'oct_layers.layer_continuity', 'oct_mask', 'gaps in per-A-scan EZ visibility'),
    ('ft_elm_continuity', 'oct_layers.layer_continuity', 'oct_mask', 'gaps in per-A-scan ELM visibility'),
    ('ft_layer_continuity_generic', 'oct_layers.layer_continuity', 'oct_mask', 'gaps in per-A-scan visibility'),
    ('ft_ez_preserved_area', 'oct_layers.ez_preserved', 'oct_mask', 'en-face EZ area', 'Birch 2011'),
    ('ft_ez_preserved_fraction', 'oct_layers.ez_preserved', 'oct_mask', 'visible A-scan fraction'),
    ('ft_ez_disruption_width', 'oct_layers.ez_preserved', 'oct_mask', 'widest gap on a B-scan'),
    ('ft_ez_loss_area', 'oct_lesions.enface_area', 'oct_mask', 'en-face projection area'),
    ('ft_hypertd_width', 'oct_lesions.transmission_width', 'oct_mask', 'greatest linear dimension on sub-RPE slab', 'Liu 2019 / CAM'),
    ('ft_erm_extent', 'oct_lesions.enface_area', 'oct_mask', 'en-face projection area'),
    ('ft_vmt_attachment_width', 'oct_lesions.attachment_width', 'oct_surfaces', 'hyaloid–ILM contact width', 'Duker 2013 (IVTS)'),
    ('ft_mh_min_diameter', 'oct_lesions.hole_diameters', 'oct_mask', 'narrowest hole width', 'Duker 2013 (IVTS)'),
    ('ft_mh_base_diameter', 'oct_lesions.hole_diameters', 'oct_mask', 'hole width at RPE level'),
    # --- atrophy ---
    ('ft_atrophy_area', 'atrophy.area', 'lesion_mask', 'pixel area'),
    ('ft_atrophy_growth_rate', 'atrophy.growth_rate', 'longitudinal', 'square-root area change per year', 'Feuer 2013'),
    ('ft_atrophy_focality', 'atrophy.focality', 'lesion_mask', 'unifocal / multifocal by components'),
    ('ft_atrophy_foveal_involvement', 'atrophy.foveal_involvement', 'lesion_mask', 'mask covers fovea point'),
    ('ft_ppa_area', 'optic_disc.ppa_area', 'disc_cup_mask', 'pixel area'),
    # --- optic disc ---
    ('ft_disc_area', 'optic_disc.disc_area', 'disc_cup_mask', 'pixel area'),
    ('ft_disc_diameter', 'optic_disc.disc_diameter', 'disc_cup_mask', 'bounding extent'),
    ('ft_cup_area', 'optic_disc.cup_area', 'disc_cup_mask', 'pixel area'),
    ('ft_cdr_vertical', 'optic_disc.cup_disc_ratio', 'disc_cup_mask', 'vertical cup / disc extent'),
    ('ft_rim_area', 'optic_disc.rim_area', 'disc_cup_mask', 'disc minus cup area'),
    ('ft_isnt_pattern', 'optic_disc.isnt_pattern', 'disc_cup_mask', 'sector mean rim width order', 'Jonas 1988'),
    ('ft_cupping_notch', 'optic_disc.rim_notch', 'disc_cup_mask', 'focal radial rim thinning'),
    ('ft_disc_shape', 'optic_disc.disc_shape', 'disc_cup_mask', 'ellipse fit'),
    ('ft_disc_tilt_ratio', 'optic_disc.tilt_ratio', 'disc_cup_mask', 'major / minor axis ratio'),
    ('ft_disc_fovea_distance', 'optic_disc.disc_fovea_geometry', 'landmarks', 'centre distance (DD)'),
    ('ft_disc_fovea_angle', 'optic_disc.disc_fovea_geometry', 'landmarks', 'angle to horizontal'),
    ('ft_bmo_mrw', 'optic_disc.bmo_mrw', 'oct_surfaces', 'shortest BMO-to-ILM distance', 'Chauhan 2013'),
    ('ft_rd_extent', 'lesions.field_fraction', 'lesion_mask', 'detached share of the field'),
    ('ft_rd_macula_status', 'lesions.involves_point', 'lesion_mask', 'detachment covers fovea'),
    ('ft_mh_vmt_status', 'oct_lesions.attachment_width', 'oct_surfaces', 'hyaloid–ILM contact present'),
    ('ft_rnfl_defect_angle', 'optic_disc.rnfl_defect_angle', 'profile', 'widest arc below reference'),
    # --- OCT layers ---
    ('ft_central_subfield_thickness', 'oct_layers.central_subfield_thickness', 'oct_surfaces', 'ILM–BM mean inside 1 mm', 'ETDRS grid'),
    ('ft_etdrs_subfield_thickness', 'oct_layers.etdrs_thickness', 'oct_surfaces', 'nine ETDRS subfield means', 'ETDRS grid'),
    ('ft_macular_volume', 'oct_layers.macular_volume', 'oct_surfaces', 'thickness integral in 6 mm circle'),
    ('ft_layer_thickness_generic', 'oct_layers.layer_thickness', 'oct_surfaces', 'mean surface difference'),
    ('ft_gcipl_thickness', 'oct_layers.layer_thickness', 'oct_surfaces', 'RNFL/GCL to IPL/INL'),
    ('ft_onl_thickness', 'oct_layers.layer_thickness', 'oct_surfaces', 'OPL/ONL to ELM'),
    ('ft_os_length', 'oct_layers.layer_thickness', 'oct_surfaces', 'EZ to interdigitation'),
    ('ft_rpe_bm_thickness', 'oct_layers.layer_thickness', 'oct_surfaces', 'RPE to BM'),
    ('ft_rnfl_thickness_macular', 'oct_layers.layer_thickness', 'oct_surfaces', 'ILM to RNFL/GCL'),
    ('ft_rnfl_thickness_peripapillary', 'oct_layers.rnfl_peripapillary', 'oct_surfaces', '3.46 mm circle TSNIT profile'),
    ('ft_disc_edema_rnfl', 'oct_layers.rnfl_peripapillary', 'oct_surfaces', '3.46 mm circle mean RNFL'),
    ('ft_choroid_thickness_map', 'oct_layers.layer_thickness', 'oct_surfaces', 'BM to CSI'),
    ('ft_choroid_thickness_subfoveal', 'oct_layers.subfoveal_choroid_thickness', 'oct_surfaces', 'BM–CSI at fovea', 'Spaide 2008 (EDI)'),
    ('ft_foveal_pit_shape', 'oct_layers.foveal_pit', 'oct_surfaces', 'ILM pit depth, width, slope'),
    ('ft_foveal_contour', 'oct_layers.foveal_contour', 'oct_surfaces', 'pit / shallow / inverted from depth'),
    ('ft_rpe_contour', 'oct_layers.surface_contour', 'oct_surfaces', 'RMS deviation from quadratic baseline'),
    ('ft_layer_order', 'oct_layers.layer_order', 'oct_surfaces', 'surface ordering per A-scan'),
    ('ft_layer_reflectivity_generic', 'oct_layers.layer_reflectivity', 'oct_surfaces', 'mean intensity normalised vitreous→RPE'),
    ('ft_staphyloma_depth', 'oct_layers.staphyloma_depth', 'oct_surfaces', 'BM sag below chord'),
    # --- choroid ---
    ('ft_choroidal_vascularity_index', 'choroid.vascularity_index', 'oct_surfaces', 'Niblack luminal / total area', 'Agrawal 2016'),
    ('ft_haller_vessel_diameter', 'choroid.large_vessel_diameter', 'oct_surfaces', 'max inscribed diameter in outer choroid'),
    # --- vessels (fundus / OCTA) ---
    ('ft_vessel_area_density', 'vessels.area_density', 'vessel_mask', 'vessel pixels / field'),
    ('ft_vessel_pixel_count', 'vessels.pixel_count', 'vessel_mask', 'mask and skeleton pixel counts'),
    ('ft_vessel_length_density', 'vessels.length_density', 'vessel_mask', 'skeleton length / field area'),
    ('ft_vessel_caliber', 'vessels.caliber', 'vessel_mask', '2 × distance transform on skeleton'),
    ('ft_vessel_caliber_variability', 'vessels.caliber_variability', 'vessel_mask', 'CV of skeleton widths'),
    ('ft_vessel_tortuosity', 'vessels.tortuosity', 'vessel_mask', 'arc / chord per segment', 'Hart 1999'),
    ('ft_vessel_path_length', 'vessels.path_length', 'vessel_mask', 'segment arc length'),
    ('ft_vessel_topology', 'vessels.topology', 'vessel_mask', 'branch and end points per area'),
    ('ft_vessel_connectivity', 'vessels.connectivity', 'vessel_mask', 'largest-component share'),
    ('ft_branching_angle', 'vessels.branching_angle', 'vessel_mask', 'angle between daughter arms', 'Zamir 1978'),
    ('ft_fractal_dimension', 'vessels.fractal_dimension', 'vessel_mask', 'box-counting dimension', 'Mainster 1990'),
    ('ft_vessel_orientation', 'vessels.orientation', 'vessel_mask', 'orientation histogram entropy'),
    ('ft_vessel_regional_density', 'vessels.regional_density', 'vessel_mask', 'density in concentric rings'),
    ('ft_crae', 'vessels.crae', 'av_mask', 'revised Knudtson big-6 (0.88)', 'Knudtson 2003'),
    ('ft_crve', 'vessels.crve', 'av_mask', 'revised Knudtson big-6 (0.95)', 'Knudtson 2003'),
    ('ft_avr', 'vessels.avr', 'av_mask', 'CRAE / CRVE', 'Knudtson 2003'),
    # --- OCTA ---
    ('ft_octa_vessel_density_scp', 'octa.vessel_density', 'octa_slab', 'binarised perfusion density'),
    ('ft_octa_vessel_density_dcp', 'octa.vessel_density', 'octa_slab', 'binarised perfusion density'),
    ('ft_rpc_density', 'octa.rpc_density', 'octa_slab', 'density in peripapillary annulus'),
    ('ft_faz_area', 'octa.faz_area', 'octa_slab', 'FAZ mask area'),
    ('ft_faz_circularity', 'octa.faz_shape', 'octa_slab', '4πA/P², perimeter, acircularity'),
    ('ft_faz_enlargement', 'octa.faz_enlargement', 'longitudinal', 'FAZ area change per year'),
    ('ft_cc_flow_deficit', 'octa.flow_deficit', 'octa_slab', 'Phansalkar local threshold FD%', 'Spaide 2016; Chu 2019'),
    ('ft_nonperfusion_area', 'octa.nonperfusion', 'octa_slab', 'non-perfused mask area'),
    ('ft_ischemic_index', 'octa.nonperfusion', 'octa_slab', 'non-perfused / gradable field'),
    # --- whole image ---
    ('ft_image_color_stats', 'image.color_stats', 'image', 'channel mean, SD, percentiles in FOV'),
    ('ft_image_texture', 'image.texture', 'image', 'GLCM + LBP entropy', 'Haralick 1973; Ojala 2002'),
    ('ft_image_quality', 'image.quality', 'image', 'sharpness, contrast, illumination descriptors'),
    ('ft_oct_signal_strength', 'image.oct_signal', 'image', 'signal over background noise (dB)'),
]

REGISTRY: dict[str, Entry] = {}
for row in _ROWS:
    entry = Entry(*row)
    if entry.feature_id in REGISTRY:
        raise ValueError(f'duplicate registry entry {entry.feature_id}')
    REGISTRY[entry.feature_id] = entry

INPUT_LABELS = {
    'image': '영상만', 'vessel_mask': '혈관 mask', 'av_mask': '동·정맥 mask', 'lesion_mask': '병변 mask',
    'disc_cup_mask': '유두·컵 mask', 'landmarks': '유두·중심와 위치', 'oct_surfaces': 'OCT 경계면',
    'oct_mask': 'OCT 병변 mask', 'octa_slab': 'OCTA 슬랩', 'profile': '두께 프로파일',
    'longitudinal': '두 시점 입력',
}


def get(feature_id: str) -> Entry:
    return REGISTRY[feature_id]


def as_records() -> list[dict]:
    return [{'feature_id': e.feature_id, 'function': e.function, 'input': e.input,
             'method': e.method, 'reference': e.reference} for e in REGISTRY.values()]
