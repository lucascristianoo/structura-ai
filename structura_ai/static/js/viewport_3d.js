/**
 * Structura.AI — Interactive 3D WebGL Viewport (Three.js)
 * Reads scene, grid, and structural element colors directly from theme.css tokens.
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
    this.activeVariant = 0;
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
      accent: css('--three-accent', '#1e4b85'),
      cable: css('--three-cable', '#a16207')
    };
  }

  init() {
    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 450;

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
      this.controls.minDistance = 3;
      this.controls.maxDistance = 60;
      this.controls.target.set(5, 1.8, 0);
    }

    this.applySceneTheme();

    // Neutral Architectural Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.72);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.82);
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
      this.rebuildScene();
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
      30,
      30,
      new THREE.Color(tc.gridMain),
      new THREE.Color(tc.gridSub)
    );
    this.gridHelper.position.y = 0;
    this.scene.add(this.gridHelper);
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
    this.currentParams = {
      ...this.currentParams,
      ...params,
      max_deflection_mm: params.max_deflection_mm ?? params.deflection_mm ?? 50.0
    };
    this.rebuildScene();
  }

  updateGeometry(params) {
    this.updateFromParams(params);
  }

  rebuildScene() {
    while (this.meshGroup.children.length > 0) {
      const obj = this.meshGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
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
      is_viable: false
    };

    const span = parseFloat(p.span_length_m) || 10.0;
    const cant = parseFloat(p.cantilever_length_m) || 0.0;
    const bh = (parseFloat(p.beam_height_cm) || 30.0) / 100.0;
    const bw = (parseFloat(p.beam_width_cm) || 20.0) / 100.0;
    const ch = parseFloat(p.column_height_m) || 3.2;
    const cw = (parseFloat(p.column_section_cm) || 20.0) / 100.0;
    const cd = cw * 2.0;

    if (this.controls) {
      this.controls.target.set(span / 2, ch / 2, 0);
    }

    const tc = this.getThemeColors();
    const colMat = this.createMaterial(new THREE.Color(tc.col), 0.92);
    const beamBaseColor = new THREE.Color(p.is_viable || this.activeVariant > 0 ? tc.beamOk : tc.beamFail);
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
    const effectiveDefl = this.activeVariant > 0 ? maxDeflM * 0.25 : maxDeflM;
    const ampDefl = effectiveDefl * this.amplification;

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
      const cantGeom = new THREE.BoxGeometry(cant, bh, bw);
      const cantMesh = new THREE.Mesh(cantGeom, beamMat);
      cantMesh.position.set(span + cant / 2, ch - bh / 2, 0);
      cantMesh.castShadow = true;
      this.meshGroup.add(cantMesh);
    }

    // 5. Structural Variant Specifics
    this.renderVariantSpecifics(span, ch, bh, bw, cant, tc);
  }

  renderVariantSpecifics(span, ch, bh, bw, cant, tc) {
    const accentColor = new THREE.Color(tc.accent);
    const cableColor = new THREE.Color(tc.cable);
    const colColor = new THREE.Color(tc.col);

    if (this.activeVariant === 1) {
      const tendonPoints = [];
      for (let i = 0; i <= 20; i++) {
        const xi = (i / 20) * span;
        const tendonSag = 0.2;
        const yi = ch - 0.05 - (4 * tendonSag / (span * span)) * xi * (span - xi);
        tendonPoints.push(new THREE.Vector3(xi, yi, 0));
      }
      const tendonGeom = new THREE.BufferGeometry().setFromPoints(tendonPoints);
      const tendonLine = new THREE.Line(tendonGeom, new THREE.LineBasicMaterial({ color: cableColor, linewidth: 3 }));
      this.meshGroup.add(tendonLine);
    } else if (this.activeVariant === 2) {
      const trussHeight = 2.8;
      const topChordGeom = new THREE.BoxGeometry(span, 0.25, bw);
      const topChord = new THREE.Mesh(topChordGeom, this.createMaterial(colColor, 0.92));
      topChord.position.set(span / 2, ch + trussHeight, 0);
      this.meshGroup.add(topChord);

      const numPosts = 5;
      for (let i = 0; i <= numPosts; i++) {
        const xp = (i / numPosts) * span;
        const postGeom = new THREE.BoxGeometry(0.2, trussHeight, bw);
        const post = new THREE.Mesh(postGeom, this.createMaterial(accentColor, 0.92));
        post.position.set(xp, ch + trussHeight / 2, 0);
        this.meshGroup.add(post);
      }
    } else if (this.activeVariant === 3) {
      const mastHeight = 4.5;
      const mastGeom = new THREE.CylinderGeometry(0.08, 0.08, mastHeight);
      const mast = new THREE.Mesh(mastGeom, this.createMaterial(colColor, 1.0));
      mast.position.set(0, ch + mastHeight / 2, 0);
      this.meshGroup.add(mast);

      const cablePts1 = [new THREE.Vector3(0, ch + mastHeight, 0), new THREE.Vector3(span * 0.55, ch, 0)];
      const cLine1 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts1), new THREE.LineBasicMaterial({ color: cableColor, linewidth: 2 }));
      this.meshGroup.add(cLine1);

      if (cant > 0) {
        const cablePts2 = [new THREE.Vector3(0, ch + mastHeight, 0), new THREE.Vector3(span + cant, ch, 0)];
        const cLine2 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts2), new THREE.LineBasicMaterial({ color: cableColor, linewidth: 2 }));
        this.meshGroup.add(cLine2);
      }
    } else if (this.activeVariant === 4) {
      const waffleMat = this.createMaterial(colColor, 0.88);
      const ribs = 6;
      for (let r = 1; r < ribs; r++) {
        const xr = (r / ribs) * span;
        const ribGeom = new THREE.BoxGeometry(0.12, 0.35, 4.5);
        const rib = new THREE.Mesh(ribGeom, waffleMat);
        rib.position.set(xr, ch - 0.15, 2.25);
        this.meshGroup.add(rib);
      }
    } else if (this.activeVariant === 5) {
      const archPoints = [];
      const archHeight = 1.4;
      for (let i = 0; i <= 24; i++) {
        const xi = (i / 24) * span;
        const yi = (4 * archHeight / (span * span)) * xi * (span - xi);
        archPoints.push(new THREE.Vector3(xi, yi + 0.1, 0));
      }
      const archGeom = new THREE.BufferGeometry().setFromPoints(archPoints);
      const archLine = new THREE.Line(archGeom, new THREE.LineBasicMaterial({ color: accentColor, linewidth: 4 }));
      this.meshGroup.add(archLine);
    }
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
