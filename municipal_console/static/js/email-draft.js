(() => {
  const open = document.querySelector('#open-draft');
  if (!open) return;
  const recipient = document.querySelector('#draft-email');
  const subject = document.querySelector('#draft-subject');
  const body = document.querySelector('#draft-body');
  const feedback = document.querySelector('#draft-feedback');
  const updateLink = () => {
    open.href = `mailto:${encodeURIComponent(recipient.value)}?subject=${encodeURIComponent(subject.value)}&body=${encodeURIComponent(body.value.replace(/\r?\n/g, '\r\n'))}`;
  };
  subject.addEventListener('input', updateLink);
  body.addEventListener('input', updateLink);
  open.addEventListener('click', updateLink);
  document.querySelector('#copy-draft').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(`Konu: ${subject.value}\n\n${body.value}`);
      feedback.textContent = 'E-posta metni kopyalandı.';
    } catch {
      body.focus(); body.select();
      feedback.textContent = 'Metin seçildi. Kopyalamak için Ctrl+C veya Cmd+C kullanın.';
    }
  });
  const base64 = text => {
    const bytes = new TextEncoder().encode(text);
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
  };
  document.querySelector('#download-draft').addEventListener('click', () => {
    const subjectChunks = [];
    let chunk = '';
    for (const char of subject.value.replace(/[\r\n]/g, ' ')) {
      if (new TextEncoder().encode(chunk+char).length > 42) { subjectChunks.push(chunk); chunk = ''; }
      chunk += char;
    }
    subjectChunks.push(chunk);
    const encodedSubject = subjectChunks.map(s => `=?UTF-8?B?${base64(s)}?=`).join('\r\n ');
    const encodedBody = base64(body.value.replace(/\r?\n/g, '\r\n')).match(/.{1,76}/g)?.join('\r\n') || '';
    const content = `To: ${recipient.value.replace(/[\r\n]/g, '')}\r\nSubject: ${encodedSubject}\r\nX-Unsent: 1\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n${encodedBody}\r\n`;
    const url = URL.createObjectURL(new Blob([content], {type: 'message/rfc822'}));
    const link = document.createElement('a');
    link.href = url; link.download = 'hesap-daveti.eml'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  updateLink();
  open.click();
})();
