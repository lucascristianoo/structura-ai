/**
 * Structura.AI — Viewport Switcher & Multi-Format Technical Drawings
 * Manages switching between 3D WebGL, 2D Plan, ELS Section, Internal Force Diagrams & Sketch Canvas.
 */

class ViewportSwitcher {
  constructor() {
    this.activeMode = '3d';
    this.threeViewport = null;
    this.init();
  }

  init() {
    if (document.getElementById('three-viewport-box') && window.Structura3DViewport) {
      this.threeViewport = new window.Structura3DViewport('three-viewport-box');
    }

    this.bindButtons();
    this.switchMode('3d');
  }

  bindButtons() {
    const buttons = document.querySelectorAll('[data-view-mode]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.viewMode;
        this.switchMode(mode);
      });
    });

    const shadeBtns = document.querySelectorAll('[data-shading-mode]');
    shadeBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.shadingMode;
        if (this.threeViewport) {
          this.threeViewport.setShadingMode(mode);
        }
        shadeBtns.forEach((b) => b.classList.toggle('is-active', b === btn));
      });
    });

    const ampSlider = document.getElementById('slider-amp-deflection');
    const ampVal = document.getElementById('val-amp-deflection');
    if (ampSlider) {
      ampSlider.addEventListener('input', (e) => {
        const amp = parseFloat(e.target.value);
        if (ampVal) ampVal.textContent = `${amp}x`;
        if (this.threeViewport) {
          this.threeViewport.setDeflectionAmplification(amp);
        }
      });
    }
  }

  switchMode(mode) {
    this.activeMode = mode;

    const buttons = document.querySelectorAll('[data-view-mode]');
    buttons.forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.viewMode === mode);
    });

    const controls3dBar = document.getElementById('controls-3d-bar');
    if (controls3dBar) {
      controls3dBar.classList.toggle('hidden', mode !== '3d');
    }

    const containers = {
      '3d': document.getElementById('view-container-3d'),
      blueprint: document.getElementById('view-container-blueprint'),
      section: document.getElementById('view-container-section'),
      diagrams: document.getElementById('view-container-diagrams'),
      canvas: document.getElementById('view-container-canvas')
    };

    Object.keys(containers).forEach((k) => {
      const el = containers[k];
      if (el) {
        el.classList.toggle('hidden', k !== mode);
      }
    });

    if (mode === '3d' && this.threeViewport) {
      setTimeout(() => this.threeViewport.onResize(), 50);
    } else if (mode === 'canvas' && window.archCanvas) {
      setTimeout(() => {
        window.archCanvas.initCanvasSize(false);
        const spanM = parseFloat(document.getElementById('input-span')?.value) || 9.5;
        const cantM = parseFloat(document.getElementById('input-cantilever')?.value) || 0.0;
        if (window.archCanvas.elements.length <= 4) {
          window.archCanvas.setLayoutFromParams(spanM, cantM);
        } else {
          window.archCanvas.render();
        }
      }, 30);
    }
  }

  updateFromParams(params) {
    if (this.threeViewport) {
      this.threeViewport.updateFromParams(params);
    }
    this.renderBlueprint(params);
    this.renderSection(params);
    this.renderDiagrams(params);
  }

  setActiveVariant(variantNum) {
    if (this.threeViewport) {
      this.threeViewport.setActiveVariant(variantNum);
    }
  }

  renderBlueprint(params) {
    const container = document.getElementById('svg-blueprint-content');
    if (!container) return;
    const span = parseFloat(params.span_length_m) || 10.0;
    const cant = parseFloat(params.cantilever_length_m) || 0.0;
    const bw = parseFloat(params.beam_width_cm) || 20.0;
    const bh = parseFloat(params.beam_height_cm) || 30.0;

    const totalLen = span + cant;
    const scale = 470 / Math.max(totalLen + 1.5, 8.0);
    const startX = 76;
    const p1X = startX;
    const p2X = startX + span * scale;
    const cantX = p2X + cant * scale;
    const yAxis = 138;
    const beamPlanW = Math.min(Math.max(bw * 0.55, 8), 22);

    const cantPx = cantX - p2X;
    const cantLabelX = cantPx < 78 ? p2X + 8 : (p2X + cantX) / 2;
    const cantLabelAnchor = cantPx < 78 ? 'start' : 'middle';

    container.innerHTML = `
      <svg viewBox="0 0 700 250" class="bp-svg w-full h-auto font-mono text-xs rounded">
        <defs>
          <pattern id="cad-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" class="bp-grid-line" stroke-width="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#cad-grid)" />

        <!-- Drawing Header -->
        <text x="26" y="26" class="bp-text-strong" font-size="10.5">Planta de fôrma · Eixo estrutural A</text>

        <!-- Structural Axis Bubble & Centerline -->
        <circle cx="32" cy="${yAxis}" r="11" class="bp-slab" stroke-width="1.2"/>
        <text x="32" y="${yAxis + 3.5}" class="bp-text-strong" font-size="9.5" text-anchor="middle">A</text>
        <line x1="43" y1="${yAxis}" x2="${cantX + 36}" y2="${yAxis}" class="bp-dim-line" stroke-dasharray="8,4,2,4" stroke-width="1"/>

        <!-- Primary Beam Plan -->
        <rect x="${p1X}" y="${yAxis - beamPlanW / 2}" width="${cantX - p1X}" height="${beamPlanW}" class="bp-slab" stroke-width="1.5"/>

        <!-- Columns in Section -->
        <rect x="${p1X - 9}" y="${yAxis - 16}" width="18" height="32" class="bp-struct" stroke-width="1.5"/>
        <line x1="${p1X - 9}" y1="${yAxis - 16}" x2="${p1X + 9}" y2="${yAxis + 16}" class="bp-dim-line" stroke-width="0.8"/>
        <text x="${p1X}" y="${yAxis + 32}" class="bp-text-strong" font-size="9.5" text-anchor="middle">P1</text>

        <rect x="${p2X - 9}" y="${yAxis - 16}" width="18" height="32" class="bp-struct" stroke-width="1.5"/>
        <line x1="${p2X - 9}" y1="${yAxis - 16}" x2="${p2X + 9}" y2="${yAxis + 16}" class="bp-dim-line" stroke-width="0.8"/>
        <text x="${p2X}" y="${yAxis + 32}" class="bp-text-strong" font-size="9.5" text-anchor="middle">P2</text>

        <!-- Main Span Dimension -->
        <line x1="${p1X}" y1="72" x2="${p2X}" y2="72" class="bp-dim-line" stroke-width="1"/>
        <line x1="${p1X}" y1="66" x2="${p1X}" y2="78" class="bp-dim-line" stroke-width="1"/>
        <line x1="${p2X}" y1="66" x2="${p2X}" y2="78" class="bp-dim-line" stroke-width="1"/>
        <text x="${(p1X + p2X) / 2}" y="61" class="bp-text-strong" font-size="10" text-anchor="middle">L = ${span.toFixed(2)} m</text>

        ${cant > 0 ? `
          <line x1="${p2X}" y1="72" x2="${cantX}" y2="72" class="bp-stroke-amber" stroke-width="1.2"/>
          <line x1="${cantX}" y1="66" x2="${cantX}" y2="78" class="bp-stroke-amber" stroke-width="1.2"/>
          <text x="${cantLabelX}" y="61" class="bp-accent-amber" font-size="10" text-anchor="${cantLabelAnchor}">Lc = ${cant.toFixed(2)} m</text>
        ` : ''}

        <!-- Footer Metadata -->
        <text x="26" y="230" class="bp-text-muted" font-size="9.5">Seção da viga: ${bw}×${bh} cm</text>
        <text x="674" y="230" class="bp-text-muted" font-size="9.5" text-anchor="end">Escala esquemática 1:50</text>
      </svg>
    `;
  }

  renderSection(params) {
    const container = document.getElementById('svg-section-content');
    if (!container) return;
    const span = parseFloat(params.span_length_m) || 10.0;
    const bh = parseFloat(params.beam_height_cm) || 30.0;
    const defl = parseFloat(params.max_deflection_mm) || 54.2;
    const allowable = parseFloat(params.allowable_deflection_mm) || 40.0;
    const isViable = defl <= allowable;

    const scale = 500 / Math.max(span, 8.0);
    const x0 = 80;
    const x1 = x0 + span * scale;
    const yTop = 64;
    const beamHpx = Math.min(Math.max(bh * 0.42, 10), 34);
    const yBot = yTop + beamHpx;
    const xm = (x0 + x1) / 2;

    // True midpoint of quadratic Bezier M(x0,yBot) Q(xm,ctrlY) (x1,yBot) is yBot + sagPx when ctrlY = yBot + 2*sagPx
    const sagPx = Math.min(Math.max(defl * 0.5, 10), 46);
    const curveMidY = yBot + sagPx;
    const ctrlY = yBot + 2 * sagPx;

    container.innerHTML = `
      <svg viewBox="0 0 700 240" class="bp-svg w-full h-auto font-mono text-xs rounded">
        <text x="26" y="30" class="bp-text-strong" font-size="10.5">Corte longitudinal · Deformada em serviço (ELS)</text>

        <!-- Columns -->
        <rect x="${x0 - 12}" y="${yTop}" width="24" height="146" class="bp-struct" stroke-width="1.25"/>
        <rect x="${x1 - 12}" y="${yTop}" width="24" height="146" class="bp-struct" stroke-width="1.25"/>

        <!-- Undeformed Beam Reference -->
        <rect x="${x0}" y="${yTop}" width="${x1 - x0}" height="${beamHpx}" fill="none" class="bp-dim-line" stroke-dasharray="4,4" stroke-width="1"/>

        <!-- Elastic Deflection Curve -->
        <path d="M ${x0} ${yBot} Q ${xm} ${ctrlY} ${x1} ${yBot}" fill="none" class="${isViable ? 'bp-stroke-emerald' : 'bp-stroke-rose'}" stroke-width="2"/>

        <!-- Midspan Deflection Marker (strictly terminating at the curve vertex) -->
        <line x1="${xm}" y1="${yBot}" x2="${xm}" y2="${curveMidY}" class="bp-dim-line" stroke-width="1.25"/>
        <circle cx="${xm}" cy="${curveMidY}" r="3.2" class="${isViable ? 'bp-accent-emerald' : 'bp-accent-rose'}"/>

        <!-- Callout cleanly positioned below the lowest point of the curve -->
        <text x="${xm}" y="${curveMidY + 18}" text-anchor="middle" class="${isViable ? 'bp-accent-emerald' : 'bp-accent-rose'}" font-size="10">
          δ = ${defl.toFixed(1)} mm
        </text>
        <text x="${xm}" y="${curveMidY + 32}" text-anchor="middle" class="bp-text-muted" font-size="9">
          Limite: ≤ ${allowable.toFixed(1)} mm
        </text>
      </svg>
    `;
  }

  renderDiagrams(params) {
    const container = document.getElementById('svg-diagrams-content');
    if (!container) return;
    const span = parseFloat(params.span_length_m) || 10.0;
    const q = 25.0;
    const mMax = (q * span * span) / 8.0;
    const vMax = (q * span) / 2.0;

    const x0 = 80;
    const x1 = 580;
    const xm = (x0 + x1) / 2;

    const yM = 46;
    const yMPeak = 84;
    const ctrlMY = yM + 2 * (yMPeak - yM);

    const yV = 186;

    container.innerHTML = `
      <svg viewBox="0 0 700 250" class="bp-svg w-full h-auto font-mono text-xs rounded">
        <!-- 1. Bending Moment Diagram (M) -->
        <text x="26" y="26" class="bp-text-strong" font-size="10.5">Momento fletor (Mk) · Máx = ${mMax.toFixed(1)} kN·m</text>
        <line x1="${x0}" y1="${yM}" x2="${x1}" y2="${yM}" class="bp-dim-line" stroke-width="1.25"/>
        <path d="M ${x0} ${yM} Q ${xm} ${ctrlMY} ${x1} ${yM} Z" class="bp-glass bp-stroke-brand" stroke-width="1.5"/>
        <text x="${xm}" y="${yMPeak + 16}" class="bp-accent-brand" font-size="9.5" text-anchor="middle">+${mMax.toFixed(1)} kN·m</text>

        <!-- 2. Shear Force Diagram (V) -->
        <text x="26" y="136" class="bp-text-strong" font-size="10.5">Esforço cortante (Vk) · Máx = ${vMax.toFixed(1)} kN</text>
        <line x1="${x0}" y1="${yV}" x2="${x1}" y2="${yV}" class="bp-dim-line" stroke-width="1.25"/>
        <polygon points="${x0},${yV} ${x0},${yV - 26} ${xm},${yV}" class="bp-panel" stroke-width="1.25"/>
        <polygon points="${xm},${yV} ${x1},${yV + 26} ${x1},${yV}" class="bp-panel" stroke-width="1.25"/>
        <text x="${x0}" y="${yV - 32}" class="bp-text-strong" font-size="9" text-anchor="start">+${vMax.toFixed(1)} kN</text>
        <text x="${x1}" y="${yV + 40}" class="bp-text-strong" font-size="9" text-anchor="end">-${vMax.toFixed(1)} kN</text>
      </svg>
    `;
  }
}

window.ViewportSwitcher = ViewportSwitcher;
