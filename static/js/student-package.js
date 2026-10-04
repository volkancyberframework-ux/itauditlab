(() => {
  'use strict';
  const dialog = document.getElementById('student-package-modal');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const key = 'grc-student-package-seen-v1';
  let seen = false;
  try { seen = localStorage.getItem(key) === 'true'; } catch (_) {}
  const close = () => dialog.close();
  dialog.querySelector('.student-modal-close').addEventListener('click', close);
  dialog.querySelector('.student-modal-dismiss').addEventListener('click', close);
  dialog.querySelector('.student-modal-details').addEventListener('click', close);
  dialog.addEventListener('click', event => { if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
  }});
  dialog.addEventListener('close', () => document.body.classList.remove('student-offer-open'));
  if (seen || document.querySelector('[data-auto-open="true"]')) return;
  window.setTimeout(() => {
    if (document.querySelector('dialog[open]')) return;
    dialog.showModal();
    document.body.classList.add('student-offer-open');
    try { localStorage.setItem(key, 'true'); } catch (_) {}
  }, 1400);
})();
