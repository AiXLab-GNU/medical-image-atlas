"""Tests for the outcome-blind ICDR grading-assessment contract."""

from pathlib import Path
import sys
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.dr_grading import (  # noqa: E402
    default_dr_grading_assessment,
    reconstruct_icdr_grade,
    validate_dr_grading_assessment,
)


def reviewed_assessment() -> dict[str, object]:
    assessment = default_dr_grading_assessment()
    assessment["image_gradability"] = "gradable"
    assessment["ungradable_reason"] = "none"
    assessment["obscuration_fraction"] = 0.0
    assessment["pdr_status"] = "absent"
    for group in ("hemorrhage_compartments", "neovascularization_sites"):
        for key in assessment[group]:
            assessment[group][key] = "absent"
    for finding in assessment["quadrant_findings"].values():
        for quadrant in finding:
            finding[quadrant] = "absent"
    return assessment


def lesion_reviews(*present: str) -> dict[str, dict[str, str]]:
    lesions = (
        "microaneurysm", "hemorrhage", "hard_exudate", "soft_exudate",
        "irma", "venous_beading", "neovascularization",
    )
    return {
        lesion: {"status": "present" if lesion in present else "absent"}
        for lesion in lesions
    }


class DrGradingContractTest(unittest.TestCase):
    def test_default_is_valid_but_not_yet_gradeable(self) -> None:
        assessment = validate_dr_grading_assessment(default_dr_grading_assessment())
        result = reconstruct_icdr_grade(lesion_reviews(), assessment)
        self.assertEqual(result["grade_status"], "indeterminate")
        self.assertIsNone(result["grade_1_to_4"])

    def test_grade_one_and_two_are_reconstructed_separately(self) -> None:
        assessment = reviewed_assessment()
        mild = reconstruct_icdr_grade(lesion_reviews("microaneurysm"), assessment)
        moderate = reconstruct_icdr_grade(
            lesion_reviews("microaneurysm", "hard_exudate"), assessment
        )
        self.assertEqual(mild["grade_1_to_4"], 1)
        self.assertEqual(moderate["grade_1_to_4"], 2)

    def test_each_421_route_can_reconstruct_grade_three(self) -> None:
        cases = (
            (
                "hemorrhage_microaneurysm_severe",
                ("q1", "q2", "q3", "q4"),
                ("microaneurysm", "hemorrhage"),
            ),
            ("venous_beading", ("q1", "q2"), ("microaneurysm", "venous_beading")),
            ("prominent_irma", ("q3",), ("microaneurysm", "irma")),
        )
        for finding, quadrants, present_lesions in cases:
            with self.subTest(finding=finding):
                assessment = reviewed_assessment()
                if "hemorrhage" in present_lesions:
                    assessment["hemorrhage_compartments"]["intraretinal"] = "present"
                for quadrant in quadrants:
                    assessment["quadrant_findings"][finding][quadrant] = "present"
                result = reconstruct_icdr_grade(lesion_reviews(*present_lesions), assessment)
                self.assertEqual(result["rule_421"]["overall"], "positive")
                self.assertEqual(result["grade_1_to_4"], 3)

    def test_nvd_or_preretinal_hemorrhage_reconstructs_grade_four(self) -> None:
        nvd = reviewed_assessment()
        nvd["neovascularization_sites"]["nvd"] = "present"
        nvd_result = reconstruct_icdr_grade(
            lesion_reviews("microaneurysm", "neovascularization"), nvd
        )
        self.assertEqual(nvd_result["grade_1_to_4"], 4)

        preretinal = reviewed_assessment()
        preretinal["hemorrhage_compartments"]["preretinal"] = "present"
        preretinal_result = reconstruct_icdr_grade(
            lesion_reviews("microaneurysm", "hemorrhage"), preretinal
        )
        self.assertEqual(preretinal_result["grade_1_to_4"], 4)

    def test_treated_stable_pdr_is_not_coerced_to_active_pdr(self) -> None:
        assessment = reviewed_assessment()
        assessment["pdr_status"] = "treated_stable"
        result = reconstruct_icdr_grade(lesion_reviews("microaneurysm"), assessment)
        self.assertEqual(result["grade_1_to_4"], 1)
        self.assertTrue(result["treated_pdr_history"])
        self.assertEqual(result["pdr_visual_evidence"], "negative")

    def test_ungradable_image_does_not_receive_a_grade(self) -> None:
        assessment = reviewed_assessment()
        assessment["image_gradability"] = "ungradable"
        assessment["ungradable_reason"] = "media_opacity"
        assessment["obscuration_fraction"] = 0.65
        result = reconstruct_icdr_grade(lesion_reviews("microaneurysm"), assessment)
        self.assertEqual(result["grade_status"], "ungradable")
        self.assertIsNone(result["grade_1_to_4"])

    def test_invalid_status_and_fraction_fail_closed(self) -> None:
        invalid = reviewed_assessment()
        invalid["quadrant_findings"]["venous_beading"]["q1"] = "likely"
        with self.assertRaisesRegex(ValueError, "venous_beading.q1"):
            validate_dr_grading_assessment(invalid)
        invalid = reviewed_assessment()
        invalid["obscuration_fraction"] = 1.2
        with self.assertRaisesRegex(ValueError, "obscuration_fraction"):
            validate_dr_grading_assessment(invalid)


if __name__ == "__main__":
    unittest.main()
