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

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024; // 25 MB

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

    // Legacy Optional Variants Containers
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

    // Multi-Format Viewport Switcher & Redesign Decision Deck
    if (window.ViewportSwitcher) {
      this.viewportSwitcher = new window.ViewportSwitcher();
    }
    if (window.RedesignDecisionDeck) {
      this.decisionDeck = new window.RedesignDecisionDeck('decision-deck-container', {
        onVariantSelect: (variantNum) => {
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
        this.dropzone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'dragend', 'drop'].forEach((evtName) => {
      this.dropzone.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.remove('is-dragover');
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

    const allowedExt = /\.(png|jpe?g|webp|gif|bmp|svg|pdf|dxf|ifc|obj|gltf|glb|stl)$/i;
    const isAllowedMime = file.type.startsWith('image/') || file.type === 'application/pdf';
    if (!isAllowedMime && !allowedExt.test(file.name)) {
      this.clearSelectedFile();
      this.showFeedback('Formato não suportado. Envie DXF, IFC, OBJ, glTF, PNG, JPG, SVG ou PDF.', 'error');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      this.clearSelectedFile();
      this.showFeedback(`Arquivo excede 25 MB (${formatBytes(file.size)}). Escolha um arquivo menor.`, 'error');
      return;
    }

    if (this.fileLabel) {
      this.fileLabel.textContent = file.name;
    }
    if (this.fileSublabel) {
      this.fileSublabel.textContent = `Selecionado · ${formatBytes(file.size)}`;
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
      this.fileLabel.textContent = 'Arraste um arquivo ou clique para selecionar';
    }
    if (this.fileSublabel) {
      this.fileSublabel.textContent = 'DXF, IFC, OBJ, glTF, SVG, PNG, JPG ou PDF até 25 MB';
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
        ? 'ui-alert-fail text-xs font-mono text-accent-rose'
        : 'ui-alert-ok text-xs font-mono text-accent-emerald';
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
        customOpt.textContent = `Projeto: ${project.title}`;
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
        ? 'h-full bg-accent-emerald rounded-full transition-all duration-300'
        : isWarning
          ? 'h-full bg-accent-amber rounded-full transition-all duration-300'
          : 'h-full bg-accent-rose rounded-full transition-all duration-300';
    }

    if (this.verdictBadge && this.verdictTitle) {
      this.verdictTitle.className = 'text-base sm:text-lg font-semibold text-ink-strong';
      if (isViable) {
        this.verdictBadge.className = 'ui-badge ui-badge-ok';
        this.verdictBadge.textContent = 'Conforme NBR 6118';
        this.verdictTitle.textContent = evaluation.compliance_level || 'Aprovado para detalhamento executivo';
      } else if (isWarning) {
        this.verdictBadge.className = 'ui-badge ui-badge-warn';
        this.verdictBadge.textContent = 'Atenção estrutural (ELS/ELU)';
        this.verdictTitle.textContent = `${evaluation.compliance_level || 'Ajustes recomendados'} — 5 alternativas disponíveis`;
      } else {
        this.verdictBadge.className = 'ui-badge ui-badge-fail';
        this.verdictBadge.textContent = 'Revisão necessária (ELS/ELU)';
        this.verdictTitle.textContent = 'Parâmetros acima dos limites normativos — 5 alternativas dimensionadas';
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
          ? 'ui-metric-value is-fail'
          : 'ui-metric-value is-ok';
    }
    if (this.metricAllowable) {
      this.metricAllowable.textContent = `≤ ${evaluation.allowable_deflection_mm} mm (L/250)`;
    }

    // 2. Bending Moment
    if (this.metricMoment) {
      this.metricMoment.textContent = `${evaluation.max_bending_moment_knm} kN·m`;
    }

    // 3. Column Slenderness & Buckling
    const colCheck = evaluation.compliance_checklist?.esbeltez_pilar;
    const lambdaVal = colCheck?.indice_esbeltez_lambda ?? 0;
    const colFailed = colCheck?.status === 'FAIL';
    if (this.metricBuckling) {
      this.metricBuckling.textContent = `λ = ${lambdaVal}`;
      this.metricBuckling.className = colFailed
        ? 'ui-metric-value is-fail'
        : lambdaVal > 90
          ? 'ui-metric-value is-warn'
          : 'ui-metric-value';
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
          ? 'ui-metric-value is-warn'
          : 'ui-metric-value';
    }
    if (this.metricSpanDepthHint) {
      this.metricSpanDepthHint.textContent = `h ref. ≥ ${recMinHCm} cm (L/13)`;
    }

    // Failures list
    if (this.failuresContainer && this.failuresList) {
      if (evaluation.failure_reasons && evaluation.failure_reasons.length > 0) {
        this.failuresContainer.classList.remove('hidden');
        this.failuresList.innerHTML = evaluation.failure_reasons
          .map(
            (f) =>
              `<li class="flex items-start gap-2 text-ink-primary text-xs leading-relaxed"><span class="text-accent-rose font-mono shrink-0">—</span><span>${escapeHtml(f)}</span></li>`
          )
          .join('');
      } else {
        this.failuresContainer.classList.add('hidden');
        this.failuresList.innerHTML = '';
      }
    }

    this.renderVariantsTabs();

    if (this.viewportSwitcher) {
      this.viewportSwitcher.updateFromParams({
        ...this.getPayload(),
        max_deflection_mm: evaluation.max_deflection_mm,
        allowable_deflection_mm: evaluation.allowable_deflection_mm,
        is_viable: isViable,
        score: score
      });
    }

    if (this.decisionDeck) {
      this.decisionDeck.init(variants, {
        deflection_mm: evaluation.max_deflection_mm,
        allowable_mm: evaluation.allowable_deflection_mm,
        score: score,
        span_m: parseFloat(this.spanSlider ? this.spanSlider.value : 10.0)
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
      btn.className = `ui-tab ${isActive ? 'is-active' : ''}`;
      btn.innerHTML = `<span>0${escapeHtml(v.variant_number)} · ${escapeHtml(v.strategy_name)}</span>`;
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
        <div class="flex flex-wrap gap-1.5">
          ${features.map((feat) => `<span class="ui-badge">${escapeHtml(feat)}</span>`).join('')}
        </div>
      `
      : '';

    this.variantContent.innerHTML = `
      <div class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-edge pb-3">
          <div>
            <span class="text-[11px] font-mono text-ink-muted uppercase">Proposta ${String(activeV.variant_number).padStart(2, '0')} · ${escapeHtml(activeV.strategy_name)}</span>
            <h3 class="text-sm sm:text-base font-semibold text-ink-strong mt-0.5">${escapeHtml(activeV.title)}</h3>
          </div>
          <span class="ui-badge ui-badge-ok">${escapeHtml(delta.clearance_status || 'Conforme ELS')}</span>
        </div>

        ${featuresHtml}

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="ui-metric">
            <span class="ui-metric-label">Flecha final</span>
            <span class="ui-metric-value is-ok">${escapeHtml(delta.deflection_final_mm)} mm</span>
            <span class="ui-metric-hint">-${escapeHtml(delta.deflection_reduction_pct)}% redução</span>
          </div>
          <div class="ui-metric">
            <span class="ui-metric-label">Momento máximo</span>
            <span class="ui-metric-value">${escapeHtml(delta.moment_final_knm)} kN·m</span>
            <span class="ui-metric-hint">Alívio de esforços</span>
          </div>
          <div class="ui-metric">
            <span class="ui-metric-label">Alívio de massa</span>
            <span class="ui-metric-value">-${escapeHtml(delta.weight_reduction_pct)}%</span>
            <span class="ui-metric-hint">Menor carga própria</span>
          </div>
          <div class="ui-metric">
            <span class="ui-metric-label">Fator de segurança</span>
            <span class="ui-metric-value">FS = ${escapeHtml(delta.safety_factor)}</span>
            <span class="ui-metric-hint">Reserva resistente</span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs leading-relaxed">
          <div class="ui-well">
            <h4 class="font-mono font-semibold text-ink-strong uppercase text-[11px] mb-1.5">Partido arquitetônico</h4>
            <p class="text-ink-secondary">${escapeHtml(activeV.architectural_concept)}</p>
          </div>
          <div class="ui-well">
            <h4 class="font-mono font-semibold text-ink-strong uppercase text-[11px] mb-1.5">Solução estrutural</h4>
            <p class="text-ink-secondary">${escapeHtml(activeV.engineering_solution)}</p>
          </div>
        </div>

        <div class="ui-note text-xs leading-relaxed">
          <span class="font-mono font-semibold text-ink-strong block mb-1 text-[11px]">Síntese para apresentação ao cliente</span>
          <p class="text-ink-secondary">"${escapeHtml(activeV.pitch_narrative || '')}"</p>
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
      btn.textContent = 'Salvando e emitindo parecer...';
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
        btn.innerHTML = '<span>Salvar e emitir parecer técnico</span>';
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.studio = new StructuraStudio();
});
