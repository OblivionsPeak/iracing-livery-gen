// Available Designs Map
const DESIGNS = [
  {id:'solid', name:'Solid', svg:'<svg><rect width="24" height="24" fill="currentColor"/></svg>'},
  {id:'racing_stripes', name:'Stripes', svg:'<svg><rect width="24" height="24" fill="currentColor" fill-opacity="0.2"/><path d="M8 0h3v24H8zM13 0h3v24h-3z"/></svg>'},
  {id:'diagonal_stripes', name:'Diagonal', svg:'<svg><rect width="24" height="24" fill="currentColor" fill-opacity="0.2"/><path d="M0 16L16 0h8L0 24z"/></svg>'},
  {id:'gradient', name:'Gradient', svg:'<svg><defs><linearGradient id="g1"><stop offset="0%" stop-color="currentColor"/><stop offset="100%" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><rect width="24" height="24" fill="url(#g1)"/></svg>'},
  {id:'sweep', name:'GT Sweep', svg:'<svg><path d="M0 16l12-8h12v6l-12 10H0z"/></svg>'},
  {id:'split', name:'Split', svg:'<svg><rect y="6" width="24" height="12"/></svg>'},
  {id:'chevron', name:'Chevron', svg:'<svg><path d="M0 0l12 12L0 24h6l12-12L6 0z"/></svg>'},
  {id:'two_tone', name:'Two-Tone', svg:'<svg><path d="M0 24L24 0v24z"/></svg>'},
  {id:'gradient_chevron', name:'Grad Chev', svg:'<svg><path d="M0 0l10 10v4L0 24z" fill-opacity="0.5"/><path d="M0 4l6 8-6 8z"/></svg>'},
  {id:'radial_gradient', name:'Radial', svg:'<svg><circle cx="12" cy="12" r="10" fill="currentColor" fill-opacity="0.5"/></svg>'},
  {id:'harlequin', name:'Harlequin', svg:'<svg><path d="M12 0l6 6-6 6-6-6z M12 12l6 6-6 6-6-6z M0 6l6 6-6 6-6-6z M24 6l-6 6-6-6 6-6z"/></svg>'},
  {id:'pinstripe', name:'Pinstripe', svg:'<svg><path d="M0 20L20 0h2L0 22zM0 10L10 0h2L0 12z" /></svg>'},
  {id:'checkered', name:'Checkered', svg:'<svg><rect x="0" y="0" width="6" height="6" fill="currentColor"/><rect x="12" y="0" width="6" height="6" fill="currentColor"/><rect x="6" y="6" width="6" height="6" fill="currentColor"/><rect x="18" y="6" width="6" height="6" fill="currentColor"/><rect x="0" y="12" width="6" height="6" fill="currentColor"/><rect x="12" y="12" width="6" height="6" fill="currentColor"/><rect x="6" y="18" width="6" height="6" fill="currentColor"/><rect x="18" y="18" width="6" height="6" fill="currentColor"/></svg>'},
  {id:'hexagon', name:'Honeycomb', svg:'<svg><path d="M9 2l4 0 2 3.5-2 3.5-4 0-2-3.5z M15 9l4 0 2 3.5-2 3.5-4 0-2-3.5z M3 9l4 0 2 3.5-2 3.5-4 0-2-3.5z M9 16l4 0 2 3.5-2 3.5-4 0-2-3.5z" fill="currentColor" fill-opacity="0.7"/></svg>'},
  {id:'shard', name:'Shard', svg:'<svg><path d="M12 2 L22 12 L12 22 L2 12 Z M12 2 L8 8 L12 14 L16 8 Z" fill="currentColor" fill-opacity="0.7"/></svg>'},
  {id:'tearing', name:'Tearing', svg:'<svg><path d="M2 12 L8 10 L6 8 L12 6 L10 12 L18 10 L16 14 L22 12 L18 20 L4 18 Z" fill="currentColor"/></svg>'},
  {id:'digital_camo', name:'Digi-Camo', svg:'<svg><rect x="2" y="2" width="6" height="6" fill="currentColor"/><rect x="10" y="6" width="6" height="6" fill="currentColor" fill-opacity="0.6"/><rect x="4" y="12" width="8" height="8" fill="currentColor" fill-opacity="0.4"/><rect x="16" y="14" width="6" height="6" fill="currentColor"/></svg>'},
  {id:'speed_blur', name:'Speed Blur', svg:'<svg><path d="M2 6h14M4 12h18M2 18h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'},
  {id:'topographic', name:'Topo', svg:'<svg><path d="M12 2c-5 0-9 4-9 9s4 9 9 9 9-4 9-9-4-9-9-9zm0 16c-3.9 0-7-3.1-7-7s3.1-7 7-7 7 3.1 7 7-3.1 7-7 7z" fill="none" stroke="currentColor" stroke-width="1"/><path d="M12 6c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5z" fill="currentColor" fill-opacity="0.3"/></svg>'},
  {id:'circuit', name:'Circuit', svg:'<svg><path d="M4 4h8v8h8M4 12h8v8M18 4v4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="4" cy="4" r="2" fill="currentColor"/><circle cx="20" cy="12" r="2" fill="currentColor"/></svg>'},
  {id:'splatter', name:'Splatter', svg:'<svg><path d="M12 4c-4 0-4 4-8 4s-2 4 2 6-2 6 6 6 6-2 8-6-2-10-8-10z" fill="currentColor"/><circle cx="4" cy="16" r="1" fill="currentColor"/><circle cx="20" cy="8" r="1.5" fill="currentColor"/></svg>'},
  {id:'sunburst', name:'Sunburst', svg:'<svg><path d="M12 12L0 6M12 12L6 0M12 12L18 0M12 12L24 6M12 12L24 18M12 12L18 24M12 12L6 24M12 12L0 18" stroke="currentColor" stroke-width="1.5"/></svg>'}
];

