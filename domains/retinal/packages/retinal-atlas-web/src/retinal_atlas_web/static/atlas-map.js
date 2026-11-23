'use strict';
// Hovering or focusing a list link brightens the matching region in the schematics.
(() => {
  const targets = path => document.querySelectorAll(`.schematic a[href="${path}"] > *`);
  document.querySelectorAll('[data-sync]').forEach(link => {
    const on = () => targets(link.dataset.sync).forEach(node => node.classList.add('sync'));
    const off = () => targets(link.dataset.sync).forEach(node => node.classList.remove('sync'));
    link.addEventListener('mouseenter', on);
    link.addEventListener('mouseleave', off);
    link.addEventListener('focus', on);
    link.addEventListener('blur', off);
  });
})();
