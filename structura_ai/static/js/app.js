/**
 * Structura.AI — Interactive Studio State Manager
 * Handles real-time sliders, instant physics recalculation,
 * tab switching between the 5 Redesign Variants, and Gemini AI synthesis.
 */

class StructuraStudio {
  constructor() {
    this.currentVariants = [];
    this.activeVariantIndex = 0;
    this.debounceTimer = null;

    this.initElements();
    this.initEventListeners();
    this.triggerQuickCalc(); // Initial run on page load
  }

  initElements() {
    // Inputs & Sliders
    this.spanSlider = document.getElementById('input-span');
    this.spanVal = document.getElementById('val-span');

    this.cantileverSlider = document.getElementById('input-cantilever');
    this.cantileverVal = document.getElementById('val-cantilever');

    this.beamHSlider = document.getElementById('input-beam-h');
    this.beamHVal = document.getElementById('val-beam-h');

    this.beamWSlider = document.getElementById('input-beam-w');
    this.beamWVal = document.getElementById('val-beam-w');

    this.colSecSlider = document.getElementById('input-col-sec');
    this.colSecVal = document.getElementById('val-col-sec');

    this.colHSlider = document.getElementById('input-col-h');
    this.colHVal = document.getElementById('val-col-h');

    this.occupancySelect = document.getElementById('select-occupancy');
    this.fckSelect = document.getElementById('select-fck');

    // Display Badges & Gauges
    this.verdictBadge = document.getElementById('verdict-badge');
    this.verdictTitle = document.getElementById('verdict-title');
    this.verdictDesc = document.getElementById('verdict-desc');
    this.scoreVal = document.getElementById('score-val');
    this.scoreBar = document.getElementById('score-bar');

    // Metric Displays
    this.metricDeflection = document.getElementById('metric-deflection');
    this.metricAllowable = document.getElementById('metric-allowable');
    this.metricMoment = document.getElementById('metric-moment');
    this.metricBuckling = document.getElementById('metric-buckling');

    // Diagnostics & Failure List
    this.failuresContainer = document.getElementById('failures-container');
    this.failuresList = document.getElementById('failures-list');

    // 5 Variants Section
    this.variantsSection = document.getElementById('variants-section');
    this.variantsTabs = document.getElementById('variants-tabs');
    this.variantContent = document.getElementById('variant-active-content');
    this.svgContainer = document.getElementById('variant-svg-container');

    // Upload & Save Form
    this.saveForm = document.getElementById('studio-save-form');
    this.btnSave = document.getElementById('btn-save-project');
  }

  initEventListeners() {
    // Sliders live update
    const sliders = [
      { slider: this.spanSlider, display: this.spanVal, suffix: 'm' },
      { slider: this.cantileverSlider, display: this.cantileverVal, suffix: 'm' },
      { slider: this.beamHSlider, display: this.beamHVal, suffix: 'cm' },
      { slider: this.beamWSlider, display: this.beamWVal, suffix: 'cm' },
      { slider: this.colSecSlider, display: this.colSecVal, suffix: 'cm' },
      { slider: this.colHSlider, display: this.colHVal, suffix: 'm' }
    ];

    sliders.forEach(({ slider, display, suffix }) => {
      if (slider && display) {
        slider.addEventListener('input', (e) => {
          display.textContent = `${parseFloat(e.target.value).toFixed(1)} ${suffix}`;
          this.scheduleQuickCalc();
        });
      }
    });

    if (this.occupancySelect) {
      this.occupancySelect.addEventListener('change', () => this.scheduleQuickCalc());
    }
    if (this.fckSelect) {
      this.fckSelect.addEventListener('change', () => this.scheduleQuickCalc());
    }

    // Save & Gemini Full Analysis Form
    if (this.saveForm) {
      this.saveForm.addEventListener('submit', (e) => this.handleSaveProject(e));
    }
  }

