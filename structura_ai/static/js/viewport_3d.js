/**
 * Structura.AI — Interactive 3D WebGL Viewport (Three.js)
 * Reads scene, grid, and structural element colors directly from theme.css tokens.
 * Supports parametric structural frames, CAD/BIM elements, and imported 3D meshes (OBJ/glTF/STL).
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
    this.currentMode = 'shaded';
    this.amplification = 25.0;
    this.currentParams = null;

    this.init();
  }

  getThemeColors() {
    const css = (name, fallback) => {
      const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return val || fallback;
    };
    return {
      bg: css('--three-bg', '#fafafa'),
      gridMain: css('--three-grid-main', '#a1a1aa'),
      gridSub: css('--three-grid-sub', '#e4e4e7'),
      col: css('--three-col', '#52525b'),
      slab: css('--three-slab', '#d4d4d8'),
      beamOk: css('--three-beam-ok', '#1e4b85'),
      beamFail: css('--three-beam-fail', '#b91c1c'),
      accent: css('--three-accent', '#1e4b85')
    };
  }

  init() {
    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 420;

    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.camera.position.set(14, 8, 16);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    if (typeof THREE.OrbitControls !== 'undefined') {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.maxPolarAngle = Math.PI / 2 + 0.05;
      this.controls.minDistance = 2;
      this.controls.maxDistance = 80;
      this.controls.target.set(5, 1.8, 0);
    }

    this.applySceneTheme();

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight.position.set(15, 25, 20);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    this.scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(0xe4e4e7, 0.3);
    rimLight.position.set(-15, 10, -10);
    this.scene.add(rimLight);

    this.scene.add(this.meshGroup);

    window.addEventListener('resize', () => this.onResize());
    window.addEventListener('structura:themechange', () => {
      this.applySceneTheme();
      if (this.currentParams) {
        this.rebuildScene();
      }
    });

    this.animate();
  }

  applySceneTheme() {
    if (!this.scene) return;
    const tc = this.getThemeColors();
    this.scene.background = new THREE.Color(tc.bg);

    if (this.gridHelper) {
      this.scene.remove(this.gridHelper);
      if (this.gridHelper.geometry) this.gridHelper.geometry.dispose();
      if (this.gridHelper.material) {
        if (Array.isArray(this.gridHelper.material)) {
          this.gridHelper.material.forEach((m) => m.dispose());
        } else {
          this.gridHelper.material.dispose();
        }
      }
    }
    this.gridHelper = new THREE.GridHelper(
      36,
      36,
      new THREE.Color(tc.gridMain),
      new THREE.Color(tc.gridSub)
    );
    this.gridHelper.position.y = 0;
    this.scene.add(this.gridHelper);
  }

  onResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight || 420;
    if (width <= 0 || height <= 0) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  setShadingMode(mode) {
    this.currentMode = mode;
    if (this.currentParams) {
      this.rebuildScene();
    }
  }

  resetCamera() {
    if (!this.camera || !this.controls) return;
    const p = this.currentParams || {};
    const span = parseFloat(p.span_length_m) || 10.0;
    const cant = parseFloat(p.cantilever_length_m) || 0.0;
    const ch = parseFloat(p.column_height_m) || 3.2;
    const totalX = Math.max(span + cant, 6.0);

    const centerX = totalX / 2.0;
    const centerY = ch / 2.0;
    const dist = Math.max(totalX * 1.35, 11.0);

    this.camera.position.set(centerX + dist * 0.72, ch + dist * 0.48, dist * 0.95);
    this.controls.target.set(centerX, centerY, 0);
    this.controls.update();
  }

  updateFromParams(params, { fitCamera = false } = {}) {
    this.currentParams = {
      ...this.currentParams,
      ...params,
      max_deflection_mm: params.max_deflection_mm ?? params.deflection_mm ?? 50.0
    };
    this.rebuildScene();
    if (fitCamera) {
      this.resetCamera();
    }
  }

  updateGeometry(params, opts) {
    this.updateFromParams(params, opts);
  }

  clearMeshGroup() {
    while (this.meshGroup.children.length > 0) {
      const obj = this.meshGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
        else obj.material.dispose();
      }
      this.meshGroup.remove(obj);
    }
  }

  rebuildScene() {
    this.clearMeshGroup();
    if (!this.currentParams) return;

    const p = this.currentParams;
    const tc = this.getThemeColors();

    // If an imported 3D surface mesh (OBJ/glTF/STL) has vertices & faces, render it directly
    const cadMesh = p.cad_mesh;
    if (
      cadMesh &&
      Array.isArray(cadMesh.vertices) &&
      cadMesh.vertices.length >= 3 &&
      Array.isArray(cadMesh.faces) &&
      cadMesh.faces.length >= 1
    ) {
      this.renderImportedTrimesh(cadMesh, p, tc);
      return;
    }

    const span = parseFloat(p.span_length_m) || 10.0;
    const cant = parseFloat(p.cantilever_length_m) || 0.0;
    const bh = (parseFloat(p.beam_height_cm) || 30.0) / 100.0;
    const bw = (parseFloat(p.beam_width_cm) || 20.0) / 100.0;
    const ch = parseFloat(p.column_height_m) || 3.2;
    const cw = (parseFloat(p.column_section_cm) || 20.0) / 100.0;
    const cd = cw * 2.0;

    const colMat = this.createMaterial(new THREE.Color(tc.col), 0.92);
    const beamBaseColor = new THREE.Color(p.is_viable ? tc.beamOk : tc.beamFail);
    const beamMat = this.createMaterial(beamBaseColor, 0.95);
    const slabMat = this.createMaterial(new THREE.Color(tc.slab), 0.85);

    // 1. Columns
    const colGeom = new THREE.BoxGeometry(cw, ch, cd);
    const p1Mesh = new THREE.Mesh(colGeom, colMat);
    p1Mesh.position.set(0, ch / 2, 0);
    p1Mesh.castShadow = true;
    p1Mesh.receiveShadow = true;
    this.meshGroup.add(p1Mesh);

    const p2Mesh = new THREE.Mesh(colGeom, colMat);
    p2Mesh.position.set(span, ch / 2, 0);
    p2Mesh.castShadow = true;
    p2Mesh.receiveShadow = true;
    this.meshGroup.add(p2Mesh);

    // 2. Segmented Primary Beam (Elastic Deflection Curve)
    const segments = 24;
    const maxDeflM = (parseFloat(p.max_deflection_mm) || 50.0) / 1000.0;
    const ampDefl = Math.min(maxDeflM * this.amplification, ch * 0.45);

    for (let i = 0; i < segments; i++) {
      const x0 = (i / segments) * span;
      const x1 = ((i + 1) / segments) * span;
      const dx = x1 - x0;
      const xm = (x0 + x1) / 2;

      const dy = -(4 * ampDefl / (span * span)) * xm * (span - xm);
      const stressRatio = (4 / (span * span)) * xm * (span - xm);

      let segMat = beamMat;
      if (this.currentMode === 'stress') {
        segMat = this.createMaterial(this.getStressColor(stressRatio), 1.0);
      }

      const segGeom = new THREE.BoxGeometry(dx * 1.02, bh, bw);
      const segMesh = new THREE.Mesh(segGeom, segMat);
      segMesh.position.set(xm, ch - bh / 2 + dy, 0);
      segMesh.castShadow = true;
      segMesh.receiveShadow = true;
      this.meshGroup.add(segMesh);
    }

    // 3. Upper Slab
    const slabDepth = 5.0;
    const slabThick = 0.12;
    const slabGeom = new THREE.BoxGeometry(span + cant + 1.0, slabThick, slabDepth);
    const slabMesh = new THREE.Mesh(slabGeom, slabMat);
    slabMesh.position.set((span + cant) / 2, ch + slabThick / 2, slabDepth / 2 - 0.5);
    slabMesh.castShadow = true;
    slabMesh.receiveShadow = true;
    this.meshGroup.add(slabMesh);

    // 4. Cantilever
    if (cant > 0) {
      let cantMat = beamMat;
      if (this.currentMode === 'stress') {
        cantMat = this.createMaterial(this.getStressColor(0.85), 1.0);
      }
      const cantGeom = new THREE.BoxGeometry(cant, bh, bw);
      const cantMesh = new THREE.Mesh(cantGeom, cantMat);
      cantMesh.position.set(span + cant / 2, ch - bh / 2, 0);
      cantMesh.castShadow = true;
      this.meshGroup.add(cantMesh);
    }
  }

  renderImportedTrimesh(cadMesh, p, tc) {
    const positions = [];
    const colors = [];

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    // Convert CAD Z-up or Y-up cleanly and find bounds
    const verts = cadMesh.vertices;
    for (let i = 0; i < verts.length; i++) {
      const vx = verts[i][0] || 0;
      const vy = verts[i][2] !== undefined ? verts[i][2] : (verts[i][1] || 0);
      const vz = verts[i][2] !== undefined ? -(verts[i][1] || 0) : 0;
      if (vx < minX) minX = vx;
      if (vx > maxX) maxX = vx;
      if (vy < minY) minY = vy;
      if (vy > maxY) maxY = vy;
      if (vz < minZ) minZ = vz;
      if (vz > maxZ) maxZ = vz;
    }

    const spanX = Math.max(maxX - minX, 0.1);
    const centerZ = (minZ + maxZ) / 2.0;

    for (let f = 0; f < cadMesh.faces.length; f++) {
      const face = cadMesh.faces[f];
      if (!face || face.length < 3) continue;
      for (let k = 0; k < 3; k++) {
        const idx = face[k];
        const v = verts[idx] || [0, 0, 0];
        const x = (v[0] || 0) - minX;
        const y = (v[2] !== undefined ? v[2] : (v[1] || 0)) - minY;
        const z = (v[2] !== undefined ? -(v[1] || 0) : 0) - centerZ;
        positions.push(x, y, z);

        const normX = Math.min(Math.max(x / spanX, 0), 1);
        const stressRatio = 4 * normX * (1 - normX);
        const c = new THREE.Color(this.getStressColor(stressRatio));
        colors.push(c.r, c.g, c.b);
      }
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    if (this.currentMode === 'stress') {
      geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    }
    geom.computeVertexNormals();

    let mat;
    if (this.currentMode === 'stress') {
      mat = new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.45,
        metalness: 0.1,
        side: THREE.DoubleSide
      });
    } else {
      const baseCol = new THREE.Color(p.is_viable ? tc.beamOk : tc.accent);
      mat = this.createMaterial(baseCol, 0.94);
      mat.side = THREE.DoubleSide;
    }

    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    this.meshGroup.add(mesh);
  }

  createMaterial(colorVal, opacity = 1.0) {
    if (this.currentMode === 'wireframe') {
      return new THREE.MeshBasicMaterial({ color: colorVal, wireframe: true });
    } else if (this.currentMode === 'xray') {
      return new THREE.MeshStandardMaterial({
        color: colorVal,
        roughness: 0.3,
        metalness: 0.1,
        transparent: true,
        opacity: 0.45
      });
    }
    return new THREE.MeshStandardMaterial({
      color: colorVal,
      roughness: 0.5,
      metalness: 0.15,
      transparent: opacity < 1.0,
      opacity: opacity
    });
  }

  getStressColor(ratio) {
    if (ratio < 0.4) {
      return 0x156d4d;
    } else if (ratio < 0.75) {
      return 0xa16207;
    }
    return 0xb91c1c;
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (this.controls) this.controls.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }
}

window.Structura3DViewport = Structura3DViewport;
