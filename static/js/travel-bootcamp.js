(() => {
  'use strict';
  function track(name, location) {
    try {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({event: name, product: 'travel_bootcamp', value: 249, currency: 'USD', location});
      window.dispatchEvent(new CustomEvent(name, {detail: {location}}));
    } catch (_) { /* Analytics must never prevent checkout. */ }
  }
  document.querySelectorAll('.tb-checkout').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const buttons = document.querySelectorAll('.tb-checkout button');
      const error = form.querySelector('.tb-checkout-error');
      error.textContent = '';
      buttons.forEach(button => { button.disabled = true; });
      form.setAttribute('aria-busy', 'true');
      track('travel_bootcamp_cta_click', form.dataset.location);
      try {
        const response = await fetch(form.action, {
          method: 'POST', body: new FormData(form), headers: {'Accept': 'application/json'}, credentials: 'same-origin'
        });
        if (!response.ok) throw new Error('Checkout unavailable');
        const data = await response.json();
        const url = new URL(data.url);
        if (url.protocol !== 'https:' || url.hostname !== 'checkout.stripe.com') throw new Error('Invalid Checkout URL');
        track('travel_bootcamp_checkout', form.dataset.location);
        window.location.assign(url.href);
      } catch (_) {
        error.textContent = 'Ödeme başlatılamadı. Tekrar dene veya volkan@grcustasi.com adresine yaz.';
        buttons.forEach(button => { button.disabled = false; });
        form.removeAttribute('aria-busy');
      }
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
