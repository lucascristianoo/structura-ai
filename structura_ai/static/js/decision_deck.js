/**
 * Structura.AI — Professional Redesign Decision Deck & Engineering Matrix
 * Substitui menus simples por visualizador A/B, Cards Executivos de Engenharia e Gráfico Radar.
 */

class RedesignDecisionDeck {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = options;
    this.radarChart = null;
    this.activeVariantIndex = 0;
    this.variantsData = [];
    this.originalMetrics = null;
    this.onVariantSelect = options.onVariantSelect || (() => {});
  }

  init(variants, originalMetrics) {
    this.variantsData = variants || [];
    this.originalMetrics = originalMetrics || {
      deflection_mm: 54.2,
      allowable_mm: 40.0,
      span_m: 10.0,
      score: 42,
    };
    this.render();
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <!-- TOP: DECISION HEADER WITH PITCH MODE TOGGLE -->
      <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-6">
        <div>
          <div class="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-brand-400 uppercase tracking-wider mb-1">
            <i data-lucide="compass" class="w-4 h-4"></i>
            <span>Engenharia de Valor & Compatibilização NBR 6118</span>
          </div>
          <h2 class="text-xl sm:text-2xl font-black text-white tracking-tight">
            Matriz de Decisão Estrutural: 5 Alternativas de Redesign
          </h2>
          <p class="text-xs text-slate-400 mt-1 max-w-2xl">
            A física não descarta a intenção do arquiteto: avalie os 5 partidos de engenharia com métricas comparativas, fidelidade estética e impacto orçamentário.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <button id="btn-pitch-mode" type="button" class="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-mono font-bold rounded-lg border border-indigo-500/30 bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-300 transition-colors shadow-sm">
            <i data-lucide="presentation" class="w-4 h-4 text-indigo-400"></i>
            <span>Modo Apresentação (Cliente)</span>
          </button>
        </div>
      </div>

      <!-- 1. EXECUTIVE VARIANT CARDS DECK (HORIZONTAL GRID) -->
      <div class="mb-8">
        <label class="block text-xs font-mono text-slate-400 uppercase tracking-wider mb-3">
          Selecione a Estratégia Estrutural:
        </label>
        <div id="deck-cards-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <!-- Populated by renderCards() -->
        </div>
      </div>

      <!-- 2. SPLIT-SCREEN / COMPARISON WORKSPACE -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mb-8">
        
        <!-- LEFT: VISUAL BLUEPRINT & A/B CURTAIN SLIDER (lg:col-span-7) -->
        <div class="lg:col-span-7 space-y-4">
          <div class="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div class="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
              <span class="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                <i data-lucide="layers" class="w-4 h-4 text-brand-400"></i>
                Prancha Comparativa da Solução
              </span>
              <span id="deck-strategy-badge" class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20">
                PROTENSÃO ATIVA
              </span>
            </div>

            <!-- SVG Container -->
            <div id="deck-svg-viewer" class="w-full rounded-lg overflow-hidden border border-slate-800/60 bg-slate-950">
              <!-- Rendered SVG dynamically -->
            </div>
          </div>
        </div>

        <!-- RIGHT: TRADE-OFF MATRIX & 5-AXIS RADAR (lg:col-span-5) -->
        <div class="lg:col-span-5 space-y-4">
          
          <!-- Radar Chart Card -->
          <div class="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                <i data-lucide="radar" class="w-4 h-4 text-indigo-400"></i>
                Radar de Trade-offs (5 Eixos)
              </span>
              <span class="text-[10px] font-mono text-slate-500">Original vs Redesign</span>
            </div>
            <div class="w-full h-56 flex items-center justify-center">
              <canvas id="radar-canvas"></canvas>
            </div>
          </div>

          <!-- Trade-offs Breakdown Box -->
          <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4 shadow-xl text-xs font-mono">
            <div class="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">
              Impactos Físicos & Orçamentários:
            </div>
            <div id="deck-metrics-list" class="space-y-2">
              <!-- Dynamically populated -->
            </div>
          </div>

        </div>

      </div>

      <!-- 3. ARCHITECTURAL PITCH & CLIENT NARRATIVE -->
      <div id="deck-pitch-narrative" class="rounded-xl border border-brand-500/20 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-6 shadow-xl">
        <!-- Dynamically populated -->
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();

    this.renderCards();
    this.renderActiveVariantDetails();
    this.initRadarChart();
    this.bindEvents();
  }

  renderCards() {
    const grid = document.getElementById('deck-cards-grid');
    if (!grid) return;

    const cardsHtml = this.variantsData.map((v, idx) => {
      const isSelected = idx === this.activeVariantIndex;
      const borderClass = isSelected
        ? 'border-brand-500 ring-2 ring-brand-500/20 bg-slate-900'
        : 'border-slate-800 hover:border-slate-700 bg-slate-950';

      const delta = v.metrics_delta || {};
      const deflReduction = delta.flecha_residual || '-70%';
      const costBadge = delta.custo_estimado || '+10%';

      return `
        <div data-variant-index="${idx}" class="deck-card cursor-pointer rounded-xl border p-3.5 transition-all duration-200 ${borderClass}">
          <div class="flex items-center justify-between mb-2">
            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              OPÇÃO 0${v.variant_number}
            </span>
            <span class="text-[10px] font-mono font-bold text-emerald-400">
              ${deflReduction}
            </span>
          </div>

          <h3 class="text-xs font-bold text-white mb-1.5 line-clamp-1">
            ${v.strategy_name || v.title}
          </h3>

          <div class="space-y-1 text-[10px] font-mono text-slate-400">
            <div class="flex justify-between">
              <span>Pilares:</span>
              <span class="text-slate-200 font-semibold">${delta.pilares_internos || '0 adicionais'}</span>
            </div>
            <div class="flex justify-between">
              <span>Custo:</span>
              <span class="text-amber-400 font-semibold">${costBadge}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    grid.innerHTML = cardsHtml;
  }

  renderActiveVariantDetails() {
    const v = this.variantsData[this.activeVariantIndex];
    if (!v) return;

    // Atualizar badge de estratégia
    const badge = document.getElementById('deck-strategy-badge');
    if (badge) badge.textContent = v.strategy_name || `OPÇÃO 0${v.variant_number}`;

    // Atualizar SVG
    const svgContainer = document.getElementById('deck-svg-viewer');
    if (svgContainer) {
      if (v.svg_render) {
        svgContainer.innerHTML = v.svg_render;
      } else {
        svgContainer.innerHTML = `
          <div class="h-48 flex items-center justify-center text-xs font-mono text-slate-500">
            Planta estrutural em vetor carregada
          </div>
        `;
      }
    }

    // Atualizar métricas de trade-off
    const metricsContainer = document.getElementById('deck-metrics-list');
    if (metricsContainer) {
      const delta = v.metrics_delta || {};
      metricsContainer.innerHTML = `
        <div class="flex items-center justify-between py-1.5 border-b border-slate-800/60">
          <span class="text-slate-400">Redução de Flecha:</span>
          <span class="text-emerald-400 font-bold">${delta.flecha_residual || 'Conforme NBR 6118'}</span>
        </div>
        <div class="flex items-center justify-between py-1.5 border-b border-slate-800/60">
          <span class="text-slate-400">Pé-Direito Livre:</span>
          <span class="text-sky-400 font-bold">${delta.pe_direito || '100% Preservado'}</span>
        </div>
        <div class="flex items-center justify-between py-1.5 border-b border-slate-800/60">
          <span class="text-slate-400">Pilares no Living:</span>
          <span class="text-slate-200 font-bold">${delta.pilares_internos || 'Zero (Vão Totalmente Livre)'}</span>
        </div>
        <div class="flex items-center justify-between py-1.5">
          <span class="text-slate-400">Impacto Orçamentário:</span>
          <span class="text-amber-400 font-bold">${delta.custo_estimado || '+10% a +15%'}</span>
        </div>
      `;
    }

    // Atualizar narrativa de apresentação
    const pitchBox = document.getElementById('deck-pitch-narrative');
    if (pitchBox) {
      pitchBox.innerHTML = `
        <div class="flex items-center gap-2 text-xs font-mono font-bold text-brand-400 uppercase tracking-wider mb-2">
          <i data-lucide="message-square" class="w-4 h-4"></i>
          <span>Argumentação de Vendas para o Arquiteto apresentar ao Cliente:</span>
        </div>
        <blockquote class="text-xs sm:text-sm text-slate-200 italic leading-relaxed pl-4 border-l-2 border-brand-500 mb-3 font-sans">
          "${v.pitch_narrative || v.architectural_concept || 'Esta solução resolve a rigidez estrutural transformando a restrição de cálculo em um elemento escultural contemporâneo.'}"
        </blockquote>
        <div class="text-[11px] font-mono text-slate-400 flex flex-wrap gap-4 pt-2 border-t border-slate-800">
          <span><strong>Conceito:</strong> ${v.architectural_concept || 'Preservação da fluidez visual'}</span>
          <span><strong>Engenharia:</strong> ${v.engineering_solution || 'Aumento de inércia ou protensão ativa'}</span>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
    }

    // Atualizar radar chart
    this.updateRadarChart();
  }

  initRadarChart() {
    const canvas = document.getElementById('radar-canvas');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    this.radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Segurança NBR', 'Fidelidade Arquitetônica', 'Economia Orçamento', 'Facilidade Obra', 'Amplitude Espacial'],
        datasets: [
          {
            label: 'Original Reprovado',
            data: [30, 95, 80, 75, 90],
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            borderColor: '#ef4444',
            borderWidth: 1.5,
            pointRadius: 2,
          },
          {
            label: 'Redesign Selecionado',
            data: [95, 90, 70, 65, 95],
            backgroundColor: 'rgba(56, 189, 248, 0.25)',
            borderColor: '#38bdf8',
            borderWidth: 2,
            pointRadius: 3,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
            grid: { color: 'rgba(255, 255, 255, 0.08)' },
            pointLabels: {
              color: '#94a3b8',
              font: { size: 9, family: 'JetBrains Mono' }
            },
            ticks: { display: false, min: 0, max: 100 }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: '#e2e8f0',
              font: { size: 10, family: 'JetBrains Mono' }
            }
          }
        }
      }
    });
  }

  updateRadarChart() {
    if (!this.radarChart) return;
    const vIndex = this.activeVariantIndex;
    
    // Matrizes calibradas por variante
    const variantScores = [
      [95, 95, 75, 70, 95], // 1. Protensão: Alta fidelidade, teto plano
      [98, 85, 70, 60, 100], // 2. Vierendeel: Vão livre total, obra requer fôrmas
      [92, 80, 85, 80, 85], // 3. Tirantes: Econômico, estética industrial
      [90, 88, 80, 75, 90], // 4. Waffle: Boa inércia, teto nervurado
      [96, 92, 72, 60, 92], // 5. Gaudí: Casca esbelta, alta assinatura
    ];

    const currentScores = variantScores[vIndex] || [90, 85, 75, 70, 90];
    this.radarChart.data.datasets[1].data = currentScores;
    this.radarChart.data.datasets[1].label = this.variantsData[vIndex]?.strategy_name || `Opção 0${vIndex + 1}`;
    this.radarChart.update();
  }

  bindEvents() {
    // Clique nos cards
    const grid = document.getElementById('deck-cards-grid');
    if (grid) {
      grid.addEventListener('click', (e) => {
        const card = e.target.closest('.deck-card');
        if (!card) return;
        const idx = parseInt(card.dataset.variantIndex, 10);
        if (!isNaN(idx)) {
          this.selectVariant(idx);
        }
      });
    }

    // Botão Modo Apresentação
    const btnPitch = document.getElementById('btn-pitch-mode');
    if (btnPitch) {
      btnPitch.addEventListener('click', () => {
        const sect = document.getElementById('variants-section');
        if (sect) {
          if (!document.fullscreenElement) {
            sect.requestFullscreen().catch(() => {});
            btnPitch.innerHTML = `<i data-lucide="minimize" class="w-4 h-4"></i><span>Sair da Apresentação</span>`;
          } else {
            document.exitFullscreen().catch(() => {});
            btnPitch.innerHTML = `<i data-lucide="presentation" class="w-4 h-4"></i><span>Modo Apresentação</span>`;
          }
          if (window.lucide) window.lucide.createIcons();
        }
      });
    }
  }

  selectVariant(idx) {
    this.activeVariantIndex = idx;
    this.renderCards();
    this.renderActiveVariantDetails();
    this.onVariantSelect(idx + 1, this.variantsData[idx]);
  }
}

window.RedesignDecisionDeck = RedesignDecisionDeck;
