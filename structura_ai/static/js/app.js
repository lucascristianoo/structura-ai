/**
 * Structura.AI — Interactive Studio State Manager
 * Handles real-time sliders, bidirectional canvas sync, drag-and-drop blueprint upload,
 * loading existing saved projects (?project=<id>), and the 5 Redesign Variants UI.
 */

const LIVE_LOAD_MAP = {
  Residencial: 2.5,
  Comercial: 3.5,
  Institucional: 4.5,
  Cultural: 2.5
};

const MAX_UPLOAD_BYTES = 15 * 1024 * 1024; // 15 MB

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

class StructuraStudio {
  constructor() {
    this.currentVariants = [];
    this.activeVariantIndex = 0;
    this.debounceTimer = null;
    this.calcAbortController = null;

    const root = document.getElementById('studio-root');
    this.deadLoadKpa = parseFloat(root?.dataset.deadLoad) || 4.5;
    this.overrideLiveLoadKpa = root?.dataset.liveLoad ? parseFloat(root.dataset.liveLoad) : null;
    this.viewportSwitcher = null;
    this.decisionDeck = null;

    this.initElements();
    this.initEventListeners();
    this.initDragAndDrop();
    this.init();
  }

  async init() {
    const params = new URLSearchParams(window.location.search);
    const projectId = params.get('project');
    if (projectId) {
      await this.loadExistingProject(projectId);
    }
    await this.triggerQuickCalc();
  }

  initElements() {
    this.presetSelect = document.getElementById('preset-select');

    // Sliders & Labels
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
    this.metricBucklingHint = document.getElementById('metric-buckling-hint');
    this.metricSpanDepth = document.getElementById('metric-span-depth');
    this.metricSpanDepthHint = document.getElementById('metric-span-depth-hint');

    // Diagnostics & Failure List
    this.failuresContainer = document.getElementById('failures-container');
    this.failuresList = document.getElementById('failures-list');

    // 5 Variants Section
    this.variantsTabs = document.getElementById('variants-tabs');
    this.variantContent = document.getElementById('variant-active-content');
    this.svgContainer = document.getElementById('variant-svg-container');

    // Upload & Save Form
    this.saveForm = document.getElementById('studio-save-form');
    this.titleInput = document.getElementById('input-project-title');
    this.authorInput = document.getElementById('input-project-author');
    this.descriptionInput = document.getElementById('input-project-description');
    this.dropzone = document.getElementById('upload-dropzone');
    this.fileInput = document.getElementById('file-upload');
    this.fileLabel = document.getElementById('file-label');
    this.fileSublabel = document.getElementById('file-sublabel');
    this.btnClearFile = document.getElementById('btn-clear-file');
    this.linkedBanner = document.getElementById('linked-drawing-banner');
    this.linkedName = document.getElementById('linked-drawing-name');
    this.linkedLink = document.getElementById('linked-drawing-link');
    this.formFeedback = document.getElementById('form-feedback');
    this.btnSave = document.getElementById('btn-save-project');

    // Multi-Format Viewport Switcher & Professional Redesign Deck
    if (window.ViewportSwitcher) {
      this.viewportSwitcher = new window.ViewportSwitcher();
    }
    if (window.RedesignDecisionDeck) {
      this.decisionDeck = new window.RedesignDecisionDeck('decision-deck-container', {
        onVariantSelect: (variantNum, variantData) => {
          this.activeVariantIndex = variantNum - 1;
          if (this.viewportSwitcher) {
            this.viewportSwitcher.setActiveVariant(variantNum);
          }
        }
      });
    }
  }

