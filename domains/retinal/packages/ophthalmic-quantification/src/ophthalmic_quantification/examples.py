"""Build a deterministic, nonclinical example for every registered metric."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, replace
import hashlib
from html import escape
import json
import math
from pathlib import Path

import numpy as np

from .catalog import metric_catalog
from .clinical_extraction import ClinicalNumber, extract_clinical_numbers, extract_clinical_numbers_hybrid, parse_iop, parse_visual_acuity
from .disease_links import DISEASE_LABELS_KO, disease_context_catalog
from .fundus_metrics import REQUIRED_UPSTREAM_VALUES, extract_fundus_metrics, fundus_metric_catalog
from .mask_metrics import binary_mask_metrics, segmentation_agreement
from .oct_metrics import extract_oct_metrics, oct_metric_catalog


@dataclass(frozen=True, slots=True)
class MetricExample:
    collection: str
    metric_id: str
    domain: str
    modality: str
    method: str
    input_source: str
    unit: str
    value: float | None
    status: str
    missing_reason: str
    algorithm_version: str
    disease_ids: str = ""
    related_diseases_ko: str = "질병 비특이적"
    clinical_role: str = "연구용 정량 특성"
    evidence_level: str = "unmapped_nonspecific"
    evidence_ids: str = ""
    standalone_diagnostic: bool = False
    clinical_note: str = "단독 진단용 아님"
    synthetic_example: bool = True


def _record(
    collection: str,
    metric_id: str,
    value: object,
    *,
    domain: str,
    modality: str,
    method: str,
    input_source: str,
    unit: str,
    version: str,
) -> MetricExample:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float("nan")
    finite = math.isfinite(numeric)
    return MetricExample(
        collection=collection,
        metric_id=metric_id,
        domain=domain,
        modality=modality,
        method=method,
        input_source=input_source,
        unit=unit,
        value=numeric if finite else None,
        status="computed" if finite else "undefined_by_rule",
        missing_reason="" if finite else "synthetic input produced an undefined denominator or absent structure",
        algorithm_version=version,
    )


def _synthetic_fundus() -> tuple[np.ndarray, np.ndarray]:
    size = 192
    yy, xx = np.indices((size, size))
    fov = (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size * 0.44) ** 2
    texture = 8 * np.sin(xx / 5) + 5 * np.cos(yy / 7)
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    rgb[..., 0][fov] = np.clip(145 + xx[fov] / 5 + texture[fov], 0, 255)
    rgb[..., 1][fov] = np.clip(72 + yy[fov] / 7 + texture[fov], 0, 255)
    rgb[..., 2][fov] = np.clip(38 + texture[fov] / 2, 0, 255)
    vessel = fov & (
        ((np.abs(yy - size / 2 - 0.30 * (xx - size / 2)) < 1.4))
        | (np.abs(yy - size / 2 + 0.42 * (xx - size / 2)) < 1.2)
        | ((xx.astype(int) - size // 2) % 31 == 0)
    )
    return rgb, vessel


def _synthetic_oct_mask() -> np.ndarray:
    mask = np.zeros((80, 120), dtype=np.uint8)
    mask[8:22, 12:32] = 1
    mask[28:40, 45:78] = 2
    mask[44:61, 16:42] = 3
    mask[14:27, 88:108] = 4
    mask[69:72, 8:112] = 5
    mask[69:72, 54:66] = 0
    return mask


def build_synthetic_examples() -> tuple[MetricExample, ...]:
    examples: list[MetricExample] = []
    rgb, vessel = _synthetic_fundus()
    upstream = {
        "ensemble_uncertainty_mean": 0.023,
        "mask_failure": 0,
        "retfound_score": 6.45,
        "dr_expected_grade": 1.20,
        "referable_probability": 0.18,
        "he_probability_burden": 0.032,
        "he_threshold_burden": 0.009,
        "ex_probability_burden": 0.041,
        "ex_threshold_burden": 0.013,
    }
    if set(upstream) != set(REQUIRED_UPSTREAM_VALUES):
        raise RuntimeError("synthetic upstream fixture does not cover the locked contract")
    fundus_values = extract_fundus_metrics(rgb, vessel, upstream_values=upstream, strict=True)
    fundus_metadata = {row["metric_id"]: row for row in fundus_metric_catalog()}
    for metric_id, value in fundus_values.items():
        metadata = fundus_metadata[metric_id]
        examples.append(
            _record(
                "fundus_legacy_139", metric_id, value,
                domain=metadata["domain"], modality="fundus",
                method="upstream_adapter" if metadata["input_source"] == "upstream_model_output" else "rule_based",
                input_source=f"synthetic_{metadata['input_source']}", unit=metadata["unit"],
                version=metadata["algorithm_version"],
            )
        )
    oct_values = extract_oct_metrics(_synthetic_oct_mask())
    oct_metadata = {row["metric_name"]: row for row in oct_metric_catalog()}
    for metric_id, value in oct_values.items():
        metadata = oct_metadata[metric_id]
        examples.append(
            _record(
                "oct_mask_25", metric_id, value, domain="oct_mask_phenotype", modality="oct",
                method="rule_based", input_source="synthetic_ground_truth_label_mask",
                unit=str(metadata["unit"]), version=str(metadata["algorithm_version"]),
            )
        )
    mask = np.zeros((64, 64), dtype=bool)
    mask[10:26, 12:30] = True
    mask[38:50, 42:57] = True
    mask_values = binary_mask_metrics(mask, pixel_spacing=(0.01, 0.01))
    for metric_id, value in mask_values.items():
        unit = "mm2" if metric_id == "area_physical" else "defined_scale"
        examples.append(
            _record(
                "generic_binary_mask", metric_id, value, domain="mask_morphology", modality="generic_mask",
                method="rule_based", input_source="synthetic_ground_truth_binary_mask", unit=unit,
                version="ophthalmic_quantification.mask.v0.1.0",
            )
        )
    predicted = np.roll(mask, shift=2, axis=1)
    for metric_id, value in segmentation_agreement(predicted, mask).items():
        examples.append(
            _record(
                "segmentation_agreement", metric_id, value, domain="mask_agreement", modality="generic_mask",
                method="rule_based", input_source="synthetic_prediction_and_ground_truth", unit="fraction_or_binary",
                version="ophthalmic_quantification.mask.v0.1.0",
            )
        )
    acuity = parse_visual_acuity("20/40")
    pressure = parse_iop("18 mmHg")
    clinical_values = (("va_decimal", acuity.decimal, "decimal_acuity"), ("va_logmar", acuity.logmar, "logMAR"), ("iop_mmhg", pressure.value_mmhg, "mmHg"))
    for metric_id, value, unit in clinical_values:
        examples.append(
            _record(
                "structured_clinical", metric_id, value, domain="clinical_measurement", modality="clinical_table",
                method="rule_based", input_source="synthetic_structured_field", unit=unit,
                version="ophthalmic_quantification.clinical.v0.1.0",
            )
        )
    text_values = extract_clinical_numbers("우안 IOP 18 mmHg, VA 20/40, CMT 312 µm.")
    for item in text_values:
        metric_id = {"iop": "text_iop_value", "visual_acuity": "text_visual_acuity_value", "thickness": "text_thickness_value"}[item.kind]
        examples.append(
            _record(
                "clinical_text", metric_id, item.value, domain=item.kind, modality="clinical_text",
                method="rule_based_span_extraction", input_source="synthetic_clinical_text", unit=item.unit,
                version="ophthalmic_quantification.clinical.v0.1.0",
            )
        )
    hybrid_text = "IOP 18 mmHg, RNFL 92 µm"

    def synthetic_ai_extractor(source: str) -> tuple[ClinicalNumber, ...]:
        start = source.index("RNFL")
        return (
            ClinicalNumber(
                "thickness", source[start:], 92.0, "um", "parsed",
                start, len(source), None, "ai",
            ),
        )

    hybrid_values = extract_clinical_numbers_hybrid(hybrid_text, synthetic_ai_extractor)
    ai_value = next(item for item in hybrid_values if item.method == "ai")
    examples.append(
        _record(
            "clinical_text_hybrid", "ai_rnfl_thickness_value", ai_value.value,
            domain="thickness", modality="clinical_text", method="hybrid_validated_ai_span",
            input_source="synthetic_clinical_text_and_mock_ai_candidate", unit=ai_value.unit,
            version="ophthalmic_quantification.clinical.v0.1.0",
        )
    )
    keys = [(row.collection, row.metric_id) for row in examples]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate example key")
    catalog_keys = {(str(row["collection"]), str(row["metric_id"])) for row in metric_catalog()}
    if set(keys) != catalog_keys:
        missing = sorted(catalog_keys - set(keys))
        extra = sorted(set(keys) - catalog_keys)
        raise RuntimeError(f"example/catalog mismatch: missing={missing}, extra={extra}")
    contexts = {
        (str(row["collection"]), str(row["metric_id"])): row
        for row in disease_context_catalog(metric_catalog())
    }
    examples = [
        replace(
            row,
            disease_ids="|".join(contexts[(row.collection, row.metric_id)]["disease_ids"]),
            related_diseases_ko=" · ".join(contexts[(row.collection, row.metric_id)]["disease_labels_ko"])
            or "질병 비특이적",
            clinical_role=str(contexts[(row.collection, row.metric_id)]["clinical_role"]),
            evidence_level=str(contexts[(row.collection, row.metric_id)]["evidence_level"]),
            evidence_ids=" · ".join(contexts[(row.collection, row.metric_id)]["evidence_ids"]),
            standalone_diagnostic=bool(contexts[(row.collection, row.metric_id)]["standalone_diagnostic"]),
            clinical_note=str(contexts[(row.collection, row.metric_id)]["clinical_note"]),
        )
        for row in examples
    ]
    return tuple(examples)


def _html_document(rows: tuple[MetricExample, ...]) -> str:
    # Import lazily because atlas builds its catalog from these synthetic examples.
    # The generated HTML reuses that canonical classification instead of maintaining
    # a second Tier mapping in this report generator.
    from .atlas import build_atlas_catalog

    atlas = build_atlas_catalog()
    taxonomy_by_id = {str(row["id"]): row for row in atlas["metrics"]}
    data = []
    for row in rows:
        item = asdict(row)
        taxonomy = taxonomy_by_id[f"{row.collection}:{row.metric_id}"]
        item.update(
            tier=taxonomy["tier"],
            registry=taxonomy["registry"],
            domain=taxonomy["domain"],
            domain_label=taxonomy["domain_label"],
            family_id=taxonomy["family_id"],
        )
        data.append(item)
    collections = sorted({row.collection for row in rows})
    computed = sum(row.status == "computed" for row in rows)
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    taxonomy_encoded = json.dumps(
        {
            "summary": atlas["summary"],
            "tier_meta": atlas["tier_meta"],
            "families": atlas["families"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    collection_options = "".join(f'<option value="{escape(name)}">{escape(name)}</option>' for name in collections)
    disease_ids = sorted({item for row in rows for item in row.disease_ids.split("|") if item})
    disease_options = "".join(
        f'<option value="{escape(disease_id)}">{escape(DISEASE_LABELS_KO[disease_id])}</option>'
        for disease_id in disease_ids
    )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>전체 안과 정량지표 합성 계산 예제</title>
<style>
:root{{--ink:#17212b;--muted:#617080;--line:#d9e0e5;--paper:#f4f7f5;--accent:#4f3fa0;--teal:#087f75;--navy:#071c2c;--t1:#d65743;--t2:#df913d;--t3:#278e82;--t4:#4f72b5;--analysis:#74579c}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Noto Sans KR",sans-serif}}header,main{{width:min(1500px,calc(100% - 2rem));margin:auto}}.topnav{{position:sticky;top:0;z-index:20;display:flex;gap:.45rem;align-items:center;padding:.65rem max(1rem,calc((100vw - 1500px)/2));background:#071c2cf2;backdrop-filter:blur(12px)}}.topnav a{{padding:.42rem .68rem;color:#dce8ea;text-decoration:none;border-radius:7px;font-size:.8rem;font-weight:800}}.topnav a:first-child{{margin-right:auto;color:#92e2d5}}.topnav a:hover{{color:white;background:#ffffff17}}header{{padding:3rem 0 1.4rem}}h1{{margin:.2rem 0;font-size:clamp(2rem,5vw,4.6rem);letter-spacing:-.05em}}h2{{margin:.2rem 0;font-size:clamp(1.65rem,3.5vw,2.8rem);letter-spacing:-.035em}}.eyebrow{{margin:0 0 .5rem;color:var(--teal);font-size:.72rem;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}.warning{{padding:1rem;border:2px solid #b94848;background:#fff3f0;border-radius:12px;font-weight:800}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin:1.2rem 0}}.metric{{padding:1rem;background:white;border:1px solid var(--line);border-radius:12px}}.metric strong{{display:block;font-size:1.8rem;color:var(--accent)}}.taxonomy{{margin:1rem 0 2rem;padding:clamp(1rem,3vw,2rem);background:white;border:1px solid var(--line);border-radius:18px}}.section-head{{display:flex;justify-content:space-between;gap:2rem;align-items:end;margin-bottom:1.2rem}}.section-head>p,.section-side p{{max-width:650px;color:var(--muted);line-height:1.65}}.section-side{{max-width:650px;text-align:right}}.section-side p{{margin:0 0 .65rem}}.map-link{{display:inline-flex;padding:.62rem .85rem;color:white;background:var(--accent);border-radius:9px;text-decoration:none;font-size:.86rem;font-weight:850}}.map-link:hover{{background:#37277f}}.tier-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem}}.tier-card{{min-height:205px;padding:1rem;text-align:left;background:white;border:1px solid var(--line);border-top:5px solid var(--tier);border-radius:13px;cursor:pointer}}.tier-card:hover,.tier-card.active{{transform:translateY(-2px);box-shadow:0 12px 26px #183a3020;outline:2px solid var(--tier)}}.tier-card>span{{display:block;color:var(--muted);font-size:.72rem;font-weight:800}}.tier-card strong{{display:block;margin:.15rem 0;color:var(--tier);font-size:2rem}}.tier-card h3{{margin:.15rem 0}}.tier-card p{{min-height:48px;color:var(--muted);line-height:1.45}}.analysis-note{{width:100%;display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-top:.8rem;padding:.8rem 1rem;color:#46326c;background:#f1edf8;border:1px solid #d8cdeb;border-radius:10px;cursor:pointer;text-align:left}}.analysis-note strong{{font-size:1.4rem}}.lineage-panel{{margin-top:1rem;padding:1rem;background:var(--navy);border-radius:14px}}.lineage-head{{display:flex;justify-content:space-between;gap:1rem;margin-bottom:.8rem;color:white}}.lineage-head span{{color:#9edfd5}}.network-scroll{{overflow:auto;background:#f8faf8;border-radius:10px}}.network-scroll svg{{display:block;min-width:1120px}}.edge{{fill:none;stroke:#9eaca7;stroke-width:1.3}}.family rect{{fill:white;stroke:#cad4d0}}.family .accent{{fill:var(--c);stroke:none}}.family text{{fill:#193040}}.family .count{{fill:var(--c);font-weight:850}}.family{{cursor:pointer}}.family:hover rect{{stroke:var(--c);stroke-width:2}}.table-section{{scroll-margin-top:60px}}.result-count{{margin:.7rem 0;color:var(--muted);font-weight:800}}.toolbar{{position:sticky;top:55px;z-index:8;display:grid;grid-template-columns:2fr repeat(4,1fr);gap:.7rem;padding:.9rem;background:#17212bef;border-radius:10px 10px 0 0}}input,select{{min-height:42px;padding:.55rem;border:1px solid var(--line);border-radius:7px;background:white}}.scroll-hint{{margin:.75rem 0 .4rem;color:var(--muted);font-weight:700}}.x-scroll{{height:20px;overflow-x:scroll;overflow-y:hidden;background:#edf2f0;border:1px solid var(--line);scrollbar-color:var(--accent) #dce4e1;scrollbar-width:auto}}.x-scroll-inner{{height:1px}}.x-scroll::-webkit-scrollbar{{height:16px}}.x-scroll::-webkit-scrollbar-thumb{{background:var(--accent);border-radius:8px}}.x-scroll::-webkit-scrollbar-track{{background:#dce4e1}}.table-wrap{{max-height:min(70vh,800px);overflow:auto;background:white;border:1px solid var(--line);scrollbar-color:var(--accent) #dce4e1;scrollbar-width:auto}}table{{width:100%;min-width:2200px;border-collapse:separate;border-spacing:0;font-size:.84rem}}th,td{{padding:.65rem;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{position:sticky;top:0;z-index:1;background:#e9eeeb;box-shadow:0 2px 0 var(--line)}}td.context-cell{{min-width:180px;max-width:270px;white-space:normal;line-height:1.45}}.tier-badge{{display:inline-block;padding:.2rem .45rem;color:white;background:var(--tier);border-radius:999px;font-weight:900}}tr:hover{{background:#f3f0ff}}.status{{font-weight:800;color:var(--teal)}}.undefined_by_rule{{color:#a05b16}}footer{{padding:2rem;text-align:center;color:var(--muted)}}@media(max-width:1000px){{.tier-grid{{grid-template-columns:1fr 1fr}}.toolbar{{grid-template-columns:1fr 1fr}}}}@media(max-width:800px){{.topnav a:not(:first-child){{display:none}}.metrics,.tier-grid{{grid-template-columns:1fr 1fr}}.section-head{{display:block}}.section-side{{text-align:left}}.toolbar{{position:relative;top:auto;grid-template-columns:1fr}}.table-wrap{{max-height:65vh}}.analysis-note{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><nav class="topnav" aria-label="문서 메뉴"><a href="/">⌂ 연구 포털 홈</a><a href="#tier-map-section">Tier map</a><a href="#table-section">190개 계산표</a></nav><header><p>OcuPhenome XAI · E017</p><h1>전체 안과 정량지표<br>합성 계산 예제</h1><p class="warning">SYNTHETIC · NOT CLINICAL RESULT — 환자자료가 아닌 결정론적 합성 RGB·mask·임상 문자열로 계산한 구현 검증 예제입니다. 모든 질병 연결은 단독 진단용 아님이며 임상 역할과 근거 수준을 함께 해석해야 합니다.</p><div class="metrics"><div class="metric"><span>전체 예제</span><strong>{len(rows)}</strong></div><div class="metric"><span>안저 legacy</span><strong>139</strong></div><div class="metric"><span>OCT mask</span><strong>25</strong></div><div class="metric"><span>계산값</span><strong>{computed}</strong></div></div></header>
<main><section id="tier-map-section" class="taxonomy"><div class="section-head"><div><p class="eyebrow">Interactive quantitative map</p><h2>임상 기준축에서 모델까지</h2></div><div class="section-side"><p>Tier는 성능 순위가 아니라 의료 기준값으로부터의 파생 거리입니다. 카드를 누르면 아래 190개 계산표가 해당 Tier로 필터됩니다.</p><a class="map-link" href="ophthalmic_disease_metric_map_v01_ko.html">질병–정량지표 지도 →</a> <a class="map-link" href="ophthalmic_full_metric_relationship_map_v01_ko.html">190개 전체 관계 지도 →</a></div></div><div id="tier-map" class="tier-grid"></div><button id="analysis-map" class="analysis-note" type="button"><span><b>QC·검증은 별도 Analysis registry</b><br>영상 품질·FOV·mask agreement는 환자 상태 지표와 분리합니다.</span><strong id="analysis-count">—</strong></button><div class="lineage-panel"><div class="lineage-head"><strong>T1–T4 지표 family 계보</strong><span id="network-count"></span></div><div class="network-scroll" tabindex="0"><svg id="lineage-svg" role="img" aria-label="T1에서 T4까지 안과 정량지표 family 계보"></svg></div></div></section><section id="table-section" class="table-section"><div class="section-head"><div><p class="eyebrow">190 metric calculators</p><h2>계산값과 질병 맥락</h2></div><p>Tier·질병·collection·상태를 함께 필터하고 각 지표의 임상 역할과 근거 수준을 확인합니다.</p></div><div class="toolbar"><input id="search" type="search" placeholder="지표명·질병·역할·domain 검색"><select id="tier-filter"><option value="">전체 Tier·registry</option><option value="T1">T1 · 임상 기준축</option><option value="T2">T2 · 앵커 파생계측</option><option value="T3">T3 · 영상 정량 proxy</option><option value="T4">T4 · 모델 파생량</option><option value="ANALYSIS">Analysis · QC·검증</option></select><select id="disease"><option value="">전체 질병·비특이 지표</option>{disease_options}</select><select id="collection"><option value="">전체 collection</option>{collection_options}</select><select id="status"><option value="">전체 상태</option><option>computed</option><option>undefined_by_rule</option></select></div><p id="result-count" class="result-count"></p><p class="scroll-hint">↔ 넓은 표입니다. 위쪽 보조 막대나 표 아래쪽 기본 막대를 좌우로 움직이세요.</p><div class="x-scroll" id="table-scroll-top" tabindex="0" aria-label="표 위쪽 가로 스크롤"><div class="x-scroll-inner"></div></div><div class="table-wrap" id="table-wrap"><table id="metric-table"><thead><tr><th>Tier</th><th>Registry</th><th>Collection</th><th>Metric ID</th><th>질병 연결</th><th>임상 역할</th><th>근거 수준</th><th>Domain</th><th>Modality</th><th>Method</th><th>Input</th><th>Value</th><th>Unit</th><th>Status</th></tr></thead><tbody id="rows"></tbody></table></div></section></main><footer>Tier는 성능 우열이 아님 · 질병 연관성 ≠ 단독 진단 · synthetic_example=true · E017</footer>
<script>const DATA={encoded};const TAXONOMY={taxonomy_encoded};const COLORS={{T1:'#d65743',T2:'#df913d',T3:'#278e82',T4:'#4f72b5',ANALYSIS:'#74579c'}};const body=document.getElementById('rows');const search=document.getElementById('search');const tier=document.getElementById('tier-filter');const disease=document.getElementById('disease');const collection=document.getElementById('collection');const status=document.getElementById('status');const table=document.getElementById('metric-table');const tableWrap=document.getElementById('table-wrap');const topScroll=document.getElementById('table-scroll-top');let syncing=false;let selectedFamily='';function syncWidth(){{document.querySelector('.x-scroll-inner').style.width=table.scrollWidth+'px'}}function syncScroll(source){{if(syncing)return;syncing=true;[tableWrap,topScroll].forEach(target=>{{if(target!==source)target.scrollLeft=source.scrollLeft}});syncing=false}}function setTier(value,scroll=true){{tier.value=value;selectedFamily='';document.querySelectorAll('[data-tier]').forEach(card=>card.classList.toggle('active',card.dataset.tier===value));draw();if(scroll)document.getElementById('table-section').scrollIntoView({{behavior:'smooth'}})}}function renderTierMap(){{const target=document.getElementById('tier-map');target.innerHTML=TAXONOMY.tier_meta.map(t=>`<button class="tier-card" type="button" data-tier="${{t.tier}}" style="--tier:${{COLORS[t.tier]}}"><span>${{t.name_en}}</span><strong>${{t.tier}}</strong><h3>${{t.name}}</h3><p>${{t.description}}</p><b>${{TAXONOMY.summary.tier_counts[t.tier]||0}} metrics</b></button>`).join('');target.querySelectorAll('[data-tier]').forEach(card=>card.addEventListener('click',()=>setTier(card.dataset.tier)));document.getElementById('analysis-count').textContent=`${{TAXONOMY.summary.analysis_registry_total}} metrics`;document.getElementById('analysis-map').addEventListener('click',()=>setTier('ANALYSIS'))}}function renderLineage(){{const families=TAXONOMY.families;const tiers=['T1','T2','T3','T4'];const ordered=Object.fromEntries(tiers.map(t=>[t,families.filter(f=>f.tier===t)]));const max=Math.max(1,...tiers.map(t=>ordered[t].length)),row=62,top=68,width=1120,height=top+max*row+42,x={{T1:15,T2:300,T3:585,T4:870}},pos=new Map(),nodeW=235,nodeH=42;tiers.forEach(t=>ordered[t].forEach((f,i)=>pos.set(f.id,{{x:x[t],y:top+i*row}})));let svgText='<title>안과 정량지표 family T1–T4 계보</title>';tiers.forEach(t=>{{svgText+=`<text x="${{x[t]}}" y="30" font-weight="850" fill="${{COLORS[t]}}">${{t}} · ${{ordered[t].length}}</text>`}});families.forEach(f=>(f.parents||[]).forEach(parent=>{{const a=pos.get(parent),b=pos.get(f.id);if(!a||!b)return;const sy=a.y+nodeH/2,ey=b.y+nodeH/2;svgText+=`<path class="edge" d="M ${{a.x+nodeW}} ${{sy}} C ${{a.x+nodeW+30}} ${{sy}}, ${{b.x-30}} ${{ey}}, ${{b.x}} ${{ey}}"></path>`}}));tiers.forEach(t=>ordered[t].forEach(f=>{{const p=pos.get(f.id);svgText+=`<g class="family" data-family="${{f.id}}" data-family-tier="${{t}}" transform="translate(${{p.x}} ${{p.y}})" style="--c:${{COLORS[t]}}"><rect width="${{nodeW}}" height="${{nodeH}}" rx="8"></rect><rect class="accent" width="5" height="${{nodeH}}" rx="3"></rect><text x="13" y="18">${{f.name}}</text><text class="count" x="13" y="34">${{f.count}} metrics</text></g>`}}));const svg=document.getElementById('lineage-svg');svg.setAttribute('viewBox',`0 0 ${{width}} ${{height}}`);svg.setAttribute('height',height);svg.innerHTML=svgText;document.getElementById('network-count').textContent=`${{families.length}} family nodes`;svg.querySelectorAll('[data-family]').forEach(group=>group.addEventListener('click',()=>{{tier.value=group.dataset.familyTier;selectedFamily=group.dataset.family.startsWith('anchor.')?'':group.dataset.family;document.querySelectorAll('[data-tier]').forEach(card=>card.classList.toggle('active',card.dataset.tier===tier.value));draw();document.getElementById('table-section').scrollIntoView({{behavior:'smooth'}})}}))}}function draw(){{const q=search.value.toLowerCase();const filtered=DATA.filter(r=>(!tier.value||r.tier===tier.value)&&(!selectedFamily||r.family_id===selectedFamily)&&(!disease.value||r.disease_ids.split('|').includes(disease.value))&&(!collection.value||r.collection===collection.value)&&(!status.value||r.status===status.value)&&(!q||JSON.stringify(r).toLowerCase().includes(q)));document.getElementById('result-count').textContent=`${{filtered.length}} / ${{DATA.length}} metrics`;body.replaceChildren(...filtered.map(r=>{{const tr=document.createElement('tr');const evidence=r.evidence_level+(r.evidence_ids?' · '+r.evidence_ids:'');[r.tier,r.registry,r.collection,r.metric_id,r.related_diseases_ko,r.clinical_role,evidence,r.domain_label,r.modality,r.method,r.input_source,r.value===null?'—':Number(r.value).toPrecision(6),r.unit,r.status].forEach((v,i)=>{{const td=document.createElement('td');td.textContent=v;if(i===0){{td.innerHTML=`<span class="tier-badge" style="--tier:${{COLORS[r.tier]}}">${{r.tier}}</span>`}}if([4,5,6].includes(i))td.classList.add('context-cell');if(i===13)td.classList.add('status',r.status);tr.append(td)}});tr.title=[r.clinical_note,r.missing_reason].filter(Boolean).join(' · ');return tr}}));requestAnimationFrame(syncWidth)}}[search,disease,collection,status].forEach(element=>element.addEventListener('input',()=>{{selectedFamily='';draw()}}));tier.addEventListener('input',()=>setTier(tier.value,false));[tableWrap,topScroll].forEach(element=>element.addEventListener('scroll',()=>syncScroll(element),{{passive:true}}));window.addEventListener('resize',syncWidth);renderTierMap();renderLineage();draw();</script></body></html>"""


