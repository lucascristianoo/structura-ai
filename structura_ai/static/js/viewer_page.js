/**
 * Structura.AI — 3D CAD/BIM Viewer & Live Inspector Controller
 * Extracted from viewer.html for clean separation of structure, style, and behavior.
 */

function escapeViewerHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

document.addEventListener('DOMContentLoaded', () => {
  const viewportBox = document.getElementById('viewer-three-container');
  let viewport = null;
  if (viewportBox && window.Structura3DViewport) {
    viewport = new window.Structura3DViewport('viewer-three-container');
  }

  // Software Compatibility Modal
  const modalGuide = document.getElementById('modal-guide');
  const btnOpenGuide = document.getElementById('btn-open-guide');
  const btnCloseGuide = document.getElementById('btn-close-guide');
  const btnGuideOk = document.getElementById('btn-guide-ok');

  if (btnOpenGuide && modalGuide) {
    btnOpenGuide.addEventListener('click', () => {
      modalGuide.classList.remove('hidden');
      modalGuide.classList.add('flex');
    });
  }
  const hideGuide = () => {
    if (modalGuide) {
      modalGuide.classList.add('hidden');
      modalGuide.classList.remove('flex');
    }
  };
  if (btnCloseGuide) btnCloseGuide.addEventListener('click', hideGuide);
  if (btnGuideOk) btnGuideOk.addEventListener('click', hideGuide);

  // Shading Mode Tabs
  const shadeBtns = document.querySelectorAll('[data-shade]');
  shadeBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.shade;
      if (viewport) viewport.setShadingMode(mode);
      shadeBtns.forEach((b) => b.classList.toggle('is-active', b === btn));
    });
  });

  // Deflection Amplification Slider
  const scaleSlider = document.getElementById('slider-scale-deflection');
  const scaleLabel = document.getElementById('label-scale-deflection');
  if (scaleSlider) {
    scaleSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (scaleLabel) scaleLabel.textContent = `${val}x`;
      if (viewport && viewport.setDeflectionAmplification) {
        viewport.setDeflectionAmplification(val);
      }
    });
  }

  // Reset Camera
  const btnResetCam = document.getElementById('btn-reset-cam');
  if (btnResetCam && viewport && viewport.camera && viewport.controls) {
    btnResetCam.addEventListener('click', () => {
      viewport.camera.position.set(14, 8, 16);
      viewport.controls.target.set(5, 1.8, 0);
      viewport.controls.update();
    });
  }

  let currentSpan = 10.0;
  let currentH = 28.0;
  let currentCant = 0.0;

  async function updatePhysicsFromSliders() {
    try {
      const payload = {
        span_length_m: currentSpan,
        beam_height_cm: currentH,
        beam_width_cm: 20.0,
        cantilever_length_m: currentCant,
        concrete_fck_mpa: 30.0,
        selected_variant: 0
      };

      const res = await fetch('/api/analysis/micro-adjust', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) return;
      const data = await res.json();

      const badge = document.getElementById('inspector-badge');
      if (badge) {
        if (data.is_physically_viable) {
          badge.className = 'ui-badge ui-badge-ok';
          badge.textContent = 'Conforme NBR 6118';
        } else {
          badge.className = 'ui-badge ui-badge-fail';
          badge.textContent = 'ELS reprovado';
        }
      }

      const nameEl = document.getElementById('insp-elem-name');
      if (nameEl) nameEl.textContent = `Viga Principal V101 (${currentSpan.toFixed(1)}m)`;

      const dimEl = document.getElementById('insp-elem-dim');
      if (dimEl) dimEl.textContent = `Seção: 20×${currentH.toFixed(0)} cm · Concreto C30`;

      const deflEl = document.getElementById('insp-defl-val');
      if (deflEl) {
        deflEl.textContent = `${data.max_deflection_mm} mm`;
        deflEl.className = data.is_physically_viable
          ? 'ui-metric-value is-ok'
          : 'ui-metric-value is-fail';
      }

      const deflLim = document.getElementById('insp-defl-lim');
      if (deflLim) deflLim.textContent = `Limite: ≤ ${data.allowable_deflection_mm} mm`;

      const momEl = document.getElementById('insp-moment-val');
      if (momEl && data.dsm_analysis && data.dsm_analysis.internal_moments_knm) {
        momEl.textContent = `${data.dsm_analysis.internal_moments_knm.midspan_positive_m} kN·m`;
      }

      if (data.bom_and_cost) {
        const bom = data.bom_and_cost;
        const vConc = document.getElementById('insp-vol-conc');
        if (vConc) vConc.textContent = `${bom.quantities.concrete_volume_total_m3} m³`;

        const stKg = document.getElementById('insp-steel-kg');
        if (stKg) stKg.textContent = `${bom.quantities.steel_rebar_ca50_kg} kg`;

        const cTot = document.getElementById('insp-cost-total');
        if (cTot) {
          cTot.textContent = `R$ ${bom.financial_sinapi_2026.total_estimated_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        }

        const cCo2 = document.getElementById('insp-carbon-val');
        if (cCo2) cCo2.textContent = `${bom.embodied_carbon_a1_a3.total_emissions_kg_co2} kg CO₂e`;
      }

      if (viewport) {
        const geomParams = {
          span_length_m: currentSpan,
          beam_height_cm: currentH,
          cantilever_length_m: currentCant,
          deflection_mm: data.max_deflection_mm,
          max_deflection_mm: data.max_deflection_mm,
          allowable_deflection_mm: data.allowable_deflection_mm,
          is_viable: data.is_physically_viable
        };
        if (viewport.updateGeometry) {
          viewport.updateGeometry(geomParams);
        } else if (viewport.updateFromParams) {
          viewport.updateFromParams(geomParams);
        }
      }
    } catch (e) {
      console.warn('Micro-slider fetch error:', e);
    }
  }

  // Parametric Sliders
  const spanSlider = document.getElementById('viewer-span-slider');
  const spanLabel = document.getElementById('slider-span-val');
  if (spanSlider) {
    spanSlider.addEventListener('input', (e) => {
      currentSpan = parseFloat(e.target.value);
      if (spanLabel) spanLabel.textContent = `${currentSpan.toFixed(1)}m`;
      updatePhysicsFromSliders();
    });
  }

  const hSlider = document.getElementById('viewer-h-slider');
  const hLabel = document.getElementById('slider-h-val');
  if (hSlider) {
    hSlider.addEventListener('input', (e) => {
      currentH = parseFloat(e.target.value);
      if (hLabel) hLabel.textContent = `${currentH.toFixed(0)}cm`;
      updatePhysicsFromSliders();
    });
  }

  const cantSlider = document.getElementById('viewer-cant-slider');
  const cantLabel = document.getElementById('slider-cant-val');
  if (cantSlider) {
    cantSlider.addEventListener('input', (e) => {
      currentCant = parseFloat(e.target.value);
      if (cantLabel) cantLabel.textContent = `${currentCant.toFixed(1)}m`;
      updatePhysicsFromSliders();
    });
  }

  // Benchmark Loaders
  const btnLoadS1 = document.getElementById('btn-load-s1');
  if (btnLoadS1) {
    btnLoadS1.addEventListener('click', () => {
      currentSpan = 10.0;
      currentH = 28.0;
      currentCant = 3.5;
      if (spanSlider) spanSlider.value = currentSpan;
      if (spanLabel) spanLabel.textContent = '10.0m';
      if (hSlider) hSlider.value = currentH;
      if (hLabel) hLabel.textContent = '28cm';
      if (cantSlider) cantSlider.value = currentCant;
      if (cantLabel) cantLabel.textContent = '3.5m';
      const dropOverlay = document.getElementById('drop-overlay');
      if (dropOverlay) dropOverlay.classList.add('opacity-0');
      updatePhysicsFromSliders();
    });
  }

  const btnLoadS2 = document.getElementById('btn-load-s2');
  if (btnLoadS2) {
    btnLoadS2.addEventListener('click', () => {
      currentSpan = 5.0;
      currentH = 45.0;
      currentCant = 0.0;
      if (spanSlider) spanSlider.value = currentSpan;
      if (spanLabel) spanLabel.textContent = '5.0m';
      if (hSlider) hSlider.value = currentH;
      if (hLabel) hLabel.textContent = '45cm';
      if (cantSlider) cantSlider.value = currentCant;
      if (cantLabel) cantLabel.textContent = '0.0m';
      const dropOverlay = document.getElementById('drop-overlay');
      if (dropOverlay) dropOverlay.classList.add('opacity-0');
      updatePhysicsFromSliders();
    });
  }

  // Export Actions
  const btnExpIfc = document.getElementById('btn-export-current-ifc');
  if (btnExpIfc) {
    btnExpIfc.addEventListener('click', () => {
      window.location.href = '/api/export/residencia_vao_livre_critico/bim.ifc';
    });
  }
  const btnExpDxf = document.getElementById('btn-export-current-dxf');
  if (btnExpDxf) {
    btnExpDxf.addEventListener('click', () => {
      window.location.href = '/api/export/residencia_vao_livre_critico/cad.dxf';
    });
  }

  // Technical Assistant Multi-Turn Chat
  const copilotForm = document.getElementById('copilot-form');
  const copilotInput = document.getElementById('copilot-input');
  const copilotChatBox = document.getElementById('copilot-chat-box');

  if (copilotForm && copilotInput && copilotChatBox) {
    copilotForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const query = copilotInput.value.trim();
      if (!query) return;

      const userMsgDiv = document.createElement('div');
      userMsgDiv.className = 'p-2.5 rounded bg-surface-elevated border border-edge text-ink-strong text-right leading-relaxed';
      userMsgDiv.innerHTML = `<span class="font-mono font-semibold text-ink-muted text-[10px] block mb-0.5">CONSULTA</span>${escapeViewerHtml(query)}`;
      copilotChatBox.appendChild(userMsgDiv);
      copilotInput.value = '';
      copilotChatBox.scrollTop = copilotChatBox.scrollHeight;

      try {
        const res = await fetch('/api/analysis/copilot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: query,
            project_context: {
              span_length_m: currentSpan,
              beam_height_cm: currentH,
              beam_width_cm: 20.0
            }
          })
        });
        const data = await res.json();
        const replyDiv = document.createElement('div');
        replyDiv.className = 'p-2.5 rounded bg-surface-card border border-edge text-ink-secondary leading-relaxed';
        replyDiv.innerHTML = `<span class="font-mono font-semibold text-ink-strong text-[10px] block mb-0.5">PARECER (${escapeViewerHtml(data.model || 'AI')})</span>${escapeViewerHtml(data.reply)}`;
        copilotChatBox.appendChild(replyDiv);
        copilotChatBox.scrollTop = copilotChatBox.scrollHeight;
      } catch (err) {
        console.error('Copilot error:', err);
      }
    });
  }

  updatePhysicsFromSliders();
});

