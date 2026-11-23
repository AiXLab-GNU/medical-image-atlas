"""Build the self-contained Ophthalmic Medical Metric Atlas."""

from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path

from .catalog import metric_catalog
from .disease_links import DISEASE_LABELS_KO, EVIDENCE_REGISTRY, disease_context_catalog
from .examples import build_synthetic_examples


TIER_META = {
    "T1": ("임상 기준축", "Clinician-native", "직접 기록된 시력·안압 등 임상 기준값"),
    "T2": ("앵커 파생계측", "Clinician-anchored", "임상값·전문의 annotation에서 명시적 산식으로 파생"),
    "T3": ("영상 정량 proxy", "Research computational", "영상과 mask에서 계산한 연구용 phenotype"),
    "T4": ("모델 파생량", "Model-derived", "AI score·확률·불확실성·hybrid 추출값"),
}

DOMAIN_LABELS = {
    "visual_acuity": "시력",
    "intraocular_pressure": "안압",
    "retinal_thickness": "망막·RNFL 두께",
    "oct_mask_phenotype": "OCT 병변·구조",
    "mask_morphology": "병변 mask 형태",
    "vessel": "망막혈관",
    "texture": "안저 texture",
    "model_derived": "질병·병변 모델 출력",
    "reliability": "모델 신뢰성",
    "color_quality": "색상·조명·선명도 QC",
    "fov_geometry": "FOV geometry QC",
    "mask_agreement": "mask 일치도 검증",
}


def _classification(row: dict[str, object]) -> tuple[str, str]:
    collection = str(row["collection"])
    domain = str(row["domain"])
    metric_id = str(row["metric_id"])
    if collection == "segmentation_agreement":
        return "ANALYSIS", "VALIDATION"
    if domain in {"color_quality", "fov_geometry"} or metric_id == "mask_failure":
        return "ANALYSIS", "QC"
    if collection == "structured_clinical":
        return "T1", "MEDICAL"
    if collection in {"clinical_text", "oct_mask_25", "generic_binary_mask"}:
        return "T2", "MEDICAL"
    if collection == "clinical_text_hybrid" or domain in {"model_derived", "reliability"}:
        return "T4", "MEDICAL"
    return "T3", "MEDICAL"


def _family_id(tier: str, domain: str) -> str:
    return f"{tier.lower()}.{domain}"


