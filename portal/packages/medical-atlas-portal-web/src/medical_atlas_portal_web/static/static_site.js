// Static export only: free-text search in the browser (the dynamic service searches on the server).
(function () {
  const me = document.currentScript;
  const root = me.dataset.root || './';
  const domain = me.dataset.domain;
  const english = me.dataset.language === 'en';
  const params = new URLSearchParams(location.search);
  const q = (params.get('q') || '').trim();
  if (!domain || !q) return;
  const onSearch = /\/search\/(index\.html)?$/.test(location.pathname);
  if (!onSearch) {                                   // name filter on the anatomy / lesion lists → search page
    const section = /\/anatomy\//.test(location.pathname) ? 'anatomy' : (/\/lesions\//.test(location.pathname) ? 'lesions' : '');
    const next = new URLSearchParams({ q });
    if (section) next.set('section', section);
    location.replace(root + domain + '/search/?' + next.toString());
    return;
  }
  const section = params.get('section') || '';
  const esc = (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  fetch(root + '_static/search_' + domain + '.json').then((r) => r.json()).then((items) => {
    const tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
    const hits = items.filter((i) => (!section || i.section === section) &&
      tokens.every((t) => [i.name, i.name_en, i.abbr, i.definition, i.location].join(' ').toLowerCase().includes(t)));
    document.querySelectorAll('input[name="q"]').forEach((el) => { el.value = q; });
    const head = document.querySelector('.page-heading') || document.querySelector('main');
    const box = document.createElement('div');
    const label = english
      ? (section === 'anatomy' ? ' · Anatomy' : (section === 'lesions' ? ' · Lesions' : ''))
      : (section === 'anatomy' ? ' · 해부 구조' : (section === 'lesions' ? ' · 병변' : ''));
    box.innerHTML = '<p class="muted">‘' + esc(q) + '’' + label + (english ? ' · Results: ' : ' 결과 ') + hits.length + (english ? '</p>' : '개</p>') +
      (hits.length ? '<div class="item-grid">' + hits.map((i) =>
        '<a class="item-card" href="' + root + i.path.replace(/^\//, '') + '"><span class="item-name">' + esc(i.name) +
        (i.abbr ? ' <span class="abbr">' + esc(i.abbr) + '</span>' : '') + '</span><span class="item-en">' + esc(i.name_en) +
        '</span><span class="item-def">' + esc(i.definition) + '</span></a>').join('') + '</div>'
        : (english ? '<p class="empty">No matching items. Try another name or abbreviation.</p>'
          : '<p class="empty">찾는 항목이 없습니다. 다른 이름이나 영문·약어로 검색해 보세요.</p>'));
    head.after(box);
  });
})();
