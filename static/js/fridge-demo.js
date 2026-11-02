(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let authenticated = false;
  const mailLink = (code, offer) => 'mailto:volkan@grcustasi.com?subject=' + encodeURIComponent('GRC Ustası | ' + code) + '&body=' + encodeURIComponent('Merhaba Volkan,\n\nBuzdolabı demosunu tamamladım.\nBaşvuru kodum: ' + code + '\nKazandığım ödül: ' + offer + '\nİlgilendiğim eğitim: \n\nTeşekkürler.');
  document.querySelectorAll('.copy-code').forEach(button => button.addEventListener('click', async () => {
    const code = $(button.dataset.target).textContent;
    try { await navigator.clipboard.writeText(code); button.textContent = 'Kopyalandı ✓'; }
    catch (_) { button.textContent = 'Kodu seçip kopyalayın'; }
  }));
  $('fridge-grid').innerHTML = Array.from({length: 6}, (_, i) => `<article class="fridge"><div class="fridge-symbol" aria-hidden="true">🧊</div><small>SOĞUTUCU ${String(i+1).padStart(2,'0')}</small><div class="temp">−5°C</div><span class="status">❄️ Hedef sıcaklıkta</span></article>`).join('');
  $('demo-login').addEventListener('submit', async event => {
    event.preventDefault();
    const button = $('demo-login').querySelector('button');
    button.disabled = true;
    try {
      const response = await fetch('/buzdolabi/giris', {method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':$('csrf-token').value},body:JSON.stringify({token:$('demo-token').value,username:$('username').value.trim(),password:$('password').value})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Giriş yapılamadı.');
      $('demo-token').value = data.token;
      $('login-reward-code').textContent = data.code;
      $('login-reward-email').href = mailLink(data.code, '%25 bootcamp indirimi');
      $('password').value = '';
      authenticated = true;
      $('login-error').hidden = true;
      $('login-view').hidden = true; $('panel-view').hidden = false; window.scrollTo({top:0,behavior:'smooth'});
    } catch (error) { $('login-error').textContent = error.message; $('login-error').hidden = false; }
    finally { button.disabled = false; }
  });
  $('reset').addEventListener('click', () => window.location.reload());
  $('temperature-form').addEventListener('submit', async event => {
    event.preventDefault();
    const value = Number($('temperature').value);
    const error = $('temperature-error');
    error.hidden = true;
    if (!authenticated || !Number.isFinite(value) || value < -30 || value > 50 || value === -5) {
      error.textContent = 'Başlangıç sıcaklığı −5°C. Demoyu tamamlamak için farklı bir sıcaklık seçin.'; error.hidden = false; return;
    }
    $('apply').disabled = true; $('apply').textContent = 'Onaylanıyor…';
    try {
      const response = await fetch('/buzdolabi/onay', {method: 'POST', headers: {'Content-Type':'application/json','X-CSRFToken':$('csrf-token').value}, body: JSON.stringify({token:$('demo-token').value, temperature:value})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'İşlem tamamlanamadı.');
      document.querySelectorAll('.fridge .temp').forEach(el => {el.textContent = `${value}°C`;});
      $('target-value').textContent = `${value}°C`;
      $('panel-view').hidden = true; $('reward-view').hidden = false;
      $('reward-code').textContent = data.code;
      $('reward-email').href = mailLink(data.code, '15 dakika birebir görüşme ve %60 bootcamp indirimi');
      $('reward-contact').href = $('reward-email').href;
      $('expiry').textContent = `İndirim için son başvuru: ${data.expires} (Türkiye saati).`;
      $('reward-view').setAttribute('tabindex','-1'); $('reward-view').focus(); window.scrollTo({top:0,behavior:'smooth'});
    } catch (exception) {error.textContent = exception.message; error.hidden = false;}
    finally { $('apply').disabled = false; $('apply').textContent = 'Değişikliği onayla ↗'; }
  });
})();
