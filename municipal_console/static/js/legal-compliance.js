(() => {
  const panel = document.querySelector('[data-compliance-url]');
  if (!panel) return;
  let pending = false;
  const refresh = async () => {
    if (document.hidden || pending) return;
    pending = true;
    try {
      const response = await fetch(panel.dataset.complianceUrl, {credentials:'same-origin', cache:'no-store'});
      if (response.ok && !response.redirected) panel.innerHTML = await response.text();
    } catch { /* Keep the last successful result and its timestamp. */ }
    finally { pending = false; }
  };
  setInterval(refresh, 30000);
})();
