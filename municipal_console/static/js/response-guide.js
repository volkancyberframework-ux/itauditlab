(() => {
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
    const deficiency = assessment.form.querySelector('select[name="deficiency"]');
    if (!deficiency) return;
    const update = () => {
      const required = ['partial', 'noncompliant'].includes(assessment.value);
      deficiency.required = required;
      deficiency.disabled = !required;
      deficiency.closest('p').hidden = !required;
    };
    assessment.addEventListener('change', update);
    update();
  });
})();
