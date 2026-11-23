'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const image = $('sample-image');
  if (!image) return;
  const data = JSON.parse($('viewer-data').textContent);
  const svgNS = 'http://www.w3.org/2000/svg';
  function svgElement(name, attrs) {
    const node = document.createElementNS(svgNS, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  }
  function updateColors() {
    const detail = $('layer-level').value === 'detail';
    const points = detail ? data.layers : data.broad;
    $('layer-overlay').toggleAttribute('hidden', !$('colors').checked);
    $('layer-overlay').replaceChildren();
    $('layer-legend').replaceChildren();
    $('legend-title').textContent = detail ? '세부 망막층의 색상 범례' : '큰 해부 구조의 색상';
    points.forEach(([code, name, color, x, y], index) => {
      const group = svgElement('g', {});
      group.append(svgElement('circle', {cx:x, cy:y, r:10, fill:color}));
      const number = svgElement('text', {x:x-30, y:y+7});
      number.textContent = index + 1;
      group.append(number);
      $('layer-overlay').append(group);
      const key = document.createElement('span');
      key.className = 'layer-key';
      const swatch = svgElement('svg', {viewBox:'0 0 13 13', 'aria-hidden':'true', class:'swatch'});
      swatch.append(svgElement('rect', {width:13, height:13, rx:3, fill:color}));
      key.append(swatch, document.createTextNode(`${index+1}. ${name} · ${code}`));
      $('layer-legend').append(key);
    });
  }
  if ($('colors')) {
    $('colors').addEventListener('change', updateColors);
    $('layer-level').addEventListener('change', updateColors);
    updateColors();
  }
  const lesionButtons = [...document.querySelectorAll('[data-lesion]')];
  lesionButtons.forEach(button => button.addEventListener('click', () => {
    const selected = button.getAttribute('aria-pressed') === 'true';
    lesionButtons.forEach(b => b.setAttribute('aria-pressed', 'false'));
    const overlay = $('lesion-overlay');
    overlay.setAttribute('hidden', '');
    if (selected) return;
    button.setAttribute('aria-pressed', 'true');
    const [x, y, width, height] = JSON.parse(button.dataset.lesion);
    const rect = overlay.querySelector('rect');
    for (const [key, value] of Object.entries({x:x+3, y:y+3, width:width-6, height:height-6})) {
      rect.setAttribute(key, value);
    }
    overlay.removeAttribute('hidden');
    $('image-stage').scrollTop = y / image.naturalHeight * image.clientHeight;
  }));
  const dialog = $('image-dialog');
  $('enlarge').addEventListener('click', () => {
    $('modal-image').src = image.src;
    $('fit-image').checked = true;
    $('modal-image-wrap').classList.add('fit');
    dialog.showModal();
  });
  $('close-dialog').addEventListener('click', () => dialog.close());
  $('fit-image').addEventListener('change', () => {
    $('modal-image-wrap').classList.toggle('fit', $('fit-image').checked);
  });
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right ||
          event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    }
  });
})();
