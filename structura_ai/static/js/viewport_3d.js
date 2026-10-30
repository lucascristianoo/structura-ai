/**
 * Structura.AI — Interactive 3D WebGL Viewport (Three.js)
 * Renderizador tridimensional de elementos estruturais, deformações e mapa de tensões FEA.
 */

class Structura3DViewport {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.meshGroup = new THREE.Group();
    this.gridHelper = null;
    this.currentMode = 'shaded'; // 'shaded', 'wireframe', 'xray', 'stress'
    this.amplification = 25.0; // Fator de ampliação da flecha
    this.activeVariant = 0; // 0 = original, 1..5 = redesign variants
    this.currentParams = null;

    this.init();
  }

  init() {
    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 450;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x030712); // slate-950

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.camera.position.set(14, 8, 16);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    // Orbit Controls
    if (typeof THREE.OrbitControls !== 'undefined') {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.maxPolarAngle = Math.PI / 2 + 0.05; // Não descer abaixo do piso
      this.controls.minDistance = 3;
      this.controls.maxDistance = 60;
      this.controls.target.set(5, 1.8, 0);
    }

    // Grid Floor
    this.gridHelper = new THREE.GridHelper(30, 30, 0x0284c7, 0x1e293b);
    this.gridHelper.position.y = 0;
    this.scene.add(this.gridHelper);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight.position.set(15, 25, 20);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    this.scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.4);
    rimLight.position.set(-15, 10, -10);
    this.scene.add(rimLight);

    this.scene.add(this.meshGroup);

    // Resize Handler
    window.addEventListener('resize', () => this.onResize());

    // Animation Loop
    this.animate();
  }

  onResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight || 450;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  setShadingMode(mode) {
    this.currentMode = mode;
    this.rebuildScene();
  }

  setDeflectionAmplification(amp) {
    this.amplification = amp;
    this.rebuildScene();
  }

  setActiveVariant(variantNum) {
    this.activeVariant = variantNum;
    this.rebuildScene();
  }

  updateFromParams(params) {
    this.currentParams = params;
    this.rebuildScene();
  }

  rebuildScene() {
    // Limpar meshes anteriores
    while (this.meshGroup.children.length > 0) {
      const obj = this.meshGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
        else obj.material.dispose();
      }
      this.meshGroup.remove(obj);
    }

    const p = this.currentParams || {
      span_length_m: 10.0,
      cantilever_length_m: 0.0,
      beam_height_cm: 30.0,
      beam_width_cm: 20.0,
      column_height_m: 3.2,
      column_section_cm: 20.0,
      max_deflection_mm: 54.2,
      allowable_deflection_mm: 40.0,
      is_viable: false,
    };

    const span = parseFloat(p.span_length_m) || 10.0;
    const cant = parseFloat(p.cantilever_length_m) || 0.0;
    const bh = (parseFloat(p.beam_height_cm) || 30.0) / 100.0;
    const bw = (parseFloat(p.beam_width_cm) || 20.0) / 100.0;
    const ch = parseFloat(p.column_height_m) || 3.2;
    const cw = (parseFloat(p.column_section_cm) || 20.0) / 100.0;
    const cd = cw * 2.0;

    // Atualizar target da câmera para o centro da estrutura
    if (this.controls) {
      this.controls.target.set(span / 2, ch / 2, 0);
    }

    // Cores e materiais base
    const colMat = this.createMaterial(0x64748b, 0.9); // slate-500
    const beamBaseColor = p.is_viable ? 0x0ea5e9 : 0xef4444; // sky-500 ou red-500
    const beamMat = this.createMaterial(beamBaseColor, 0.95);
    const slabMat = this.createMaterial(0x1e293b, 0.85); // slate-800
    const cableMat = new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 3 }); // amber-500

    // 1. PILARES
    const colGeom = new THREE.BoxGeometry(cw, ch, cd);
    // Pilar P1 (Esquerda)
    const p1Mesh = new THREE.Mesh(colGeom, colMat);
    p1Mesh.position.set(0, ch / 2, 0);
    p1Mesh.castShadow = true;
    p1Mesh.receiveShadow = true;
    this.meshGroup.add(p1Mesh);

    // Pilar P2 (Direita)
    const p2Mesh = new THREE.Mesh(colGeom, colMat);
    p2Mesh.position.set(span, ch / 2, 0);
    p2Mesh.castShadow = true;
    p2Mesh.receiveShadow = true;
    this.meshGroup.add(p2Mesh);

    // 2. VIGA PRINCIPAL (Segmentada para curva da deformada elástica)
    const segments = 24;
    const maxDeflM = (parseFloat(p.max_deflection_mm) || 50.0) / 1000.0;
    const effectiveDefl = (this.activeVariant > 0) ? (maxDeflM * 0.25) : maxDeflM; // Redesign reduz flecha
    const ampDefl = effectiveDefl * this.amplification;

    for (let i = 0; i < segments; i++) {
      const x0 = (i / segments) * span;
      const x1 = ((i + 1) / segments) * span;
      const dx = x1 - x0;
      const xm = (x0 + x1) / 2;

      // Parábola da flecha: f(x) = (4 * f_max / L^2) * x * (L - x)
      const dy = -(4 * ampDefl / (span * span)) * xm * (span - xm);
      const stressRatio = (4 / (span * span)) * xm * (span - xm);

      let segMat = beamMat;
      if (this.currentMode === 'stress') {
        const stressColor = this.getStressColor(stressRatio);
        segMat = this.createMaterial(stressColor, 1.0);
      }

      const segGeom = new THREE.BoxGeometry(dx * 1.02, bh, bw);
      const segMesh = new THREE.Mesh(segGeom, segMat);
      segMesh.position.set(xm, ch - (bh / 2) + dy, 0);
      segMesh.castShadow = true;
      segMesh.receiveShadow = true;
      this.meshGroup.add(segMesh);
    }

    // 3. LAJE DE COBERTURA / PISO SUPERIOR
    const slabDepth = 5.0;
    const slabThick = 0.12;
    const slabGeom = new THREE.BoxGeometry(span + cant + 1.0, slabThick, slabDepth);
    const slabMesh = new THREE.Mesh(slabGeom, slabMat);
    slabMesh.position.set((span + cant) / 2, ch + (slabThick / 2), slabDepth / 2 - 0.5);
    slabMesh.castShadow = true;
    slabMesh.receiveShadow = true;
    this.meshGroup.add(slabMesh);

    // 4. BALANÇO (se houver)
    if (cant > 0) {
      const cantGeom = new THREE.BoxGeometry(cant, bh, bw);
      const cantMesh = new THREE.Mesh(cantGeom, beamMat);
      cantMesh.position.set(span + (cant / 2), ch - (bh / 2), 0);
      cantMesh.castShadow = true;
      this.meshGroup.add(cantMesh);
    }

    // 5. CUSTOMIZAÇÃO VISUAL POR ALTERNATIVA DE REDESIGN
    this.renderVariantSpecifics(span, ch, bh, bw, cant);
  }

  renderVariantSpecifics(span, ch, bh, bw, cant) {
    if (this.activeVariant === 1) {
      // OPÇÃO 01: PROTENSÃO ATIVA (Cabo parabólico interno visível)
      const tendonPoints = [];
      for (let i = 0; i <= 20; i++) {
        const xi = (i / 20) * span;
        const tendonSag = 0.20; // 20cm de flecha contrária ascendente
        const yi = ch - 0.05 - (4 * tendonSag / (span * span)) * xi * (span - xi);
        tendonPoints.push(new THREE.Vector3(xi, yi, 0));
      }
      const tendonGeom = new THREE.BufferGeometry().setFromPoints(tendonPoints);
      const tendonLine = new THREE.Line(tendonGeom, new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 4 }));
      this.meshGroup.add(tendonLine);

    } else if (this.activeVariant === 2) {
      // OPÇÃO 02: EXOESQUELETO VIERENDEEL (Estrutura superior treliçada sem diagonais)
      const trussHeight = 2.8;
      const topChordGeom = new THREE.BoxGeometry(span, 0.25, bw);
      const topChord = new THREE.Mesh(topChordGeom, this.createMaterial(0x38bdf8, 0.9));
      topChord.position.set(span / 2, ch + trussHeight, 0);
      this.meshGroup.add(topChord);

      // Montantes verticais Vierendeel
      const numPosts = 5;
      for (let i = 0; i <= numPosts; i++) {
        const xp = (i / numPosts) * span;
        const postGeom = new THREE.BoxGeometry(0.2, trussHeight, bw);
        const post = new THREE.Mesh(postGeom, this.createMaterial(0x0284c7, 0.9));
        post.position.set(xp, ch + (trussHeight / 2), 0);
        this.meshGroup.add(post);
      }

    } else if (this.activeVariant === 3) {
      // OPÇÃO 03: BALANÇO ATIRANTADO COM PILARES EM V
      const mastHeight = 4.5;
      // Mastro de ancoragem acima do pilar P1
      const mastGeom = new THREE.CylinderGeometry(0.08, 0.08, mastHeight);
      const mast = new THREE.Mesh(mastGeom, this.createMaterial(0xd97706, 1.0));
      mast.position.set(0, ch + (mastHeight / 2), 0);
      this.meshGroup.add(mast);

      // Tirantes de aço ASTM A572 conectando ao centro e ao balanço
      const cablePts1 = [new THREE.Vector3(0, ch + mastHeight, 0), new THREE.Vector3(span * 0.55, ch, 0)];
      const cLine1 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts1), new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 3 }));
      this.meshGroup.add(cLine1);

      if (cant > 0) {
        const cablePts2 = [new THREE.Vector3(0, ch + mastHeight, 0), new THREE.Vector3(span + cant, ch, 0)];
        const cLine2 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts2), new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 3 }));
        this.meshGroup.add(cLine2);
      }

    } else if (this.activeVariant === 4) {
      // OPÇÃO 04: GRELHA NERVURADA WAFFLE (Nervuras cruzadas e cubetas)
      const waffleMat = this.createMaterial(0x818cf8, 0.85);
      const ribs = 6;
      for (let r = 1; r < ribs; r++) {
        const xr = (r / ribs) * span;
        const ribGeom = new THREE.BoxGeometry(0.12, 0.35, 4.5);
        const rib = new THREE.Mesh(ribGeom, waffleMat);
        rib.position.set(xr, ch - 0.15, 2.25);
        this.meshGroup.add(rib);
      }

    } else if (this.activeVariant === 5) {
      // OPÇÃO 05: ARCO FUNICULAR CATENÁRIO (Gaudí)
      const archPoints = [];
      const archHeight = 1.4;
      for (let i = 0; i <= 24; i++) {
        const xi = (i / 24) * span;
        // Curva parabólica ascendente do arco: y = h * 4 * x * (L - x) / L^2
        const yi = (4 * archHeight / (span * span)) * xi * (span - xi);
        archPoints.push(new THREE.Vector3(xi, yi + 0.1, 0));
      }
      const archGeom = new THREE.BufferGeometry().setFromPoints(archPoints);
      const archLine = new THREE.Line(archGeom, new THREE.LineBasicMaterial({ color: 0x10b981, linewidth: 5 }));
      this.meshGroup.add(archLine);
    }
  }

  createMaterial(colorHex, opacity = 1.0) {
    if (this.currentMode === 'wireframe') {
      return new THREE.MeshBasicMaterial({ color: colorHex, wireframe: true });
    } else if (this.currentMode === 'xray') {
      return new THREE.MeshStandardMaterial({
        color: colorHex,
        roughness: 0.2,
        metalness: 0.1,
        transparent: true,
        opacity: 0.45,
      });
    } else {
      // shaded ou stress
      return new THREE.MeshStandardMaterial({
        color: colorHex,
        roughness: 0.4,
        metalness: 0.2,
        transparent: opacity < 1.0,
        opacity: opacity,
      });
    }
  }

  getStressColor(ratio) {
    // 0.0 (Azul/Verde seguro) -> 0.5 (Amarelo) -> 1.0 (Vermelho crítico)
    if (ratio < 0.4) {
      return 0x10b981; // Verde seguro
    } else if (ratio < 0.75) {
      return 0xf59e0b; // Amarelo atenção
    } else {
      return 0xef4444; // Vermelho tensão crítica
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (this.controls) this.controls.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }
}

// Exportar globalmente
window.Structura3DViewport = Structura3DViewport;
