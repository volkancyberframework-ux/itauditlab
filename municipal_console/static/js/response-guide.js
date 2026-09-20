(() => {
  // Keep actions clickable; explain validation failures next to the action.
  document.querySelectorAll('form.response-form').forEach(form => {
    let notice;
    form.addEventListener('invalid', event => {
      if (!notice) {
        notice = document.createElement('p');
        notice.className = 'notice error';
        notice.setAttribute('role', 'alert');
        form.append(notice);
      }
      const label = event.target.labels?.[0]?.textContent.trim() || 'Zorunlu alan';
      notice.textContent = `Kayıt için bu alanı kontrol edin: ${label}`;
      notice.hidden = false;
    }, true);
    form.addEventListener('input', () => { if (notice) notice.hidden = true; });
  });
  const hints={
    implemented:'Hangi uygulama veya süreç yürürlükte? Kim yürütüyor, ne sıklıkta uygulanıyor? Kısa bir örnek ve varsa kanıt belirtin.',
    partial:'İsteğe bağlı: Hangi kısım uygulanıyor, hangi eksikler var?',
    missing:'Açıklama zorunlu değil. İsterseniz mevcut engeli veya planınızı paylaşabilirsiniz.',
    na:'Bu kontrol kurumunuzda neden uygulanamaz? Kapsam dışında kalan sistem veya süreçleri ve gerekçeyi yazın.'
  };
  document.querySelectorAll('textarea[data-response-guide]').forEach(textarea => {
    const select=textarea.closest('form')?.querySelector('select[name="status"]');
    if(!select)return;
    const update=()=>{textarea.placeholder=hints[select.value]||'';textarea.required=['implemented','na'].includes(select.value);textarea.setAttribute('aria-required',String(textarea.required));};
    select.addEventListener('change',update);update();
  });
  document.querySelectorAll('select[name="assessment"]').forEach(assessment => {
    const form = assessment.closest('form');
    const deficiency = form?.querySelector('select[name="deficiency"]');
    if (!deficiency) return;
    const update = () => {
      const required = ['partial', 'noncompliant'].includes(assessment.value);
      deficiency.required = required;
      deficiency.disabled = !required;
      if (deficiency.closest('p')) deficiency.closest('p').hidden = !required;
      const dueDate = form.querySelector('input[name="due_date"]');
      if (dueDate) {
        dueDate.disabled = !required;
        if (dueDate.closest('p')) dueDate.closest('p').hidden = !required;
      }
    };
    assessment.addEventListener('change', update);
    update();
  });
})();
