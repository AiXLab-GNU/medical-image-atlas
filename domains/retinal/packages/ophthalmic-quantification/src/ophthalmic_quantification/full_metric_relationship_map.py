"""Build a complete 190-node metric, tier-lineage, and disease relationship map."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

from .atlas import build_atlas_catalog


def build_full_metric_relationship_catalog() -> dict[str, Any]:
    """Return all calculators and only explicitly typed relationship layers."""
    atlas = build_atlas_catalog()
    metrics = [
        {
            key: metric[key]
            for key in (
                "id",
                "metric_id",
                "collection",
                "tier",
                "registry",
                "family_id",
                "domain_label",
                "modality",
                "clinical_role",
                "disease_ids",
                "disease_labels",
                "evidence_level",
            )
        }
        for metric in atlas["metrics"]
    ]
    metrics_by_family: dict[str, list[dict[str, Any]]] = {}
    for metric in metrics:
        metrics_by_family.setdefault(str(metric["family_id"]), []).append(metric)

    families = []
    for family in atlas["families"]:
        family_metrics = metrics_by_family.get(str(family["id"]), [])
        families.append(
            {
                **family,
                "metric_ids": [metric["id"] for metric in family_metrics],
            }
        )
    for family_id, name, registry in (
        ("analysis.qc", "영상 QC", "QC"),
        ("analysis.validation", "알고리즘 검증", "VALIDATION"),
    ):
        family_metrics = metrics_by_family.get(family_id, [])
        families.append(
            {
                "id": family_id,
                "tier": "ANALYSIS",
                "name": name,
                "count": len(family_metrics),
                "parents": [],
                "disease_ids": [],
                "registry": registry,
                "metric_ids": [metric["id"] for metric in family_metrics],
            }
        )

    lineage_edges = [
        {
            "source_family_id": parent,
            "target_family_id": family["id"],
            "relation_type": "explicit_lineage",
        }
        for family in families
        for parent in family.get("parents", [])
    ]

    family_lookup = {str(family["id"]): family for family in families}
    metric_lookup = {str(metric["id"]): metric for metric in metrics}
    cross_tier_edges = []
    for source_tier, target_tier, scope in (
        ("T1", "T2", "T1_T2"),
        ("T3", "T4", "T3_T4"),
    ):
        source_families = [
            family for family in families if family["tier"] == source_tier and family["metric_ids"]
        ]
        target_families = [
            family for family in families if family["tier"] == target_tier and family["metric_ids"]
        ]
        for source in source_families:
            source_diseases = {
                disease_id
                for metric_id in source["metric_ids"]
                for disease_id in metric_lookup[metric_id]["disease_ids"]
            }
            for target in target_families:
                target_diseases = {
                    disease_id
                    for metric_id in target["metric_ids"]
                    for disease_id in metric_lookup[metric_id]["disease_ids"]
                }
                shared = sorted(source_diseases & target_diseases)
                if not shared:
                    continue
                source_metric_ids = [
                    metric_id
                    for metric_id in source["metric_ids"]
                    if set(metric_lookup[metric_id]["disease_ids"]) & set(shared)
                ]
                target_metric_ids = [
                    metric_id
                    for metric_id in target["metric_ids"]
                    if set(metric_lookup[metric_id]["disease_ids"]) & set(shared)
                ]
                cross_tier_edges.append(
                    {
                        "source_family_id": source["id"],
                        "target_family_id": target["id"],
                        "source_metric_ids": source_metric_ids,
                        "target_metric_ids": target_metric_ids,
                        "shared_disease_ids": shared,
                        "metric_pair_count": len(source_metric_ids) * len(target_metric_ids),
                        "relation_type": "shared_disease_context",
                        "scope": scope,
                    }
                )

    disease_edges = [
        {
            "disease_id": disease_id,
            "metric_id": metric["id"],
            "relation_type": "explicit_disease_context",
        }
        for metric in metrics
        for disease_id in metric["disease_ids"]
    ]
    diseases = [
        {
            **disease,
            "metric_ids": [
                metric["id"] for metric in metrics if disease["id"] in metric["disease_ids"]
            ],
        }
        for disease in atlas["diseases"]
    ]
    tier_counts = {
        tier: sum(metric["tier"] == tier for metric in metrics)
        for tier in ("T1", "T2", "T3", "T4", "ANALYSIS")
    }
    return {
        "version": "1.0",
        "generated": date.today().isoformat(),
        "summary": {
            "metric_total": len(metrics),
            "tier_counts": tier_counts,
            "disease_total": len(diseases),
            "disease_edge_total": len(disease_edges),
            "lineage_edge_total": len(lineage_edges),
            "cross_tier_edge_total": len(cross_tier_edges),
        },
        "metrics": metrics,
        "families": families,
        "diseases": diseases,
        "disease_edges": disease_edges,
        "lineage_edges": lineage_edges,
        "cross_tier_edges": cross_tier_edges,
        "family_names": {
            family_id: str(family_lookup[family_id]["name"]) for family_id in family_lookup
        },
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="190개 안과 정량지표의 Tier 계보와 질병 연결을 모두 표시한 관계 지도">
<title>190개 전체 지표 관계 지도 · OcuPhenome XAI</title>
<style>
:root{--navy:#071c2c;--ink:#172735;--muted:#687984;--paper:#f3f6f3;--line:#d7dfdc;--t1:#d65743;--t2:#df913d;--t3:#278e82;--t4:#4f72b5;--analysis:#74579c;--disease:#087f75;--context:#aa4d87}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font-family:Inter,system-ui,-apple-system,"Noto Sans KR",sans-serif}.topbar{position:sticky;top:0;z-index:30;display:flex;gap:.4rem;align-items:center;padding:.65rem max(1rem,calc((100vw - 1600px)/2));background:#071c2cf3;backdrop-filter:blur(12px)}.topbar a{padding:.44rem .65rem;color:#dce8ea;text-decoration:none;border-radius:8px;font-size:.78rem;font-weight:850}.topbar a:first-child{color:#91e0d4}.topbar a:hover{background:#ffffff17;color:white}.topbar b{margin-left:auto;color:#91e0d4;font-size:.72rem}.shell{width:min(1600px,calc(100% - 2rem));margin:auto}.hero{padding:3.2rem 0 1.4rem}.eyebrow{margin:0 0 .45rem;color:#168076;font-size:.7rem;font-weight:900;letter-spacing:.15em;text-transform:uppercase}.hero h1{max-width:1050px;margin:.1rem 0;font-size:clamp(2.2rem,5vw,5.2rem);line-height:.98;letter-spacing:-.055em}.hero>p{max-width:940px;color:var(--muted);line-height:1.7}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:.7rem;margin:1.2rem 0}.stat{padding:.9rem;background:white;border:1px solid var(--line);border-radius:11px}.stat span{display:block;color:var(--muted);font-size:.72rem}.stat strong{font-size:1.65rem}.notice{padding:1rem;color:#6f4517;background:#fff3df;border-left:5px solid var(--t2);border-radius:8px}.map-panel{margin-bottom:1.2rem;padding:1rem;background:var(--navy);border-radius:17px}.map-toolbar{position:sticky;top:52px;z-index:15;display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;padding:.7rem;color:white;background:#0c293cea;border:1px solid #ffffff1c;border-radius:10px}.map-toolbar strong{margin-right:auto}.map-toolbar input,.map-toolbar select,.map-toolbar button{min-height:38px;padding:.45rem .65rem;border:1px solid #ffffff2d;border-radius:7px;background:white}.map-toolbar input{min-width:260px}.map-toolbar button{cursor:pointer;font-weight:850}.legend{display:flex;gap:.7rem;flex-wrap:wrap;padding:.8rem .2rem;color:#dce7e8;font-size:.75rem}.legend i{display:inline-block;width:28px;margin-right:.3rem;vertical-align:middle;border-top:3px solid}.legend .lineage{border-color:#304c60}.legend .context{border-color:var(--context);border-top-style:dashed}.legend .disease{border-color:var(--disease)}.top-scroll{height:18px;overflow-x:scroll;overflow-y:hidden;background:#e7eeeb;border-radius:7px 7px 0 0}.top-scroll>div{height:1px}.map-scroll{max-height:76vh;overflow:auto;background:#fafcf9;border-radius:0 0 9px 9px;cursor:grab}.map-scroll:active{cursor:grabbing}.map-scroll svg{display:block;max-width:none;background:linear-gradient(#ffffffcc,#f8fbf8)}.family-box{fill:#f4f7f5;stroke:#d3dcd8}.family-title{fill:#253d4c;font-size:13px;font-weight:900}.family-count{fill:#687984;font-size:11px}.metric-node{cursor:pointer}.metric-node rect{fill:white;stroke:#d4ddda}.metric-node .accent{fill:var(--tier);stroke:none}.metric-node text{fill:#203947;font-size:10.5px}.metric-node:hover rect,.metric-node.active rect{stroke:var(--tier);stroke-width:2.5}.metric-node.dim{opacity:.12}.anchor-node rect,.disease-node rect{fill:white;stroke:#bad3ce}.anchor-node text,.disease-node text{fill:#173d43;font-size:12px;font-weight:800}.disease-node{cursor:pointer}.disease-node:hover rect,.disease-node.active rect{stroke:var(--disease);stroke-width:3}.column-label{font-size:16px;font-weight:950;letter-spacing:.08em}.edge{fill:none;transition:opacity .15s}.disease-edge{stroke:var(--disease);stroke-width:1;stroke-opacity:.13}.lineage-edge{stroke:#304c60;stroke-width:3;stroke-opacity:.55}.context-edge{stroke:var(--context);stroke-width:4;stroke-dasharray:11 7;stroke-opacity:.58}.edge.dim{stroke-opacity:.018}.edge.active{stroke-opacity:.95;stroke-width:4}.edge.layer-hidden{display:none}.relation-label{fill:#873b6e;font-size:11px;font-weight:850}.detail{display:grid;grid-template-columns:290px 1fr;gap:1rem;margin:0 auto 1.5rem;padding:1.2rem;background:white;border:1px solid var(--line);border-radius:13px}.detail h2{margin:.2rem 0;word-break:break-word}.detail p{color:var(--muted);line-height:1.55}.chips{display:flex;gap:.35rem;flex-wrap:wrap;max-height:200px;overflow:auto}.chips code{padding:.3rem .45rem;background:#edf2f0;border-radius:6px;font-size:.72rem}.scope{margin-bottom:3rem;padding:1rem;background:#e9eeeb;border-radius:9px;color:var(--muted);line-height:1.6}.footer{padding:2rem;text-align:center;color:var(--muted)}@media(max-width:900px){.topbar b{display:none}.stats{grid-template-columns:1fr 1fr}.map-toolbar strong{width:100%}.map-toolbar input{min-width:0;flex:1}.detail{display:block}}
</style></head><body>
<nav class="topbar" aria-label="지도 이동"><a href="ophthalmic_quantitative_metric_examples_v01_ko.html">← 190개 계산 예제</a><a href="ophthalmic_disease_metric_map_v01_ko.html">질병–지표 지도</a><a href="/">⌂ 포털 홈</a><b>ALL 190 METRICS · TIER × DISEASE</b></nav>
<header class="hero shell"><p class="eyebrow">Complete relationship map</p><h1>190개 전체 지표<br>관계 지도</h1><p>모든 계산기를 T1·T2·T3·T4와 Analysis/QC 열에 빠짐없이 배치하고, 명시적 파생 계보와 T1↔T2·T3↔T4의 공통 질병 맥락, 질병–개별 지표 연결을 함께 표시합니다.</p><div id="summary" class="stats"></div><p class="notice"><b>선의 의미:</b> 실선 계보는 정의된 parent 관계, 점선은 같은 질병을 공유하는 관계입니다. 점선은 인과·파생 또는 진단 성능을 의미하지 않습니다.</p></header>
<main class="shell"><section class="map-panel"><div class="map-toolbar"><strong id="map-count">190 metric nodes</strong><input id="metric-search" type="search" placeholder="지표 ID·질병·family 검색"><select id="relationship-layer" aria-label="관계선 선택"><option value="ALL">모든 관계선</option><option value="DISEASE">질병–지표만</option><option value="T1_T2">T1 ↔ T2 공통 맥락</option><option value="T3_T4">T3 ↔ T4 공통 맥락</option><option value="LINEAGE">명시적 계보만</option><option value="NONE">관계선 숨기기</option></select><button id="zoom-out" type="button">−</button><button id="zoom-reset" type="button">100%</button><button id="zoom-in" type="button">+</button><button id="fit-map" type="button">전체 맞춤</button></div><div class="legend"><span><i class="lineage"></i>명시적 파생 계보</span><span><i class="context"></i>공통 질병 맥락</span><span><i class="disease"></i>질병–개별 지표</span></div><div id="map-scroll-top" class="top-scroll" tabindex="0" aria-label="지도 위쪽 가로 스크롤"><div></div></div><div id="full-map-scroll" class="map-scroll" tabindex="0"><svg id="full-metric-svg" role="img" aria-label="190개 안과 정량지표 Tier와 질병 전체 관계 지도"></svg></div></section><section id="metric-detail" class="detail" aria-live="polite"><div><p class="eyebrow">Selected node</p><h2 id="detail-title">전체 지도</h2><p id="detail-summary">노드를 클릭하면 연결 관계를 강조합니다.</p><button id="reset-selection" type="button">선택 초기화</button></div><div><p id="detail-context">190개 지표가 모두 표시되어 있습니다.</p><div id="detail-items" class="chips"></div></div></section><p class="scope"><b>해석 범위:</b> 질병 연결은 연구·모니터링 맥락이며 단독 진단을 뜻하지 않습니다. Analysis 79개(QC 73, 검증 6)는 전체성 확보를 위해 표시하지만 의료 Tier 계보와 분리합니다.</p></main>
<footer class="footer">OcuPhenome XAI · P001 · E017 · 190/190 nodes · 갱신 <span id="updated"></span></footer>
<script>window.OPHTHALMIC_FULL_METRIC_RELATIONSHIP_MAP=__MAP_JSON__;</script>
<script>
(function(){"use strict";const C=window.OPHTHALMIC_FULL_METRIC_RELATIONSHIP_MAP;const COLORS={T1:'#d65743',T2:'#df913d',T3:'#278e82',T4:'#4f72b5',ANALYSIS:'#74579c'};const svg=document.getElementById('full-metric-svg'),scroll=document.getElementById('full-map-scroll'),topScroll=document.getElementById('map-scroll-top'),metricById=new Map(C.metrics.map(x=>[x.id,x])),familyById=new Map(C.families.map(x=>[x.id,x])),diseaseById=new Map(C.diseases.map(x=>[x.id,x]));const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');let scale=1,syncing=false;const W=2820,nodeW=410,nodeH=22,row=27,gap=18,top=74,x={SOURCE:20,T1:410,T2:890,T3:1370,T4:1850,ANALYSIS:2330},familyPos=new Map(),metricPos=new Map(),diseasePos=new Map();
function layoutColumn(tier){let y=top;C.families.filter(f=>f.tier===tier&&!f.id.startsWith('anchor.')).forEach(f=>{const ids=f.metric_ids||[];const h=34+ids.length*row+8;familyPos.set(f.id,{x:x[tier],y,center:y+h/2,w:nodeW,h});ids.forEach((id,i)=>metricPos.set(id,{x:x[tier]+6,y:y+30+i*row}));y+=h+gap});return y}
const heights=['T1','T2','T3','T4','ANALYSIS'].map(layoutColumn);C.diseases.forEach((d,i)=>diseasePos.set(d.id,{x:x.SOURCE,y:top+i*36}));C.families.filter(f=>f.id.startsWith('anchor.')).forEach((f,i)=>familyPos.set(f.id,{x:x.SOURCE,y:top+C.diseases.length*36+65+i*48,center:top+C.diseases.length*36+65+i*48+17,w:320,h:34}));const H=Math.max(...heights,top+C.diseases.length*36+300)+40;
function curve(a,b){const sx=a.x+(a.w||nodeW),sy=a.center??a.y+nodeH/2,ex=b.x,ey=b.center??b.y+nodeH/2,m=(sx+ex)/2;return `M ${sx} ${sy} C ${m} ${sy}, ${m} ${ey}, ${ex} ${ey}`}
function render(){let s='<title>190개 안과 정량지표 Tier·질병 전체 관계</title>';Object.entries({SOURCE:'질병 · 입력 앵커',T1:'T1 · 3',T2:'T2 · 41',T3:'T3 · 58',T4:'T4 · 9',ANALYSIS:'ANALYSIS · 79'}).forEach(([tier,label])=>s+=`<text class="column-label" x="${x[tier]}" y="34" fill="${COLORS[tier]||'#087f75'}">${label}</text>`);C.disease_edges.forEach(e=>{const a=diseasePos.get(e.disease_id),b=metricPos.get(e.metric_id);if(a&&b)s+=`<path class="edge disease-edge" data-edge-disease="${e.disease_id}" data-edge-metric="${esc(e.metric_id)}" d="${curve({x:a.x,y:a.y,w:320},b)}"></path>`});C.lineage_edges.forEach(e=>{const a=familyPos.get(e.source_family_id),b=familyPos.get(e.target_family_id);if(a&&b)s+=`<path class="edge lineage-edge" data-lineage-source="${e.source_family_id}" data-lineage-target="${e.target_family_id}" d="${curve(a,b)}"><title>명시적 계보 · ${esc(C.family_names[e.source_family_id])} → ${esc(C.family_names[e.target_family_id])}</title></path>`});C.cross_tier_edges.forEach(e=>{const a=familyPos.get(e.source_family_id),b=familyPos.get(e.target_family_id);if(a&&b){s+=`<path class="edge context-edge" data-context-scope="${e.scope}" data-context-source="${e.source_family_id}" data-context-target="${e.target_family_id}" d="${curve(a,b)}"><title>${e.scope} · 공통 질병 ${esc(e.shared_disease_ids.join(', '))} · ${e.metric_pair_count} metric pairs</title></path>`;const mx=(a.x+a.w+b.x)/2,my=(a.center+b.center)/2;s+=`<text class="relation-label" x="${mx}" y="${my-5}">${e.metric_pair_count} pairs · ${esc(e.shared_disease_ids.join('/'))}</text>`}});C.diseases.forEach(d=>{const p=diseasePos.get(d.id);s+=`<g class="disease-node" data-disease-node="${d.id}" transform="translate(${p.x} ${p.y})"><rect width="320" height="28" rx="7"></rect><text x="10" y="19">${esc(d.label)} · ${d.count}</text></g>`});C.families.filter(f=>f.id.startsWith('anchor.')).forEach(f=>{const p=familyPos.get(f.id);s+=`<g class="anchor-node" data-family-node="${f.id}" transform="translate(${p.x} ${p.y})"><rect width="320" height="34" rx="8"></rect><text x="10" y="22">${esc(f.name)}</text></g>`});C.families.filter(f=>!f.id.startsWith('anchor.')).forEach(f=>{const p=familyPos.get(f.id);if(!p)return;s+=`<g data-family-node="${f.id}"><rect class="family-box" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="9"></rect><text class="family-title" x="${p.x+10}" y="${p.y+18}">${esc(f.name)}</text><text class="family-count" x="${p.x+p.w-70}" y="${p.y+18}">${f.count} metrics</text></g>`;(f.metric_ids||[]).forEach(id=>{const m=metricById.get(id),q=metricPos.get(id);s+=`<g class="metric-node" data-metric-node="${esc(id)}" data-tier="${m.tier}" data-family="${m.family_id}" transform="translate(${q.x} ${q.y})" style="--tier:${COLORS[m.tier]}"><rect width="${nodeW-12}" height="${nodeH}" rx="5"></rect><rect class="accent" width="5" height="${nodeH}" rx="3"></rect><text x="11" y="15">${esc(m.metric_id)} · ${esc(m.collection)}</text><title>${esc(m.metric_id)} · ${esc(m.domain_label)} · ${esc(m.disease_labels.join(', ')||'질병 비특이적')}</title></g>`})});svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.innerHTML=s;setScale(1);bindNodes()}
function setScale(value,fit=false){scale=Math.max(.35,Math.min(1.8,value));svg.style.width=fit?'100%':`${W*scale}px`;svg.style.height=fit?'auto':`${H*scale}px`;document.getElementById('zoom-reset').textContent=fit?'맞춤':`${Math.round(scale*100)}%`;requestAnimationFrame(()=>topScroll.firstElementChild.style.width=svg.getBoundingClientRect().width+'px')}
function layer(value){svg.querySelectorAll('.edge').forEach(e=>{const visible=value==='ALL'||(value==='DISEASE'&&e.classList.contains('disease-edge'))||(value==='LINEAGE'&&e.classList.contains('lineage-edge'))||(e.classList.contains('context-edge')&&e.dataset.contextScope===value);e.classList.toggle('layer-hidden',!visible)});svg.querySelectorAll('.relation-label').forEach(e=>e.style.display=value==='ALL'||value.startsWith('T')?'':'none')}
function clearHighlight(){svg.querySelectorAll('.dim,.active').forEach(e=>e.classList.remove('dim','active'))}
function highlightMetric(id){clearHighlight();svg.querySelectorAll('.metric-node').forEach(n=>n.classList.toggle('dim',n.dataset.metricNode!==id));svg.querySelector(`[data-metric-node="${CSS.escape(id)}"]`)?.classList.add('active');svg.querySelectorAll('.edge').forEach(e=>{const active=e.dataset.edgeMetric===id||e.dataset.lineageSource===metricById.get(id).family_id||e.dataset.lineageTarget===metricById.get(id).family_id||e.dataset.contextSource===metricById.get(id).family_id||e.dataset.contextTarget===metricById.get(id).family_id;e.classList.toggle('active',active);e.classList.toggle('dim',!active)});const m=metricById.get(id);show(m.metric_id,`${m.tier} · ${m.domain_label} · ${m.registry}`,`${m.disease_labels.join(' · ')||'질병 비특이적'} · ${m.clinical_role}`,[m.collection,m.family_id,m.evidence_level])}
function highlightDisease(id){clearHighlight();const d=diseaseById.get(id),ids=new Set(d.metric_ids);svg.querySelectorAll('.metric-node').forEach(n=>n.classList.toggle('dim',!ids.has(n.dataset.metricNode)));svg.querySelector(`[data-disease-node="${id}"]`)?.classList.add('active');svg.querySelectorAll('.edge').forEach(e=>{const active=e.dataset.edgeDisease===id||(e.classList.contains('context-edge')&&C.cross_tier_edges.some(x=>x.scope===e.dataset.contextScope&&x.shared_disease_ids.includes(id)));e.classList.toggle('active',active);e.classList.toggle('dim',!active)});show(d.label,`${d.count}개 연결 지표`,'명시적으로 연결된 지표만 강조합니다.',d.metric_ids.map(x=>metricById.get(x).metric_id))}
function highlightFamily(id){clearHighlight();const f=familyById.get(id),ids=new Set(f.metric_ids||[]);svg.querySelectorAll('.metric-node').forEach(n=>n.classList.toggle('dim',!ids.has(n.dataset.metricNode)));svg.querySelectorAll('.edge').forEach(e=>{const active=[e.dataset.lineageSource,e.dataset.lineageTarget,e.dataset.contextSource,e.dataset.contextTarget].includes(id);e.classList.toggle('active',active);e.classList.toggle('dim',!active)});show(f.name,`${f.tier} · ${f.count}개 지표`,'family의 명시적 계보와 공통 질병 맥락을 강조합니다.',(f.metric_ids||[]).map(x=>metricById.get(x).metric_id))}
function show(title,summary,context,items){document.getElementById('detail-title').textContent=title;document.getElementById('detail-summary').textContent=summary;document.getElementById('detail-context').textContent=context;document.getElementById('detail-items').innerHTML=items.map(x=>`<code>${esc(x)}</code>`).join('')}
function bindNodes(){svg.querySelectorAll('[data-metric-node]').forEach(n=>n.addEventListener('click',()=>highlightMetric(n.dataset.metricNode)));svg.querySelectorAll('[data-disease-node]').forEach(n=>n.addEventListener('click',()=>highlightDisease(n.dataset.diseaseNode)));svg.querySelectorAll('[data-family-node]').forEach(n=>n.addEventListener('click',()=>highlightFamily(n.dataset.familyNode)))}
document.getElementById('metric-search').addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();clearHighlight();let count=0;svg.querySelectorAll('.metric-node').forEach(n=>{const m=metricById.get(n.dataset.metricNode),match=!q||[m.metric_id,m.collection,m.domain_label,m.family_id,...m.disease_labels].join(' ').toLowerCase().includes(q);n.classList.toggle('dim',!match);if(match)count++});document.getElementById('map-count').textContent=`${count} / 190 metric nodes`});document.getElementById('relationship-layer').addEventListener('change',e=>layer(e.target.value));document.getElementById('zoom-out').addEventListener('click',()=>setScale(scale-.15));document.getElementById('zoom-in').addEventListener('click',()=>setScale(scale+.15));document.getElementById('zoom-reset').addEventListener('click',()=>setScale(1));document.getElementById('fit-map').addEventListener('click',()=>setScale(.35,true));document.getElementById('reset-selection').addEventListener('click',()=>{clearHighlight();document.getElementById('metric-search').value='';document.getElementById('map-count').textContent='190 metric nodes';show('전체 지도','노드를 클릭하면 연결 관계를 강조합니다.','190개 지표가 모두 표시되어 있습니다.',[])});[scroll,topScroll].forEach(el=>el.addEventListener('scroll',()=>{if(syncing)return;syncing=true;(el===scroll?topScroll:scroll).scrollLeft=el.scrollLeft;syncing=false},{passive:true}));document.getElementById('updated').textContent=C.generated;const t=C.summary.tier_counts;document.getElementById('summary').innerHTML=[['전체 지표',C.summary.metric_total],['T1 / T2',`${t.T1} / ${t.T2}`],['T3 / T4',`${t.T3} / ${t.T4}`],['Analysis',t.ANALYSIS],['질병 연결선',C.summary.disease_edge_total]].map(([a,b])=>`<article class="stat"><span>${a}</span><strong>${b}</strong></article>`).join('');render()})();
</script></body></html>'''


def write_full_metric_relationship_map(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        build_full_metric_relationship_catalog(), ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    target.write_text(HTML_TEMPLATE.replace("__MAP_JSON__", encoded), encoding="utf-8")
    return target
