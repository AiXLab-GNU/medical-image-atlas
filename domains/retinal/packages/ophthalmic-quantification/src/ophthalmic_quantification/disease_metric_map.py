"""Build a single-view disease-to-quantitative-metric family map."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import json
from pathlib import Path
from typing import Any

from .atlas import build_atlas_catalog


def build_disease_metric_map_catalog() -> dict[str, Any]:
    """Aggregate explicit disease links without assigning nonspecific or QC metrics."""
    atlas = build_atlas_catalog()
    linked_metrics = [
        metric
        for metric in atlas["metrics"]
        if metric["disease_ids"] and metric["tier"] in {"T1", "T2", "T3", "T4"}
    ]
    family_lookup = {family["id"]: family for family in atlas["families"]}
    edges: dict[tuple[str, str], list[str]] = defaultdict(list)
    for metric in linked_metrics:
        for disease_id in metric["disease_ids"]:
            edges[(str(disease_id), str(metric["family_id"]))].append(str(metric["metric_id"]))
    edge_rows = [
        {
            "disease_id": disease_id,
            "family_id": family_id,
            "count": len(metric_ids),
            "metric_ids": sorted(metric_ids),
        }
        for (disease_id, family_id), metric_ids in sorted(edges.items())
    ]
    visible_family_ids = {edge["family_id"] for edge in edge_rows}
    tier_order = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}
    families = sorted(
        (
            {
                "id": family["id"],
                "tier": family["tier"],
                "name": family["name"],
                "count": sum(
                    metric["family_id"] == family["id"] for metric in linked_metrics
                ),
            }
            for family in atlas["families"]
            if family["id"] in visible_family_ids
        ),
        key=lambda family: (tier_order[str(family["tier"])], str(family["name"])),
    )
    diseases = []
    for disease in atlas["diseases"]:
        metric_ids = sorted(
            {
                str(metric["metric_id"])
                for metric in linked_metrics
                if disease["id"] in metric["disease_ids"]
            }
        )
        if metric_ids:
            diseases.append({**disease, "metric_count": len(metric_ids), "metric_ids": metric_ids})
    return {
        "version": "1.0",
        "generated": date.today().isoformat(),
        "summary": {
            "calculator_total": atlas["summary"]["calculator_total"],
            "disease_linked_metric_total": len(linked_metrics),
            "nonspecific_or_analysis_total": atlas["summary"]["calculator_total"]
            - len(linked_metrics),
            "disease_total": len(diseases),
            "family_total": len(families),
            "edge_total": len(edge_rows),
        },
        "diseases": diseases,
        "families": families,
        "edges": edge_rows,
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="안과 질병과 T1–T4 정량지표 family를 연결한 한 장 지도">
<title>질병–정량지표 한 장 지도 · OcuPhenome XAI</title>
<style>
:root{--navy:#071c2c;--ink:#172735;--muted:#667681;--paper:#f3f6f3;--line:#d8dfdc;--t1:#d65743;--t2:#df913d;--t3:#278e82;--t4:#4f72b5}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);font-family:Inter,system-ui,-apple-system,"Noto Sans KR",sans-serif}.topbar{position:sticky;top:0;z-index:20;display:flex;gap:.45rem;align-items:center;padding:.7rem max(1rem,calc((100vw - 1500px)/2));color:white;background:#071c2cf2;backdrop-filter:blur(12px)}.topbar a{padding:.45rem .7rem;color:#dce8ea;text-decoration:none;border-radius:8px;font-size:.82rem;font-weight:850}.topbar a:first-child{color:#92e2d5}.topbar a:hover{color:white;background:#ffffff17}.topbar b{margin-left:auto;color:#9cded3;font-size:.75rem}.shell{width:min(1500px,calc(100% - 2rem));margin:auto}.hero{padding:3.5rem 0 1.5rem}.eyebrow{margin:0 0 .5rem;color:#168076;font-size:.72rem;font-weight:900;letter-spacing:.15em;text-transform:uppercase}.hero h1{max-width:950px;margin:.2rem 0;font-size:clamp(2.3rem,6vw,5.8rem);line-height:.97;letter-spacing:-.06em}.hero p{max-width:850px;color:var(--muted);line-height:1.7}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin:1.3rem 0}.stat{padding:1rem;background:white;border:1px solid var(--line);border-radius:12px}.stat span{display:block;color:var(--muted);font-size:.76rem}.stat strong{font-size:1.9rem}.notice{padding:1rem 1.1rem;color:#724413;background:#fff3dd;border-left:5px solid #df913d;border-radius:9px}.map-section{margin-bottom:1.5rem;padding:1rem;background:var(--navy);border-radius:18px;box-shadow:0 20px 55px #071c2c1c}.map-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;padding:.4rem .3rem 1rem;color:white}.map-head h2{margin:0;font-size:1.5rem}.legend{display:flex;gap:.45rem;flex-wrap:wrap}.legend span{padding:.28rem .5rem;background:#ffffff12;border:1px solid #ffffff22;border-radius:999px;font-size:.72rem;font-weight:850}.map-scroll{overflow:auto;background:#fbfcfa;border-radius:12px}.map-scroll svg{display:block;min-width:1320px}.map-edge{fill:none;stroke:var(--edge);stroke-opacity:.25;transition:.18s}.map-edge.active{stroke-opacity:.88}.map-edge.dim{stroke-opacity:.035}.disease-node,.family-node{cursor:pointer}.node-box{fill:white;stroke:#cfd9d5;transition:.18s}.disease-node:hover .node-box,.disease-node.active .node-box{stroke:#087f75;stroke-width:3}.family-node:hover .node-box,.family-node.active .node-box{stroke:var(--tier);stroke-width:3}.node-accent{fill:var(--tier)}.node-title{fill:#173042;font-weight:850}.node-meta{fill:#667681;font-size:12px}.map-label{fill:#647781;font-size:13px;font-weight:850;letter-spacing:.08em}.detail{display:grid;grid-template-columns:260px 1fr;gap:1rem;margin-bottom:1.5rem;padding:1.2rem;background:white;border:1px solid var(--line);border-radius:14px}.detail h2{margin:.15rem 0}.detail-copy p{color:var(--muted)}.metric-list{display:flex;flex-wrap:wrap;gap:.38rem;max-height:220px;overflow:auto}.metric-list code{padding:.28rem .46rem;color:#334d60;background:#eef3f1;border-radius:6px;font-size:.72rem}.reset{align-self:start;padding:.58rem .8rem;color:white;background:#087f75;border:0;border-radius:8px;font-weight:850;cursor:pointer}.scope{margin-bottom:3rem;padding:1rem;background:#ecefea;border-radius:10px;color:var(--muted)}.footer{padding:2rem;text-align:center;color:var(--muted)}@media(max-width:800px){.topbar b{display:none}.stats{grid-template-columns:1fr 1fr}.map-head,.detail{display:block}.legend{margin-top:.7rem}.reset{margin-top:.8rem}}
</style></head><body>
<nav class="topbar" aria-label="지도 이동"><a href="ophthalmic_quantitative_metric_examples_v01_ko.html">← 190개 계산 예제로 돌아가기</a><a href="ophthalmic_full_metric_relationship_map_v01_ko.html">190개 전체 관계 지도</a><a href="/">⌂ 포털 홈</a><b>DISEASE × QUANTITATIVE METRIC</b></nav>
<header class="hero shell"><p class="eyebrow">One-view evidence map</p><h1>질병–정량지표<br>한 장 지도</h1><p>190개 계산기 가운데 질병과 명시적으로 연결된 T1–T4 의료·파생 지표를 family 단위로 묶었습니다. 선의 굵기는 해당 질병–family에 속한 지표 수를 나타냅니다.</p><div id="summary" class="stats"></div><p class="notice">질병 연결은 연구·모니터링 맥락이며 단독 진단을 의미하지 않습니다. 질병 비특이 지표와 QC·검증 계산값은 연결선을 만들지 않습니다.</p></header>
<main class="shell"><section class="map-section"><div class="map-head"><h2>질병 → T1–T4 정량지표 family</h2><div class="legend"><span style="color:var(--t1)">T1 임상 기준</span><span style="color:var(--t2)">T2 앵커 파생</span><span style="color:var(--t3)">T3 영상 proxy</span><span style="color:var(--t4)">T4 모델 파생</span></div></div><div class="map-scroll" tabindex="0"><svg id="disease-metric-svg" role="img" aria-label="질병과 T1–T4 정량지표 family 연결 지도"></svg></div></section><section id="map-detail" class="detail" aria-live="polite"><div><p class="eyebrow">Selected node</p><h2 id="detail-title">지도를 선택하세요</h2><p id="detail-summary">질병 또는 지표 family를 누르면 연결된 지표를 확인할 수 있습니다.</p><button id="reset-map" class="reset" type="button">전체 연결 보기</button></div><div class="detail-copy"><p id="detail-context">모든 명시적 질병–지표 연결을 표시하고 있습니다.</p><div id="detail-metrics" class="metric-list"></div></div></section><p class="scope"><b>지도 범위:</b> T1–T4의 명시적 질병 연결만 표시합니다. 질병 비특이 임상 endpoint, 영상 QC, FOV, 색상·texture control과 Dice·IoU 같은 검증 지표는 190개 계산 예제 표에서 별도로 확인합니다.</p></main>
<footer class="footer">OcuPhenome XAI · P001 · E017 · 질병 연관성 ≠ 단독 진단 · 갱신 <span id="updated"></span></footer>
<script>window.OPHTHALMIC_DISEASE_METRIC_MAP=__MAP_JSON__;</script>
<script>
(function(){"use strict";const C=window.OPHTHALMIC_DISEASE_METRIC_MAP;const COLORS={T1:'#d65743',T2:'#df913d',T3:'#278e82',T4:'#4f72b5'};const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');const svg=document.getElementById('disease-metric-svg');const diseaseById=new Map(C.diseases.map(item=>[item.id,item]));const familyById=new Map(C.families.map(item=>[item.id,item]));const edgeKey=(disease,family)=>`${disease}::${family}`;const edgeByKey=new Map(C.edges.map(item=>[edgeKey(item.disease_id,item.family_id),item]));document.getElementById('updated').textContent=C.generated;document.getElementById('summary').innerHTML=[['전체 계산기',C.summary.calculator_total],['질병 연결 지표',C.summary.disease_linked_metric_total],['질병',C.summary.disease_total],['연결 family',C.summary.family_total]].map(([label,value])=>`<article class="stat"><span>${label}</span><strong>${value}</strong></article>`).join('');
function render(){const width=1400,row=70,top=75,diseaseX=28,diseaseW=250,familyX=1030,familyW=330,nodeH=48,height=Math.max(C.diseases.length,C.families.length)*row+top+45;const diseasePos=new Map(C.diseases.map((item,index)=>[item.id,{x:diseaseX,y:top+index*row}]));const familyPos=new Map(C.families.map((item,index)=>[item.id,{x:familyX,y:top+index*row}]));let content='<title>질병과 T1–T4 정량지표 family 연결</title><text class="map-label" x="28" y="34">DISEASE CONTEXT</text><text class="map-label" x="1030" y="34">QUANTITATIVE METRIC FAMILY</text>';C.edges.forEach(edge=>{const left=diseasePos.get(edge.disease_id),right=familyPos.get(edge.family_id),family=familyById.get(edge.family_id);const sy=left.y+nodeH/2,ey=right.y+nodeH/2,stroke=1.2+Math.sqrt(edge.count)*1.35;content+=`<path class="map-edge" data-disease="${edge.disease_id}" data-family="${edge.family_id}" style="--edge:${COLORS[family.tier]}" stroke-width="${stroke}" d="M ${left.x+diseaseW} ${sy} C 540 ${sy}, 760 ${ey}, ${right.x} ${ey}"><title>${esc(diseaseById.get(edge.disease_id).label)} → ${esc(family.name)} · ${edge.count} metrics</title></path>`});C.diseases.forEach(item=>{const p=diseasePos.get(item.id);content+=`<g class="disease-node" data-disease-node="${item.id}" transform="translate(${p.x} ${p.y})"><rect class="node-box" width="${diseaseW}" height="${nodeH}" rx="9"></rect><text class="node-title" x="13" y="20">${esc(item.label)}</text><text class="node-meta" x="13" y="38">${item.id} · ${item.metric_count} metrics</text></g>`});C.families.forEach(item=>{const p=familyPos.get(item.id);content+=`<g class="family-node" data-family-node="${item.id}" transform="translate(${p.x} ${p.y})" style="--tier:${COLORS[item.tier]}"><rect class="node-box" width="${familyW}" height="${nodeH}" rx="9"></rect><rect class="node-accent" width="7" height="${nodeH}" rx="4"></rect><text class="node-title" x="17" y="20">${esc(item.name)}</text><text class="node-meta" x="17" y="38">${item.tier} · ${item.count} linked metrics</text></g>`});svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('height',height);svg.innerHTML=content;svg.querySelectorAll('[data-disease-node]').forEach(node=>node.addEventListener('click',()=>focusDisease(node.dataset.diseaseNode)));svg.querySelectorAll('[data-family-node]').forEach(node=>node.addEventListener('click',()=>focusFamily(node.dataset.familyNode)))}
function highlight(diseaseId='',familyId=''){svg.querySelectorAll('.map-edge').forEach(edge=>{const active=(!diseaseId||edge.dataset.disease===diseaseId)&&(!familyId||edge.dataset.family===familyId);edge.classList.toggle('active',active);edge.classList.toggle('dim',!active)});svg.querySelectorAll('[data-disease-node]').forEach(node=>node.classList.toggle('active',node.dataset.diseaseNode===diseaseId));svg.querySelectorAll('[data-family-node]').forEach(node=>node.classList.toggle('active',node.dataset.familyNode===familyId))}
function showDetail(title,summary,context,metricIds){document.getElementById('detail-title').textContent=title;document.getElementById('detail-summary').textContent=summary;document.getElementById('detail-context').textContent=context;document.getElementById('detail-metrics').innerHTML=metricIds.map(id=>`<code>${esc(id)}</code>`).join('');document.getElementById('map-detail').scrollIntoView({behavior:'smooth',block:'nearest'})}
function focusDisease(id){const disease=diseaseById.get(id),edges=C.edges.filter(edge=>edge.disease_id===id),families=edges.map(edge=>`${familyById.get(edge.family_id).tier} ${familyById.get(edge.family_id).name} (${edge.count})`);highlight(id,'');showDetail(disease.label,`${disease.metric_count}개 명시적 연결 지표`,families.join(' · '),disease.metric_ids)}
function focusFamily(id){const family=familyById.get(id),edges=C.edges.filter(edge=>edge.family_id===id),metrics=[...new Set(edges.flatMap(edge=>edge.metric_ids))].sort(),diseases=edges.map(edge=>`${diseaseById.get(edge.disease_id).label} (${edge.count})`);highlight('',id);showDetail(`${family.tier} · ${family.name}`,`${metrics.length}개 질병 연결 지표`,diseases.join(' · '),metrics)}
function reset(){highlight();document.getElementById('detail-title').textContent='전체 연결';document.getElementById('detail-summary').textContent=`${C.summary.disease_total}개 질병 · ${C.summary.family_total}개 family`;document.getElementById('detail-context').textContent='모든 명시적 질병–지표 연결을 표시하고 있습니다.';document.getElementById('detail-metrics').replaceChildren()}document.getElementById('reset-map').addEventListener('click',reset);render();reset()})();
</script></body></html>'''


def write_disease_metric_map(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        build_disease_metric_map_catalog(), ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    target.write_text(HTML_TEMPLATE.replace("__MAP_JSON__", encoded), encoding="utf-8")
    return target
