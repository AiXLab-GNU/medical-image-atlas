"""Conservative disease context for the quantitative metric registry.

Links describe clinical context, not regulatory claims or standalone diagnosis.
Every calculator receives an explicit context, including QC-only and
target-dependent metrics that must not be assigned to a disease.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


DISEASE_LABELS_KO = {
    "DR": "당뇨망막병증",
    "DME": "당뇨황반부종",
    "HTR": "고혈압성 망막변화",
    "NAMD": "신생혈관성 황반변성",
    "RVO": "망막정맥폐쇄",
    "POAG": "원발개방각녹내장",
    "OHT": "고안압증",
    "MULTI_OCULAR": "다양한 안과질환",
}


EVIDENCE_REGISTRY = {
    "E_DR_VESSEL": {
        "identifier": "PMID:33515071",
        "title": "Retinal venular tortuosity and fractal dimension predict incident retinopathy",
        "url": "https://pubmed.ncbi.nlm.nih.gov/33515071/",
        "design": "prospective cohort",
    },
    "E_HTN_VESSEL": {
        "identifier": "PMID:36583807",
        "title": "Retinal Vascular Geometry in Hypertension",
        "url": "https://pubmed.ncbi.nlm.nih.gov/36583807/",
        "design": "cross-sectional clinical study",
    },
    "E_NAMD_OCT": {
        "identifier": "PMCID:PMC11732971",
        "title": "Retinal fluid volume dynamics in neovascular AMD",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11732971/",
        "design": "HARBOR phase III post-hoc cohort analysis",
    },
    "E_DME_OCT": {
        "identifier": "PMCID:PMC6899163",
        "title": "Ellipsoid zone dynamics and retinal fluid index in VISTA-DME",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6899163/",
        "design": "phase III trial post-hoc analysis",
    },
    "E_RVO_OCT": {
        "identifier": "PMID:39742143",
        "title": "Machine learning quantification of fluid volume in retinal vein occlusion",
        "url": "https://pubmed.ncbi.nlm.nih.gov/39742143/",
        "design": "clinical treatment cohort",
    },
    "E_OHTS": {
        "identifier": "PMID:12049574",
        "title": "Ocular Hypertension Treatment Study",
        "url": "https://pubmed.ncbi.nlm.nih.gov/12049574/",
        "design": "randomized clinical trial",
    },
    "E_GLAUCOMA_RNFL": {
        "identifier": "PMID:36862395",
        "title": "Rates of GCIPL and cpRNFL thinning and development of glaucoma",
        "url": "https://pubmed.ncbi.nlm.nih.gov/36862395/",
        "design": "longitudinal glaucoma-suspect cohort",
    },
}


def _context(
    diseases: tuple[str, ...],
    role: str,
    evidence_level: str,
    evidence_ids: tuple[str, ...] = (),
    note: str = "단독 진단용 아님",
) -> dict[str, object]:
    return {
        "disease_ids": diseases,
        "disease_labels_ko": tuple(DISEASE_LABELS_KO[item] for item in diseases),
        "clinical_role": role,
        "evidence_level": evidence_level,
        "evidence_ids": evidence_ids,
        "standalone_diagnostic": False,
        "clinical_note": note,
    }


def _metric_context(row: Mapping[str, object]) -> dict[str, object]:
    collection = str(row["collection"])
    metric_id = str(row["metric_id"])
    domain = str(row["domain"])

    if collection == "segmentation_agreement":
        return _context((), "알고리즘 일치도 검증", "validation_only")
    if collection == "generic_binary_mask":
        return _context(
            (), "대상 병변의 형태·부담 정량", "target_label_required",
            note="mask가 나타내는 병변 label을 지정한 뒤에만 질병 연결 가능",
        )
    if collection == "oct_mask_25":
        prefix = metric_id.split("_", 1)[0]
        if prefix in {"irf", "srf"}:
            return _context(
                ("NAMD", "DME", "RVO"), "질병 활성도·치료반응·시력 예후 보조",
                "primary_cohort_supported", ("E_NAMD_OCT", "E_DME_OCT", "E_RVO_OCT"),
            )
        if prefix in {"ped", "shrm"}:
            return _context(
                ("NAMD",), "질병 활성도·치료반응·시력 예후 보조",
                "primary_cohort_supported", ("E_NAMD_OCT",),
            )
        if prefix == "is":
            return _context(
                ("NAMD", "DME", "RVO"), "광수용체 구조 보존·시력 예후 보조",
                "primary_cohort_supported", ("E_NAMD_OCT", "E_DME_OCT", "E_RVO_OCT"),
            )

    if domain == "vessel":
        return _context(
            ("DR", "HTR"), "망막 미세혈관 연관성·위험도 연구",
            "primary_cohort_association", ("E_DR_VESSEL", "E_HTN_VESSEL"),
            note="연관성 지표이며 확진 또는 질병 특이 지표가 아님",
        )
    if domain in {"color_quality", "fov_geometry", "reliability"}:
        return _context((), "영상 품질·교란·실패 통제", "qc_only")
    if domain == "texture":
        return _context(
            (), "탐색적 영상 phenotype", "exploratory_nonspecific",
            note="질병별 외부검증 전에는 진단 연결 금지",
        )
    if domain == "model_derived":
        if metric_id in {"dr_expected_grade", "referable_probability"}:
            return _context(
                ("DR",), "AI 선별·중증도 후보", "model_target_requires_external_validation",
                note="모델 target 의미 연결이며 독립 외부검증 전 임상 진단 사용 금지",
            )
        if metric_id.startswith(("he_", "ex_")):
            return _context(
                ("DR",), "출혈·삼출물 burden 및 중증도 후보",
                "model_target_requires_external_validation",
                note="병변 모델의 외부검증과 전문의 기준 truth가 필요",
            )
        return _context((), "foundation-model 탐색 score", "exploratory_nonspecific")
    if domain == "intraocular_pressure":
        return _context(
            ("POAG", "OHT"), "위험도 평가·치료반응 모니터링",
            "randomized_trial_supported", ("E_OHTS",),
            note="안압 단독으로 녹내장을 진단하지 않음",
        )
    if domain == "retinal_thickness" and "rnfl" in metric_id:
        return _context(
            ("POAG", "OHT"), "구조적 진단 보조·진행 모니터링",
            "longitudinal_cohort_supported", ("E_GLAUCOMA_RNFL",),
        )
    if domain == "retinal_thickness":
        return _context(
            ("DME", "NAMD", "RVO"), "황반부종·망막구조 모니터링",
            "primary_cohort_supported", ("E_NAMD_OCT", "E_DME_OCT", "E_RVO_OCT"),
            note="두께만으로 원인 질환을 구분할 수 없음",
        )
    if domain == "visual_acuity":
        return _context(
            ("MULTI_OCULAR",), "시기능 결과·중증도·치료반응",
            "clinical_endpoint_nonspecific",
            note="질병 비특이적 기능 endpoint이며 단독 감별진단 불가",
        )
    return _context((), "연구용 정량 특성", "unmapped_nonspecific")


def disease_context_catalog(
    metrics: Iterable[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    """Return one conservative disease-context row for every metric."""

    contexts: list[dict[str, object]] = []
    for row in metrics:
        context = _metric_context(row)
        contexts.append(
            {
                "collection": str(row["collection"]),
                "metric_id": str(row["metric_id"]),
                "domain": str(row["domain"]),
                **context,
            }
        )
    keys = [(row["collection"], row["metric_id"]) for row in contexts]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate disease-context key")
    return tuple(contexts)
