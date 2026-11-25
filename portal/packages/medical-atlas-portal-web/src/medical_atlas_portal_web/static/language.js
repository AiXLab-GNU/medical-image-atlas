// Preserve the selected image/example anchor while switching between mirror pages.
'use strict';
(() => {
  document.querySelectorAll('[data-language-switch]').forEach(link => {
    const target = new URL(link.href, location.href);
    if (location.search) target.search = location.search;
    target.hash = location.hash;
    link.href = target.href;
    link.addEventListener('click', () => {
      const next = new URL(link.href, location.href);
      if (location.search) next.search = location.search;
      next.hash = location.hash;
      link.href = next.href;
    });
  });
})();
