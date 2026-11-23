from pathlib import Path
import sys
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.clinical_extraction import (  # noqa: E402
    ClinicalNumber,
    extract_clinical_numbers,
    extract_clinical_numbers_hybrid,
    parse_iop,
    parse_visual_acuity,
)


class ClinicalExtractionTest(unittest.TestCase):
    def test_decimal_and_snellen_visual_acuity(self) -> None:
        decimal = parse_visual_acuity("0.8")
        self.assertEqual(decimal.status, "parsed")
        self.assertAlmostEqual(decimal.decimal, 0.8)
        self.assertAlmostEqual(decimal.logmar, 0.096910013, places=6)
        snellen = parse_visual_acuity("20/40")
        self.assertAlmostEqual(snellen.decimal, 0.5)
        self.assertAlmostEqual(snellen.logmar, 0.301029996, places=6)

    def test_non_chart_acuity_is_not_imputed(self) -> None:
        result = parse_visual_acuity("CF")
        self.assertEqual(result.status, "categorical_unconverted")
        self.assertIsNone(result.decimal)
        self.assertEqual(result.category, "CF")

    def test_iop_requires_a_unit_for_unstructured_values(self) -> None:
        self.assertEqual(parse_iop("18").status, "unit_missing")
        parsed = parse_iop("18 mmHg")
        self.assertEqual(parsed.status, "parsed")
        self.assertEqual(parsed.value_mmhg, 18.0)
        self.assertEqual(parse_iop("120 mmHg").status, "out_of_range")

    def test_text_numbers_retain_source_spans(self) -> None:
        text = "우안 IOP 18 mmHg, VA 20/40, CMT 312 µm."
        values = extract_clinical_numbers(text)
        self.assertEqual([item.kind for item in values], ["iop", "visual_acuity", "thickness"])
        self.assertEqual([text[item.start:item.end] for item in values], [item.raw for item in values])

    def test_hybrid_adapter_validates_ai_spans_and_keeps_rule_precedence(self) -> None:
        text = "IOP 18 mmHg, RNFL 92 µm"

        def ai_extractor(source: str):
            start = source.index("RNFL")
            raw = source[start:]
            return [ClinicalNumber("thickness", raw, 92.0, "um", "parsed", start, len(source), None, "ai")]

        values = extract_clinical_numbers_hybrid(text, ai_extractor)
        self.assertEqual([item.kind for item in values], ["iop", "thickness"])
        self.assertEqual([item.method for item in values], ["rule_based", "ai"])

        def invalid_span(_source: str):
            return [ClinicalNumber("thickness", "wrong", 92.0, "um", "parsed", 0, 5, None, "ai")]

        with self.assertRaisesRegex(ValueError, "span"):
            extract_clinical_numbers_hybrid(text, invalid_span)


if __name__ == "__main__":
    unittest.main()
