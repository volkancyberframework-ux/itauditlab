document.addEventListener('DOMContentLoaded', () => {
  for (const source of document.querySelectorAll('textarea.grc-information-pages')) {
    let pages;
    try { pages = JSON.parse(source.value || '[]'); } catch (_) { continue; }
    if (!Array.isArray(pages)) continue;
    const editor = document.createElement('div');
    editor.className = 'grc-pages-editor';
    source.after(editor);
    source.hidden = true;
    const persist = () => { source.value = JSON.stringify(pages); };
    const button = (label, callback) => {
      const b = document.createElement('button'); b.type = 'button'; b.textContent = label;
      b.addEventListener('click', callback); return b;
    };
    const render = () => {
      editor.replaceChildren();
      pages.forEach((page, index) => {
        const box = document.createElement('section'); box.className = 'grc-page';
        const header = document.createElement('div'); header.className = 'grc-page-tools';
        const title = document.createElement('strong'); title.textContent = `Sayfa ${index + 1}`;
        header.append(title);
        if (index > 0) header.append(button('↑ Yukarı', () => {
          [pages[index - 1], pages[index]] = [pages[index], pages[index - 1]]; persist(); render();
        }));
        if (index < pages.length - 1) header.append(button('↓ Aşağı', () => {
          [pages[index + 1], pages[index]] = [pages[index], pages[index + 1]]; persist(); render();
        }));
        header.append(button('Sayfayı kaldır', () => { pages.splice(index, 1); persist(); render(); }));
        box.append(header);
        for (const [key, label] of [['title', 'Başlık'], ['body', 'Anlatım'], ['reveal', 'Dokununca açılan açıklama (isteğe bağlı)']]) {
          const wrap = document.createElement('div'); wrap.className = 'grc-page-field';
          const caption = document.createElement('label'); caption.textContent = label;
          wrap.append(caption);
          const field = document.createElement(key === 'title' ? 'input' : 'textarea');
          field.id = `grc-${source.id || 'pages'}-${index}-${key}`; caption.htmlFor = field.id;
          field.value = page[key] || ''; field.rows = key === 'body' ? 6 : 3;
          field.addEventListener('input', () => { page[key] = field.value; persist(); });
          if (key !== 'title') {
            const toolbar = document.createElement('div'); toolbar.className = 'grc-page-tools';
            for (const [name, marker] of [['Kalın', '**'], ['İtalik', '*'], ['Kalın + italik', '***']]) {
              toolbar.append(button(name, () => {
                const start = field.selectionStart, end = field.selectionEnd;
                const selected = field.value.slice(start, end) || 'metin';
                field.setRangeText(marker + selected + marker, start, end, 'select');
                page[key] = field.value; persist(); field.focus();
              }));
            }
            wrap.append(toolbar);
          }
          wrap.append(field); box.append(wrap);
        }
        editor.append(box);
      });
      if (pages.length < 12) editor.append(button('+ Sayfa ekle', () => {
        pages.push({title: '', body: '', reveal: ''}); persist(); render();
      }));
    };
    render();
    const kind = document.getElementById('id_kind');
    const row = source.closest('.form-row');
    const updateVisibility = () => { if (row) row.hidden = kind && kind.value !== 'info'; };
    kind?.addEventListener('change', updateVisibility); updateVisibility();
  }
});