  scheduleQuickCalc() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => this.triggerQuickCalc(), 60);
  }

  getPayload() {
    const liveLoadMap = {
      'Residencial': 2.5,
      'Comercial': 3.5,
      'Institucional': 4.5
    };
    const occupancy = this.occupancySelect ? this.occupancySelect.value : 'Residencial';
    const liveLoad = liveLoadMap[occupancy] || 2.5;

    return {
      span_length_m: parseFloat(this.spanSlider ? this.spanSlider.value : 9.5),
      cantilever_length_m: parseFloat(this.cantileverSlider ? this.cantileverSlider.value : 3.5),
      beam_height_cm: parseFloat(this.beamHSlider ? this.beamHSlider.value : 30.0),
      beam_width_cm: parseFloat(this.beamWSlider ? this.beamWSlider.value : 20.0),
      column_section_cm: parseFloat(this.colSecSlider ? this.colSecSlider.value : 20.0),
      column_height_m: parseFloat(this.colHSlider ? this.colHSlider.value : 3.2),
      concrete_fck_mpa: parseFloat(this.fckSelect ? this.fckSelect.value : 30.0),
      dead_load_kpa: 4.5,
      live_load_kpa: liveLoad,
      category: occupancy
    };
  }

  async triggerQuickCalc() {
    const payload = this.getPayload();
    try {
      const response = await fetch('/api/analysis/quick-calc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) return;

      const data = await response.json();
      this.renderResults(data.evaluation, data.variants);
    } catch (err) {
      console.error('Error in quick calc:', err);
    }
  }

  renderResults(evaluation, variants) {
    this.currentVariants = variants || [];

    // Verdict header
    const isViable = evaluation.is_physically_viable;
    const score = evaluation.structural_score;

    if (this.scoreVal) this.scoreVal.textContent = `${score}/100`;
    if (this.scoreBar) {
      this.scoreBar.style.width = `${score}%`;
      this.scoreBar.className = isViable 
        ? 'h-full bg-emerald-500 rounded-full transition-all duration-300' 
        : (score >= 50 ? 'h-full bg-amber-500 rounded-full transition-all duration-300' : 'h-full bg-rose-500 rounded-full transition-all duration-300');
    }

    if (this.verdictBadge) {
      if (isViable) {
        this.verdictBadge.className = 'px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        this.verdictBadge.textContent = 'CONFORME NBR 6118';
        this.verdictTitle.textContent = 'Aprovado para Engenharia de Detalhamento';
        this.verdictTitle.className = 'text-xl font-bold text-emerald-400';
      } else {
        this.verdictBadge.className = 'px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30';
        this.verdictBadge.textContent = 'REVISÃO MANDATÓRIA (ELS/ELU)';
        this.verdictTitle.textContent = 'Reprovado segundo a Física: 5 Redesigns Propostos';
        this.verdictTitle.className = 'text-xl font-bold text-rose-400';
      }
    }

    if (this.verdictDesc) {
      this.verdictDesc.textContent = evaluation.structural_diagnosis_text;
    }

    // Numbers
    if (this.metricDeflection) {
      this.metricDeflection.textContent = `${evaluation.max_deflection_mm} mm`;
      this.metricDeflection.className = evaluation.deflection_ratio > 1.0 ? 'text-2xl font-bold text-rose-400 font-mono' : 'text-2xl font-bold text-emerald-400 font-mono';
    }
    if (this.metricAllowable) {
      this.metricAllowable.textContent = `≤ ${evaluation.allowable_deflection_mm} mm (L/250)`;
    }
    if (this.metricMoment) {
      this.metricMoment.textContent = `${evaluation.max_bending_moment_knm} kN.m`;
    }
    if (this.metricBuckling) {
      this.metricBuckling.textContent = `λ = ${evaluation.compliance_checklist?.esbeltez_pilar?.indice_esbeltez_lambda || 0}`;
    }

    // Failures list
    if (this.failuresContainer && this.failuresList) {
      if (evaluation.failure_reasons && evaluation.failure_reasons.length > 0) {
        this.failuresContainer.classList.remove('hidden');
        this.failuresList.innerHTML = evaluation.failure_reasons
          .map(f => `<li class="flex items-start gap-2 text-rose-300 text-xs leading-relaxed"><span class="text-rose-500 font-bold">✕</span><span>${f}</span></li>`)
          .join('');
      } else {
        this.failuresContainer.classList.add('hidden');
      }
    }

    // Render 5 Redesign Proposals
    this.renderVariantsTabs();
  }

  renderVariantsTabs() {
    if (!this.variantsTabs || !this.currentVariants.length) return;

    this.variantsTabs.innerHTML = '';
    this.currentVariants.forEach((v, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      const isActive = idx === this.activeVariantIndex;
      btn.className = `px-3.5 py-2.5 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-2 whitespace-nowrap ${
        isActive 
          ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/25 ring-2 ring-brand-400' 
          : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800'
      }`;
      btn.innerHTML = `<span class="w-5 h-5 rounded-full ${isActive ? 'bg-white/20' : 'bg-slate-800'} flex items-center justify-center text-[10px]">${v.variant_number}</span> ${v.strategy_name}`;
      btn.addEventListener('click', () => {
        this.activeVariantIndex = idx;
        this.renderVariantsTabs();
      });
      this.variantsTabs.appendChild(btn);
    });

    const activeV = this.currentVariants[this.activeVariantIndex];
    if (activeV && this.variantContent) {
      const delta = activeV.metrics_delta || {};
      this.variantContent.innerHTML = `
        <div class="space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <span class="text-xs font-mono text-brand-400 uppercase tracking-wider font-semibold">Proposta 0${activeV.variant_number} • ${activeV.strategy_name}</span>
              <h3 class="text-lg font-bold text-white mt-0.5">${activeV.title}</h3>
            </div>
            <div class="flex items-center gap-2">
              <span class="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ${delta.clearance_status || 'APROVADO ELS'}
              </span>
            </div>
          </div>

          <!-- Quantitative Delta Badges -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
            <div class="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <div class="text-xs text-slate-400">Flecha Final</div>
              <div class="text-lg font-bold text-emerald-400 mt-1">${delta.deflection_final_mm} mm</div>
              <div class="text-[10px] text-emerald-500 font-semibold">-${delta.deflection_reduction_pct}% redução</div>
            </div>
            <div class="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <div class="text-xs text-slate-400">Momento Máx</div>
              <div class="text-lg font-bold text-sky-400 mt-1">${delta.moment_final_knm} kN.m</div>
              <div class="text-[10px] text-slate-400">Alívio de esforços</div>
            </div>
            <div class="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <div class="text-xs text-slate-400">Alívio de Concreto</div>
              <div class="text-lg font-bold text-purple-400 mt-1">-${delta.weight_reduction_pct}%</div>
              <div class="text-[10px] text-purple-400 font-semibold">Menor carga morta</div>
            </div>
            <div class="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <div class="text-xs text-slate-400">Fator de Segurança</div>
              <div class="text-lg font-bold text-amber-400 mt-1">FS = ${delta.safety_factor}</div>
              <div class="text-[10px] text-amber-500 font-semibold">Alta margem</div>
            </div>
          </div>

          <!-- Architectural & Engineering Explanations -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs leading-relaxed pt-2">
            <div class="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
              <h4 class="font-bold text-brand-400 flex items-center gap-1.5 mb-2 font-mono uppercase">
                <i data-lucide="palette" class="w-3.5 h-3.5"></i>
                Conceito Arquitetônico
              </h4>
              <p class="text-slate-300">${activeV.architectural_concept}</p>
            </div>
            <div class="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
              <h4 class="font-bold text-indigo-400 flex items-center gap-1.5 mb-2 font-mono uppercase">
                <i data-lucide="calculator" class="w-3.5 h-3.5"></i>
                Mecânica da Engenharia
              </h4>
              <p class="text-slate-300">${activeV.engineering_solution}</p>
            </div>
          </div>

          <!-- Pitch for the Client -->
          <div class="p-4 rounded-xl bg-gradient-to-r from-brand-950/40 via-indigo-950/30 to-slate-950 border border-brand-500/20 text-xs">
            <span class="font-mono text-brand-400 font-bold block mb-1">💬 Narrativa para o Arquiteto Apresentar ao Cliente:</span>
            <p class="text-slate-200 italic">"${activeV.pitch_narrative || ''}"</p>
          </div>
        </div>
      `;

      // Render Dynamic Blueprint SVG
      if (this.svgContainer && activeV.svg_render) {
        this.svgContainer.innerHTML = activeV.svg_render;
      }

      if (window.lucide) lucide.createIcons();
    }
  }

  async handleSaveProject(e) {
    e.preventDefault();
    const btn = this.btnSave;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="animate-spin inline-block mr-2">⚙</span> Salvando & Processando com Gemini...`;
    }

    try {
      const formData = new FormData(this.saveForm);
      // Append current slider values
      formData.set('span_length_m', this.spanSlider ? this.spanSlider.value : 9.5);
      formData.set('cantilever_length_m', this.cantileverSlider ? this.cantileverSlider.value : 3.5);
      formData.set('beam_height_cm', this.beamHSlider ? this.beamHSlider.value : 30.0);
      formData.set('beam_width_cm', this.beamWSlider ? this.beamWSlider.value : 20.0);
      formData.set('column_section_cm', this.colSecSlider ? this.colSecSlider.value : 20.0);
      formData.set('column_height_m', this.colHSlider ? this.colHSlider.value : 3.2);

      const response = await fetch('/api/projects/upload', {
        method: 'POST',
        body: formData
      });

      const resData = await response.json();
      if (resData.project_id) {
        window.location.href = `/project/${resData.project_id}`;
      } else {
        alert('Erro ao salvar projeto: ' + (resData.detail || 'Tente novamente.'));
      }
    } catch (err) {
      console.error(err);
      alert('Erro na requisição. Verifique o console.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Salvar & Gerar Parecer Gemini</span>`;
        if (window.lucide) lucide.createIcons();
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.studio = new StructuraStudio();
});
