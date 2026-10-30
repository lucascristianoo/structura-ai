/**
 * Structura.AI — Technical Council & Quality Audit Controller
 * Extracted from council.html for modular frontend organization.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const logEl = document.getElementById('council-log-text');
  const btnRun = document.getElementById('btn-run-council');

  async function fetchCouncilReport() {
    try {
      const res = await fetch('/api/agents/council/report');
      if (res.ok) {
        const text = await res.text();
        if (logEl) logEl.textContent = text;
      }
    } catch (e) {
      if (logEl) logEl.textContent = 'Erro ao carregar relatório: ' + e;
    }
  }

  if (btnRun) {
    btnRun.addEventListener('click', async () => {
      btnRun.disabled = true;
      btnRun.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Executando...</span>`;
      if (window.lucide) window.lucide.createIcons();

      try {
        const res = await fetch('/api/agents/council/run', { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          if (logEl) logEl.textContent = data.markdown_dossier;
        }
      } catch (err) {
        alert('Erro ao executar sessão: ' + err);
      } finally {
        btnRun.disabled = false;
        btnRun.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5"></i><span>Executar auditoria</span>`;
        if (window.lucide) window.lucide.createIcons();
      }
    });
  }

  fetchCouncilReport();
});

