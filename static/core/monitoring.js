(() => {
  'use strict';
  const link = document.getElementById('monitor-mailto');
  if (link) window.location.href = link.href;
  const data = document.getElementById('monitor-history');
  const root = document.getElementById('monitor-charts');
  if (!data || !root) return;
  const rows = JSON.parse(data.textContent);
  if (!rows.length) {
    const p = document.createElement('p');
    p.textContent = 'Henüz günlük özet kaydedilmedi. Geçmiş veri üretilmez.';
    root.appendChild(p); return;
  }
  const fields = [['behind','Gecikmiş öğrenci'],['critical','Kritik öğrenci'],['completion','Ortalama tamamlanma (%)'],['average_overdue','Ortalama gecikmiş ders'],['average_delay','Ortalama gecikme (gün)'],['warnings_today','Elle gönderildi işaretlenen uyarı'],['resolved_today','Çözülen müdahale']];
  const ns = 'http://www.w3.org/2000/svg';
  for (const [key, title] of fields) {
    const box = document.createElement('section'); box.className = 'monitor-chart';
    const h = document.createElement('h3'); h.textContent = title; box.appendChild(h);
    const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox','0 0 440 190'); svg.setAttribute('role','img'); svg.setAttribute('aria-label',title);
    const values = rows.filter(r => r[key] !== null && r[key] !== undefined);
    const start = Date.parse(rows[0].date); const end = Date.parse(rows[rows.length-1].date);
    const max = Math.max(1, ...values.map(r => r[key]));
    let d = '', previous = null;
    for (const r of values) {
      const day = Date.parse(r.date); const x = 30 + 380 * (end === start ? 0.5 : (day-start)/(end-start)); const y = 150 - 120*r[key]/max;
      d += (previous !== null && day-previous === 86400000 ? ' L ' : ' M ') + x + ' ' + y; previous = day;
      const point = document.createElementNS(ns,'circle');point.setAttribute('cx',x);point.setAttribute('cy',y);point.setAttribute('r','4');point.setAttribute('fill','#087f83');
      const tooltip = document.createElementNS(ns,'title');tooltip.textContent = r.date + ': ' + r[key];point.appendChild(tooltip);svg.appendChild(point);
    }
    const path = document.createElementNS(ns,'path');path.setAttribute('d',d);path.setAttribute('fill','none');path.setAttribute('stroke','#087f83');path.setAttribute('stroke-width','2');svg.insertBefore(path,svg.firstChild);
    for (const [x,y,label] of [[8,25,max],[8,154,0],[30,180,rows[0].date],[320,180,rows[rows.length-1].date]]) {
      const t = document.createElementNS(ns,'text');t.setAttribute('x',x);t.setAttribute('y',y);t.setAttribute('fill','currentColor');t.setAttribute('font-size','11');t.textContent=String(label);svg.appendChild(t);
    }
    box.appendChild(svg);root.appendChild(box);
  }
})();
