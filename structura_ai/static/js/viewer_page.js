/**
 * Structura.AI — Single-Page Structural Viewer, File Import/Export & Diagnostic Chatbot
 * Flow: Fake Login -> (a) Upload File -> (b) 2D/3D Visualization -> (c) Chat Diagnosis -> (d) Chat Debate
 */

const USER_STORAGE_KEY = 'structura-username';
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

/**
 * Lightweight XSS-safe Markdown formatter for technical chat responses.
 */
function renderSafeMarkdown(rawText) {
  const escaped = escapeHtml(rawText || '').replace(/\r\n/g, '\n');
  const lines = escaped.split('\n');
  const htmlParts = [];
  let inList = false;

  const formatInline = (str) =>
    str
      .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-ink-strong">$1</strong>')
      .replace(/`([^`]+)`/g, '<code class="font-mono text-[11px] px-1 py-0.5 rounded bg-surface-elevated text-ink-strong">$1</code>');

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      if (inList) {
        htmlParts.push('</ul>');
        inList = false;
      }
      continue;
    }

    if (/^#{1,4}\s+/.test(line)) {
      if (inList) {
        htmlParts.push('</ul>');
        inList = false;
      }
      const title = formatInline(line.replace(/^#{1,4}\s+/, ''));
      htmlParts.push(`<div class="font-semibold text-ink-strong mt-2 first:mt-0">${title}</div>`);
      continue;
    }

    if (/^([-*•]|\d+\.)\s+/.test(line)) {
      if (!inList) {
        htmlParts.push('<ul class="list-disc pl-4 space-y-1 my-1">');
        inList = true;
      }
      const item = formatInline(line.replace(/^([-*•]|\d+\.)\s+/, ''));
      htmlParts.push(`<li>${item}</li>`);
      continue;
    }

    if (inList) {
      htmlParts.push('</ul>');
      inList = false;
    }
    htmlParts.push(`<p class="leading-relaxed">${formatInline(line)}</p>`);
  }

  if (inList) {
    htmlParts.push('</ul>');
  }

  return htmlParts.join('');
}

document.addEventListener('DOMContentLoaded', () => {
  // 1. State
  let currentUser = '';
  let currentProject = null;
  let currentFileId = null;
  let selectedFormat = 'autocad';
  let activeDim = '3d';
  let activePlanView = 'blueprint';
  let isUploading = false;
  let chatHistory = [];
  let viewport = null;

  // 2. DOM Elements
  const loginScreen = document.getElementById('login-screen');
  const loginForm = document.getElementById('fake-login-form');
  const loginInput = document.getElementById('login-username-input');
  const userSessionBtn = document.getElementById('user-session-btn');
  const navbarUsername = document.getElementById('navbar-username');

  const workspace = document.getElementById('viewer-workspace');
  const activeFileBadge = document.getElementById('active-file-badge');
  const versionBarContainer = document.getElementById('version-bar-container');
  const softwareFormatSelect = document.getElementById('software-format-select');
  const btnConvertFormat = document.getElementById('btn-convert-format');
  const loadedFilesList = document.getElementById('loaded-files-list');
  const chatSuggestionsBar = document.getElementById('chat-suggestions-bar');

  const toolbar3d = document.getElementById('toolbar-3d-controls');
  const toolbar2d = document.getElementById('toolbar-2d-controls');
  const wrapper3d = document.getElementById('viewer-3d-wrapper');
  const wrapper2d = document.getElementById('viewer-2d-wrapper');
  const content2d = document.getElementById('viewer-2d-content');
  const tab2dOriginal = document.getElementById('tab-2d-original');
  const emptyOverlay = document.getElementById('viewport-empty-state');
  const hint3d = document.getElementById('hint-3d-controls');
  const btnResetCam = document.getElementById('btn-reset-cam');

  const dropzone = document.getElementById('file-dropzone');
  const viewportDropArea = document.getElementById('viewport-drop-area');
  const fileInput = document.getElementById('file-upload-input');
  const dropzoneTitle = document.getElementById('dropzone-title');
  const dropzoneSubtitle = document.getElementById('dropzone-subtitle');
  const fileStatusBadge = document.getElementById('file-status-badge');
  const uploadFeedback = document.getElementById('upload-feedback');

  const btnExportIfc = document.getElementById('btn-export-ifc');
  const btnExportDxf = document.getElementById('btn-export-dxf');
  const btnExportReport = document.getElementById('btn-export-report');

  const chatBox = document.getElementById('copilot-chat-box');
  const chatForm = document.getElementById('copilot-form');
  const chatInput = document.getElementById('copilot-input');
  const chatSendBtn = document.getElementById('copilot-send-btn');
  const chatStatusBadge = document.getElementById('chat-status-badge');

  // 3. Initialize 3D Viewport
  function ensureViewport() {
    if (!viewport && window.Structura3DViewport && document.getElementById('viewer-three-container')) {
      viewport = new window.Structura3DViewport('viewer-three-container');
    }
    if (viewport) {
      requestAnimationFrame(() => viewport.onResize());
    }
  }

  // 4. Fake Login Controller
  function getStoredUser() {
    try {
      return (localStorage.getItem(USER_STORAGE_KEY) || '').trim();
    } catch {
      return '';
    }
  }

  function setStoredUser(name) {
    try {
      if (name) {
        localStorage.setItem(USER_STORAGE_KEY, name);
      } else {
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  }

  function applyAuthView(username) {
    currentUser = username;

    if (!currentUser) {
      workspace?.classList.add('hidden');
      userSessionBtn?.classList.add('hidden');
      userSessionBtn?.classList.remove('inline-flex');
      loginScreen?.classList.remove('hidden');
      if (loginInput) {
        loginInput.value = '';
        setTimeout(() => loginInput.focus(), 30);
      }
      return;
    }

    loginScreen?.classList.add('hidden');
    workspace?.classList.remove('hidden');
    if (navbarUsername) navbarUsername.textContent = currentUser;
    if (userSessionBtn) {
      userSessionBtn.classList.remove('hidden');
      userSessionBtn.classList.add('inline-flex');
    }

    ensureViewport();

    if (chatBox && chatBox.children.length === 0) {
      appendAssistantMessage(
        `Olá, **${currentUser}**. Carregue um arquivo no painel ao lado (DXF, IFC, OBJ, glTF, STL, imagem ou PDF) ou use o chat para validar estruturas, consultar normas/arquitetura de Goiás e gerar código Text-to-Code.`
      );
      renderSuggestions([
        'Sou arquiteto em Goiânia e Pirenópolis, prefiro grandes balanços e concreto aparente',
        'Quais diretrizes do Art Déco Goianiense e Brutalismo do Cerrado posso aplicar?',
        'Validar se está tudo certo com a estrutura atual na NBR 6118'
      ]);
    }
    refreshUserFilesList();
  }

  if (loginForm && loginInput) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = loginInput.value.trim();
      if (!name) return;
      setStoredUser(name);
      if (chatBox && !currentProject) {
        chatBox.innerHTML = '';
        chatHistory = [];
      }
      applyAuthView(name);
    });
  }

  if (userSessionBtn) {
    userSessionBtn.addEventListener('click', () => {
      setStoredUser('');
      applyAuthView('');
    });
  }

  // 5. Chat Helpers
  function appendUserMessage(text) {
    if (!chatBox) return;
    const msgEl = document.createElement('div');
    msgEl.className = 'p-2.5 rounded-md bg-surface-elevated border border-edge text-ink-strong space-y-1';
    msgEl.innerHTML = `
      <span class="font-mono font-semibold text-ink-muted text-[10px] block">→ ${escapeHtml(currentUser || 'usuário')}</span>
      <div class="leading-relaxed break-words">${escapeHtml(text)}</div>
    `;
    chatBox.appendChild(msgEl);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function appendAssistantMessage(markdownText, label = 'chatbot') {
    if (!chatBox) return null;
    const msgEl = document.createElement('div');
    msgEl.className = 'p-2.5 rounded-md bg-surface-card border border-edge text-ink-secondary space-y-1.5';
    msgEl.innerHTML = `
      <span class="font-mono font-semibold text-ink-strong text-[10px] block">→ ${escapeHtml(label)}</span>
      <div class="space-y-1.5 leading-relaxed break-words">${renderSafeMarkdown(markdownText)}</div>
    `;
    chatBox.appendChild(msgEl);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msgEl;
  }

  function renderSuggestions(suggestions) {
    if (!chatSuggestionsBar) return;
    const list = Array.isArray(suggestions) && suggestions.length > 0
      ? suggestions.slice(0, 3)
      : [
          'Gostaria de ver essa solução em outro formato (Blender 3D / AutoCAD DXF)?',
          'Como adaptar a estética para o Brutalismo do Cerrado ou Art Déco Goianiense?',
          'Validar impacto no Latossolo Vermelho de Goiânia e NBR 6118'
        ];
    chatSuggestionsBar.innerHTML = '';
    list.forEach((s) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ui-btn ui-btn-secondary text-left py-1.5 px-2.5 text-[10px] font-mono leading-snug truncate';
      btn.title = s;
      btn.textContent = s;
      btn.addEventListener('click', () => {
        submitChatMessage(s);
      });
      chatSuggestionsBar.appendChild(btn);
    });
  }

  async function fetchWithRetry(url, options = {}, retries = 2, delayMs = 450) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        return await fetch(url, options);
      } catch (err) {
        if (attempt === retries) throw err;
        await new Promise((r) => setTimeout(r, delayMs * (attempt + 1)));
      }
    }
  }

  function applyActiveFileToUI(activeFile) {
    if (!activeFile) return;
    currentFileId = activeFile.id;
    hideUploadFeedback();
    emptyOverlay?.classList.add('opacity-0');
    hint3d?.classList.remove('hidden');

    if (activeFileBadge) {
      activeFileBadge.textContent = `${activeFile.filename} (v${activeFile.active_version_number})`;
    }
    if (versionBarContainer && Array.isArray(activeFile.versions)) {
      versionBarContainer.innerHTML = '';
      activeFile.versions.forEach((ver) => {
        const vBtn = document.createElement('button');
        vBtn.type = 'button';
        const isCurrent = ver.version_number === activeFile.active_version_number;
        vBtn.className = isCurrent
          ? 'ui-tab is-active px-2 py-0.5 text-[10px] font-mono'
          : 'ui-tab px-2 py-0.5 text-[10px] font-mono';
        vBtn.textContent = ver.version_label || `v${ver.version_number}`;
        vBtn.title = ver.change_summary || `Versão ${ver.version_label} (${ver.render_style})`;
        vBtn.addEventListener('click', async () => {
          const res = await fetchWithRetry(
            `/api/v1/files/${encodeURIComponent(activeFile.id)}/versions/${ver.version_number}/activate?user_id=${encodeURIComponent(currentUser || 'default_user')}`,
            { method: 'POST' }
          );
          if (res.ok) {
            const updatedFile = await res.json();
            applyActiveFileToUI(updatedFile);
          }
        });
        versionBarContainer.appendChild(vBtn);
      });
    }

    const activeVer = activeFile.active_version || (activeFile.versions || []).find((v) => v.version_number === activeFile.active_version_number);
    if (activeVer && softwareFormatSelect) {
      if (['autocad', 'blender', 'ifc', 'grasshopper_rhino', 'openscad', 'landscape_insight'].includes(activeVer.render_style)) {
        softwareFormatSelect.value = activeVer.render_style;
        selectedFormat = activeVer.render_style;
      }
    }

    if (activeVer && activeVer.structural_parameters) {
      const sp = activeVer.structural_parameters;
      const vr = activeVer.validation_report || {};
      if (!currentProject) {
        currentProject = {
          id: activeFile.project_id || activeFile.id,
          title: activeFile.filename,
          parameters: sp,
          latest_analysis: vr
        };
      } else {
        currentProject.id = activeFile.project_id || activeFile.id || currentProject.id;
        currentProject.title = activeFile.filename || currentProject.title;
        currentProject.parameters = { ...(currentProject.parameters || {}), ...sp };
        currentProject.latest_analysis = { ...(currentProject.latest_analysis || {}), ...vr };
      }
      ensureViewport();
      if (viewport) {
        viewport.updateFromParams(
          {
            span_length_m: sp.span_length_m ?? 9.5,
            cantilever_length_m: sp.cantilever_length_m ?? 3.5,
            beam_height_cm: sp.beam_height_cm ?? 40.0,
            beam_width_cm: sp.beam_width_cm ?? 20.0,
            column_height_m: sp.column_height_m ?? 3.2,
            column_section_cm: sp.column_section_cm ?? 25.0,
            max_deflection_mm: vr.max_deflection_mm ?? 30.0,
            allowable_deflection_mm: vr.allowable_deflection_mm ?? 38.0,
            is_viable: Boolean(vr.is_physically_viable ?? true)
          },
          { fitCamera: false }
        );
      }
      render2DView();
    }

    [btnExportIfc, btnExportDxf, btnExportReport].forEach((btn) => {
      if (btn) {
        btn.disabled = false;
        btn.removeAttribute('title');
      }
    });
  }

  async function refreshUserFilesList() {
    if (!loadedFilesList) return;
    try {
      const res = await fetch(`/api/v1/files?user_id=${encodeURIComponent(currentUser || 'default_user')}`);
      if (!res.ok) return;
      const files = await res.json();
      loadedFilesList.innerHTML = '';
      files.forEach((f) => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className = f.is_selected
          ? 'ui-badge ui-badge-ok cursor-pointer text-[10px]'
          : 'ui-badge cursor-pointer text-[10px]';
        pill.textContent = `${f.filename} (v${f.active_version_number})`;
        pill.addEventListener('click', async () => {
          const selRes = await fetch(`/api/v1/files/${encodeURIComponent(f.id)}/select`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser || 'default_user' })
          });
          if (selRes.ok) {
            const selectedFile = await selRes.json();
            applyActiveFileToUI(selectedFile);
            refreshUserFilesList();
          }
        });
        loadedFilesList.appendChild(pill);
        if (f.is_selected) {
          applyActiveFileToUI(f);
        }
      });
    } catch {
      // Ignore network errors on boot
    }
  }

  function buildProjectContext() {
    if (!currentProject) return null;
    const params = currentProject.parameters || {};
    const analysis = currentProject.latest_analysis || {};
    return {
      title: currentProject.title,
      span_length_m: params.span_length_m ?? 10.0,
      cantilever_length_m: params.cantilever_length_m ?? 0.0,
      beam_height_cm: params.beam_height_cm ?? 30.0,
      beam_width_cm: params.beam_width_cm ?? 20.0,
      concrete_fck_mpa: params.concrete_fck_mpa ?? 30.0,
      is_physically_viable: analysis.is_physically_viable ?? false,
      structural_score: analysis.structural_score ?? 0.0,
      max_deflection_mm: analysis.max_deflection_mm ?? 0.0,
      allowable_deflection_mm: analysis.allowable_deflection_mm ?? 0.0,
      max_bending_moment_knm: analysis.max_bending_moment_knm ?? 0.0,
      failure_reasons: analysis.failure_reasons || []
    };
  }

  function formatDiagnosisMessage(project) {
    const params = project.parameters || {};
    const a = project.latest_analysis || {};
    const span = Number(params.span_length_m ?? 9.5).toFixed(1);
    const cant = Number(params.cantilever_length_m ?? 0.0).toFixed(1);
    const bw = Number(params.beam_width_cm ?? 20).toFixed(0);
    const bh = Number(params.beam_height_cm ?? 30).toFixed(0);
    const fck = Number(params.concrete_fck_mpa ?? 30).toFixed(0);

    const statusLine = a.is_physically_viable
      ? `**Status:** Conforme ABNT NBR 6118 (Índice ${a.structural_score}/100)`
      : `**Status:** Revisão estrutural necessária (Índice ${a.structural_score}/100)`;

    const lines = [
      `### Resultados — ${project.title}`,
      statusLine,
      `- **Geometria:** Vão L = ${span} m · Balanço Lc = ${cant} m · Viga ${bw}×${bh} cm (C${fck})`,
      `- **Deformação (ELS):** Flecha δ = **${a.max_deflection_mm} mm** (limite normativo ≤ ${a.allowable_deflection_mm} mm)`,
      `- **Esforço solicitante:** Momento fletor máximo Mk = **${a.max_bending_moment_knm} kN·m**`
    ];

    if (Array.isArray(a.failure_reasons) && a.failure_reasons.length > 0) {
      lines.push('', '### Não conformidades identificadas');
      for (const reason of a.failure_reasons) {
        lines.push(`- ${reason}`);
      }
    }

    if (a.structural_diagnosis_text) {
      lines.push('', '### Diagnóstico técnico', a.structural_diagnosis_text);
    } else if (a.ai_gemini_review) {
      lines.push('', a.ai_gemini_review);
    }

    lines.push(
      '',
      'Fique à vontade para debater este diagnóstico aqui no chat — pergunte sobre redimensionamento, protensão, custos ou alternativas estruturais.'
    );

    return lines.join('\n');
  }

  // 6. 2D & 3D Visualization Rendering
  function isOriginalPreviewSupported(filename = '') {
    return /\.(png|jpe?g|webp|gif|bmp|svg|pdf)$/i.test(filename);
  }

  function switchDimension(dim) {
    activeDim = dim;
    document.querySelectorAll('[data-view-dim]').forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.viewDim === dim);
    });

    const is3d = dim === '3d';
    toolbar3d?.classList.toggle('hidden', !is3d);
    toolbar3d?.classList.toggle('flex', is3d);
    toolbar2d?.classList.toggle('hidden', is3d);
    toolbar2d?.classList.toggle('flex', !is3d);

    wrapper3d?.classList.toggle('hidden', !is3d);
    wrapper2d?.classList.toggle('hidden', is3d);

    if (is3d && viewport) {
      requestAnimationFrame(() => viewport.onResize());
    } else if (!is3d && currentProject) {
      render2DView();
    }
  }

  function switchPlanView(planMode) {
    activePlanView = planMode;
    document.querySelectorAll('[data-plan-view]').forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.planView === planMode);
    });
    if (currentProject) {
      render2DView();
    }
  }

  function render2DView() {
    if (!content2d || !currentProject) return;
    const params = currentProject.parameters || {};
    const analysis = currentProject.latest_analysis || {};
    const cadData = params.cad_data || null;

    const span = parseFloat(params.span_length_m) || 10.0;
    const cant = parseFloat(params.cantilever_length_m) || 0.0;
    const bw = parseFloat(params.beam_width_cm) || 20.0;
    const bh = parseFloat(params.beam_height_cm) || 30.0;
    const defl = parseFloat(analysis.max_deflection_mm) || 45.0;
    const allowable = parseFloat(analysis.allowable_deflection_mm) || 40.0;
    const momentKnm = parseFloat(analysis.max_bending_moment_knm) || 0.0;
    const isViable = Boolean(analysis.is_physically_viable);

    if (activePlanView === 'original' && currentProject.image_path) {
      const url = escapeHtml(currentProject.image_path);
      const isPdf = /\.pdf$/i.test(currentProject.image_filename || '');
      content2d.innerHTML = isPdf
        ? `<embed src="${url}" type="application/pdf" class="w-full h-[330px] rounded border border-edge bg-surface-card" />`
        : `<img src="${url}" alt="${escapeHtml(currentProject.title)}" class="max-h-[330px] mx-auto w-auto object-contain rounded border border-edge bg-surface-card p-2" />`;
      return;
    }

    if (activePlanView === 'section') {
      const scale = 500 / Math.max(span, 8.0);
      const x0 = 80;
      const x1 = x0 + span * scale;
      const yTop = 62;
      const beamHpx = Math.min(Math.max(bh * 0.42, 10), 34);
      const yBot = yTop + beamHpx;
      const xm = (x0 + x1) / 2;
      const sagPx = Math.min(Math.max(defl * 0.5, 10), 46);
      const curveMidY = yBot + sagPx;
      const ctrlY = yBot + 2 * sagPx;

      content2d.innerHTML = `
        <svg viewBox="0 0 700 245" class="bp-svg w-full h-auto font-mono text-xs rounded border border-edge">
          <text x="26" y="28" class="bp-text-strong" font-size="10.5">Corte longitudinal · Deformada em serviço (ELS) · Mk = ${momentKnm.toFixed(1)} kN·m</text>
          <rect x="${x0 - 12}" y="${yTop}" width="24" height="146" class="bp-struct" stroke-width="1.25"/>
          <rect x="${x1 - 12}" y="${yTop}" width="24" height="146" class="bp-struct" stroke-width="1.25"/>
          <rect x="${x0}" y="${yTop}" width="${x1 - x0}" height="${beamHpx}" fill="none" class="bp-dim-line" stroke-dasharray="4,4" stroke-width="1"/>
          <path d="M ${x0} ${yBot} Q ${xm} ${ctrlY} ${x1} ${yBot}" fill="none" class="${isViable ? 'bp-stroke-emerald' : 'bp-stroke-rose'}" stroke-width="2.2"/>
          <line x1="${xm}" y1="${yBot}" x2="${xm}" y2="${curveMidY}" class="bp-dim-line" stroke-width="1.25"/>
          <circle cx="${xm}" cy="${curveMidY}" r="3.4" class="${isViable ? 'bp-accent-emerald' : 'bp-accent-rose'}"/>
          <text x="${xm}" y="${curveMidY + 18}" text-anchor="middle" class="${isViable ? 'bp-accent-emerald' : 'bp-accent-rose'}" font-size="10">
            δ = ${defl.toFixed(1)} mm (${isViable ? 'Conforme' : 'Acima do limite'})
          </text>
          <text x="${xm}" y="${curveMidY + 32}" text-anchor="middle" class="bp-text-muted" font-size="9">
            Limite NBR 6118: ≤ ${allowable.toFixed(1)} mm
          </text>
        </svg>
      `;
      return;
    }

    // Planta 2D: Render extracted DXF 2D entities when present, or schematic framing plan
    if (cadData && Array.isArray(cadData.raw_2d_entities) && cadData.raw_2d_entities.length > 0) {
      const ents = cadData.raw_2d_entities;
      let maxX = 1, maxY = 1;
      for (const l of ents) {
        maxX = Math.max(maxX, l.x1 || 0, l.x2 || 0);
        maxY = Math.max(maxY, l.y1 || 0, l.y2 || 0);
      }
      const padX = 56, padY = 44;
      const drawW = 700 - padX * 2;
      const drawH = 260 - padY * 2;
      const s = Math.min(drawW / Math.max(maxX, 0.5), drawH / Math.max(maxY, 0.5));
      const offsetX = (700 - maxX * s) / 2;
      const offsetY = (260 - maxY * s) / 2;

      const svgLines = ents
        .map((l) => {
          const x1 = (offsetX + (l.x1 || 0) * s).toFixed(1);
          const y1 = (260 - (offsetY + (l.y1 || 0) * s)).toFixed(1);
          const x2 = (offsetX + (l.x2 || 0) * s).toFixed(1);
          const y2 = (260 - (offsetY + (l.y2 || 0) * s)).toFixed(1);
          const cls = l.is_structural ? 'bp-stroke-brand' : 'bp-dim-line';
          const sw = l.is_structural ? '2' : '1.1';
          return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="${cls}" stroke-width="${sw}" stroke-linecap="round"/>`;
        })
        .join('');

      content2d.innerHTML = `
        <svg viewBox="0 0 700 260" class="bp-svg w-full h-auto font-mono text-xs rounded border border-edge">
          <defs>
            <pattern id="cad-grid-dxf" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M 24 0 L 0 0 0 24" fill="none" class="bp-grid-line" stroke-width="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#cad-grid-dxf)" />
          <text x="22" y="24" class="bp-text-strong" font-size="10.5">Planta CAD 2D · Vão crítico L = ${span.toFixed(1)} m${cant > 0 ? ` · Balanço ${cant.toFixed(1)} m` : ''}</text>
          ${svgLines}
          <text x="22" y="246" class="bp-text-muted" font-size="9.5">Seção avaliada: ${bw.toFixed(0)}×${bh.toFixed(0)} cm</text>
          <text x="678" y="246" class="bp-text-muted" font-size="9.5" text-anchor="end">${ents.length} entidades vetoriais</text>
        </svg>
      `;
      return;
    }

    // Default schematic 2D framing plan
    const totalLen = span + cant;
    const scale = 470 / Math.max(totalLen + 1.5, 8.0);
    const p1X = 76;
    const p2X = p1X + span * scale;
    const cantX = p2X + cant * scale;
    const yAxis = 136;
    const beamPlanW = Math.min(Math.max(bw * 0.55, 8), 22);
    const cantPx = cantX - p2X;
    const cantLabelX = cantPx < 78 ? p2X + 8 : (p2X + cantX) / 2;
    const cantLabelAnchor = cantPx < 78 ? 'start' : 'middle';

    content2d.innerHTML = `
      <svg viewBox="0 0 700 250" class="bp-svg w-full h-auto font-mono text-xs rounded border border-edge">
        <defs>
          <pattern id="cad-grid-plan" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" class="bp-grid-line" stroke-width="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#cad-grid-plan)" />
        <text x="26" y="26" class="bp-text-strong" font-size="10.5">Planta estrutural 2D · Eixo principal A</text>
        <circle cx="32" cy="${yAxis}" r="11" class="bp-slab" stroke-width="1.2"/>
        <text x="32" y="${yAxis + 3.5}" class="bp-text-strong" font-size="9.5" text-anchor="middle">A</text>
        <line x1="43" y1="${yAxis}" x2="${cantX + 36}" y2="${yAxis}" class="bp-dim-line" stroke-dasharray="8,4,2,4" stroke-width="1"/>
        <rect x="${p1X}" y="${yAxis - beamPlanW / 2}" width="${cantX - p1X}" height="${beamPlanW}" class="bp-slab" stroke-width="1.5"/>
        <rect x="${p1X - 9}" y="${yAxis - 16}" width="18" height="32" class="bp-struct" stroke-width="1.5"/>
        <text x="${p1X}" y="${yAxis + 32}" class="bp-text-strong" font-size="9.5" text-anchor="middle">P1</text>
        <rect x="${p2X - 9}" y="${yAxis - 16}" width="18" height="32" class="bp-struct" stroke-width="1.5"/>
        <text x="${p2X}" y="${yAxis + 32}" class="bp-text-strong" font-size="9.5" text-anchor="middle">P2</text>
        <line x1="${p1X}" y1="72" x2="${p2X}" y2="72" class="bp-dim-line" stroke-width="1"/>
        <line x1="${p1X}" y1="66" x2="${p1X}" y2="78" class="bp-dim-line" stroke-width="1"/>
        <line x1="${p2X}" y1="66" x2="${p2X}" y2="78" class="bp-dim-line" stroke-width="1"/>
        <text x="${(p1X + p2X) / 2}" y="61" class="bp-text-strong" font-size="10" text-anchor="middle">L = ${span.toFixed(2)} m</text>
        ${cant > 0 ? `
          <line x1="${p2X}" y1="72" x2="${cantX}" y2="72" class="bp-stroke-amber" stroke-width="1.2"/>
          <line x1="${cantX}" y1="66" x2="${cantX}" y2="78" class="bp-stroke-amber" stroke-width="1.2"/>
          <text x="${cantLabelX}" y="61" class="bp-accent-amber" font-size="10" text-anchor="${cantLabelAnchor}">Lc = ${cant.toFixed(2)} m</text>
        ` : ''}
        <text x="26" y="230" class="bp-text-muted" font-size="9.5">Seção da viga: ${bw.toFixed(0)}×${bh.toFixed(0)} cm</text>
        <text x="674" y="230" class="bp-text-muted" font-size="9.5" text-anchor="end">Escala esquemática 1:50</text>
      </svg>
    `;
  }

  function applyLoadedProjectToViewer(project, rawFilename) {
    currentProject = project;
    const params = project.parameters || {};
    const analysis = project.latest_analysis || {};
    const cadMesh = params.cad_data?.mesh_3d || null;

    emptyOverlay?.classList.add('opacity-0');
    hint3d?.classList.remove('hidden');

    if (activeFileBadge) {
      activeFileBadge.textContent = rawFilename || project.image_filename || project.title;
      activeFileBadge.className = analysis.is_physically_viable
        ? 'ui-badge ui-badge-ok truncate max-w-[200px] sm:max-w-xs'
        : 'ui-badge ui-badge-fail truncate max-w-[200px] sm:max-w-xs';
    }

    const hasOriginalPreview = isOriginalPreviewSupported(rawFilename || project.image_filename || '') && Boolean(project.image_path);
    if (tab2dOriginal) {
      tab2dOriginal.classList.toggle('hidden', !hasOriginalPreview);
      if (!hasOriginalPreview && activePlanView === 'original') {
        activePlanView = 'blueprint';
        document.querySelectorAll('[data-plan-view]').forEach((b) => {
          b.classList.toggle('is-active', b.dataset.planView === 'blueprint');
        });
      }
    }

    ensureViewport();
    if (viewport) {
      viewport.updateFromParams(
        {
          span_length_m: params.span_length_m ?? 10.0,
          cantilever_length_m: params.cantilever_length_m ?? 0.0,
          beam_height_cm: params.beam_height_cm ?? 30.0,
          beam_width_cm: params.beam_width_cm ?? 20.0,
          column_height_m: params.column_height_m ?? 3.2,
          column_section_cm: params.column_section_cm ?? 20.0,
          max_deflection_mm: analysis.max_deflection_mm ?? 45.0,
          allowable_deflection_mm: analysis.allowable_deflection_mm ?? 40.0,
          is_viable: Boolean(analysis.is_physically_viable),
          cad_mesh: cadMesh
        },
        { fitCamera: true }
      );
    }

    render2DView();

    // Enable Export Buttons
    [btnExportIfc, btnExportDxf, btnExportReport].forEach((btn) => {
      if (btn) {
        btn.disabled = false;
        btn.removeAttribute('title');
      }
    });
  }

  // 7. Toolbar Bindings
  document.querySelectorAll('[data-view-dim]').forEach((btn) => {
    btn.addEventListener('click', () => switchDimension(btn.dataset.viewDim));
  });

  document.querySelectorAll('[data-plan-view]').forEach((btn) => {
    btn.addEventListener('click', () => switchPlanView(btn.dataset.planView));
  });

  const shadeBtns = document.querySelectorAll('[data-shade]');
  shadeBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.shade;
      if (viewport) viewport.setShadingMode(mode);
      shadeBtns.forEach((b) => b.classList.toggle('is-active', b === btn));
    });
  });

  if (btnResetCam) {
    btnResetCam.addEventListener('click', () => {
      if (viewport) viewport.resetCamera();
    });
  }

  // 8. Export Actions
  if (btnExportIfc) {
    btnExportIfc.addEventListener('click', () => {
      if (!currentProject) return;
      window.location.href = `/api/export/${encodeURIComponent(currentProject.id)}/bim.ifc`;
    });
  }

  if (btnExportDxf) {
    btnExportDxf.addEventListener('click', () => {
      if (!currentProject) return;
      window.location.href = `/api/export/${encodeURIComponent(currentProject.id)}/cad.dxf`;
    });
  }

  if (btnExportReport) {
    btnExportReport.addEventListener('click', () => {
      if (!currentProject) return;
      window.open(`/api/export/${encodeURIComponent(currentProject.id)}/report.html`, '_blank', 'noopener');
    });
  }

  // 9. File Upload & Analysis Flow
  function showUploadFeedback(msg, isError = true) {
    if (!uploadFeedback) return;
    uploadFeedback.textContent = msg;
    uploadFeedback.className = isError
      ? 'text-[11px] font-mono px-2.5 py-1.5 rounded border border-accent-rose/30 bg-accent-rose/5 text-accent-rose shrink-0'
      : 'text-[11px] font-mono px-2.5 py-1.5 rounded border border-accent-emerald/30 bg-accent-emerald/5 text-accent-emerald shrink-0';
  }

  function hideUploadFeedback() {
    uploadFeedback?.classList.add('hidden');
  }

  async function handleFileUpload(file) {
    if (!file || isUploading) return;
    hideUploadFeedback();

    const allowedExt = /\.(png|jpe?g|webp|gif|bmp|svg|pdf|dxf|ifc|obj|gltf|glb|stl|blend|py|scad)$/i;
    const isAllowedMime = file.type.startsWith('image/') || file.type === 'application/pdf';
    if (!isAllowedMime && !allowedExt.test(file.name)) {
      showUploadFeedback('Formato não suportado. Use DXF, IFC, OBJ, glTF, STL, SVG, PNG, JPG ou PDF.');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      showUploadFeedback(`Arquivo excede 25 MB (${formatBytes(file.size)}).`);
      return;
    }

    isUploading = true;
    const cleanTitle = file.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim() || 'Modelo importado';

    if (dropzoneTitle) dropzoneTitle.textContent = `Processando ${file.name}...`;
    if (dropzoneSubtitle) dropzoneSubtitle.textContent = 'Extraindo geometria e verificando NBR 6118...';
    if (fileStatusBadge) fileStatusBadge.textContent = 'Analisando...';
    if (chatStatusBadge) {
      chatStatusBadge.className = 'ui-badge ui-badge-warn';
      chatStatusBadge.textContent = 'Analisando...';
    }

    appendUserMessage(`Arquivo enviado: ${file.name} (${formatBytes(file.size)})`);
    const loadingBubble = appendAssistantMessage('Processando geometria 2D/3D e calculando diagnóstico estrutural...');

    try {
      const formData = new FormData();
      formData.append('title', cleanTitle);
      formData.append('author_architect', currentUser || 'Usuário');
      formData.append('category', 'Residencial');
      formData.append('file', file);

      const uploadRes = await fetchWithRetry('/api/projects/upload', {
        method: 'POST',
        body: formData
      });

      if (!uploadRes.ok) {
        const errBody = await uploadRes.json().catch(() => ({}));
        throw new Error(errBody.detail || 'Falha ao processar o arquivo enviado.');
      }

      const uploadData = await uploadRes.json();
      if (uploadData.file_id) {
        currentFileId = uploadData.file_id;
      }

      let project = uploadData.project;
      if (!project) {
        const projRes = await fetchWithRetry(`/api/projects/${encodeURIComponent(uploadData.project_id)}`);
        if (!projRes.ok) {
          throw new Error('Não foi possível recuperar os resultados da análise.');
        }
        project = await projRes.json();
      }

      // Update dropzone readout
      if (dropzoneTitle) dropzoneTitle.textContent = file.name;
      if (dropzoneSubtitle) {
        dropzoneSubtitle.textContent = `${formatBytes(file.size)} · Clique ou arraste outro arquivo para substituir`;
      }
      const extUpper = (file.name.split('.').pop() || 'ARQUIVO').toUpperCase();
      if (fileStatusBadge) fileStatusBadge.textContent = `${extUpper} carregado`;

      // Step (b): Update 2D / 3D Visualization & Version Bar
      applyLoadedProjectToViewer(project, file.name);
      if (uploadData.active_file) {
        applyActiveFileToUI(uploadData.active_file);
      }
      await refreshUserFilesList();

      // Step (c): Post Results & Diagnosis into Chatbot + 3 ICP Suggestions
      loadingBubble?.remove();
      const diagnosisMarkdown = formatDiagnosisMessage(project);
      appendAssistantMessage(diagnosisMarkdown);

      const isViable = Boolean(project.latest_analysis?.is_physically_viable);
      if (isViable) {
        renderSuggestions([
          'Gostaria de ver essa solução de outra forma (converter para Blender 3D)?',
          'Que tal testar brises Art Déco Goianiense ou Pedra de Pirenópolis na fachada?',
          'Exportar código executável em AutoCAD DXF / BIM IFC'
        ]);
      } else {
        renderSuggestions([
          'Gostaria de ver isso corrigido em uma nova versão v2 com viga redimensionada?',
          'Como resolver esse balanço com Viga Vierendel Brutalista ou Aço Corten?',
          'Verificar impacto dessa carga no Latossolo Vermelho de Goiânia'
        ]);
      }

      chatHistory.push(
        { role: 'user', content: `Enviei o arquivo ${file.name} para análise estrutural.` },
        { role: 'assistant', content: diagnosisMarkdown }
      );

      if (chatStatusBadge) {
        chatStatusBadge.className = project.latest_analysis?.is_physically_viable
          ? 'ui-badge ui-badge-ok'
          : 'ui-badge ui-badge-fail';
        chatStatusBadge.textContent = project.latest_analysis?.is_physically_viable
          ? 'Conforme'
          : 'Revisão';
      }
    } catch (err) {
      loadingBubble?.remove();
      const rawMsg = err?.message || 'Erro inesperado ao analisar o arquivo.';
      const errMsg = rawMsg === 'Failed to fetch'
        ? 'Conexão com o servidor interrompida. Verifique se o backend está ativo (./run.sh) e tente novamente.'
        : rawMsg;
      showUploadFeedback(errMsg);
      appendAssistantMessage(`Não foi possível concluir a análise do arquivo: **${errMsg}**`);
      if (dropzoneTitle) dropzoneTitle.textContent = 'Carregar arquivo...';
      if (dropzoneSubtitle) dropzoneSubtitle.textContent = 'Drag & Drop ou clique para selecionar';
      if (fileStatusBadge) fileStatusBadge.textContent = 'Importar / Exportar';
      if (chatStatusBadge) {
        chatStatusBadge.className = 'ui-badge';
        chatStatusBadge.textContent = 'Assistente';
      }
    } finally {
      isUploading = false;
      if (fileInput) fileInput.value = '';
    }
  }

  function bindDropSurface(surfaceEl) {
    if (!surfaceEl) return;

    ['dragenter', 'dragover'].forEach((evtName) => {
      surfaceEl.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone?.classList.add('is-dragover');
      });
    });

    ['dragleave', 'dragend', 'drop'].forEach((evtName) => {
      surfaceEl.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone?.classList.remove('is-dragover');
      });
    });

    surfaceEl.addEventListener('drop', (e) => {
      const droppedFile = e.dataTransfer?.files?.[0];
      if (droppedFile) {
        handleFileUpload(droppedFile);
      }
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => {
      if (!isUploading) fileInput.click();
    });

    dropzone.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && !isUploading) {
        e.preventDefault();
        fileInput.click();
      }
    });

    fileInput.addEventListener('change', () => {
      const selected = fileInput.files?.[0];
      if (selected) handleFileUpload(selected);
    });

    bindDropSurface(dropzone);
    bindDropSurface(viewportDropArea);
  }

  // Seletor de Formato de Software & Conversão no Canto Superior Direito
  if (softwareFormatSelect) {
    softwareFormatSelect.addEventListener('change', () => {
      selectedFormat = softwareFormatSelect.value || 'autocad';
    });
  }

  if (btnConvertFormat) {
    btnConvertFormat.addEventListener('click', async () => {
      const fmt = softwareFormatSelect?.value || selectedFormat || 'blender';
      selectedFormat = fmt;
      if (currentFileId) {
        try {
          const res = await fetch(
            `/api/v1/files/${encodeURIComponent(currentFileId)}/convert?target_format=${encodeURIComponent(fmt)}&user_id=${encodeURIComponent(currentUser || 'default_user')}`,
            { method: 'POST' }
          );
          if (res.ok) {
            const updatedFile = await res.json();
            applyActiveFileToUI(updatedFile);
            await refreshUserFilesList();
            appendAssistantMessage(
              `Projeto convertido para o formato **${fmt.toUpperCase()}**, gerando a versão **v${updatedFile.active_version_number}**. Gostaria de ver essa solução em outro formato ou validar os cálculos?`
            );
            renderSuggestions([
              `Validar versão v${updatedFile.active_version_number} na NBR 6118`,
              'Converter também para BIM IFC 4 (.ifc)',
              'Voltar para a versão v1'
            ]);
            return;
          }
        } catch {
          // Fall through to chat conversion
        }
      }
      submitChatMessage(`Converter projeto atual para o formato ${fmt}`);
    });
  }

  // 10. Step (d): Multi-Turn Debate with Chatbot + 3 ICP Suggestions + Live UI Mutations
  async function submitChatMessage(rawQuery) {
    const query = (rawQuery || '').trim();
    if (!query) return;

    appendUserMessage(query);
    if (chatInput) chatInput.value = '';
    if (chatSendBtn) chatSendBtn.disabled = true;

    const thinkingBubble = appendAssistantMessage('Analisando consulta...');

    try {
      const res = await fetch('/api/analysis/copilot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          user_id: currentUser || 'default_user',
          active_file_id: currentFileId,
          selected_format: selectedFormat,
          region_country: 'BR-GO',
          project_context: buildProjectContext(),
          history: chatHistory
        })
      });

      const data = await res.json();
      thinkingBubble?.remove();

      const replyText = data.reply || 'Sem resposta disponível no momento.';
      appendAssistantMessage(replyText);

      if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
        renderSuggestions(data.suggestions);
      }

      if (data.active_file) {
        applyActiveFileToUI(data.active_file);
        await refreshUserFilesList();
      }

      chatHistory.push(
        { role: 'user', content: query },
        { role: 'assistant', content: replyText }
      );
    } catch (err) {
      console.error('Copilot error:', err);
      thinkingBubble?.remove();
      appendAssistantMessage('Falha de comunicação ao consultar o assistente. Tente novamente.');
    } finally {
      if (chatSendBtn) chatSendBtn.disabled = false;
      chatInput?.focus();
    }
  }

  if (chatForm && chatInput) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const query = chatInput.value.trim();
      if (!query) return;
      await submitChatMessage(query);
    });
  }

  // Boot authentication view
  applyAuthView(getStoredUser());
});
