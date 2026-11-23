# retinal-measures

Measurement functions for the P003 retinal atlas measurement list. Each function takes segmentation
outputs (masks, OCT surfaces, landmarks) or a raw image and returns a `Measurement` tagged with the
atlas feature ID. Segmentation and grading criteria are out of scope.

- Coverage: 146 of the 160 atlas measurements (`d_features_v01.csv`, `feature_role = measurement`).
- Survey and method notes: [`docs/surveys/10_retinal_measurement_algorithm_survey_v01_ko.md`](../../docs/surveys/10_retinal_measurement_algorithm_survey_v01_ko.md).
- Dependencies: numpy, scipy, scikit-image.

## Modules

| Module | Input | Measurements |
|---|---|---|
| `lesions` | 2D lesion mask, fovea/disc points | presence, count, area, size distribution, shape, extent, fovea distance, quadrant counts, distribution (Clark–Evans), vessel relation, change, turnover, clock hour, focality |
| `vessels` | vessel mask; artery/vein masks for CRAE | area/length density, caliber, tortuosity, topology, branching angle, fractal dimension, orientation, CRAE/CRVE/AVR (revised Knudtson) |
| `optic_disc` | disc, cup, PPA masks; BMO/ILM points | areas, vertical CDR, rim width profile, ISNT, notch, shape/tilt, disc–fovea geometry, RNFL defect arc, BMO-MRW |
| `oct_layers` | surface depth maps `(n_bscans, n_ascans)` | thickness maps, CST, ETDRS subfields, macular volume, choroid thickness, foveal pit/contour, RPE contour, continuity/EZ, reflectivity, layer order, peripapillary RNFL, staphyloma depth |
| `oct_lesions` | 3D/2D OCT lesion mask, surfaces | volume, height, B-scan area, en-face area, lateral diameter, centre involvement, layer location, MNV depth type, count, hole diameters, VMT attachment width, internal reflectivity, hypertransmission width |
| `octa` | en-face slab, FAZ / non-perfusion mask | vessel density, RPC density, FAZ area/shape/enlargement, CC flow deficit (Phansalkar), non-perfusion area, ischemic index |
| `atrophy` | atrophy mask | area, square-root growth rate, focality, foveal involvement |
| `choroid` | B-scan with BM and CSI | CVI (Niblack), large-vessel diameter |
| `image` | raw image | colour statistics, GLCM/LBP texture, quality descriptors, OCT signal |
| `registry` | — | feature ID → function, input kind, method, reference |

## Use

```python
from retinal_measures import Spacing, get, lesions

he = lesions.quadrant_counts(hemorrhage_mask, fovea=(1400, 2100), disc=(1300, 3400))
he.value          # {'superotemporal': 3, 'superonasal': 1, ...}

entry = get('ft_crae')
entry.function, entry.input, entry.method   # 'vessels.crae', 'av_mask', 'revised Knudtson big-6 (0.88)'
```

`status` is `ok`, `not_observed` (evaluated, nothing found) or `not_evaluable` (input insufficient);
missing evidence is never reported as 0. Pass `Spacing(x_mm, y_mm, z_um)` for physical units,
otherwise values are in pixels.

## Tests

```bash
PYTHONPATH=src ../../../../.venv/bin/python -m unittest discover -s tests
```

Synthetic inputs with known answers (circle areas, a straight line for tortuosity and fractal
dimension, flat surfaces for ETDRS thickness and volume, the Knudtson formula, FAZ circularity), and
a check that every registry ID exists in the atlas feature table.

## Limits

Method references are author–year pointers, not yet checked against the papers. Values depend on
the segmentation used upstream; these functions do not measure clinical accuracy.
