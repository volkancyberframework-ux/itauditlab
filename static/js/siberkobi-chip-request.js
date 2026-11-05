(() => {
  'use strict';
  const form = document.getElementById('chip-request-form');
  if (!form) return;
  const button = document.getElementById('chip-request-button');
  const error = document.getElementById('chip-request-error');
  const label = button.textContent;
  let submitting = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submitting) return;
    submitting = true; button.disabled = true; button.textContent = 'Kaydınız hazırlanıyor…'; error.hidden = true;
    try {
      // A login in another tab can rotate the CSRF cookie after this form loaded.
      const response = await fetch(form.dataset.csrfUrl, {credentials: 'same-origin', cache: 'no-store', referrerPolicy: 'strict-origin'});
      if (!response.ok) throw new Error('Token unavailable');
      const data = await response.json();
      if (!data.token) throw new Error('Missing token');
      form.elements.csrfmiddlewaretoken.value = data.token;
      HTMLFormElement.prototype.submit.call(form);
    } catch (_) {
      error.textContent = 'Bağlantı kurulamadı. Bilgileriniz kaybolmadı; yeniden deneyebilirsiniz.';
      error.hidden = false; submitting = false; button.disabled = false; button.textContent = label;
    }
  });
})();