def write_example_bundle(output_dir: str | Path) -> dict[str, Path]:
    from .disease_metric_map import write_disease_metric_map
    from .full_metric_relationship_map import write_full_metric_relationship_map

    destination = Path(output_dir)
    metrics_dir = destination / "metrics"
    reports_dir = destination / "reports"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    rows = build_synthetic_examples()
    csv_path = metrics_dir / "ophthalmic_quantitative_metric_examples_v01.csv"
    html_path = reports_dir / "ophthalmic_quantitative_metric_examples_v01_ko.html"
    disease_map_path = reports_dir / "ophthalmic_disease_metric_map_v01_ko.html"
    full_relationship_map_path = reports_dir / "ophthalmic_full_metric_relationship_map_v01_ko.html"
    validation_path = reports_dir / "ophthalmic_quantification_validation_v01.json"
    fieldnames = list(asdict(rows[0]))
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    html_path.write_text(_html_document(rows), encoding="utf-8")
    write_disease_metric_map(disease_map_path)
    write_full_metric_relationship_map(full_relationship_map_path)
    validation = {
        "synthetic_only": True,
        "total_examples": len(rows),
        "computed": sum(row.status == "computed" for row in rows),
        "undefined_by_rule": sum(row.status == "undefined_by_rule" for row in rows),
        "disease_context_complete": all(row.clinical_role and row.evidence_level for row in rows),
        "disease_linked_examples": sum(bool(row.disease_ids) for row in rows),
        "standalone_diagnostic_examples": sum(row.standalone_diagnostic for row in rows),
        "collection_counts": {name: sum(row.collection == name for row in rows) for name in sorted({row.collection for row in rows})},
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "html_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
        "disease_map_sha256": hashlib.sha256(disease_map_path.read_bytes()).hexdigest(),
        "full_relationship_map_sha256": hashlib.sha256(
            full_relationship_map_path.read_bytes()
        ).hexdigest(),
        "direct_identifiers": 0,
    }
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "csv": csv_path,
        "html": html_path,
        "disease_map": disease_map_path,
        "full_relationship_map": full_relationship_map_path,
        "validation": validation_path,
    }
