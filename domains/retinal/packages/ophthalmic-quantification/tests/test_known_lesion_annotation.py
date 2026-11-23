from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.known_lesion_phenomics import (  # noqa: E402
    KNOWN_DR_LESIONS,
    KNOWN_LESION_MEASUREMENT_IDS,
    extract_known_lesion_measurements,
)
from ophthalmic_quantification.lesion_annotation import (  # noqa: E402
    lesion_annotation_catalog,
    quantify_annotation_file,
    quantify_annotation_document,
    rasterize_annotation_document,
    validate_annotation_document,
)
from ophthalmic_quantification.dr_grading import default_dr_grading_assessment  # noqa: E402


def document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "image": {"id": "DEMO-001", "width": 96, "height": 96},
        "lesion_reviews": {
            "microaneurysm": {"status": "present"},
            "hemorrhage": {"status": "absent"},
            "hard_exudate": {"status": "uncertain"},
        },
        "annotations": [
            {
                "id": "a1",
                "lesion_id": "microaneurysm",
                "geometry_type": "point",
                "points": [[55, 45]],
                "radius_px": 2,
                "confidence": "definite",
            },
            {
                "id": "a2",
                "lesion_id": "hard_exudate",
                "geometry_type": "polygon",
                "points": [[68, 60], [74, 60], [73, 67], [67, 66]],
                "confidence": "uncertain",
            },
        ],
    }


class KnownLesionAnnotationTest(unittest.TestCase):
    def test_catalog_covers_seven_lesions_and_three_marking_tools(self) -> None:
        catalog = lesion_annotation_catalog()
        self.assertEqual(tuple(row["lesion_id"] for row in catalog), KNOWN_DR_LESIONS)
        self.assertEqual({row["default_tool"] for row in catalog}, {"point", "polygon", "brush"})

    def test_unreviewed_and_uncertain_are_not_coerced_to_negative(self) -> None:
        masks = rasterize_annotation_document(document())
        self.assertEqual(set(masks), {"microaneurysm", "hemorrhage"})
        self.assertGreater(int(masks["microaneurysm"].sum()), 0)
        self.assertEqual(int(masks["hemorrhage"].sum()), 0)
        self.assertNotIn("hard_exudate", masks)
        self.assertEqual(set(rasterize_annotation_document(document(), include_uncertain=True)), {
            "microaneurysm", "hemorrhage", "hard_exudate"
        })

    def test_invalid_absent_annotation_fails_closed(self) -> None:
        invalid = document()
        invalid["lesion_reviews"]["microaneurysm"] = {"status": "absent"}
        with self.assertRaisesRegex(ValueError, "absent review cannot contain"):
            validate_annotation_document(invalid)

    def test_annotation_to_measurement_bank_is_deterministic(self) -> None:
        size = 96
        yy, xx = np.indices((size, size))
        fov = (yy - 48) ** 2 + (xx - 48) ** 2 <= 44**2
        disc = (yy - 48) ** 2 + (xx - 24) ** 2 <= 6**2
        fovea = (yy - 48) ** 2 + (xx - 66) ** 2 <= 2**2
        vessel = np.abs(yy - 48) <= 1
        first = quantify_annotation_document(
            document(), fov_mask=fov, disc_mask=disc, fovea_mask=fovea, vessel_mask=vessel
        )
        second = quantify_annotation_document(
            document(), fov_mask=fov, disc_mask=disc, fovea_mask=fovea, vessel_mask=vessel
        )
        self.assertEqual(len(first), 40)
        np.testing.assert_allclose(list(first.values()), list(second.values()), equal_nan=True)
        self.assertEqual(first["microaneurysm__presence"], 1.0)
        self.assertEqual(first["hemorrhage__presence"], 0.0)

    def test_twenty_metric_contract_matches_e046(self) -> None:
        mask = np.zeros((32, 32), dtype=bool)
        mask[10:13, 16:19] = True
        values = extract_known_lesion_measurements(mask, fov_mask=np.ones_like(mask))
        self.assertEqual(tuple(values), KNOWN_LESION_MEASUREMENT_IDS)

    def test_web_json_to_file_quantification_uses_json_null_for_missing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            annotation_path = root / "annotations.json"
            fov_path = root / "fov.npy"
            output_path = root / "measurements.json"
            annotation_path.write_text(json.dumps(document()), encoding="utf-8")
            np.save(fov_path, np.ones((96, 96), dtype=bool))
            quantify_annotation_file(
                annotation_path, fov_mask_path=fov_path, output_path=output_path
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["measurement_count"], 40)
            self.assertIsNone(payload["measurements"]["microaneurysm__component_area_mean_disc2"])
            self.assertEqual(payload["measurements"]["hemorrhage__presence"], 0.0)

    def test_v2_document_requires_and_preserves_grading_assessment(self) -> None:
        value = document()
        value["schema_version"] = 2
        value["grading_assessment"] = default_dr_grading_assessment()
        validated = validate_annotation_document(value)
        self.assertEqual(validated["schema_version"], 2)
        self.assertEqual(
            validated["grading_assessment"]["image_gradability"], "not_reviewed"
        )

    def test_v2_document_rejects_conflicting_neovascularization_site(self) -> None:
        value = document()
        value["schema_version"] = 2
        value["grading_assessment"] = default_dr_grading_assessment()
        value["lesion_reviews"]["neovascularization"] = {"status": "absent"}
        value["grading_assessment"]["neovascularization_sites"]["nvd"] = "present"
        with self.assertRaisesRegex(ValueError, "neovascularization"):
            validate_annotation_document(value)

    def test_v2_quantification_file_includes_fail_closed_grading_reconstruction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            value = document()
            value["schema_version"] = 2
            value["grading_assessment"] = default_dr_grading_assessment()
            annotation_path = root / "grading_annotations.json"
            fov_path = root / "fov.npy"
            output_path = root / "measurements.json"
            annotation_path.write_text(json.dumps(value), encoding="utf-8")
            np.save(fov_path, np.ones((96, 96), dtype=bool))
            quantify_annotation_file(
                annotation_path, fov_mask_path=fov_path, output_path=output_path
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 2)
            self.assertEqual(
                payload["grading_reconstruction"]["grade_status"], "indeterminate"
            )


if __name__ == "__main__":
    unittest.main()
