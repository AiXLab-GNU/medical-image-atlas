'use strict';
// Measurement display examples: modality tabs → region chips → one card per image,
// with one switch per measurement layer.
(() => {
  const root = document.getElementById('examples');
  if (!root) return;
  const cards = [...root.querySelectorAll('.mx-card')];
  const mods = [...root.querySelectorAll('.mx-mod')];
  const regionRows = [...root.querySelectorAll('.mx-regions')];
  const tabs = [...root.querySelectorAll('.mx-tab')];

  function show(id) {
    const card = cards.find(c => c.id === id);
    if (!card) return;
    const group = card.dataset.group;
    cards.forEach(c => c.toggleAttribute('hidden', c !== card));
    mods.forEach(m => m.classList.toggle('on', m.dataset.group === group));
    regionRows.forEach(r => r.toggleAttribute('hidden', r.dataset.group !== group));
    tabs.forEach(t => {
      const on = t.dataset.example === id;
      t.classList.toggle('on', on);
      if (on) t.scrollIntoView({block: 'nearest', inline: 'nearest'});
    });
  }

  function refresh(card) {
    const boxes = [...card.querySelectorAll('input[data-layer]')];
    const n = boxes.filter(b => b.checked).length;
    const progress = card.querySelector('[data-progress]');
    if (progress) progress.textContent = `${n} / ${boxes.length} 실행`;
    const tag = card.querySelector('[data-stage-tag]');
    if (tag) {
      tag.textContent = n ? `측정 ${n}개 표시 중` : '원 영상 · 실행 전';
      tag.classList.toggle('on', n > 0);
    }
  }

  function setLayer(key, on) {
    root.querySelectorAll(`img.mx-layer[data-layer="${key}"]`).forEach(img => img.toggleAttribute('hidden', !on));
    const state = root.querySelector(`.mx-state[data-state="${key}"]`);
    if (state) {
      state.closest('.mx-item').querySelector('.mx-off').toggleAttribute('hidden', on);
      state.querySelector('.mx-vals').toggleAttribute('hidden', !on);
      state.classList.toggle('on', on);
    }
  }

  root.addEventListener('change', event => {
    const box = event.target.closest('input[type=checkbox][data-layer]');
    if (!box) return;
    setLayer(box.dataset.layer, box.checked);
    refresh(box.closest('.mx-card'));
  });

  root.addEventListener('click', event => {
    const tab = event.target.closest('.mx-tab, .mx-mod, .mx-link');
    if (tab) { show(tab.dataset.example); return; }
    const bulk = event.target.closest('[data-all]');
    if (bulk) {
      const card = bulk.closest('.mx-card');
      card.querySelectorAll('input[type=checkbox][data-layer]').forEach(box => {
        box.checked = bulk.dataset.all === 'on';
        setLayer(box.dataset.layer, box.checked);
      });
      refresh(card);
    }
  });

  // "표시 예시" links in the measurement rows open the matching example and switch its layer on.
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-open-example]');
    if (!link) return;
    show(link.dataset.openExample);
    const row = link.closest('.ms-row');
    const card = document.getElementById(link.dataset.openExample);
    if (row && card) {
      card.querySelectorAll('.mx-item').forEach(item => {
        if (item.querySelector(`a[href="#${row.id}"]`)) {
          const box = item.querySelector('input[type=checkbox]');
          box.checked = true;
          setLayer(box.dataset.layer, true);
        }
      });
      refresh(card);
    }
  });

  const fromHash = location.hash.slice(1);
  if (cards.some(card => card.id === fromHash)) show(fromHash);
})();
