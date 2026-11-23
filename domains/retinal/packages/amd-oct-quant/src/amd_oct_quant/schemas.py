"""Small reusable provenance schemas for package consumers."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MetricProvenance:
    dataset: str
    sample_uid: str
    patient_key: str | None
    eye_key: str | None
    analysis_split: str
    relative_source_path: str
    source_sha256: str
    mask_source: str
    metric_version: str
    physical_unit_verified: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
