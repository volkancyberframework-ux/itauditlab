const toggle = document.querySelector('.password-toggle');
const password = document.querySelector('#password');
if (toggle && password) {
  toggle.addEventListener('click', () => {
    const reveal = password.type === 'password';
    password.type = reveal ? 'text' : 'password';
    toggle.setAttribute('aria-label', reveal ? 'Parolayı gizle' : 'Parolayı göster');
    toggle.setAttribute('aria-pressed', String(reveal));
  });
  password.addEventListener('keyup', event => {
    document.querySelector('#caps-warning').hidden = !event.getModifierState('CapsLock');
  });
}
const forgot = document.querySelector('#forgot-toggle');
forgot?.addEventListener('click', () => {
  const panel = document.querySelector('#reset-info');
  panel.hidden = !panel.hidden;
  forgot.setAttribute('aria-expanded', String(!panel.hidden));
});
document.querySelector('.signin-form')?.addEventListener('submit', event => {
  if (!event.target.checkValidity()) return;
  const button = event.target.querySelector('[type=submit]');
  button.disabled = true;
  button.setAttribute('aria-busy','true');
  button.querySelector('span').textContent = 'Giriş yapılıyor…';
});
