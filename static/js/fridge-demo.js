(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let authenticated = false;
  $('fridge-grid').innerHTML = Array.from({length: 6}, (_, i) => `<article class="fridge"><small>SOĞUTUCU ${String(i+1).padStart(2,'0')}</small><div class="temp">−5°C</div><span class="status">● Hedef sıcaklıkta</span></article>`).join('');
  $('demo-login').addEventListener('submit', event => {
    event.preventDefault();
    authenticated = $('username').value.trim() === 'volkanadmin' && $('password').value === 'volkanseyahat1234';
    $('login-error').hidden = authenticated;
    if (authenticated) { $('login-view').hidden = true; $('panel-view').hidden = false; $('temperature').focus(); }
  });
  $('reset').addEventListener('click', () => window.location.reload());
  $('temperature-form').addEventListener('submit', async event => {
    event.preventDefault();
    const value = Number($('temperature').value);
    const error = $('temperature-error');
    error.hidden = true;
    if (!authenticated || !Number.isFinite(value) || value < -30 || value > 15 || value === -5) {
      error.textContent = 'Başlangıç sıcaklığı −5°C. Demoyu tamamlamak için farklı bir sıcaklık seçin.'; error.hidden = false; return;
    }
    $('apply').disabled = true; $('apply').textContent = 'Onaylanıyor…';
    try {
      const response = await fetch('/buzdolabi/onay', {method: 'POST', headers: {'Content-Type':'application/json','X-CSRFToken':$('csrf-token').value}, body: JSON.stringify({token:$('demo-token').value, temperature:value, username:'volkanadmin',password:'volkanseyahat1234'})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'İşlem tamamlanamadı.');
      document.querySelectorAll('.fridge .temp').forEach(el => {el.textContent = `${value}°C`;});
      $('target-value').textContent = `${value}°C`;
      $('panel-view').hidden = true; $('reward-view').hidden = false;
      $('expiry').textContent = `İndirim için son başvuru: ${data.expires} (Türkiye saati).`;
      $('reward-view').setAttribute('tabindex','-1'); $('reward-view').focus(); window.scrollTo({top:0,behavior:'smooth'});
    } catch (exception) {error.textContent = exception.message; error.hidden = false;}
    finally { $('apply').disabled = false; $('apply').textContent = 'Değişikliği onayla ↗'; }
  });
})();
