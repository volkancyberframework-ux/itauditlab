(() => {
  const cfg = window.STUDENT_MEETING;
  const calendar = document.querySelector('#student-calendar');
  if (!cfg || !calendar) return;

  const csrf = () => document.cookie.split('; ').find(value => value.startsWith('csrftoken='))?.split('=')[1] || '';
  const error = document.querySelector('#student-calendar-error');
  const panel = document.querySelector('#student-slot-panel');
  const list = document.querySelector('#student-slot-list');
  let slots = [];
  let viewDate = new Date();

  const keyFor = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

  function renderCalendar() {
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    document.querySelector('#month-title').textContent = new Intl.DateTimeFormat('tr-TR', {month: 'long', year: 'numeric'}).format(viewDate);
    calendar.innerHTML = '';
    const offset = (new Date(year, month, 1).getDay() + 6) % 7;
    for (let index = 0; index < offset; index += 1) calendar.insertAdjacentHTML('beforeend', '<span class="empty"></span>');
    const availableDates = new Set(slots.map(slot => slot.date));
    for (let day = 1; day <= new Date(year, month + 1, 0).getDate(); day += 1) {
      const key = keyFor(new Date(year, month, day));
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = day;
      button.disabled = !availableDates.has(key);
      if (availableDates.has(key)) {
        button.className = 'available';
        button.addEventListener('click', () => showSlots(key, button));
      }
      calendar.appendChild(button);
    }
  }

  function showSlots(dateKey, selectedDay) {
    calendar.querySelectorAll('button').forEach(button => button.classList.remove('selected'));
    selectedDay.classList.add('selected');
    panel.hidden = false;
    panel.querySelector('h3').textContent = new Intl.DateTimeFormat('tr-TR', {dateStyle: 'long'}).format(new Date(`${dateKey}T12:00:00`));
    list.innerHTML = '';
    slots.filter(slot => slot.date === dateKey).forEach(slot => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'slot-button';
      button.textContent = `${slot.start} – ${slot.end}`;
      button.addEventListener('click', () => book(slot));
      list.appendChild(button);
    });
  }

  async function book(slot) {
    if (!confirm(`${slot.date} • ${slot.start}–${slot.end} görüşmesini planlamak istiyor musun?`)) return;
    try {
      const response = await fetch(cfg.bookUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
        body: JSON.stringify({slot_id: slot.id}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Rezervasyon tamamlanamadı.');
      location.href = result.redirect;
    } catch (exception) {
      error.hidden = false;
      error.textContent = exception.message;
    }
  }

  document.querySelector('#prev-month').addEventListener('click', () => { viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1); renderCalendar(); });
  document.querySelector('#next-month').addEventListener('click', () => { viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1); renderCalendar(); });

  fetch(cfg.slotsUrl)
    .then(response => response.json().then(data => ({ok: response.ok, data})))
    .then(({ok, data}) => { if (!ok) throw new Error(data.error); slots = data.slots; renderCalendar(); })
    .catch(exception => { error.hidden = false; error.textContent = exception.message || 'Takvim yüklenemedi.'; });
})();
