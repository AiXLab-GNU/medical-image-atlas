"""Fail-closed structured extraction of ophthalmic clinical quantities."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from collections.abc import Callable, Iterable


NON_CHART_ACUITIES = {"CF", "HM", "LP", "NLP"}


@dataclass(frozen=True, slots=True)
class VisualAcuity:
    raw: str
    status: str
    decimal: float | None
    logmar: float | None
    notation: str
    category: str | None = None


@dataclass(frozen=True, slots=True)
class IntraocularPressure:
    raw: str
    status: str
    value_mmhg: float | None
    source_unit: str | None


@dataclass(frozen=True, slots=True)
class ClinicalNumber:
    kind: str
    raw: str
    value: float | None
    unit: str
    status: str
    start: int
    end: int
    laterality: str | None = None
    method: str = "rule_based"


def parse_visual_acuity(value: object) -> VisualAcuity:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return VisualAcuity(raw, "missing", None, None, "unknown")
    normalized = raw.upper().replace(" ", "")
    if normalized in NON_CHART_ACUITIES:
        return VisualAcuity(raw, "categorical_unconverted", None, None, "category", normalized)
    fraction = re.fullmatch(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", normalized)
    try:
        if fraction:
            numerator, denominator = (float(item) for item in fraction.groups())
            decimal = numerator / denominator if denominator > 0 else float("nan")
            notation = "snellen_fraction"
        else:
            decimal = float(normalized)
            notation = "decimal"
    except ValueError:
        return VisualAcuity(raw, "unparsed", None, None, "unknown")
    if not math.isfinite(decimal) or not 0 < decimal <= 4:
        return VisualAcuity(raw, "out_of_range", None, None, notation)
    return VisualAcuity(raw, "parsed", decimal, -math.log10(decimal), notation)


def parse_iop(value: object, *, assumed_unit: str | None = None) -> IntraocularPressure:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return IntraocularPressure(raw, "missing", None, None)
    match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*([A-Za-z]+)?\s*", raw)
    if not match:
        return IntraocularPressure(raw, "unparsed", None, None)
    number, embedded_unit = match.groups()
    unit = embedded_unit or assumed_unit
    if unit is None:
        return IntraocularPressure(raw, "unit_missing", None, None)
    if unit.casefold() != "mmhg":
        return IntraocularPressure(raw, "unsupported_unit", None, unit)
    pressure = float(number)
    if not 0 <= pressure <= 80:
        return IntraocularPressure(raw, "out_of_range", None, "mmHg")
    return IntraocularPressure(raw, "parsed", pressure, "mmHg")


_LATERALITY = r"(?:(?P<laterality>우안|좌안|OD|OS|R|L)\s*)?"
_TEXT_PATTERNS = (
    (
        "iop",
        re.compile(_LATERALITY + r"(?:IOP|안압)\s*[:=]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mmHg)", re.IGNORECASE),
    ),
    (
        "visual_acuity",
        re.compile(_LATERALITY + r"(?:BCVA|UCVA|VA|시력)\s*[:=]?\s*(?P<value>\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)", re.IGNORECASE),
    ),
    (
        "thickness",
        re.compile(_LATERALITY + r"(?:CMT|CST|두께|thickness)\s*[:=]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>µm|μm|um)", re.IGNORECASE),
    ),
)


def extract_clinical_numbers(text: object) -> tuple[ClinicalNumber, ...]:
    source = "" if text is None else str(text)
    records: list[ClinicalNumber] = []
    for kind, pattern in _TEXT_PATTERNS:
        for match in pattern.finditer(source):
            raw = match.group(0)
            laterality = match.groupdict().get("laterality")
            if kind == "visual_acuity":
                parsed = parse_visual_acuity(match.group("value"))
                value = parsed.decimal
                unit = "decimal_acuity"
                status = parsed.status
            elif kind == "iop":
                parsed_iop = parse_iop(f"{match.group('value')} {match.group('unit')}")
                value = parsed_iop.value_mmhg
                unit = "mmHg"
                status = parsed_iop.status
            else:
                value = float(match.group("value"))
                unit = "um"
                status = "parsed"
            records.append(
                ClinicalNumber(kind, raw, value, unit, status, match.start(), match.end(), laterality)
            )
    return tuple(sorted(records, key=lambda item: (item.start, item.end, item.kind)))


def extract_clinical_numbers_hybrid(
    text: object,
    ai_extractor: Callable[[str], Iterable[ClinicalNumber]],
) -> tuple[ClinicalNumber, ...]:
    """Merge validated AI candidates with deterministic rules; rules win overlaps."""
    source = "" if text is None else str(text)
    rules = list(extract_clinical_numbers(source))
    accepted = list(rules)
    allowed_units = {
        "iop": {"mmHg"},
        "visual_acuity": {"decimal_acuity", "logMAR"},
        "thickness": {"um"},
    }
    for candidate in ai_extractor(source):
        if not isinstance(candidate, ClinicalNumber):
            raise ValueError("AI extractor must return ClinicalNumber records")
        if not 0 <= candidate.start < candidate.end <= len(source):
            raise ValueError("AI evidence span is out of bounds")
        if source[candidate.start:candidate.end] != candidate.raw:
            raise ValueError("AI evidence span does not match raw text")
        if candidate.kind not in allowed_units or candidate.unit not in allowed_units[candidate.kind]:
            raise ValueError("AI candidate kind or unit is unsupported")
        if candidate.value is None or not math.isfinite(float(candidate.value)):
            raise ValueError("AI candidate value must be finite")
        if candidate.status != "parsed" or candidate.method != "ai":
            raise ValueError("AI candidate must be marked parsed with method=ai")
        overlaps_rule = any(
            candidate.start < rule.end and rule.start < candidate.end
            for rule in rules
        )
        if not overlaps_rule:
            accepted.append(candidate)
    return tuple(sorted(accepted, key=lambda item: (item.start, item.end, item.kind)))
