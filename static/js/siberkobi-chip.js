(() => {
  const root = document.getElementById('chip-result');
  if (!root || !root.dataset.statusUrl) return;
  let attempts = 0;
  const text = (id, value) => { document.getElementById(id).textContent = value; };
  async function update() {
    try {
      const response = await fetch(root.dataset.statusUrl, {cache: 'no-store', credentials: 'same-origin'});
      if (!response.ok) throw new Error('pending');
      const data = await response.json();
      if (data.state === 'paid') {
        text('result-title', 'Katılımın kaydedildi.');
        text('result-note', 'Sıran ve hesaplanan payın aşağıda. Sonuç bağlantın e-postana gönderilecek.');
        text('position', data.position + '.'); text('share', '%' + data.share); text('payer-email', data.email);
        const rows = document.getElementById('participants'); rows.replaceChildren();
        data.participants.forEach(row => {
          const tr = document.createElement('tr'); if (row.self) tr.className = 'self';
          [row.position + '.', row.name + (row.self ? ' · Sen' : ''), row.email, '%' + row.share].forEach(value => {
            const td = document.createElement('td'); td.textContent = value; tr.append(td);
          }); rows.append(tr);
        }); document.getElementById('paid-result').hidden = false; return;
      }
      if (data.state === 'archived' || data.state === 'expired') {
        text('result-title', data.state === 'archived' ? 'Test dönemi sıfırlandı.' : 'Ödeme oturumunun süresi doldu.');
        text('result-note', data.message || 'Bu oturum için katılım kaydı oluşmadı.'); return;
      }
    } catch (_) { /* A delayed webhook or connection failure must not look like a successful payment. */ }
    if (++attempts < 40) setTimeout(update, 3000);
    else text('result-note', 'Onay henüz gelmedi. Ödeme yaptıysan tekrar ödeme yapma; sayfayı yenile veya volkan@grcustasi.com adresine yaz.');
  }
  update();
})();
