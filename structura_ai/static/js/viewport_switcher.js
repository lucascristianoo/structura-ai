/**
 * Structura.AI — Viewport Switcher & Multi-Format Manager
 * Gerencia a alternância entre 3D WebGL, Planta Baixa Blueprint, Corte Transversal, Diagramas e Croqui.
 */

class ViewportSwitcher {
  constructor() {
    this.activeMode = '3d'; // '3d', 'blueprint', 'section', 'diagrams', 'canvas'
    this.threeViewport = null;
    this.init();
  }

  init() {
    // Inicializar viewport 3D se container existir
    if (document.getElementById('three-viewport-box') && window.Structura3DViewport) {
      this.threeViewport = new window.Structura3DViewport('three-viewport-box');
    }

    this.bindButtons();
    this.switchMode('3d');
  }

  bindButtons() {
    const buttons = document.querySelectorAll('[data-view-mode]');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.viewMode;
        this.switchMode(mode);
      });
    });

    // Shading controls (Sólido, Aramado, Raio-X, Stress)
    const shadeBtns = document.querySelectorAll('[data-shading-mode]');
    shadeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.shadingMode;
        if (this.threeViewport) {
          this.threeViewport.setShadingMode(mode);
        }
        shadeBtns.forEach(b => {
          const isSelected = b === btn;
          b.classList.toggle('bg-brand-600', isSelected);
          b.classList.toggle('text-white', isSelected);
          b.classList.toggle('font-semibold', isSelected);
          b.classList.toggle('bg-surface-elevated', !isSelected);
          b.classList.toggle('text-ink-secondary', !isSelected);
          b.classList.toggle('hover:text-ink-strong', !isSelected);
          b.classList.toggle('hover:bg-surface-hover', !isSelected);
        });
      });
    });

    // Slider de ampliação da deformada
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

    // Atualizar botões
    const buttons = document.querySelectorAll('[data-view-mode]');
    buttons.forEach(btn => {
      const isSelected = btn.dataset.viewMode === mode;
      btn.classList.toggle('bg-brand-600', isSelected);
      btn.classList.toggle('text-white', isSelected);
      btn.classList.toggle('font-semibold', isSelected);
      btn.classList.toggle('bg-surface-elevated', !isSelected);
      btn.classList.toggle('text-ink-secondary', !isSelected);
      btn.classList.toggle('hover:text-ink-strong', !isSelected);
      btn.classList.toggle('hover:bg-surface-hover', !isSelected);
    });

    // Mostrar controles 3D apenas no modo 3D
    const controls3dBar = document.getElementById('controls-3d-bar');
    if (controls3dBar) {
      controls3dBar.classList.toggle('hidden', mode !== '3d');
    }

    // Alternar visibilidade dos containers
    const containers = {
      '3d': document.getElementById('view-container-3d'),
      'blueprint': document.getElementById('view-container-blueprint'),
      'section': document.getElementById('view-container-section'),
      'diagrams': document.getElementById('view-container-diagrams'),
      'canvas': document.getElementById('view-container-canvas'),
    };

    Object.keys(containers).forEach(k => {
      const el = containers[k];
      if (el) {
        if (k === mode) {
          el.classList.remove('hidden');
        } else {
          el.classList.add('hidden');
        }
      }
    });

    // Se mudou para 3D, acionar resize do Three.js; se mudou para Croqui Manual, redimensionar canvas
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
    const scale = 500 / Math.max(totalLen + 2.0, 8.0);
    const startX = 60;
    const p1X = startX;
    const p2X = startX + (span * scale);
    const cantX = p2X + (cant * scale);
    const yAxis = 130;

    container.innerHTML = `
      <svg viewBox="0 0 700 260" class="bp-svg w-full h-auto font-mono text-xs rounded-lg">
        <defs>
          <pattern id="cad-grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" class="bp-grid-line" stroke-width="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#cad-grid)" />
        
        <!-- Eixo estrutural traço-ponto -->
        <line x1="30" y1="${yAxis}" x2="${cantX + 40}" y2="${yAxis}" stroke="#0284c7" stroke-dasharray="8,4,2,4" stroke-width="1.2"/>
        <text x="35" y="${yAxis - 8}" class="bp-accent-brand" font-size="10">EIXO ESTRUTURAL 01</text>

        <!-- Vigas principais em planta -->
        <rect x="${p1X}" y="${yAxis - (bw * 0.4)}" width="${cantX - p1X}" height="${bw * 0.8}" class="bp-panel" stroke="#0284c7" stroke-width="2"/>

        <!-- Pilares em corte (hachura) -->
        <rect x="${p1X - 10}" y="${yAxis - 18}" width="20" height="36" class="bp-struct" stroke="#0284c7" stroke-width="2"/>
        <line x1="${p1X - 10}" y1="${yAxis - 18}" x2="${p1X + 10}" y2="${yAxis + 18}" stroke="#0284c7" stroke-width="1"/>
        <text x="${p1X - 12}" y="${yAxis + 32}" class="bp-text-muted" font-size="10" font-weight="bold">P1 (20x40)</text>

        <rect x="${p2X - 10}" y="${yAxis - 18}" width="20" height="36" class="bp-struct" stroke="#0284c7" stroke-width="2"/>
        <line x1="${p2X - 10}" y1="${yAxis - 18}" x2="${p2X + 10}" y2="${yAxis + 18}" stroke="#0284c7" stroke-width="1"/>
        <text x="${p2X - 12}" y="${yAxis + 32}" class="bp-text-muted" font-size="10" font-weight="bold">P2 (20x40)</text>

        <!-- Linha de Cota Vão Principal -->
        <line x1="${p1X}" y1="60" x2="${p2X}" y2="60" stroke="#d97706" stroke-width="1.5"/>
        <line x1="${p1X}" y1="52" x2="${p1X}" y2="68" stroke="#d97706" stroke-width="1.5"/>
        <line x1="${p2X}" y1="52" x2="${p2X}" y2="68" stroke="#d97706" stroke-width="1.5"/>
        <text x="${(p1X + p2X) / 2}" y="52" class="bp-accent-amber" font-size="11" font-weight="bold" text-anchor="middle">VÃO LIVRE L = ${span.toFixed(2)} m</text>

        ${cant > 0 ? `
          <!-- Cota Balanço -->
          <line x1="${p2X}" y1="60" x2="${cantX}" y2="60" stroke="#ea580c" stroke-width="1.5"/>
          <line x1="${cantX}" y1="52" x2="${cantX}" y2="68" stroke="#ea580c" stroke-width="1.5"/>
          <text x="${(p2X + cantX) / 2}" y="52" fill="#ea580c" font-size="11" font-weight="bold" text-anchor="middle">BALANÇO Lc = ${cant.toFixed(2)} m</text>
        ` : ''}

        <!-- Detalhes de Seção -->
        <text x="500" y="210" class="bp-text-muted" font-size="10">SEÇÃO: ${bw}x${bh} cm</text>
        <text x="500" y="225" class="bp-text-muted" font-size="10">ESCALA: 1:50</text>
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
    const x1 = x0 + (span * scale);
    const yTop = 80;
    const yBot = yTop + (bh * 0.8);
    const xm = (x0 + x1) / 2;
    const deflY = yBot + Math.min(defl * 0.6, 50);

    container.innerHTML = `
      <svg viewBox="0 0 700 240" class="bp-svg w-full h-auto font-mono text-xs rounded-lg">
        <!-- Pilares em corte -->
        <rect x="${x0 - 15}" y="${yTop}" width="30" height="130" class="bp-struct" stroke="#64748b" stroke-width="1.5"/>
        <rect x="${x1 - 15}" y="${yTop}" width="30" height="130" class="bp-struct" stroke="#64748b" stroke-width="1.5"/>

        <!-- Viga sem deformação (tracejada) -->
        <rect x="${x0}" y="${yTop}" width="${x1 - x0}" height="${yBot - yTop}" fill="none" stroke="#64748b" stroke-dasharray="4,4" stroke-width="1"/>

        <!-- Curva da deformada elástica em serviço ELS -->
        <path d="M ${x0} ${yBot} Q ${xm} ${deflY} ${x1} ${yBot}" fill="none" stroke="${isViable ? '#10b981' : '#ef4444'}" stroke-width="3"/>
        
        <!-- Indicação da flecha no ponto médio -->
        <line x1="${xm}" y1="${yBot}" x2="${xm}" y2="${deflY}" stroke="#d97706" stroke-width="2"/>
        <circle cx="${xm}" cy="${deflY}" r="4" fill="#d97706"/>
        
        <text x="${xm + 12}" y="${(yBot + deflY) / 2 + 4}" class="bp-accent-amber" font-size="11" font-weight="bold">
          f_calc = ${defl.toFixed(1)} mm
        </text>
        <text x="${xm + 12}" y="${(yBot + deflY) / 2 + 18}" class="bp-text-muted" font-size="9">
          f_adm ≤ ${allowable.toFixed(1)} mm
        </text>

        <text x="80" y="35" class="bp-text-strong" font-size="12" font-weight="bold">
          CORTE LONGITUDINAL: VIGA SOB CARGA EM SERVIÇO (ELS)
        </text>
      </svg>
    `;
  }

  renderDiagrams(params) {
    const container = document.getElementById('svg-diagrams-content');
    if (!container) return;
    const span = parseFloat(params.span_length_m) || 10.0;
    const q = 25.0; // kN/m
    const mMax = (q * span * span) / 8.0; // kNm
    const vMax = (q * span) / 2.0; // kN

    const x0 = 80;
    const x1 = 580;
    const xm = (x0 + x1) / 2;

    container.innerHTML = `
      <svg viewBox="0 0 700 240" class="bp-svg w-full h-auto font-mono text-xs rounded-lg">
        <!-- 1. DIAGRAMA DE MOMENTO FLETOR (M) -->
        <text x="80" y="30" class="bp-accent-brand" font-size="11" font-weight="bold">DIAGRAMA DE MOMENTO FLETOR (M_k): M_max = ${mMax.toFixed(1)} kN.m</text>
        <line x1="${x0}" y1="50" x2="${x1}" y2="50" class="bp-dim-line" stroke-width="1.5"/>
        <path d="M ${x0} 50 Q ${xm} 105 ${x1} 50 Z" fill="rgba(2, 132, 199, 0.16)" stroke="#0284c7" stroke-width="2"/>
        <text x="${xm}" y="85" class="bp-accent-brand" font-size="10" font-weight="bold" text-anchor="middle">+${mMax.toFixed(1)} kN.m (Tração inferior)</text>

        <!-- 2. DIAGRAMA DE ESFORÇO CORTANTE (V) -->
        <text x="80" y="140" class="bp-accent-purple" font-size="11" font-weight="bold">DIAGRAMA DE ESFORÇO CORTANTE (V_k): V_max = ${vMax.toFixed(1)} kN</text>
        <line x1="${x0}" y1="180" x2="${x1}" y2="180" class="bp-dim-line" stroke-width="1.5"/>
        <!-- Triângulo positivo esquerda, negativo direita -->
        <polygon points="${x0},180 ${x0},150 ${xm},180" fill="rgba(147, 51, 234, 0.18)" stroke="#9333ea" stroke-width="1.5"/>
        <polygon points="${xm},180 ${x1},210 ${x1},180" fill="rgba(147, 51, 234, 0.18)" stroke="#9333ea" stroke-width="1.5"/>
        <text x="${x0 + 30}" y="170" class="bp-accent-purple" font-size="9" font-weight="bold">+${vMax.toFixed(1)} kN</text>
        <text x="${x1 - 65}" y="200" class="bp-accent-purple" font-size="9" font-weight="bold">-${vMax.toFixed(1)} kN</text>
      </svg>
    `;
  }
}

window.ViewportSwitcher = ViewportSwitcher;
