/**
 * Structura.AI — Interactive Architectural Floorplan & Structural Grid Canvas
 * Allows architects to sketch columns and beams directly, extracting spans and cantilever geometry.
 */

class ArchitecturalCanvas {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;

    this.ctx = this.canvas.getContext('2d');
    this.elements = [];
    this.currentTool = 'column'; // 'column', 'beam', 'cantilever', 'clear'
    this.scale = 40.0; // 40px = 1.0 meter
    this.isDrawing = false;
    this.startPoint = null;

    this.initCanvasSize();
    this.initEventListeners();
    this.loadDefaultLayout();
  }

  initCanvasSize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width || 700;
    this.canvas.height = 360;
    this.render();
  }

  initEventListeners() {
    window.addEventListener('resize', () => this.initCanvasSize());

    this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
    this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
    this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));

    // Tool selector buttons if present
    document.querySelectorAll('[data-canvas-tool]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('[data-canvas-tool]').forEach(b => b.classList.remove('bg-brand-600', 'text-white'));
        btn.classList.add('bg-brand-600', 'text-white');
        this.currentTool = btn.getAttribute('data-canvas-tool');
        if (this.currentTool === 'clear') {
          this.elements = [];
          this.render();
          this.currentTool = 'column';
        }
      });
    });

    const btnAnalyzeCanvas = document.getElementById('btn-analyze-canvas');
    if (btnAnalyzeCanvas) {
      btnAnalyzeCanvas.addEventListener('click', () => this.analyzeCanvas());
    }
  }

  getCanvasCoords(e) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  }

  onMouseDown(e) {
    const pt = this.getCanvasCoords(e);
    if (this.currentTool === 'column') {
      this.elements.push({
        id: 'col_' + Date.now(),
        type: 'column',
        start: pt,
        properties: { section_cm: 20 }
      });
      this.render();
      this.syncWithStudio();
    } else if (this.currentTool === 'beam' || this.currentTool === 'cantilever') {
      this.isDrawing = true;
      this.startPoint = pt;
    }
  }

  onMouseMove(e) {
    if (!this.isDrawing) return;
    const pt = this.getCanvasCoords(e);
    this.render();

    // Draw preview line
    this.ctx.beginPath();
    this.ctx.strokeStyle = this.currentTool === 'cantilever' ? '#f59e0b' : '#38bdf8';
    this.ctx.lineWidth = 3;
    this.ctx.setLineDash([4, 4]);
    this.ctx.moveTo(this.startPoint.x, this.startPoint.y);
    this.ctx.lineTo(pt.x, pt.y);
    this.ctx.stroke();
    this.ctx.setLineDash([]);
  }

  onMouseUp(e) {
    if (!this.isDrawing) return;
    this.isDrawing = false;
    const pt = this.getCanvasCoords(e);

    const dist = Math.hypot(pt.x - this.startPoint.x, pt.y - this.startPoint.y);
    if (dist > 15) {
      this.elements.push({
        id: (this.currentTool === 'cantilever' ? 'cant_' : 'beam_') + Date.now(),
        type: this.currentTool,
        start: this.startPoint,
        end: pt,
        properties: { length_m: (dist / this.scale).toFixed(1) }
      });
      this.render();
      this.syncWithStudio();
    }
  }

  loadDefaultLayout() {
    // Default demo: 2 columns separated by ~9.5m (380px) and a cantilever of 3.5m (140px)
    const centerY = 180;
    this.elements = [
      { id: 'c1', type: 'column', start: { x: 140, y: centerY } },
      { id: 'c2', type: 'column', start: { x: 520, y: centerY } },
      { id: 'b1', type: 'beam', start: { x: 140, y: centerY }, end: { x: 520, y: centerY } },
      { id: 'cant1', type: 'cantilever', start: { x: 520, y: centerY }, end: { x: 660, y: centerY } }
    ];
    this.render();
  }

  render() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Architectural Grid Background
    const gridSize = 20;
    ctx.strokeStyle = '#1e293b';
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

    // Beams and Cantilevers
    this.elements.filter(e => e.type === 'beam' || e.type === 'cantilever').forEach(e => {
      ctx.beginPath();
      const isCant = e.type === 'cantilever';
      ctx.strokeStyle = isCant ? '#f59e0b' : '#38bdf8';
      ctx.lineWidth = isCant ? 4 : 5;
      ctx.lineCap = 'round';
      ctx.moveTo(e.start.x, e.start.y);
      ctx.lineTo(e.end.x, e.end.y);
      ctx.stroke();

      // Dimension Tag
      const midX = (e.start.x + e.end.x) / 2;
      const midY = (e.start.y + e.end.y) / 2;
      const distM = (Math.hypot(e.end.x - e.start.x, e.end.y - e.start.y) / this.scale).toFixed(1);
      
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(midX - 25, midY - 18, 50, 18);
      ctx.strokeStyle = '#334155';
      ctx.strokeRect(midX - 25, midY - 18, 50, 18);

      ctx.fillStyle = isCant ? '#f59e0b' : '#38bdf8';
      ctx.font = '10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${distM}m`, midX, midY - 5);
    });

    // Columns
    this.elements.filter(e => e.type === 'column').forEach(e => {
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(e.start.x - 9, e.start.y - 9, 18, 18);
      ctx.strokeStyle = '#0284c7';
      ctx.lineWidth = 2;
      ctx.strokeRect(e.start.x - 9, e.start.y - 9, 18, 18);

      ctx.fillStyle = '#94a3b8';
      ctx.font = '9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('PILAR', e.start.x, e.start.y + 20);
    });
  }

  syncWithStudio() {
    // Computes max span between any 2 columns
    const cols = this.elements.filter(e => e.type === 'column');
    let maxDistM = 6.0;
    if (cols.length >= 2) {
      for (let i = 0; i < cols.length; i++) {
        for (let j = i + 1; j < cols.length; j++) {
          const d = Math.hypot(cols[j].start.x - cols[i].start.x, cols[j].start.y - cols[i].start.y) / this.scale;
          if (d >= 2.0) maxDistM = Math.max(maxDistM, d);
        }
      }
    }

    const cants = this.elements.filter(e => e.type === 'cantilever');
    let maxCantM = 1.0;
    cants.forEach(c => {
      const d = Math.hypot(c.end.x - c.start.x, c.end.y - c.start.y) / this.scale;
      maxCantM = Math.max(maxCantM, d);
    });

    // Update main studio sliders
    if (window.studio) {
      if (window.studio.spanSlider) {
        window.studio.spanSlider.value = maxDistM.toFixed(1);
        if (window.studio.spanVal) window.studio.spanVal.textContent = `${maxDistM.toFixed(1)} m`;
      }
      if (window.studio.cantileverSlider) {
        window.studio.cantileverSlider.value = maxCantM.toFixed(1);
        if (window.studio.cantileverVal) window.studio.cantileverVal.textContent = `${maxCantM.toFixed(1)} m`;
      }
      window.studio.scheduleQuickCalc();
    }
  }

  async analyzeCanvas() {
    this.syncWithStudio();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.archCanvas = new ArchitecturalCanvas('structural-canvas');
});