document.addEventListener('alpine:init', () => {
    Alpine.data('liveryEditor', () => ({
        designs: DESIGNS,
        activeCar: null,
        
        // UI State
        dropZoneActive: false,
        logoZoneActive: false,
        templateStatus: '',
        statusMsg: '',
        statusError: false,
        isBuilding: false,
        previewClean: null,
        previewBaked: null,
        timestamp: Date.now(),
        viewMode: '2d',
        toastMsg: '',
        toastTimer: null,
        
        // Three.js State
        threeInit: false,
        threeScene: null,
        threeRenderer: null,
        threeMaterial: null,
        threeControls: null,
        threeCarMesh: null,

        // Abort controller for in-flight builds
        _buildController: null,

        // True when running locally — enables direct iRacing export
        isLocalhost: location.hostname === 'localhost' || location.hostname === '127.0.0.1',

        // Named saves
        savedDesigns: [],
        showSavesPanel: false,
        saveNameInput: '',

        // Core Config State
        history: [],
        historyIndex: -1,
        isUndoing: false,
        
        config: {
            carId: 'custom',
            customerId: '0',
            carNumber: '42',
            primary: '#111111',
            secondary: '#e63946',
            accent: '#ffd700',
            texture: 'none',
            texture_opacity: 25,
            template_opacity: 35,
            grunge_amount: 0,
            base_metallic: 0.05,
            base_roughness: 0.15,
            layers: [
                { type: 'design', id: 'solid', metallic: 0.1, roughness: 0.5, params: { scale: 1.0, x: 50, y: 50 }, visible: true, collapsed: false }
            ]
        },

        init() {
            this.loadSavedDesigns();

            // 1. Try URL load
            const param = new URLSearchParams(location.search).get('c');
            if (param) {
                try {
                    const urlCfg = JSON.parse(decodeURIComponent(escape(atob(param))));
                    Object.assign(this.config, urlCfg);
                    this.showToast('Loaded config from URL link.');
                } catch(e) { console.error('URL config decode failed'); }
            } else {
                // 2. Try LocalStorage
                const saved = localStorage.getItem('iRacingLiveryConfig');
                if (saved) {
                    try {
                        Object.assign(this.config, JSON.parse(saved));
                    } catch(e) {}
                }
                // Restore activeCar separately
                const savedCar = localStorage.getItem('iRacingActiveCar');
                if (savedCar) {
                    this.activeCar = savedCar;
                    this.templateStatus = `✓ Template ready (${this.activeCar})`;
                    // Trigger a build — will show error if template is gone from server
                    this.$nextTick(() => this.triggerBuild(false));
                }
            }

            // Initialize Three.js scene dynamically when DOM is ready
            this.$watch('viewMode', (val) => {
                if (val === '3d') {
                    this.$nextTick(() => {
                        if (!this.threeInit) this.initThreeJS();
                        if (this.previewBaked) this.updateThreeTexture();
                    });
                }
            });
            
            // Material finish live updates to 3D
            this.$watch('config.base_metallic', (v) => this.threeMaterial && (this.threeMaterial.metalness = v));
            this.$watch('config.base_roughness', (v) => this.threeMaterial && (this.threeMaterial.roughness = v));
            this.$watch('config.texture', () => {
                 if(this.viewMode === '3d') this.updateThreeMaterialProps && this.updateThreeMaterialProps();
            });

            // Setup Sortable
            this.$nextTick(() => {
                this.initSortable();
            });

            // Initial trigger if we have a car
            if (this.activeCar) this.triggerBuild(false);
        },

        initSortable() {
            const list = document.getElementById('layers-list');
            if (!list || !window.Sortable) return;
            
            window.Sortable.create(list, {
                handle: '.layer-drag-handle',
                animation: 150,
                onEnd: (evt) => {
                    // Alpine array is reversed in the UI (flex-direction: column-reverse)
                    const domesticCount = this.config.layers.length;
                    const oldIdx = domesticCount - 1 - evt.oldIndex;
                    const newIdx = domesticCount - 1 - evt.newIndex;
                    
                    const moved = this.config.layers.splice(oldIdx, 1)[0];
                    this.config.layers.splice(newIdx, 0, moved);
                    this.markChanged();
                }
            });
        },

        applyMaterialPreset(preset) {
            const presets = {
                'matte':  { m: 0.0,  r: 0.90 },
                'satin':  { m: 0.10, r: 0.45 },
                'chrome': { m: 1.0,  r: 0.05 },
                'gloss':  { m: 0.05, r: 0.10 },
                'gold':   { m: 0.9,  r: 0.20 }
            };
            const p = presets[preset];
            if (!p) return;
            this.config.base_metallic = p.m;
            this.config.base_roughness = p.r;
            this.markChanged();
            this.showToast(`Applied ${preset.toUpperCase()} finish.`);
        },

        markChanged() {
            // Live Sync Mirroring Logic
            this.config.layers.forEach((layer, idx) => {
                if (layer.mirror && layer.mirror !== 'none' && !layer._isMirror) {
                    let sibling = this.config.layers.find(l => l._parentIdx === idx);
                    if (!sibling) {
                        sibling = JSON.parse(JSON.stringify(layer));
                        sibling._parentIdx = idx;
                        sibling._isMirror = true;
                        this.config.layers.push(sibling);
                    }
                    sibling.metallic = layer.metallic;
                    sibling.roughness = layer.roughness;
                    sibling.opacity = layer.opacity || 1.0;
                    sibling.params.scale = layer.params.scale;
                    sibling.params.y = layer.params.y;
                    if (layer.mirror === 'horizontal') {
                        sibling.params.x = 100 - layer.params.x;
                    }
                }
            });

            // Cleanup: Remove mirrors whose parents are gone
            this.config.layers = this.config.layers.filter(l => {
                if (!l._isMirror) return true;
                const parent = this.config.layers[l._parentIdx];
                return parent && !parent._isMirror && parent.mirror !== 'none';
            });

            this.saveConfig();
            if (this.activeCar) this.triggerBuild(false);
            
            if (!this.isUndoing) {
                if (this.historyIndex < this.history.length - 1) {
                    this.history.splice(this.historyIndex + 1);
                }
                this.history.push(JSON.stringify(this.config));
                if (this.history.length > 30) this.history.shift();
                this.historyIndex = this.history.length - 1;
            }
        },

        saveConfig() {
            localStorage.setItem('iRacingLiveryConfig', JSON.stringify(this.config));
        },

        async triggerBuild(isManual) {
            if (!this.activeCar) return;
            if (this._buildController) this._buildController.abort();
            this._buildController = new AbortController();

            if (isManual) {
                this.isBuilding = true;
                this.statusMsg = '';
            }
            try {
                const r = await fetch('/build', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.getPayload()),
                    signal: this._buildController.signal
                });
                const d = await r.json();
                if (d.error) throw new Error(d.error);
                this.previewClean = d.image_clean;
                this.previewBaked = d.image_baked;
                this.timestamp = Date.now() + "_" + Math.floor(Math.random() * 100000);
                this.statusError = false;
                if (this.threeInit) this.updateThreeTexture();
            } catch(e) {
                if (e.name === 'AbortError') return;
                this.statusError = true;
                this.statusMsg = 'Build failed: ' + e.message;
                if (e.message.includes('Template not uploaded')) {
                    this.activeCar = null;
                    localStorage.removeItem('iRacingActiveCar');
                    this.templateStatus = '';
                    this.showToast('Template missing — please re-upload your car template.');
                } else {
                    this.showToast('Build error: ' + e.message);
                }
            } finally {
                if (isManual) this.isBuilding = false;
            }
        },

        getPayload() {
            return {
                car_id: this.activeCar || (this.config.carId !== 'custom' ? this.config.carId : 'custom'),
                customer_id: this.config.customerId,
                primary: this.config.primary,
                secondary: this.config.secondary,
                accent: this.config.accent,
                texture: this.config.texture,
                texture_opacity: this.config.texture_opacity / 100,
                template_opacity: this.config.template_opacity / 100,
                grunge_amount: this.config.grunge_amount / 100,
                base_metallic: this.config.base_metallic,
                base_roughness: this.config.base_roughness,
                layers: this.config.layers.filter(l => l.visible !== false)
            };
        },

        addLayer(type, id, params = {}) {
            const defaults = { scale: 1.0, x: 50, y: 50, fade_direction: 'none' };
            if (id === 'tearing') {
                defaults.fill_pattern   = 'solid';
                defaults.fill_primary   = this.config.primary;
                defaults.fill_secondary = this.config.secondary;
                defaults.fill_accent    = this.config.accent;
            }
            if (id === 'gradient')   { defaults.direction = 'horizontal'; defaults.angle = 45; }
            if (id === 'hexagon')    { defaults.tile_size = 40; defaults.style = 'filled'; }
            if (id === 'checkered')  { defaults.tile_size = 64; }
            if (id === 'racing_stripes') { defaults.count = 3; defaults.direction = 'vertical'; }

            const layer = {
                type: type,
                id: id,
                name: '',
                visible: true,
                collapsed: false,
                metallic: 0,
                roughness: 0.2,
                opacity: 1.0,
                mirror: 'none',
                use_custom_colors: false,
                override_primary:   this.config.primary,
                override_secondary: this.config.secondary,
                override_accent:    this.config.accent,
                params: { ...defaults, ...params }
            };
            this.config.layers.push(layer);
            this.markChanged();
        },

        removeLayer(index) {
            this.config.layers.splice(index, 1);
            this.markChanged();
        },

        moveLayer(index, direction) {
            const target = index + direction;
            if (target < 0 || target >= this.config.layers.length) return;
            const layers = this.config.layers;
            [layers[index], layers[target]] = [layers[target], layers[index]];
            this.config.layers = [...layers];
            this.markChanged();
        },

        duplicateLayer(index) {
            const clone = JSON.parse(JSON.stringify(this.config.layers[index]));
            delete clone._isMirror;
            delete clone._parentIdx;
            this.config.layers.splice(index + 1, 0, clone);
            this.markChanged();
        },

        async uploadTemplate(file) {
            if (!file) return;
            this.isBuilding = true;
            this.templateStatus = 'Processing...';
            const form = new FormData();
            form.append('car_id', this.config.carId === 'custom' ? '' : this.config.carId);
            form.append('file', file);
            try {
                const r = await fetch('/upload-template', { method: 'POST', body: form });
                const d = await r.json();
                if (d.error) throw new Error(d.error);
                this.activeCar = d.car_id;
                localStorage.setItem('iRacingActiveCar', this.activeCar);
                this.templateStatus = `✓ Template ready (${this.activeCar})`;
                this.statusError = false;
                this.markChanged();
            } catch(ex) {
                this.templateStatus = 'Upload failed: ' + ex.message;
                this.statusError = true;
            } finally {
                this.isBuilding = false;
            }
        },

        async uploadLogo(file) {
            if (!file) return;
            const form = new FormData();
            form.append('car_id', this.activeCar || this.config.carId);
            form.append('file', file);
            try {
                const r = await fetch('/upload-logo', { method: 'POST', body: form });
                const d = await r.json();
                if (d.error) throw new Error(d.error);
                this.addLayer('logo', d.logo_id, { filename: d.filename, x: 50, y: 50, scale: 25 });
                this.showToast('✓ Decal layer added.');
            } catch(e) {
                this.statusError = true;
                this.statusMsg = 'Upload failed: ' + e.message;
            }
        },

        async exportiRacingZIP() {
            this.isBuilding = true;
            try {
                const r = await fetch('/export-tga', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.getPayload())
                });
                if (!r.ok) throw new Error('Export failed.');
                const blob = await r.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `iracing_${this.config.carId}_${this.config.carNumber}.zip`;
                a.click();
                this.showToast('✓ ZIP Export Complete');
            } catch(e) {
                this.showToast('Export failed.');
            } finally {
                this.isBuilding = false;
            }
        },

        async exportiRacingDirect() {
            if (!this.previewBaked) {
                alert("Please generate a livery first.");
                return;
            }
            this.isBuilding = true;
            try {
                const r = await fetch('/export-to-iracing', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        car_id: this.config.carId !== 'custom' ? this.config.carId : this.activeCar,
                        car_number: this.config.carNumber,
                        filename: this.previewBaked
                    })
                });
                const d = await r.json();
                if (d.error) throw new Error(d.error);
                this.showToast('✓ Exported to iRacing paint folder');
            } catch(e) {
                alert('Direct export failed: ' + e.message);
            } finally {
                this.isBuilding = false;
            }
        },

        loadSavedDesigns() {
            try { this.savedDesigns = JSON.parse(localStorage.getItem('iRacingLiverySaves') || '[]'); }
            catch(e) { this.savedDesigns = []; }
        },

        saveDesignAs() {
            const name = this.saveNameInput.trim();
            if (!name) return;
            this.loadSavedDesigns();
            const idx = this.savedDesigns.findIndex(s => s.name === name);
            const entry = { name, savedAt: new Date().toLocaleString(), config: JSON.parse(JSON.stringify(this.config)) };
            if (idx >= 0) this.savedDesigns[idx] = entry;
            else this.savedDesigns.unshift(entry);
            localStorage.setItem('iRacingLiverySaves', JSON.stringify(this.savedDesigns));
            this.saveNameInput = '';
            this.showToast(`✓ Saved "${name}"`);
        },

        loadSavedDesign(entry) {
            Object.assign(this.config, JSON.parse(JSON.stringify(entry.config)));
            this.showSavesPanel = false;
            this.markChanged();
            this.showToast(`Loaded "${entry.name}"`);
        },

        deleteSavedDesign(name) {
            this.savedDesigns = this.savedDesigns.filter(s => s.name !== name);
            localStorage.setItem('iRacingLiverySaves', JSON.stringify(this.savedDesigns));
        },

        initThreeJS() {
            if (this.threeInit) return;
            const container = this.$refs.threeCanvas;
            const width = container.clientWidth || 600;
            const height = container.clientHeight || 600;

            this.threeScene = new THREE.Scene();
            this.threeScene.background = new THREE.Color(0x18181b);
            this.threeScene.fog = new THREE.Fog(0x18181b, 2, 8);

            const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
            camera.position.set(0, 1.2, 3.5);

            this.threeRenderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
            this.threeRenderer.setSize(width, height);
            this.threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            this.threeRenderer.setClearColor(0x18181b, 1);
            
            container.innerHTML = '';
            container.appendChild(this.threeRenderer.domElement);

            this.threeControls = new THREE.OrbitControls(camera, this.threeRenderer.domElement);
            this.threeControls.enablePan = false;
            this.threeControls.enableDamping = true;
            this.threeControls.dampingFactor = 0.05;

            const ambient = new THREE.AmbientLight(0xffffff, 0.4);
            this.threeScene.add(ambient);
            const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
            mainLight.position.set(2, 3, 4);
            this.threeScene.add(mainLight);

            // Generic curved mesh for preview
            const geometry = new THREE.CylinderGeometry(2, 2, 2.8, 48, 1, true, Math.PI / 4, Math.PI / 2);
            geometry.rotateX(Math.PI / 2);
            geometry.rotateY(Math.PI);
            geometry.center();
            
            this.threeMaterial = new THREE.MeshStandardMaterial({ 
                color: 0xffffff,
                metalness: this.config.base_metallic,
                roughness: this.config.base_roughness,
                side: THREE.DoubleSide
            });
            this.threeCarMesh = new THREE.Mesh(geometry, this.threeMaterial);
            this.threeScene.add(this.threeCarMesh);

            const animate = () => {
                requestAnimationFrame(animate);
                this.threeControls.update();
                this.threeRenderer.render(this.threeScene, camera);
            };
            animate();
            this.threeInit = true;
            if (this.previewBaked) this.updateThreeTexture();
        },

        updateThreeTexture() {
            if (!this.threeInit || !this.previewBaked) return;
            const loader = new THREE.TextureLoader();
            loader.load(`/preview/${this.previewBaked}?t=${this.timestamp}`, (tex) => {
                tex.encoding = THREE.sRGBEncoding;
                tex.flipY = false;
                this.threeMaterial.map = tex;
                this.threeMaterial.needsUpdate = true;
            });
        },

        updateThreeMaterialProps() {
            if (!this.threeMaterial) return;
            this.threeMaterial.metalness = this.config.base_metallic;
            this.threeMaterial.roughness = this.config.base_roughness;
        },

        showToast(msg) {
            this.toastMsg = msg;
            clearTimeout(this.toastTimer);
            this.toastTimer = setTimeout(() => this.toastMsg = '', 3000);
        },

        undo() {
            if (this.historyIndex > 0) {
                this.isUndoing = true;
                this.historyIndex--;
                this.config = JSON.parse(this.history[this.historyIndex]);
                setTimeout(() => { this.isUndoing = false; }, 50);
            }
        },

        redo() {
            if (this.historyIndex < this.history.length - 1) {
                this.isUndoing = true;
                this.historyIndex++;
                this.config = JSON.parse(this.history[this.historyIndex]);
                setTimeout(() => { this.isUndoing = false; }, 50);
            }
        },

        suggestHarmony() {
            const hex = this.config.primary;
            const [r, g, b] = [1,3,5].map(i => parseInt(hex.slice(i, i+2), 16) / 255);
            const max = Math.max(r,g,b), min = Math.min(r,g,b), d = max - min;
            let h = 0;
            if (d > 0) {
                if (max === r) h = ((g - b) / d + 6) % 6;
                else if (max === g) h = (b - r) / d + 2;
                else h = (r - g) / d + 4;
                h *= 60;
            }
            const s = max === 0 ? 0 : d / max;
            const v = max;
            const hsvToHex = (hh, ss, vv) => {
                const c = vv * ss, x = c * (1 - Math.abs((hh/60) % 2 - 1)), m = vv - c;
                let rr=0, gg=0, bb=0;
                if (hh<60) { rr=c; gg=x; } else if (hh<120) { rr=x; gg=c; } else if (hh<180) { gg=c; bb=x; } else if (hh<240) { rr=x; gg=c; } else if (hh<300) { rr=x; bb=c; } else { rr=c; bb=x; }
                return '#' + [rr+m, gg+m, bb+m].map(vl => Math.round(vl*255).toString(16).padStart(2,'0')).join('');
            };
            this.config.secondary = hsvToHex((h + 150) % 360, Math.min(s * 1.1, 1), Math.max(v * 0.9, 0.2));
            this.config.accent = hsvToHex((h + 210) % 360, Math.min(s * 0.7, 1), Math.min(v * 1.2, 1));
            this.markChanged();
        },

        shareConfig() {
            const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(this.config))));
            const url = location.origin + location.pathname + '?c=' + encoded;
            navigator.clipboard.writeText(url).then(
                () => this.showToast('Shareable Link copied to clipboard!'),
                () => prompt('Copy this link:', url)
            );
        },

        loadConfig(file) {
            if (!file) return;
            const reader = new FileReader();
            reader.onload = e => {
                try {
                    const cfg = JSON.parse(e.target.result);
                    Object.assign(this.config, cfg);
                    this.markChanged();
                    this.showToast('Config layout loaded.');
                } catch(ex) { this.showToast('Load failed.'); }
            };
            reader.readAsText(file);
        },

        resetConfig() {
            if(!confirm("Reset current design to solid and clear all overlays?")) return;
            this.config.layers = [{type:'design',id:'solid',metallic:0.1,roughness:0.5,params:{scale:1.0,x:50,y:50},visible:true,collapsed:false}];
            this.history = [];
            this.historyIndex = -1;
            this.markChanged();
            this.showToast("✓ Clean Slate: Design Reset.");
        },

        startDrag(idx, e) {
            if(this.viewMode !== '2d') return;
            const layer = this.config.layers[idx];
            layer.activeDrag = true;
            const wrapper = this.$refs.twoDWrapper;
            const onMouseMove = (ev) => {
                const rect = wrapper.getBoundingClientRect();
                let xFrac = (ev.clientX - rect.left) / rect.width * 100;
                let yFrac = (ev.clientY - rect.top) / rect.height * 100;
                xFrac = Math.max(0, Math.min(100, xFrac));
                yFrac = Math.max(0, Math.min(100, yFrac));
                layer.params.x = Math.round(xFrac);
                layer.params.y = Math.round(yFrac);
            };
            const onMouseUp = () => {
                layer.activeDrag = false;
                window.removeEventListener('mousemove', onMouseMove);
                window.removeEventListener('mouseup', onMouseUp);
                this.markChanged();
            };
            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        },

        applyPreset(p, s, a) {
            this.config.primary = p;
            this.config.secondary = s;
            this.config.accent = a;
            this.markChanged();
            this.showToast(`Applied Preset Palette.`);
        }
    }));
});
