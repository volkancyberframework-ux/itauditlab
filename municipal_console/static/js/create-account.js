(() => {
  const form = document.querySelector('#create-account-form');
  if (!form) return;
  const audits = JSON.parse(document.querySelector('#account-audits').textContent);
  const organization = form.querySelector('[name=organization]');
  const audit = form.querySelector('[name=audit]');
  const role = form.querySelector('[name=role]');
  const readonly = form.querySelector('[name=auditor_readonly]');
  const sector = form.querySelector('[name=sector]');
  const updateSector = () => {
    const chosen = audits.find(item => String(item.id) === audit.value);
    if (chosen) sector.value = chosen.sector;
  };
  const updateAudits = () => {
    for (const option of audit.options) {
      const item = audits.find(item => String(item.id) === option.value);
      option.hidden = !!item && String(item.organization) !== organization.value;
      option.disabled = option.hidden;
    }
    if (audit.selectedOptions[0]?.disabled) audit.value = '';
  };
  const updateRole = () => {
    readonly.disabled = role.value !== 'intern';
    if (readonly.disabled) readonly.checked = false;
  };
  organization.addEventListener('change', updateAudits);
  audit.addEventListener('change', updateSector);
  role.addEventListener('change', updateRole);
  updateAudits(); updateRole();
})();
