(() => {
  'use strict';
  const dialog = document.getElementById('ot-bootcamp-modal');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const key = 'grc-ot-bootcamp-seen-v1';
  let seen = false;
  try { seen = localStorage.getItem(key) === 'true'; } catch (_) {}
  const close = () => dialog.close();
  dialog.querySelector('.ot-modal-close').addEventListener('click', close);
  dialog.querySelector('.ot-modal-dismiss').addEventListener('click', close);
  dialog.querySelector('.ot-modal-details').addEventListener('click', close);
  dialog.addEventListener('click', event => { if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
  }});
  dialog.addEventListener('close', () => document.body.classList.remove('ot-offer-open'));
  document.querySelectorAll('[data-ot-announcement]').forEach(button => button.addEventListener('click', () => { dialog.showModal(); document.body.classList.add('ot-offer-open'); }));
  if (seen || document.querySelector('[data-auto-open="true"]')) return;
  window.setTimeout(() => {
    if (document.querySelector('dialog[open]')) return;
    dialog.showModal();
    document.body.classList.add('ot-offer-open');
    try { localStorage.setItem(key, 'true'); } catch (_) {}
  }, 1400);
})();
