"""Measurement → disease links derived from the atlas data (no web dependencies; also used by the registry export)."""
from __future__ import annotations


def measurement_diseases(atlas: dict) -> dict[str, list[dict]]:
    """Disease links of every measurement: direct (disease relation or grading step names the measurement)
    first, then via the measured lesion / structure (that item's disease relations). One entry per disease."""
    diseases, items = atlas['diseases'], atlas['items']
    out: dict[str, dict[str, dict]] = {}

    def add(fid, did, rel_type, condition, via, via_id=None):
        if did not in diseases:
            return
        entry = out.setdefault(fid, {})
        if did not in entry or (entry[did]['via'] is not None and via is None):
            entry[did] = {'id': did, 'name': diseases[did]['name'], 'slug': diseases[did]['slug'],
                          'type': rel_type, 'condition': condition, 'via': via, 'via_id': via_id}
    for did, d in diseases.items():
        for r in d.get('relations', []):
            add(r['finding'], did, r.get('type', ''), r.get('condition', ''), None)
        for g in d.get('grading', []):
            for st in g.get('steps', []):
                for fid in st.get('findings', []):
                    add(fid, did, 'severity_classification', f"{g['name']} · {st['grade']}", None)
    for fid, f in atlas['features'].items():
        target = items.get(f.get('target') or '')
        for r in (target or {}).get('diseases', []):
            add(fid, r['disease'], r.get('type', ''), r.get('condition', ''), target['name'], target['id'])
    return {fid: sorted(v.values(), key=lambda e: (e['via'] is not None, e['name'])) for fid, v in out.items()}