def _family_catalog(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    anchors = [
        {"id": "anchor.ophthalmic_image", "tier": "T1", "name": "안과 원영상", "count": 0, "parents": []},
        {"id": "anchor.expert_annotation", "tier": "T1", "name": "전문의 annotation", "count": 0, "parents": []},
        {"id": "anchor.expert_diagnosis", "tier": "T1", "name": "전문의 진단·등급", "count": 0, "parents": []},
        {"id": "anchor.clinical_text", "tier": "T1", "name": "임상 기록 원문", "count": 0, "parents": []},
    ]
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for metric in metrics:
        tier = str(metric["tier"])
        if tier == "ANALYSIS":
            continue
        grouped.setdefault((tier, str(metric["domain"])), []).append(metric)
    parents = {
        "T2": {
            "visual_acuity": ["t1.visual_acuity"],
            "intraocular_pressure": ["t1.intraocular_pressure"],
            "retinal_thickness": ["anchor.clinical_text"],
            "oct_mask_phenotype": ["anchor.expert_annotation"],
            "mask_morphology": ["anchor.expert_annotation"],
        },
        "T3": {
            "vessel": ["anchor.ophthalmic_image"],
            "texture": ["anchor.ophthalmic_image"],
        },
        "T4": {
            "model_derived": ["anchor.expert_diagnosis", "anchor.ophthalmic_image"],
            "reliability": ["anchor.ophthalmic_image"],
            "retinal_thickness": ["anchor.clinical_text"],
        },
    }
    families = list(anchors)
    for (tier, domain), rows in sorted(grouped.items()):
        disease_ids = sorted({item for row in rows for item in row["disease_ids"]})
        families.append(
            {
                "id": _family_id(tier, domain),
                "tier": tier,
                "name": DOMAIN_LABELS.get(domain, domain.replace("_", " ")),
                "count": len(rows),
                "parents": parents.get(tier, {}).get(domain, []),
                "disease_ids": disease_ids,
            }
        )
    return families


def build_atlas_catalog() -> dict[str, object]:
    catalog_rows = list(metric_catalog())
    examples = {(row.collection, row.metric_id): row for row in build_synthetic_examples()}
    contexts = {
        (str(row["collection"]), str(row["metric_id"])): row
        for row in disease_context_catalog(catalog_rows)
    }
    metrics: list[dict[str, object]] = []
    for row in catalog_rows:
        key = (str(row["collection"]), str(row["metric_id"]))
        example = examples[key]
        context = contexts[key]
        tier, registry = _classification(row)
        metrics.append(
            {
                "id": f"{key[0]}:{key[1]}",
                "collection": key[0],
                "metric_id": key[1],
                "tier": tier,
                "registry": registry,
                "domain": str(row["domain"]),
                "domain_label": DOMAIN_LABELS.get(str(row["domain"]), str(row["domain"]).replace("_", " ")),
                "modality": example.modality,
                "method": example.method,
                "input_source": example.input_source,
                "unit": example.unit,
                "value": example.value,
                "status": example.status,
                "algorithm_version": example.algorithm_version,
                "disease_ids": list(context["disease_ids"]),
                "disease_labels": list(context["disease_labels_ko"]),
                "clinical_role": str(context["clinical_role"]),
                "evidence_level": str(context["evidence_level"]),
                "evidence_ids": list(context["evidence_ids"]),
                "standalone_diagnostic": bool(context["standalone_diagnostic"]),
                "clinical_note": str(context["clinical_note"]),
                "family_id": _family_id(tier, str(row["domain"])) if tier != "ANALYSIS" else f"analysis.{registry.lower()}",
            }
        )
    tier_counts = Counter(str(row["tier"]) for row in metrics if row["tier"] != "ANALYSIS")
    registry_counts = Counter(str(row["registry"]) for row in metrics)
    diseases = [
        {
            "id": disease_id,
            "label": label,
            "count": sum(disease_id in row["disease_ids"] for row in metrics),
        }
        for disease_id, label in DISEASE_LABELS_KO.items()
        if any(disease_id in row["disease_ids"] for row in metrics)
    ]
    evidence = [
        {"id": evidence_id, **metadata}
        for evidence_id, metadata in EVIDENCE_REGISTRY.items()
    ]
    medical_total = registry_counts["MEDICAL"]
    return {
        "version": "2.0",
        "generated": date.today().isoformat(),
        "summary": {
            "calculator_total": len(metrics),
            "medical_tier_total": medical_total,
            "analysis_registry_total": len(metrics) - medical_total,
            "disease_linked_total": sum(bool(row["disease_ids"]) for row in metrics),
            "standalone_diagnostic_total": sum(bool(row["standalone_diagnostic"]) for row in metrics),
            "disease_context_complete": all(row["clinical_role"] and row["evidence_level"] for row in metrics),
            "tier_counts": dict(tier_counts),
            "registry_counts": dict(registry_counts),
        },
        "tier_meta": [
            {"tier": tier, "name": values[0], "name_en": values[1], "description": values[2]}
            for tier, values in TIER_META.items()
        ],
        "diseases": diseases,
        "evidence": evidence,
        "families": _family_catalog(metrics),
        "metrics": metrics,
        "source_paths": [
            "ophthalmic_quantification.catalog.metric_catalog",
            "ophthalmic_quantification.disease_links.disease_context_catalog",
            "E017 synthetic calculation bundle",
        ],
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="190개 안과 정량지표의 T1–T4 계보, 질병 연결, 계산 예제와 근거 레지스트리">
<title>Ophthalmic Medical Metric Atlas</title>
<style>
:root{--navy:#071c2c;--ink:#152331;--muted:#61717d;--paper:#f5f6f2;--line:#d9dfdc;--card:#fff;--t1:#d65743;--t2:#df913d;--t3:#278e82;--t4:#4f72b5;--qc:#74579c}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Noto Sans KR",sans-serif}.shell{width:min(1440px,calc(100% - 2rem));margin:auto}.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:1.2rem;padding:.72rem max(1rem,calc((100vw - 1440px)/2));background:#071c2cf4;color:white;backdrop-filter:blur(12px)}.brand{margin-right:auto;color:white;text-decoration:none;font-weight:850}.brand small{display:block;color:#83d8ca;font-size:.62rem;letter-spacing:.18em}.topbar nav{display:flex;gap:.25rem;flex-wrap:wrap}.topbar nav a{padding:.45rem .62rem;border-radius:7px;color:#dce6e8;text-decoration:none;font-size:.82rem}.topbar nav a:hover{background:#ffffff18;color:white}.version{font-size:.7rem;color:#83d8ca}.hero{padding:5rem 0 2rem}.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-weight:850;font-size:.72rem;color:#208378}.hero-grid{display:grid;grid-template-columns:1.45fr .75fr;gap:2rem;align-items:center}.hero h1{font-size:clamp(2.6rem,7vw,6.5rem);line-height:.91;letter-spacing:-.065em;margin:.5rem 0 1.3rem}.hero h1 em{color:var(--t3);font-style:normal}.lede{max-width:760px;font-size:1.08rem;line-height:1.75;color:var(--muted)}.hero-actions{display:flex;gap:.7rem;flex-wrap:wrap;margin-top:1.5rem}.button{display:inline-flex;align-items:center;min-height:44px;padding:.7rem 1rem;border:0;border-radius:9px;background:var(--t3);color:white;text-decoration:none;font-weight:800;cursor:pointer}.button.ghost{background:white;color:var(--ink);border:1px solid var(--line)}.orbit{aspect-ratio:1;border-radius:50%;position:relative;border:1px solid #8bccc0;background:radial-gradient(circle,#fff 0 22%,#d8efea 23% 38%,transparent 39%),conic-gradient(from 45deg,#d6574322,#df913d44,#278e8244,#4f72b544,#d6574322);box-shadow:0 30px 70px #1d77632d}.orbit b{position:absolute;inset:42%;display:grid;place-items:center;border-radius:50%;background:var(--navy);color:white;font-size:1.35rem}.orbit span{position:absolute;padding:.38rem .6rem;border-radius:999px;background:white;border:1px solid var(--line);font-weight:850}.orbit .o1{top:5%;left:43%;color:var(--t1)}.orbit .o2{top:43%;right:2%;color:var(--t2)}.orbit .o3{bottom:5%;left:43%;color:var(--t3)}.orbit .o4{top:43%;left:2%;color:var(--t4)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin:2rem 0}.stat{padding:1rem;background:white;border:1px solid var(--line);border-radius:13px}.stat span{display:block;color:var(--muted);font-size:.78rem}.stat strong{font-size:2rem}.notice{padding:1rem 1.2rem;border-left:5px solid #bd4c42;background:#fff1ee;border-radius:8px;font-weight:750}.section{padding:4.3rem 0}.section-head{display:flex;justify-content:space-between;gap:2rem;align-items:end;margin-bottom:1.5rem}.section-head h2{margin:.2rem 0;font-size:clamp(1.8rem,4vw,3.5rem);letter-spacing:-.04em}.section-head>p{max-width:620px;color:var(--muted);line-height:1.65}.grid{display:grid;gap:1rem}.tier-grid{grid-template-columns:repeat(4,1fr)}.tier-card,.disease-card,.metric-card,.evidence-card{border:1px solid var(--line);border-radius:14px;background:white;padding:1.15rem}.tier-card{border-top:5px solid var(--tier)}.tier-card strong{font-size:2.2rem;color:var(--tier)}.tier-card h3,.disease-card h3,.metric-card h3{margin:.4rem 0}.tier-card p,.disease-card p,.metric-card p{color:var(--muted);line-height:1.55}.disease-grid{grid-template-columns:repeat(4,1fr)}.disease-card{cursor:pointer;text-align:left}.disease-card:hover,.disease-card.active{border-color:var(--t3);box-shadow:0 8px 28px #174e4420}.disease-card strong{font-size:1.8rem;color:var(--t3)}.network-section,.analysis-section{background:var(--navy);color:white}.network-panel{padding:1rem;border:1px solid #ffffff22;border-radius:15px;background:#0d283b}.network-toolbar{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1rem}.network-toolbar select{min-height:42px;border-radius:8px;padding:.5rem}.network-scroll{overflow:auto;max-height:680px;background:#f8faf8;border-radius:10px}.network-scroll svg{display:block;min-width:1120px}.edge{fill:none;stroke:#9eaca7;stroke-width:1.3}.family rect{fill:white;stroke:#cad4d0}.family .accent{fill:var(--c);stroke:none}.family text{fill:#193040}.family .count{fill:var(--c);font-weight:850}.family{cursor:pointer}.family:hover rect{stroke:var(--c);stroke-width:2}.filter-bar{position:sticky;top:58px;z-index:10;display:grid;grid-template-columns:2fr repeat(3,1fr);gap:.65rem;padding:.8rem;background:#e8ece9ee;border:1px solid var(--line);border-radius:12px;backdrop-filter:blur(8px)}input,select{min-height:44px;padding:.55rem .7rem;border:1px solid #cbd5d0;border-radius:8px;background:white}.result-row{display:flex;justify-content:space-between;align-items:center;margin:1rem 0;color:var(--muted)}.metric-grid{grid-template-columns:repeat(3,1fr)}.metric-card{cursor:pointer;text-align:left;min-height:210px}.metric-card:hover{transform:translateY(-2px);box-shadow:0 12px 28px #183a3020}.badges{display:flex;gap:.4rem;flex-wrap:wrap}.badge{padding:.25rem .48rem;border-radius:999px;font-size:.68rem;font-weight:850;background:#e7ecea}.badge.tier{background:var(--c);color:white}.metric-card code{display:block;margin-top:.8rem;color:#52636b;word-break:break-all}.metric-card .diseases{color:#1e796f;font-weight:750}.analysis-grid{grid-template-columns:1fr 1.5fr}.analysis-card{padding:1rem;border:1px solid #ffffff22;border-radius:12px;background:#ffffff0c}.analysis-card strong{font-size:1.9rem;color:#7ce0cf}.evidence-grid{grid-template-columns:repeat(2,1fr)}.evidence-card a{color:#176f67;font-weight:800}.sources{padding:1rem;background:#e9efec;border-radius:10px}.sources code{display:block;padding:.25rem;word-break:break-all}dialog{width:min(760px,calc(100% - 2rem));max-height:88vh;border:0;border-radius:16px;padding:0;box-shadow:0 30px 90px #0007}dialog::backdrop{background:#061927b8}.dialog-inner{padding:1.5rem}.dialog-head{display:flex;justify-content:space-between;gap:1rem}.close{border:0;background:#e9eeeb;border-radius:50%;width:38px;height:38px;cursor:pointer;font-size:1.1rem}.detail-list{display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin:1rem 0}.detail-list div{padding:.75rem;background:#f1f4f2;border-radius:8px}.detail-list dt{font-size:.72rem;color:var(--muted);font-weight:800}.detail-list dd{margin:.25rem 0 0;line-height:1.45}.detail-evidence a{display:block;margin:.5rem 0;color:#176f67}.footer{padding:2.5rem;text-align:center;color:var(--muted)}@media(max-width:1000px){.hero-grid{grid-template-columns:1fr}.orbit{display:none}.tier-grid,.disease-grid{grid-template-columns:1fr 1fr}.metric-grid{grid-template-columns:1fr 1fr}.filter-bar{grid-template-columns:1fr 1fr}.topbar nav{display:none}}@media(max-width:650px){.stats,.tier-grid,.disease-grid,.metric-grid,.analysis-grid,.evidence-grid,.detail-list{grid-template-columns:1fr}.filter-bar{grid-template-columns:1fr}.section-head{display:block}.version{display:none}}
</style></head><body>
<header class="topbar"><a class="brand" href="#top">Ophthalmic Medical Metric Atlas<small>OCULOPHENOME XAI</small></a><nav><a href="#hierarchy">Tier map</a><a href="#diseases">Disease map</a><a href="#network">Lineage</a><a href="#explorer">190 metrics</a><a href="#analysis">QC</a><a href="#evidence">Evidence</a></nav><span class="version">ONTOLOGY · 2.0</span></header>
<main id="top"><section class="hero shell"><div class="hero-grid"><div><p class="eyebrow">Clinician-native → model-derived</p><h1>안과 정량지표와<br><em>질병 근거의 계보</em></h1><p class="lede">임상 기준값, 전문의 annotation 파생계측, 영상 phenotype, AI·hybrid 산출량을 T1–T4로 연결합니다. 190개 계산기의 실제 합성 계산값과 질병 맥락, 근거 수준, QC 경계를 한 화면에서 탐색합니다.</p><div class="hero-actions"><a class="button" href="#diseases">질병별 탐색</a><a class="button ghost" href="#explorer">190개 전체 검색</a></div></div><div class="orbit" aria-hidden="true"><b>Eye</b><span class="o1">T1</span><span class="o2">T2</span><span class="o3">T3</span><span class="o4">T4</span></div></div><div class="stats" id="summary-stats"></div><p class="notice">연구용 분류체계 · 질병 연관성은 단독 진단을 의미하지 않으며 실제 환자 결과가 아닙니다.</p></section>
<section id="hierarchy" class="section shell"><div class="section-head"><div><p class="eyebrow">Metric hierarchy</p><h2>임상 기준축에서 모델까지</h2></div><p>Tier는 우열이 아니라 임상 기준값에서 얼마나 파생됐는지를 나타냅니다. 성능평가와 영상 QC는 환자 상태 지표와 분리합니다.</p></div><div class="grid tier-grid" id="tier-map"></div></section>
<section id="diseases" class="section shell"><div class="section-head"><div><p class="eyebrow">Disease context</p><h2>질병에서 지표로 들어가기</h2></div><p>질병 카드를 누르면 190개 explorer가 해당 질병 맥락으로 필터됩니다. 질병 비특이적 endpoint와 QC는 별도로 유지합니다.</p></div><div class="grid disease-grid" id="disease-grid"></div></section>
<section id="network" class="section network-section"><div class="shell"><div class="section-head"><div><p class="eyebrow">Lineage graph</p><h2>안과 지표 family의 실제 연결</h2></div><p>선은 clinical image·전문의 annotation·진단·기록에서 파생 family로 이어지는 parent 관계입니다.</p></div><div class="network-panel"><div class="network-toolbar"><strong id="network-count"></strong><select id="network-disease" aria-label="질병으로 계보 필터"></select></div><div class="network-scroll" tabindex="0"><svg id="lineage-svg" role="img" aria-label="T1에서 T4 안과 지표 family 계보"></svg></div></div></div></section>
<section id="explorer" class="section shell"><div class="section-head"><div><p class="eyebrow">Metric explorer</p><h2>190개 계산기 찾아보기</h2></div><p>카드를 누르면 입력, 단위, 계산값, 질병 역할과 근거 논문을 함께 확인할 수 있습니다.</p></div><div class="filter-bar"><input id="search" type="search" placeholder="지표·질병·역할·domain 검색"><select id="tier-filter"></select><select id="disease-filter"></select><select id="registry-filter"><option value="ALL">전체 registry</option><option value="MEDICAL">T1–T4 의료·파생</option><option value="QC">영상 QC</option><option value="VALIDATION">알고리즘 검증</option></select></div><div class="result-row"><strong id="result-count"></strong><button class="button ghost" id="reset-filters" type="button">필터 초기화</button></div><div class="grid metric-grid" id="metric-grid"></div></section>
<section id="analysis" class="section analysis-section"><div class="shell"><div class="section-head"><div><p class="eyebrow">Separate by design</p><h2>QC·성능평가는 별도 레지스트리</h2></div><p>색상·조명·FOV·mask agreement는 중요한 계산값이지만 환자의 질병 상태를 직접 나타내지 않습니다.</p></div><div class="grid analysis-grid" id="analysis-grid"></div></div></section>
<section id="evidence" class="section shell"><div class="section-head"><div><p class="eyebrow">Primary evidence</p><h2>질병 연결 근거</h2></div><p>근거 ID를 클릭하면 원 논문으로 이동합니다. 모델 target 연결은 외부검증 전 임상 진단에 사용할 수 없습니다.</p></div><div class="grid evidence-grid" id="evidence-grid"></div><div class="sources"><h3>Single source of truth</h3><div id="source-paths"></div></div></section></main>
<dialog id="detail"><div class="dialog-inner"><div class="dialog-head"><div><div class="badges" id="detail-badges"></div><h2 id="detail-title"></h2><code id="detail-id"></code></div><button class="close" type="button" aria-label="닫기">×</button></div><p id="detail-note" class="notice"></p><dl class="detail-list" id="detail-list"></dl><div class="detail-evidence" id="detail-evidence"></div></div></dialog>
<footer class="footer">OcuPhenome XAI · P001 · E017 · 190개 synthetic calculator registry · 갱신 <span id="updated"></span></footer>
<script>window.OPHTHALMIC_METRIC_ATLAS=__CATALOG_JSON__;</script>
<script>
(function(){"use strict";const C=window.OPHTHALMIC_METRIC_ATLAS;const COLORS={T1:"#d65743",T2:"#df913d",T3:"#278e82",T4:"#4f72b5",ANALYSIS:"#74579c"};const state={tier:"ALL",disease:"ALL",registry:"ALL",query:""};const byId=new Map(C.metrics.map(m=>[m.id,m]));const evById=new Map(C.evidence.map(e=>[e.id,e]));const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");document.getElementById("updated").textContent=C.generated;
function renderSummary(){const s=C.summary;document.getElementById("summary-stats").innerHTML=[['전체 계산기',s.calculator_total],['T1–T4',s.medical_tier_total],['질병 context',s.disease_linked_total],['QC·검증',s.analysis_registry_total]].map(x=>`<article class="stat"><span>${x[0]}</span><strong>${x[1]}</strong></article>`).join("")}
function renderTiers(){document.getElementById("tier-map").innerHTML=C.tier_meta.map(t=>`<article class="tier-card" style="--tier:${COLORS[t.tier]}"><span>${esc(t.name_en)}</span><strong>${t.tier}</strong><h3>${esc(t.name)}</h3><p>${esc(t.description)}</p><b>${C.summary.tier_counts[t.tier]||0} calculators</b></article>`).join("")}
function diseaseOptions(allLabel){return [`<option value="ALL">${allLabel}</option>`,...C.diseases.map(d=>`<option value="${d.id}">${esc(d.label)} · ${d.count}</option>`)].join("")}
function setDisease(id){state.disease=id;document.getElementById("disease-filter").value=id;document.getElementById("network-disease").value=id;document.querySelectorAll(".disease-card").forEach(x=>x.classList.toggle("active",x.dataset.id===id));renderMetrics();renderNetwork();document.getElementById("explorer").scrollIntoView({behavior:"smooth"})}
function renderDiseases(){document.getElementById("disease-grid").innerHTML=C.diseases.map(d=>`<button class="disease-card" data-id="${d.id}" type="button"><span>${d.id}</span><h3>${esc(d.label)}</h3><strong>${d.count}</strong><p>연결된 계산기 · 단독 진단용 아님</p></button>`).join("");document.getElementById("disease-grid").addEventListener("click",e=>{const b=e.target.closest("[data-id]");if(b)setDisease(b.dataset.id)})}
function renderNetwork(){const selected=state.disease;const families=C.families.filter(f=>selected==="ALL"||!f.disease_ids||f.disease_ids.includes(selected)||f.id.startsWith("anchor."));const visible=new Set(families.map(f=>f.id));const tiers=["T1","T2","T3","T4"],ordered=Object.fromEntries(tiers.map(t=>[t,families.filter(f=>f.tier===t)]));const max=Math.max(1,...tiers.map(t=>ordered[t].length)),row=62,top=72,width=1120,height=top+max*row+45,x={T1:15,T2:300,T3:585,T4:870},pos=new Map(),nodeW=235,nodeH=42;tiers.forEach(t=>ordered[t].forEach((f,i)=>pos.set(f.id,{x:x[t],y:top+i*row})));let s=`<title>안과 정량지표 family T1–T4 계보</title>`;tiers.forEach(t=>{s+=`<text x="${x[t]}" y="30" font-weight="850" fill="${COLORS[t]}">${t} · ${ordered[t].length}</text>`});families.forEach(f=>(f.parents||[]).filter(p=>visible.has(p)).forEach(p=>{const a=pos.get(p),b=pos.get(f.id);if(!a||!b)return;const sx=a.x+nodeW,sy=a.y+nodeH/2,ex=b.x,ey=b.y+nodeH/2;s+=`<path class="edge" d="M ${sx} ${sy} C ${sx+30} ${sy}, ${ex-30} ${ey}, ${ex} ${ey}"></path>`}));tiers.forEach(t=>ordered[t].forEach(f=>{const p=pos.get(f.id);s+=`<g class="family" data-family="${f.id}" transform="translate(${p.x} ${p.y})" style="--c:${COLORS[t]}"><rect width="${nodeW}" height="${nodeH}" rx="8"></rect><rect class="accent" width="5" height="${nodeH}" rx="3"></rect><text x="13" y="18">${esc(f.name)}</text><text class="count" x="13" y="34">${f.count} metrics</text></g>`}));const svg=document.getElementById("lineage-svg");svg.setAttribute("viewBox",`0 0 ${width} ${height}`);svg.setAttribute("height",height);svg.innerHTML=s;document.getElementById("network-count").textContent=`${families.length} family nodes`;svg.querySelectorAll("[data-family]").forEach(n=>n.addEventListener("click",()=>{state.query=n.dataset.family.split(".").slice(1).join(" ");document.getElementById("search").value=state.query;renderMetrics();document.getElementById("explorer").scrollIntoView({behavior:"smooth"})}))}
function filtered(){const q=state.query.trim().toLowerCase();return C.metrics.filter(m=>(state.tier==="ALL"||m.tier===state.tier)&&(state.disease==="ALL"||m.disease_ids.includes(state.disease))&&(state.registry==="ALL"||m.registry===state.registry)&&(!q||[m.metric_id,m.collection,m.domain,m.domain_label,m.clinical_role,...m.disease_labels].join(" ").toLowerCase().includes(q)))}
function renderMetrics(){const rows=filtered();document.getElementById("result-count").textContent=`${rows.length} / ${C.metrics.length} metrics`;document.getElementById("metric-grid").innerHTML=rows.map(m=>`<button class="metric-card" type="button" data-id="${esc(m.id)}"><div class="badges"><span class="badge tier" style="--c:${COLORS[m.tier]}">${m.tier}</span><span class="badge">${m.registry}</span><span class="badge">${esc(m.evidence_level)}</span></div><h3>${esc(m.metric_id)}</h3><p>${esc(m.domain_label)} · ${esc(m.modality)} · ${esc(m.method)}</p><p class="diseases">${esc(m.disease_labels.join(" · ")||"질병 비특이적")}</p><p>${esc(m.clinical_role)}</p><code>${esc(m.collection)}</code></button>`).join("")||'<p>조건에 맞는 지표가 없습니다.</p>'}
function openDetail(id){const m=byId.get(id);if(!m)return;document.getElementById("detail-badges").innerHTML=`<span class="badge tier" style="--c:${COLORS[m.tier]}">${m.tier}</span><span class="badge">${m.registry}</span><span class="badge">${esc(m.evidence_level)}</span>`;document.getElementById("detail-title").textContent=m.metric_id;document.getElementById("detail-id").textContent=m.id;document.getElementById("detail-note").textContent=m.clinical_note;const rows={"질병 연결":m.disease_labels.join(" · ")||"질병 비특이적","임상 역할":m.clinical_role,"Domain":m.domain_label,"Modality":m.modality,"Method":m.method,"Input":m.input_source,"합성 계산값":m.value===null?"—":String(m.value),"Unit":m.unit,"Algorithm":m.algorithm_version,"단독 진단":m.standalone_diagnostic?"허용":"허용하지 않음"};document.getElementById("detail-list").innerHTML=Object.entries(rows).map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");document.getElementById("detail-evidence").innerHTML=m.evidence_ids.length?'<h3>근거 논문</h3>'+m.evidence_ids.map(id=>{const e=evById.get(id);return `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.identifier)} · ${esc(e.title)}</a>`}).join(""):'<p>직접 질병 근거 없음 · QC/탐색/target-dependent 분류</p>';document.getElementById("detail").showModal()}
function renderAnalysis(){const groups=[{id:"QC",title:"영상 QC",text:"색상·조명·선명도·FOV·실패 통제"},{id:"VALIDATION",title:"알고리즘 검증",text:"Dice·IoU·precision·recall·specificity"}];document.getElementById("analysis-grid").innerHTML=groups.map(g=>{const n=C.metrics.filter(m=>m.registry===g.id).length;return `<article class="analysis-card"><span>${g.id}</span><h3>${g.title}</h3><strong>${n}</strong><p>${g.text}</p></article>`}).join("")}
function renderEvidence(){document.getElementById("evidence-grid").innerHTML=C.evidence.map(e=>`<article class="evidence-card"><span>${esc(e.design)}</span><h3>${esc(e.identifier)}</h3><p>${esc(e.title)}</p><a href="${esc(e.url)}" target="_blank" rel="noopener">원 논문 열기 ↗</a></article>`).join("");document.getElementById("source-paths").innerHTML=C.source_paths.map(x=>`<code>${esc(x)}</code>`).join("")}
document.getElementById("tier-filter").innerHTML=['<option value="ALL">전체 Tier</option>',...C.tier_meta.map(t=>`<option value="${t.tier}">${t.tier} · ${esc(t.name)}</option>`),'<option value="ANALYSIS">QC·검증 registry</option>'].join("");document.getElementById("disease-filter").innerHTML=diseaseOptions("전체 질병");document.getElementById("network-disease").innerHTML=diseaseOptions("전체 질병 계보");document.getElementById("search").addEventListener("input",e=>{state.query=e.target.value;renderMetrics()});document.getElementById("tier-filter").addEventListener("change",e=>{state.tier=e.target.value;renderMetrics()});document.getElementById("disease-filter").addEventListener("change",e=>setDisease(e.target.value));document.getElementById("network-disease").addEventListener("change",e=>{state.disease=e.target.value;document.getElementById("disease-filter").value=state.disease;renderNetwork();renderMetrics()});document.getElementById("registry-filter").addEventListener("change",e=>{state.registry=e.target.value;renderMetrics()});document.getElementById("metric-grid").addEventListener("click",e=>{const b=e.target.closest("[data-id]");if(b)openDetail(b.dataset.id)});document.getElementById("reset-filters").addEventListener("click",()=>{Object.assign(state,{tier:"ALL",disease:"ALL",registry:"ALL",query:""});["search","tier-filter","disease-filter","network-disease","registry-filter"].forEach(id=>document.getElementById(id).value=id==="search"?"":"ALL");document.querySelectorAll(".disease-card").forEach(x=>x.classList.remove("active"));renderNetwork();renderMetrics()});document.querySelector(".close").addEventListener("click",()=>document.getElementById("detail").close());document.getElementById("detail").addEventListener("click",e=>{if(e.target===e.currentTarget)e.currentTarget.close()});renderSummary();renderTiers();renderDiseases();renderNetwork();renderMetrics();renderAnalysis();renderEvidence();})();
</script></body></html>'''


def write_medical_metric_atlas(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(build_atlas_catalog(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    target.write_text(HTML_TEMPLATE.replace("__CATALOG_JSON__", encoded), encoding="utf-8")
    return target
