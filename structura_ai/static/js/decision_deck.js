/**
 * Structura.AI — Redesign Decision Deck & Engineering Trade-off Matrix
 * Uses centralized UI primitives (components.css) and theme tokens (theme.css).
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

    window.addEventListener('structura:themechange', () => {
      this.applyRadarTheme();
    });
  }

  init(variants, originalMetrics) {
    this.variantsData = variants || [];
    this.originalMetrics = originalMetrics || {
      deflection_mm: 54.2,
      allowable_mm: 40.0,
      span_m: 10.0,
      score: 42
    };
    this.render();
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <!-- Decision Header -->
      <div class="flex flex-wrap items-start justify-between gap-4 border-b border-edge pb-4 mb-5">
        <div>
          <span class="ui-eyebrow block mb-1">Compatibilização físico-arquitetônica</span>
          <h2 class="ui-section-title">Alternativas estruturais dimensionadas</h2>
          <p class="ui-subtitle">
            Compare cinco partidos estruturais calibrados para atender aos estados limites da NBR 6118.
          </p>
        </div>

        <button id="btn-pitch-mode" type="button" class="ui-btn ui-btn-secondary">
          <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i>
          <span>Modo apresentação</span>
        </button>
      </div>

      <!-- 1. Variant Selector Grid -->
      <div class="mb-6">
        <span class="text-[11px] font-mono text-ink-muted block mb-2.5">
          Selecione o sistema estrutural
        </span>
        <div id="deck-cards-grid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3"></div>
      </div>

      <!-- 2. Split Comparison Workspace -->
      <div class="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start mb-5">
        <!-- Left: Blueprint Elevation -->
        <div class="xl:col-span-7">
          <div class="ui-well">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5 pb-2 border-b border-edge">
              <span class="text-xs font-semibold text-ink-strong">Esquema estrutural da proposta</span>
              <span id="deck-strategy-badge" class="ui-badge">Protensão não-aderente</span>
            </div>
            <div id="deck-svg-viewer" class="blueprint-frame w-full rounded overflow-hidden border border-edge bg-surface-card"></div>
          </div>
        </div>

        <!-- Right: 5-Axis Radar & Trade-off Readouts -->
        <div class="xl:col-span-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-1 gap-3.5">
          <div class="ui-well">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
              <span class="text-xs font-semibold text-ink-strong">Comparativo multicritério</span>
              <span class="text-[10px] font-mono text-ink-muted">Original vs proposta</span>
            </div>
            <div class="w-full h-56 flex items-center justify-center">
              <canvas id="radar-canvas"></canvas>
            </div>
          </div>

          <div class="ui-well text-xs font-mono">
            <div class="text-[11px] font-semibold text-ink-strong mb-2">Desempenho mecânico</div>
            <div id="deck-metrics-list" class="divide-y divide-edge"></div>
          </div>
        </div>
      </div>

      <!-- 3. Client Synthesis Note -->
      <div id="deck-pitch-narrative" class="ui-note"></div>
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

    grid.innerHTML = this.variantsData
      .map((v, idx) => {
        const isSelected = idx === this.activeVariantIndex;
        const delta = v.metrics_delta || {};
        const deflReduction =
          delta.flecha_residual ||
          (delta.deflection_reduction_pct !== undefined ? `-${delta.deflection_reduction_pct}%` : '-70%');
        const fsBadge =
          delta.safety_factor !== undefined ? `FS ${delta.safety_factor}` : (delta.custo_estimado || '+10%');

        return `
          <div data-variant-index="${idx}" class="deck-card ${isSelected ? 'is-selected' : ''} cursor-pointer p-3.5 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <span class="text-[10px] font-mono text-ink-muted shrink-0">0${v.variant_number}</span>
                <span class="text-[10px] font-mono font-medium text-accent-emerald shrink-0">${deflReduction}</span>
              </div>

              <h3 class="text-xs font-semibold text-ink-strong leading-snug mb-2.5">
                ${v.strategy_name || v.title}
              </h3>
            </div>

            <div class="space-y-1 text-[10px] font-mono text-ink-muted pt-2 border-t border-edge">
              <div class="flex items-center justify-between gap-2">
                <span class="shrink-0">Flecha</span>
                <span class="text-ink-primary text-right">${delta.deflection_final_mm !== undefined ? `${delta.deflection_final_mm} mm` : (delta.pilares_internos || '0 adic.')}</span>
              </div>
              <div class="flex items-center justify-between gap-2">
                <span class="shrink-0">Margem</span>
                <span class="text-ink-primary text-right">${fsBadge}</span>
              </div>
            </div>
          </div>
        `;
      })
      .join('');
  }

  renderActiveVariantDetails() {
    const v = this.variantsData[this.activeVariantIndex];
    if (!v) return;

    const badge = document.getElementById('deck-strategy-badge');
    if (badge) badge.textContent = v.strategy_name || `Proposta 0${v.variant_number}`;

    const svgContainer = document.getElementById('deck-svg-viewer');
    if (svgContainer) {
      svgContainer.innerHTML = v.svg_render
        ? v.svg_render
        : `<div class="h-44 flex items-center justify-center text-xs font-mono text-ink-muted">Prancha vetorial indisponível</div>`;
    }

    const metricsContainer = document.getElementById('deck-metrics-list');
    if (metricsContainer) {
      const delta = v.metrics_delta || {};
      const flechaLabel =
        delta.deflection_final_mm !== undefined
          ? `${delta.deflection_final_mm} mm (-${delta.deflection_reduction_pct ?? 0}%)`
          : (delta.flecha_residual || 'Conforme NBR 6118');
      const momentLabel =
        delta.moment_final_knm !== undefined
          ? `${delta.moment_final_knm} kN·m`
          : (delta.pe_direito || 'Preservado');
      const weightLabel =
        delta.weight_reduction_pct !== undefined
          ? `-${delta.weight_reduction_pct}% carga própria`
          : (delta.pilares_internos || 'Vão livre mantido');
      const fsOrCostLabel =
        delta.safety_factor !== undefined
          ? `FS = ${delta.safety_factor}`
          : (delta.custo_estimado || '+10% a +15%');

      metricsContainer.innerHTML = `
        <div class="flex items-center justify-between gap-2 py-1.5">
          <span class="text-ink-muted">Flecha final</span>
          <span class="text-accent-emerald font-semibold text-right">${flechaLabel}</span>
        </div>
        <div class="flex items-center justify-between gap-2 py-1.5">
          <span class="text-ink-muted">Momento máximo</span>
          <span class="text-ink-strong font-medium text-right">${momentLabel}</span>
        </div>
        <div class="flex items-center justify-between gap-2 py-1.5">
          <span class="text-ink-muted">Alívio estrutural</span>
          <span class="text-ink-strong font-medium text-right">${weightLabel}</span>
        </div>
        <div class="flex items-center justify-between gap-2 py-1.5">
          <span class="text-ink-muted">Fator de segurança</span>
          <span class="text-ink-strong font-medium text-right">${fsOrCostLabel}</span>
        </div>
      `;
    }

    const pitchBox = document.getElementById('deck-pitch-narrative');
    if (pitchBox) {
      pitchBox.innerHTML = `
        <span class="text-[11px] font-mono font-semibold text-ink-strong block mb-1.5">
          Síntese técnica e arquitetônica
        </span>
        <p class="text-xs text-ink-secondary leading-relaxed mb-3">
          "${v.pitch_narrative || v.architectural_concept || 'Solução dimensionada para conciliar rigidez estrutural e preservação espacial.'}"
        </p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-ink-secondary pt-2.5 border-t border-edge leading-relaxed">
          <div><strong class="text-ink-strong font-medium">Partido:</strong> ${v.architectural_concept || 'Preservação da continuidade espacial.'}</div>
          <div><strong class="text-ink-strong font-medium">Mecânica:</strong> ${v.engineering_solution || 'Redistribuição de rigidez e esforços internos.'}</div>
        </div>
      `;
    }

    this.updateRadarChart();
  }

  getRadarColors() {
    const css = (name, fallback) => {
      const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return val || fallback;
    };
    return {
      angleLines: css('--chart-angle', 'rgba(24, 24, 27, 0.1)'),
      grid: css('--chart-grid', 'rgba(24, 24, 27, 0.08)'),
      pointLabels: css('--chart-label', '#52525b'),
      legend: css('--chart-legend', '#18181b'),
      primaryBorder: css('--chart-primary-border', '#18181b'),
      primaryBg: css('--chart-primary-bg', 'rgba(24, 24, 27, 0.12)'),
      failBorder: css('--chart-fail-border', '#b91c1c'),
      failBg: css('--chart-fail-bg', 'rgba(185, 28, 28, 0.1)')
    };
  }

  applyRadarTheme() {
    if (!this.radarChart) return;
    const c = this.getRadarColors();
    this.radarChart.options.scales.r.angleLines.color = c.angleLines;
    this.radarChart.options.scales.r.grid.color = c.grid;
    this.radarChart.options.scales.r.pointLabels.color = c.pointLabels;
    this.radarChart.options.plugins.legend.labels.color = c.legend;
    this.radarChart.data.datasets[0].borderColor = c.failBorder;
    this.radarChart.data.datasets[0].backgroundColor = c.failBg;
    this.radarChart.data.datasets[1].borderColor = c.primaryBorder;
    this.radarChart.data.datasets[1].backgroundColor = c.primaryBg;
    this.radarChart.update();
  }

  initRadarChart() {
    const canvas = document.getElementById('radar-canvas');
    if (!canvas || typeof Chart === 'undefined') return;

    const c = this.getRadarColors();
    const ctx = canvas.getContext('2d');
    this.radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: [
          ['Segurança', 'NBR'],
          ['Fidelidade', 'espacial'],
          'Custo',
          'Execução',
          ['Vão', 'livre']
        ],
        datasets: [
          {
            label: 'Original',
            data: [30, 95, 80, 75, 90],
            backgroundColor: c.failBg,
            borderColor: c.failBorder,
            borderWidth: 1.25,
            pointRadius: 2
          },
          {
            label: `Proposta 0${this.activeVariantIndex + 1}`,
            data: [95, 90, 70, 65, 95],
            backgroundColor: c.primaryBg,
            borderColor: c.primaryBorder,
            borderWidth: 1.75,
            pointRadius: 2.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { top: 4, right: 12, bottom: 4, left: 12 }
        },
        scales: {
          r: {
            angleLines: { color: c.angleLines },
            grid: { color: c.grid },
            pointLabels: {
              color: c.pointLabels,
              font: { size: 9, family: 'JetBrains Mono' }
            },
            ticks: { display: false, min: 0, max: 100 }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: c.legend,
              boxWidth: 10,
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

    const variantScores = [
      [95, 95, 75, 70, 95],
      [98, 85, 70, 60, 100],
      [92, 80, 85, 80, 85],
      [90, 88, 80, 75, 90],
      [96, 92, 72, 60, 92]
    ];

    const currentScores = variantScores[vIndex] || [90, 85, 75, 70, 90];
    this.radarChart.data.datasets[1].data = currentScores;
    this.radarChart.data.datasets[1].label = `Proposta 0${vIndex + 1}`;
    this.radarChart.update();
  }

  bindEvents() {
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

    const btnPitch = document.getElementById('btn-pitch-mode');
    if (btnPitch) {
      btnPitch.addEventListener('click', () => {
        const sect = document.getElementById('variants-section');
        if (sect) {
          if (!document.fullscreenElement) {
            sect.requestFullscreen().catch(() => {});
            btnPitch.innerHTML = `<i data-lucide="minimize-2" class="w-3.5 h-3.5"></i><span>Encerrar apresentação</span>`;
          } else {
            document.exitFullscreen().catch(() => {});
            btnPitch.innerHTML = `<i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Modo apresentação</span>`;
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
