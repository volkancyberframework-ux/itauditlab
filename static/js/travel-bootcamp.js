(() => {
  'use strict';
  function track(name, location) {
    try {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({event: name, product: 'travel_bootcamp', value: 249, currency: 'USD', location});
      window.dispatchEvent(new CustomEvent(name, {detail: {location}}));
    } catch (_) { /* Analytics must never prevent checkout. */ }
  }
  document.querySelectorAll('.tb-direct-checkout').forEach(link => {
    link.addEventListener('click', () => {
      track('travel_bootcamp_cta_click', link.dataset.location);
      track('travel_bootcamp_checkout', link.dataset.location);
    });
  });
  const pending = document.querySelector('[data-payment-pending]');
  if (pending) {
    let attempts = 0;
    const query = new URLSearchParams(window.location.search);
    const url = new URL(pending.dataset.statusUrl, window.location.origin);
    url.searchParams.set('session_id', query.get('session_id') || '');
    async function poll() {
      attempts += 1;
      try {
        const response = await fetch(url, {cache: 'no-store', credentials: 'same-origin'});
        if (response.ok && (await response.json()).confirmed) { window.location.reload(); return; }
      } catch (_) { /* Allow a transient network failure to recover. */ }
      if (attempts < 40) window.setTimeout(poll, 3000);
      else document.getElementById('payment-status').textContent = 'Onay henüz ulaşmadı. Biraz sonra durumu tekrar kontrol edebilir veya bize yazabilirsin.';
    }
    window.setTimeout(poll, 2000);
    document.querySelector('.tb-refresh').addEventListener('click', () => window.location.reload());
  }
})();
