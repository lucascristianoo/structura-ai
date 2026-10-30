/**
 * Structura.AI — Interactive Architectural Floorplan & Structural Grid Canvas
 * Bidirectional sketch pad using theme.css tokens and components.css (.ui-tab) states.
 */

class ArchitecturalCanvas {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;

    this.ctx = this.canvas.getContext('2d');
    this.scaleLabel = document.getElementById('canvas-scale-label');
    this.elements = [];
    this.currentTool = 'column';
    this.scale = 40.0;
    this.isDrawing = false;
    this.startPoint = null;

    this.initCanvasSize(false);
    this.initEventListeners();
    this.initFromSliders();
  }

  initCanvasSize(shouldRender = true) {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = Math.max(Math.floor(rect.width), 320);
    this.canvas.height = 340;
    if (shouldRender) {
      this.render();
    }
  }

  initFromSliders() {
    const spanInput = document.getElementById('input-span');
    const cantInput = document.getElementById('input-cantilever');
    const initialSpan = spanInput ? parseFloat(spanInput.value) || 9.5 : 9.5;
    const initialCant = cantInput ? parseFloat(cantInput.value) || 0.0 : 3.5;
    this.setLayoutFromParams(initialSpan, initialCant);
  }

  getPalette() {
    const cssVar = (name, fallback) =>
      window.StructuraTheme ? window.StructuraTheme.getCssVar(name, fallback) : fallback;

    return {
      bg: cssVar('--canvas-bg', '#fafafa'),
      grid: cssVar('--canvas-grid', '#e4e4e7'),
      beam: cssVar('--canvas-beam', '#1e4b85'),
      cantilever: cssVar('--canvas-cantilever', '#a16207'),
      colFill: cssVar('--canvas-col-fill', '#27272a'),
      colStroke: cssVar('--canvas-col-stroke', '#111113'),
      colLabel: cssVar('--canvas-col-label', '#52525b'),
      tagBg: cssVar('--canvas-tag-bg', '#ffffff'),
      tagBorder: cssVar('--canvas-tag-border', '#d4d4d8')
    };
  }

  setActiveTool(toolName) {
    this.currentTool = toolName;
    document.querySelectorAll('[data-canvas-tool]').forEach((btn) => {
      btn.classList.toggle('is-active', btn.getAttribute('data-canvas-tool') === toolName);
    });
  }

  initEventListeners() {
    window.addEventListener('resize', () => this.initCanvasSize(true));
    window.addEventListener('structura:themechange', () => this.render());

    this.canvas.addEventListener('pointerdown', (e) => this.onPointerDown(e));
    this.canvas.addEventListener('pointermove', (e) => this.onPointerMove(e));
    this.canvas.addEventListener('pointerup', (e) => this.onPointerUp(e));
    this.canvas.addEventListener('pointercancel', () => {
      this.isDrawing = false;
      this.render();
    });

    document.querySelectorAll('[data-canvas-tool]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tool = btn.getAttribute('data-canvas-tool');
        if (tool) this.setActiveTool(tool);
      });
    });

    document.querySelectorAll('[data-canvas-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-canvas-action');
        if (action === 'clear') {
          this.elements = [];
          this.render();
          this.setActiveTool('column');
        } else if (action === 'undo' && this.elements.length > 0) {
          this.elements.pop();
          this.render();
          if (this.elements.length > 0) {
            this.syncWithStudio();
          }
        }
      });
    });
  }

  getCanvasCoords(e) {
    const rect = this.canvas.getBoundingClientRect();
    const scaleX = rect.width ? this.canvas.width / rect.width : 1;
    const scaleY = rect.height ? this.canvas.height / rect.height : 1;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }

  onPointerDown(e) {
    if (e.button !== undefined && e.button !== 0) return;
    const pt = this.getCanvasCoords(e);

    if (this.currentTool === 'column') {
      this.elements.push({
        id: 'col_' + Date.now(),
        type: 'column',
        start: pt
      });
      this.render();
      this.syncWithStudio();
    } else if (this.currentTool === 'beam' || this.currentTool === 'cantilever') {
      this.isDrawing = true;
      this.startPoint = pt;
      if (this.canvas.setPointerCapture) {
        this.canvas.setPointerCapture(e.pointerId);
      }
    }
  }

  onPointerMove(e) {
    if (!this.isDrawing || !this.startPoint) return;
    const pt = this.getCanvasCoords(e);
    this.render();

    const palette = this.getPalette();
    const isCant = this.currentTool === 'cantilever';
    const distM = (Math.hypot(pt.x - this.startPoint.x, pt.y - this.startPoint.y) / this.scale).toFixed(1);

    this.ctx.beginPath();
    this.ctx.strokeStyle = isCant ? palette.cantilever : palette.beam;
    this.ctx.lineWidth = 2;
    this.ctx.setLineDash([4, 4]);
    this.ctx.moveTo(this.startPoint.x, this.startPoint.y);
    this.ctx.lineTo(pt.x, pt.y);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    const midX = (this.startPoint.x + pt.x) / 2;
    const midY = (this.startPoint.y + pt.y) / 2;
    this.drawDimensionTag(midX, midY, `${distM} m`, isCant, palette);
  }

  onPointerUp(e) {
    if (!this.isDrawing || !this.startPoint) return;
    this.isDrawing = false;
    if (this.canvas.releasePointerCapture && this.canvas.hasPointerCapture?.(e.pointerId)) {
      this.canvas.releasePointerCapture(e.pointerId);
    }

    const pt = this.getCanvasCoords(e);
    const dist = Math.hypot(pt.x - this.startPoint.x, pt.y - this.startPoint.y);
    if (dist > 12) {
      this.elements.push({
        id: (this.currentTool === 'cantilever' ? 'cant_' : 'beam_') + Date.now(),
        type: this.currentTool,
        start: this.startPoint,
        end: pt
      });
      this.render();
      this.syncWithStudio();
    } else {
      this.render();
    }
    this.startPoint = null;
  }

  setLayoutFromParams(spanM, cantileverM) {
    const safeSpan = Math.max(parseFloat(spanM) || 6.0, 1.0);
    const safeCant = Math.max(parseFloat(cantileverM) || 0.0, 0.0);
    const totalLengthM = safeSpan + safeCant;

    const availableWidth = Math.max(this.canvas.width - 120, 200);
    this.scale = Math.min(40, Math.max(18, Math.floor(availableWidth / Math.max(totalLengthM, 1))));
    if (this.scaleLabel) {
      this.scaleLabel.textContent = `Escala: ${this.scale} px = 1,0 m · Clique ou arraste para desenhar`;
    }

    const totalPx = totalLengthM * this.scale;
    const startX = Math.max(50, Math.round((this.canvas.width - totalPx) / 2));
    const col2X = Math.round(startX + safeSpan * this.scale);
    const cantEndX = Math.round(col2X + safeCant * this.scale);
    const centerY = Math.round(this.canvas.height / 2);

    this.elements = [
      { id: 'c1', type: 'column', start: { x: startX, y: centerY } },
      { id: 'c2', type: 'column', start: { x: col2X, y: centerY } },
      { id: 'b1', type: 'beam', start: { x: startX, y: centerY }, end: { x: col2X, y: centerY } }
    ];

    if (safeCant > 0) {
      this.elements.push({
        id: 'cant1',
        type: 'cantilever',
        start: { x: col2X, y: centerY },
        end: { x: cantEndX, y: centerY }
      });
    }

    this.render();
  }

  drawDimensionTag(midX, midY, label, isCantilever, palette = this.getPalette()) {
    const ctx = this.ctx;
    ctx.font = '600 11px "JetBrains Mono", "JetBrainsMono Nerd Font", ui-monospace, monospace';
    const textW = Math.ceil(ctx.measureText(label).width);
    const boxW = Math.max(58, textW + 16);
    const boxH = 20;

    const clampedX = Math.min(Math.max(midX, boxW / 2 + 4), this.canvas.width - boxW / 2 - 4);
    const boxY = midY < 32 ? midY + 8 : midY - boxH - 6;

    ctx.fillStyle = palette.tagBg;
    ctx.fillRect(clampedX - boxW / 2, boxY, boxW, boxH);
    ctx.strokeStyle = palette.tagBorder;
    ctx.lineWidth = 1;
    ctx.strokeRect(clampedX - boxW / 2, boxY, boxW, boxH);

    ctx.fillStyle = isCantilever ? palette.cantilever : palette.beam;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, clampedX, boxY + boxH / 2);
    ctx.textBaseline = 'alphabetic';
  }

  render() {
    const ctx = this.ctx;
    const palette = this.getPalette();

    ctx.fillStyle = palette.bg;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const gridSize = 24;
    ctx.strokeStyle = palette.grid;
    ctx.lineWidth = 0.5;
    for (let x = 0; x < this.canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < this.canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvas.width, y);
      ctx.stroke();
    }

    this.elements
      .filter((e) => e.type === 'beam' || e.type === 'cantilever')
      .forEach((e) => {
        const isCant = e.type === 'cantilever';
        ctx.beginPath();
        ctx.strokeStyle = isCant ? palette.cantilever : palette.beam;
        ctx.lineWidth = isCant ? 2.5 : 3.5;
        ctx.lineCap = 'square';
        ctx.moveTo(e.start.x, e.start.y);
        ctx.lineTo(e.end.x, e.end.y);
        ctx.stroke();

        const midX = (e.start.x + e.end.x) / 2;
        const midY = (e.start.y + e.end.y) / 2;
        const distM = (Math.hypot(e.end.x - e.start.x, e.end.y - e.start.y) / this.scale).toFixed(1);
        this.drawDimensionTag(midX, midY, `${distM} m`, isCant, palette);
      });

    this.elements
      .filter((e) => e.type === 'column')
      .forEach((e) => {
        ctx.fillStyle = palette.colFill;
        ctx.fillRect(e.start.x - 7, e.start.y - 7, 14, 14);
        ctx.strokeStyle = palette.colStroke;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(e.start.x - 7, e.start.y - 7, 14, 14);

        ctx.fillStyle = palette.colLabel;
        ctx.font = '500 10px "JetBrains Mono", "JetBrainsMono Nerd Font", ui-monospace, monospace';
        ctx.textAlign = 'center';
        const labelY = e.start.y > this.canvas.height - 24 ? e.start.y - 12 : e.start.y + 21;
        ctx.fillText('P', e.start.x, labelY);
      });
  }

  syncWithStudio() {
    if (!window.studio) return;

    const cols = this.elements.filter((e) => e.type === 'column');
    const beams = this.elements.filter((e) => e.type === 'beam');
    const cants = this.elements.filter((e) => e.type === 'cantilever');

    let maxDistM = 0;

    if (beams.length > 0) {
      beams.forEach((b) => {
        if (b.end) {
          const d = Math.hypot(b.end.x - b.start.x, b.end.y - b.start.y) / this.scale;
          if (d >= 1.0) maxDistM = Math.max(maxDistM, d);
        }
      });
    }

    if (cols.length >= 2) {
      for (let i = 0; i < cols.length; i++) {
        for (let j = i + 1; j < cols.length; j++) {
          const d = Math.hypot(cols[j].start.x - cols[i].start.x, cols[j].start.y - cols[i].start.y) / this.scale;
          if (d >= 2.0) maxDistM = Math.max(maxDistM, d);
        }
      }
    }

    if (maxDistM > 0 && window.studio.spanSlider) {
      const minSpan = parseFloat(window.studio.spanSlider.min) || 3.0;
      const maxSpan = parseFloat(window.studio.spanSlider.max) || 16.0;
      const clampedSpan = Math.min(maxSpan, Math.max(minSpan, maxDistM));
      window.studio.spanSlider.value = clampedSpan.toFixed(1);
      if (window.studio.spanVal) {
        window.studio.spanVal.textContent = `${clampedSpan.toFixed(1)} m`;
      }
    }

    let maxCantM = 0.0;
    cants.forEach((c) => {
      if (c.end) {
        const d = Math.hypot(c.end.x - c.start.x, c.end.y - c.start.y) / this.scale;
        maxCantM = Math.max(maxCantM, d);
      }
    });

    if (window.studio.cantileverSlider && (cants.length > 0 || beams.length > 0 || cols.length >= 2)) {
      const minCant = parseFloat(window.studio.cantileverSlider.min) || 0.0;
      const maxCant = parseFloat(window.studio.cantileverSlider.max) || 6.0;
      const clampedCant = Math.min(maxCant, Math.max(minCant, maxCantM));
      window.studio.cantileverSlider.value = clampedCant.toFixed(1);
      if (window.studio.cantileverVal) {
        window.studio.cantileverVal.textContent = `${clampedCant.toFixed(1)} m`;
      }
    }

    window.studio.scheduleQuickCalc();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.archCanvas = new ArchitecturalCanvas('structural-canvas');
});