  initEventListeners() {
    if (this.presetSelect) {
      this.presetSelect.addEventListener('change', () => {
        if (this.presetSelect.value) {
          window.location.href = `/analyzer?preset=${encodeURIComponent(this.presetSelect.value)}`;
        }
      });
    }

    const sliders = [
      { slider: this.spanSlider, display: this.spanVal, suffix: 'm', decimals: 1, syncCanvas: true },
      { slider: this.cantileverSlider, display: this.cantileverVal, suffix: 'm', decimals: 1, syncCanvas: true },
      { slider: this.beamHSlider, display: this.beamHVal, suffix: 'cm', decimals: 0, syncCanvas: false },
      { slider: this.beamWSlider, display: this.beamWVal, suffix: 'cm', decimals: 0, syncCanvas: false },
      { slider: this.colSecSlider, display: this.colSecVal, suffix: 'cm', decimals: 0, syncCanvas: false },
      { slider: this.colHSlider, display: this.colHVal, suffix: 'm', decimals: 1, syncCanvas: false }
    ];

    sliders.forEach(({ slider, display, suffix, decimals, syncCanvas }) => {
      if (!slider || !display) return;
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        display.textContent = `${val.toFixed(decimals)} ${suffix}`;
        if (syncCanvas && window.archCanvas) {
          const spanM = parseFloat(this.spanSlider?.value) || 9.5;
          const cantM = parseFloat(this.cantileverSlider?.value) || 0.0;
          window.archCanvas.setLayoutFromParams(spanM, cantM);
        }
        this.scheduleQuickCalc();
      });
    });

    if (this.occupancySelect) {
      this.occupancySelect.addEventListener('change', () => {
        // User explicitly switched occupancy class: use standard NBR 6120 live load
        this.overrideLiveLoadKpa = null;
        this.scheduleQuickCalc();
      });
    }

    if (this.fckSelect) {
      this.fckSelect.addEventListener('change', () => this.scheduleQuickCalc());
    }

    // Official CAD/BIM Sample Loader
    const sampleSelect = document.getElementById('select-cad-sample');
    if (sampleSelect) {
      sampleSelect.addEventListener('change', async (e) => {
        const val = e.target.value;
        if (!val) return;
        sampleSelect.disabled = true;
        try {
          const res = await fetch(`/api/projects/samples/load/${val}`, { method: 'POST' });
          const data = await res.json();
          if (data.project_id) {
            window.location.href = `/project/${data.project_id}`;
          }
        } catch (err) {
          console.error('Falha ao carregar amostra:', err);
        } finally {
          sampleSelect.disabled = false;
        }
      });
    }

    // Save & Gemini Full Analysis Form
    if (this.saveForm) {
      this.saveForm.addEventListener('submit', (e) => this.handleSaveProject(e));
    }
  }

  initDragAndDrop() {
    if (!this.dropzone || !this.fileInput) return;

    this.dropzone.addEventListener('click', (e) => {
      if (e.target.closest('#btn-clear-file')) return;
      this.fileInput.click();
    });

    this.fileInput.addEventListener('change', () => {
      const file = this.fileInput.files?.[0];
      if (file) this.applySelectedFile(file);
    });

    if (this.btnClearFile) {
      this.btnClearFile.addEventListener('click', (e) => {
        e.stopPropagation();
        this.clearSelectedFile();
      });
    }

    ['dragenter', 'dragover'].forEach((evtName) => {
      this.dropzone.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.add('border-brand-400', 'bg-brand-500/10');
        this.dropzone.classList.remove('border-slate-700');
      });
    });

    ['dragleave', 'dragend', 'drop'].forEach((evtName) => {
      this.dropzone.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.remove('border-brand-400', 'bg-brand-500/10');
        this.dropzone.classList.add('border-slate-700');
      });
    });

    this.dropzone.addEventListener('drop', (e) => {
      const droppedFile = e.dataTransfer?.files?.[0];
      if (!droppedFile) return;

      const dt = new DataTransfer();
      dt.items.add(droppedFile);
      this.fileInput.files = dt.files;
      this.applySelectedFile(droppedFile);
    });
  }

  applySelectedFile(file) {
    this.hideFeedback();

    const allowedExt = /\.(png|jpe?g|webp|gif|bmp|svg|pdf)$/i;
    const isAllowedMime = file.type.startsWith('image/') || file.type === 'application/pdf';
    if (!isAllowedMime && !allowedExt.test(file.name)) {
      this.clearSelectedFile();
      this.showFeedback('Formato não suportado. Envie PNG, JPG, WEBP, SVG ou PDF.', 'error');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      this.clearSelectedFile();
      this.showFeedback(`Arquivo excede 15MB (${formatBytes(file.size)}). Escolha um arquivo menor.`, 'error');
      return;
    }

    if (this.fileLabel) {
      this.fileLabel.textContent = file.name;
    }
    if (this.fileSublabel) {
      this.fileSublabel.textContent = `Selecionado • ${formatBytes(file.size)}`;
    }
    if (this.btnClearFile) {
      this.btnClearFile.classList.remove('hidden');
    }
  }

  clearSelectedFile() {
    if (this.fileInput) {
      this.fileInput.value = '';
    }
    if (this.fileLabel) {
      this.fileLabel.textContent = 'Arraste sua planta aqui ou clique para selecionar';
    }
    if (this.fileSublabel) {
      this.fileSublabel.textContent = 'PNG, JPG, SVG ou PDF até 15MB (ou use o croqui ao lado)';
    }
    if (this.btnClearFile) {
      this.btnClearFile.classList.add('hidden');
    }
  }

  showFeedback(message, type = 'error') {
    if (!this.formFeedback) return;
    this.formFeedback.textContent = message;
    this.formFeedback.className =
      type === 'error'
        ? 'p-3 rounded-xl text-sm font-mono border bg-rose-950/40 border-rose-500/30 text-rose-300'
        : 'p-3 rounded-xl text-sm font-mono border bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
  }

  hideFeedback() {
    if (this.formFeedback) {
      this.formFeedback.classList.add('hidden');
    }
  }

  setSliderValue(slider, display, rawVal, decimals, suffix) {
    if (!slider || rawVal === undefined || rawVal === null) return;
    const min = parseFloat(slider.min);
    const max = parseFloat(slider.max);
    const clamped = Math.min(max, Math.max(min, parseFloat(rawVal)));
    slider.value = clamped.toFixed(decimals);
    if (display) {
      display.textContent = `${clamped.toFixed(decimals)} ${suffix}`;
    }
  }

  async loadExistingProject(projectId) {
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`);
      if (!resp.ok) {
        this.showFeedback('Projeto solicitado não encontrado. Carregando cenário padrão.', 'error');
        return;
      }

      const project = await resp.json();
      const p = project.parameters || {};

      this.setSliderValue(this.spanSlider, this.spanVal, p.span_length_m, 1, 'm');
      this.setSliderValue(this.cantileverSlider, this.cantileverVal, p.cantilever_length_m, 1, 'm');
      this.setSliderValue(this.beamHSlider, this.beamHVal, p.beam_height_cm, 0, 'cm');
      this.setSliderValue(this.beamWSlider, this.beamWVal, p.beam_width_cm, 0, 'cm');
      this.setSliderValue(this.colSecSlider, this.colSecVal, p.column_section_cm, 0, 'cm');
      this.setSliderValue(this.colHSlider, this.colHVal, p.column_height_m, 1, 'm');

      if (p.dead_load_kpa !== undefined) {
        this.deadLoadKpa = parseFloat(p.dead_load_kpa) || 4.5;
      }
      if (p.live_load_kpa !== undefined) {
        this.overrideLiveLoadKpa = parseFloat(p.live_load_kpa) || null;
      }

      if (this.occupancySelect && project.category) {
        const hasOption = Array.from(this.occupancySelect.options).some((o) => o.value === project.category);
        if (!hasOption) {
          const opt = document.createElement('option');
          opt.value = project.category;
          opt.textContent = project.category;
          this.occupancySelect.appendChild(opt);
        }
        this.occupancySelect.value = project.category;
      }

      if (this.fckSelect && p.concrete_fck_mpa !== undefined) {
        const fckFormatted = parseFloat(p.concrete_fck_mpa).toFixed(1);
        const hasFck = Array.from(this.fckSelect.options).some((o) => o.value === fckFormatted);
        if (!hasFck) {
          const opt = document.createElement('option');
          opt.value = fckFormatted;
          opt.textContent = `C${Math.round(parseFloat(p.concrete_fck_mpa))} (${fckFormatted} MPa)`;
          this.fckSelect.appendChild(opt);
        }
        this.fckSelect.value = fckFormatted;
      }

      if (this.titleInput && project.title) {
        this.titleInput.value = project.title;
      }
      if (this.authorInput && project.author_architect) {
        this.authorInput.value = project.author_architect;
      }
      if (this.descriptionInput) {
        this.descriptionInput.value = project.description || '';
      }

      if (this.presetSelect) {
        const customOpt = document.createElement('option');
        customOpt.value = '';
        customOpt.textContent = `📂 Projeto: ${project.title}`;
        customOpt.selected = true;
        this.presetSelect.prepend(customOpt);
      }

      const drawingUrl = project.image_path || (project.image_filename ? `/uploads/${project.image_filename}` : null);
      if (drawingUrl && this.linkedBanner && this.linkedName && this.linkedLink) {
        this.linkedName.textContent = project.image_filename || 'Desenho vinculado';
        this.linkedLink.href = drawingUrl;
        this.linkedBanner.classList.remove('hidden');
      }

      if (window.archCanvas) {
        window.archCanvas.setLayoutFromParams(
          parseFloat(this.spanSlider?.value) || 9.5,
          parseFloat(this.cantileverSlider?.value) || 0.0
        );
      }
    } catch (err) {
      console.error('Error loading project into Studio:', err);
    }
  }

  scheduleQuickCalc() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => this.triggerQuickCalc(), 60);
  }

  getActiveLiveLoad(occupancy) {
    if (this.overrideLiveLoadKpa !== null && !Number.isNaN(this.overrideLiveLoadKpa)) {
      return this.overrideLiveLoadKpa;
    }
    return LIVE_LOAD_MAP[occupancy] || 2.5;
  }

  getPayload() {
    const occupancy = this.occupancySelect ? this.occupancySelect.value : 'Residencial';
    return {
      span_length_m: parseFloat(this.spanSlider ? this.spanSlider.value : 9.5),
      cantilever_length_m: parseFloat(this.cantileverSlider ? this.cantileverSlider.value : 3.5),
      beam_height_cm: parseFloat(this.beamHSlider ? this.beamHSlider.value : 30.0),
      beam_width_cm: parseFloat(this.beamWSlider ? this.beamWSlider.value : 20.0),
      column_section_cm: parseFloat(this.colSecSlider ? this.colSecSlider.value : 20.0),
      column_height_m: parseFloat(this.colHSlider ? this.colHSlider.value : 3.2),
      concrete_fck_mpa: parseFloat(this.fckSelect ? this.fckSelect.value : 30.0),
      dead_load_kpa: this.deadLoadKpa,
      live_load_kpa: this.getActiveLiveLoad(occupancy),
      category: occupancy
    };
  }

  async triggerQuickCalc() {
    if (this.calcAbortController) {
      this.calcAbortController.abort();
    }
    this.calcAbortController = new AbortController();

    const payload = this.getPayload();
    try {
      const response = await fetch('/api/analysis/quick-calc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: this.calcAbortController.signal
      });
      if (!response.ok) return;

      const data = await response.json();
      this.renderResults(data.evaluation, data.variants);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Error in quick calc:', err);
      }
    }
  }

  renderResults(evaluation, variants) {
    this.currentVariants = variants || [];

    const isViable = evaluation.is_physically_viable;
    const score = evaluation.structural_score;
    const isWarning = !isViable && score >= 50;

    if (this.scoreVal) this.scoreVal.textContent = `${score}/100`;
    if (this.scoreBar) {
      this.scoreBar.style.width = `${score}%`;
      this.scoreBar.className = isViable
        ? 'h-full bg-emerald-500 rounded-full transition-all duration-300'
        : isWarning
          ? 'h-full bg-amber-500 rounded-full transition-all duration-300'
          : 'h-full bg-rose-500 rounded-full transition-all duration-300';
    }

    if (this.verdictBadge && this.verdictTitle) {
      if (isViable) {
        this.verdictBadge.className = 'px-3.5 py-1 rounded-full text-xs sm:text-sm font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        this.verdictBadge.textContent = 'CONFORME NBR 6118';
        this.verdictTitle.textContent = evaluation.compliance_level || 'Aprovado para Engenharia de Detalhamento';
        this.verdictTitle.className = 'text-xl sm:text-2xl font-bold text-emerald-400 mb-2';
      } else if (isWarning) {
        this.verdictBadge.className = 'px-3.5 py-1 rounded-full text-xs sm:text-sm font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30';
        this.verdictBadge.textContent = 'ALERTA ESTRUTURAL (ELS/ELU)';
        this.verdictTitle.textContent = `${evaluation.compliance_level || 'Ajustes Recomendados'}: 5 Redesigns Propostos`;
        this.verdictTitle.className = 'text-xl sm:text-2xl font-bold text-amber-400 mb-2';
      } else {
        this.verdictBadge.className = 'px-3.5 py-1 rounded-full text-xs sm:text-sm font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30';
        this.verdictBadge.textContent = 'REVISÃO MANDATÓRIA (ELS/ELU)';
        this.verdictTitle.textContent = 'Reprovado segundo a Física: 5 Redesigns Propostos';
        this.verdictTitle.className = 'text-xl sm:text-2xl font-bold text-rose-400 mb-2';
      }
    }

    if (this.verdictDesc) {
      this.verdictDesc.textContent = evaluation.structural_diagnosis_text || '';
    }

    // 1. Deflection
    if (this.metricDeflection) {
      this.metricDeflection.textContent = `${evaluation.max_deflection_mm} mm`;
      this.metricDeflection.className =
        evaluation.deflection_ratio > 1.0
          ? 'text-2xl font-bold text-rose-400 font-mono mt-1 block'
          : 'text-2xl font-bold text-emerald-400 font-mono mt-1 block';
    }
    if (this.metricAllowable) {
      this.metricAllowable.textContent = `≤ ${evaluation.allowable_deflection_mm} mm (L/250)`;
    }

    // 2. Bending Moment
    if (this.metricMoment) {
      this.metricMoment.textContent = `${evaluation.max_bending_moment_knm} kN.m`;
    }

    // 3. Column Slenderness & Buckling
    const colCheck = evaluation.compliance_checklist?.esbeltez_pilar;
    const lambdaVal = colCheck?.indice_esbeltez_lambda ?? 0;
    const colFailed = colCheck?.status === 'FAIL';
    if (this.metricBuckling) {
      this.metricBuckling.textContent = `λ = ${lambdaVal}`;
      this.metricBuckling.className = colFailed
        ? 'text-2xl font-bold text-rose-400 font-mono mt-1 block'
        : lambdaVal > 90
          ? 'text-2xl font-bold text-amber-400 font-mono mt-1 block'
          : 'text-2xl font-bold text-indigo-400 font-mono mt-1 block';
    }
    if (this.metricBucklingHint) {
      this.metricBucklingHint.textContent = colFailed ? 'Acima do limite (λ ≤ 140)' : 'Limite λ ≤ 140';
    }

    // 4. Span-to-Depth Ratio (L/h)
    const inputs = evaluation.calculated_inputs || {};
    const spanM = inputs.span_length_m || parseFloat(this.spanSlider?.value) || 9.5;
    const beamHCm = inputs.beam_height_cm || parseFloat(this.beamHSlider?.value) || 30.0;
    const spanDepthRatio = Math.round((spanM * 100.0) / Math.max(beamHCm, 1.0));
    const recMinHCm = Math.round((spanM / 13.0) * 100.0);

    if (this.metricSpanDepth) {
      this.metricSpanDepth.textContent = `L/${spanDepthRatio}`;
      this.metricSpanDepth.className =
        spanDepthRatio > 16
          ? 'text-2xl font-bold text-amber-400 font-mono mt-1 block'
          : 'text-2xl font-bold text-purple-400 font-mono mt-1 block';
    }
    if (this.metricSpanDepthHint) {
      this.metricSpanDepthHint.textContent = `h rec. ≥ ${recMinHCm} cm (L/13)`;
    }

    // Failures list
    if (this.failuresContainer && this.failuresList) {
      if (evaluation.failure_reasons && evaluation.failure_reasons.length > 0) {
        this.failuresContainer.classList.remove('hidden');
        this.failuresList.innerHTML = evaluation.failure_reasons
          .map(
            (f) =>
              `<li class="flex items-start gap-2.5 text-rose-200 text-sm leading-relaxed"><span class="text-rose-500 font-bold shrink-0">✕</span><span>${escapeHtml(f)}</span></li>`
          )
          .join('');
      } else {
        this.failuresContainer.classList.add('hidden');
        this.failuresList.innerHTML = '';
      }
    }

    this.renderVariantsTabs();

    // Sincronizar com o Viewport Multi-Formato (3D, Blueprint, Corte, Diagramas)
    if (this.viewportSwitcher) {
      this.viewportSwitcher.updateFromParams({
        ...this.getPayload(),
        max_deflection_mm: evaluation.max_deflection_mm,
        allowable_deflection_mm: evaluation.allowable_deflection_mm,
        is_viable: isViable,
        score: score,
      });
    }

    // Sincronizar com a Matriz de Decisão Executiva (Cards + Radar de Trade-offs)
    if (this.decisionDeck) {
      this.decisionDeck.init(variants, {
        deflection_mm: evaluation.max_deflection_mm,
        allowable_mm: evaluation.allowable_deflection_mm,
        score: score,
        span_m: parseFloat(this.spanSlider ? this.spanSlider.value : 10.0),
      });
    }
  }

  renderVariantsTabs() {
    if (!this.variantsTabs || !this.currentVariants.length) return;

    if (this.activeVariantIndex >= this.currentVariants.length) {
      this.activeVariantIndex = 0;
    }

    this.variantsTabs.innerHTML = '';
    this.currentVariants.forEach((v, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      const isActive = idx === this.activeVariantIndex;
      btn.className = `px-4 py-2.5 rounded-xl text-sm font-mono font-bold transition-all flex items-center gap-2 whitespace-nowrap ${
        isActive
          ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/25 ring-2 ring-brand-400'
          : 'bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-800'
      }`;
      btn.innerHTML = `<span class="w-5 h-5 rounded-full ${
        isActive ? 'bg-white/20' : 'bg-slate-800'
      } flex items-center justify-center text-xs">${escapeHtml(v.variant_number)}</span> <span>${escapeHtml(v.strategy_name)}</span>`;
      btn.addEventListener('click', () => {
        this.activeVariantIndex = idx;
        this.renderVariantsTabs();
      });
      this.variantsTabs.appendChild(btn);
    });

    const activeV = this.currentVariants[this.activeVariantIndex];
    if (!activeV || !this.variantContent) return;

    const delta = activeV.metrics_delta || {};
    const features = Array.isArray(activeV.visual_features) ? activeV.visual_features : [];
    const featuresHtml = features.length
      ? `
        <div class="flex flex-wrap gap-2 pt-1">
          ${features
            .map(
              (feat) =>
                `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-300"><span class="text-brand-400">◆</span>${escapeHtml(feat)}</span>`
            )
            .join('')}
        </div>
      `
      : '';

    this.variantContent.innerHTML = `
      <div class="space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <span class="text-xs sm:text-sm font-mono text-brand-400 uppercase tracking-wider font-semibold">Proposta ${String(activeV.variant_number).padStart(2, '0')} • ${escapeHtml(activeV.strategy_name)}</span>
            <h3 class="text-xl font-bold text-white mt-1">${escapeHtml(activeV.title)}</h3>
          </div>
          <div class="flex items-center gap-2">
            <span class="px-3 py-1 rounded-md text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              ${escapeHtml(delta.clearance_status || 'APROVADO ELS')}
            </span>
          </div>
        </div>

        ${featuresHtml}

        <!-- Quantitative Delta Badges -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3.5 font-mono">
          <div class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <div class="text-xs sm:text-sm text-slate-400">Flecha Final</div>
            <div class="text-xl font-bold text-emerald-400 mt-1">${escapeHtml(delta.deflection_final_mm)} mm</div>
            <div class="text-xs text-emerald-500 font-semibold mt-0.5">-${escapeHtml(delta.deflection_reduction_pct)}% redução</div>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <div class="text-xs sm:text-sm text-slate-400">Momento Máx</div>
            <div class="text-xl font-bold text-sky-400 mt-1">${escapeHtml(delta.moment_final_knm)} kN.m</div>
            <div class="text-xs text-slate-400 mt-0.5">Alívio de esforços</div>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <div class="text-xs sm:text-sm text-slate-400">Alívio de Concreto</div>
            <div class="text-xl font-bold text-purple-400 mt-1">-${escapeHtml(delta.weight_reduction_pct)}%</div>
            <div class="text-xs text-purple-400 font-semibold mt-0.5">Menor carga morta</div>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <div class="text-xs sm:text-sm text-slate-400">Fator de Segurança</div>
            <div class="text-xl font-bold text-amber-400 mt-1">FS = ${escapeHtml(delta.safety_factor)}</div>
            <div class="text-xs text-amber-500 font-semibold mt-0.5">Alta margem</div>
          </div>
        </div>

        <!-- Architectural & Engineering Explanations -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm leading-relaxed pt-1">
          <div class="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
            <h4 class="font-bold text-brand-400 flex items-center gap-2 mb-2 font-mono uppercase text-xs sm:text-sm">
              <i data-lucide="palette" class="w-4 h-4"></i>
              <span>Conceito Arquitetônico</span>
            </h4>
            <p class="text-slate-200">${escapeHtml(activeV.architectural_concept)}</p>
          </div>
          <div class="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
            <h4 class="font-bold text-indigo-400 flex items-center gap-2 mb-2 font-mono uppercase text-xs sm:text-sm">
              <i data-lucide="calculator" class="w-4 h-4"></i>
              <span>Mecânica da Engenharia</span>
            </h4>
            <p class="text-slate-200">${escapeHtml(activeV.engineering_solution)}</p>
          </div>
        </div>

        <!-- Pitch for the Client -->
        <div class="p-4 rounded-xl bg-gradient-to-r from-brand-950/40 via-indigo-950/30 to-slate-950 border border-brand-500/20 text-sm leading-relaxed">
          <span class="font-mono text-brand-400 font-bold block mb-1.5 text-xs sm:text-sm">💬 Narrativa para o Arquiteto Apresentar ao Cliente:</span>
          <p class="text-slate-200 italic">"${escapeHtml(activeV.pitch_narrative || '')}"</p>
        </div>
      </div>
    `;

    if (this.svgContainer && activeV.svg_render) {
      this.svgContainer.innerHTML = activeV.svg_render;
    }

    if (window.lucide) lucide.createIcons();
  }

  async handleSaveProject(e) {
    e.preventDefault();
    this.hideFeedback();

    const btn = this.btnSave;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="animate-spin inline-block mr-2">⚙</span> Salvando &amp; Processando com Gemini...`;
    }

    try {
      const formData = new FormData(this.saveForm);
      const payload = this.getPayload();

      formData.set('span_length_m', payload.span_length_m);
      formData.set('cantilever_length_m', payload.cantilever_length_m);
      formData.set('beam_height_cm', payload.beam_height_cm);
      formData.set('beam_width_cm', payload.beam_width_cm);
      formData.set('column_section_cm', payload.column_section_cm);
      formData.set('column_height_m', payload.column_height_m);
      formData.set('category', payload.category);
      formData.set('concrete_fck_mpa', payload.concrete_fck_mpa);
      formData.set('dead_load_kpa', payload.dead_load_kpa);
      formData.set('live_load_kpa', payload.live_load_kpa);

      // If no file was uploaded, capture the interactive canvas snapshot
      const hasUploadedFile = this.fileInput?.files && this.fileInput.files.length > 0;
      if (!hasUploadedFile && window.archCanvas?.canvas) {
        try {
          const canvasDataUrl = window.archCanvas.canvas.toDataURL('image/png');
          if (canvasDataUrl && canvasDataUrl.length > 50) {
            formData.set('canvas_image', canvasDataUrl);
          }
        } catch (err) {
          console.warn('Could not export canvas snapshot:', err);
        }
      }

      const response = await fetch('/api/projects/upload', {
        method: 'POST',
        body: formData
      });

      const resData = await response.json();
      if (response.ok && resData.project_id) {
        window.location.href = `/project/${resData.project_id}`;
        return;
      }

      this.showFeedback('Erro ao salvar projeto: ' + (resData.detail || 'Tente novamente.'), 'error');
    } catch (err) {
      console.error(err);
      this.showFeedback('Falha de comunicação com o servidor. Verifique sua conexão e tente novamente.', 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Salvar &amp; Gerar Parecer Gemini</span>`;
        if (window.lucide) lucide.createIcons();
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.studio = new StructuraStudio();
});
