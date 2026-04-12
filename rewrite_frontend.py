import re

with open("flask_templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Extract script block
script_match = re.search(r'(<script>.*?</script>)', text, flags=re.DOTALL)
if not script_match:
    print("Could not find script block")
    exit(1)
script_content = script_match.group(1)

# Ensure script logic aligns with the new layout
# The script logic relies on IDs. We must preserve all IDs.

new_html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>iRacing Livery Generator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-base: #09090b;
    --bg-surface: #18181b;
    --bg-surface-hover: #27272a;
    --border: #3f3f46;
    --border-hover: #52525b;
    --accent: #eab308;
    --accent-hover: #facc15;
    --text-pri: #f4f4f5;
    --text-sec: #a1a1aa;
    --text-muted: #71717a;
    --radius: 8px;
  }
  
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    background: var(--bg-base); 
    color: var(--text-pri); 
    font-family: 'Inter', sans-serif; 
    padding: 24px; 
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }
  
  .header { margin-bottom: 24px; max-width: 1600px; margin-left: auto; margin-right: auto; }
  h1 { font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; color: var(--text-pri); }
  h1 span { color: var(--accent); }
  .subtitle { font-size: 0.95rem; color: var(--text-sec); margin-top: 6px; font-weight: 400; }

  .layout { display: grid; grid-template-columns: 420px 1fr; gap: 24px; max-width: 1600px; margin: 0 auto; align-items: start; }
  @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }

  .panel { 
    background: var(--bg-surface); 
    border: 1px solid var(--border); 
    border-radius: calc(var(--radius) * 1.5); 
    padding: 24px; 
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }

  .section-title {
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    color: var(--text-muted); margin: 24px 0 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px;
  }
  .section-title:first-child { margin-top: 0; }

  label { display: flex; align-items: center; justify-content: space-between; font-size: 0.85rem; font-weight: 500; color: var(--text-pri); margin-bottom: 6px; margin-top: 16px; }
  label .val { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-sec); }
  
  select, input[type=text], input[type=number] {
    width: 100%; padding: 10px 12px; background: var(--bg-base); border: 1px solid var(--border);
    border-radius: var(--radius); color: var(--text-pri); font-size: 0.9rem; font-family: 'Inter', sans-serif;
    transition: border-color 0.15s, box-shadow 0.15s;
    appearance: none;
  }
  select:focus, input[type=text]:focus, input[type=number]:focus {
    outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(234, 179, 8, 0.2);
  }

  /* Colors */
  .preset-bar { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .preset-btn {
    padding: 6px 10px; background: var(--bg-surface-hover); border: 1px solid var(--border);
    border-radius: 6px; color: var(--text-sec); font-size: 0.75rem; font-weight: 500; cursor: pointer;
    transition: all 0.15s ease;
  }
  .preset-btn:hover { border-color: var(--accent); color: var(--text-pri); background: rgba(234, 179, 8, 0.1); }

  .color-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 16px; }
  .color-card {
    background: var(--bg-surface-hover); padding: 12px; border-radius: var(--radius); border: 1px solid var(--border);
    display: flex; flex-direction: column; align-items: center; gap: 8px;
  }
  .color-card label { margin: 0; font-size: 0.75rem; color: var(--text-sec); text-align: center; display: block; }
  
  .color-picker-wrap {
    position: relative; width: 44px; height: 44px; border-radius: 50%; overflow: hidden;
    border: 2px solid var(--border); transition: border-color 0.2s;
  }
  .color-picker-wrap:hover { border-color: var(--text-pri); }
  input[type=color] {
    position: absolute; top: -10px; left: -10px; width: 64px; height: 64px; border: none; cursor: pointer; padding: 0;
  }
  input[type=text].color-hex {
    font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; text-align: center; width: 100%;
    padding: 6px; background: var(--bg-base); border: 1px solid transparent; letter-spacing: 0.05em;
  }
  input[type=text].color-hex:focus { border-color: var(--accent); }

  .btn-row { display: flex; gap: 8px; margin-top: 16px; }
  .btn-sm {
    flex: 1; padding: 8px; background: var(--bg-surface-hover); border: 1px solid var(--border);
    border-radius: var(--radius); color: var(--text-sec); font-size: 0.8rem; font-weight: 500; cursor: pointer;
    transition: all 0.15s; text-align: center;
  }
  .btn-sm:hover { border-color: var(--border-hover); color: var(--text-pri); }
  .btn-sm.gold { color: var(--accent); border-color: rgba(234, 179, 8, 0.4); background: rgba(234, 179, 8, 0.05); }
  .btn-sm.gold:hover { border-color: var(--accent); background: rgba(234, 179, 8, 0.15); }

  /* Grid buttons with icons */
  .design-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 12px; }
  .design-btn {
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
    padding: 12px 4px; background: var(--bg-base); border: 1px solid var(--border); border-radius: var(--radius);
    color: var(--text-sec); font-size: 0.65rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
    user-select: none; text-transform: uppercase; letter-spacing: 0.05em;
  }
  .design-btn svg { width: 24px; height: 24px; fill: currentColor; }
  .design-btn:hover { border-color: var(--border-hover); color: var(--text-pri); background: var(--bg-surface-hover); }
  .design-btn.active {
    background: rgba(234, 179, 8, 0.1); border-color: var(--accent); color: var(--accent);
  }

  /* Custom Range Sliders */
  .slider-row { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
  input[type=range] { -webkit-appearance: none; width: 100%; background: transparent; height: 24px; }
  input[type=range]::-webkit-slider-runnable-track { width: 100%; height: 6px; background: var(--border); border-radius: 3px; }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; height: 16px; width: 16px; border-radius: 50%;
    background: var(--text-pri); cursor: grab; margin-top: -5px; box-shadow: 0 2px 5px rgba(0,0,0,0.5);
    transition: background 0.1s;
  }
  input[type=range]:active::-webkit-slider-thumb { background: var(--accent); cursor: grabbing; }

  /* Dropzones */
  #drop-zone, .logo-zone {
    position: relative; border: 2px dashed var(--border); border-radius: var(--radius);
    padding: 24px 16px; text-align: center; cursor: pointer;
    transition: all 0.2s; background: rgba(0,0,0,0.2);
  }
  #drop-zone:hover, .logo-zone:hover, #drop-zone.drag-over { border-color: var(--accent); background: rgba(234,179,8,0.05); }
  #drop-zone.has-file, .logo-zone.has-logo { border-color: #10b981; border-style: solid; background: rgba(16,185,129,0.05); }
  #drop-zone input[type=file], .logo-zone input {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  #drop-label, #logo-label { font-size: 0.85rem; font-weight: 500; color: var(--text-sec); pointer-events: none; line-height: 1.5; }
  #drop-label span { font-size: 0.75rem; color: var(--text-muted); font-weight: 400; }

  #template-status { font-size: 0.8rem; font-weight: 500; margin-top: 8px; display: inline-flex; align-items: center; gap: 6px; }
  .ok { color: #10b981; } .missing { color: var(--text-muted); }

  /* Buttons */
  .btn-build {
    width: 100%; padding: 14px; margin-top: 24px; background: var(--accent); color: #422006;
    font-weight: 700; font-size: 1rem; border: none; border-radius: var(--radius);
    cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 14px rgba(234, 179, 8, 0.2);
  }
  .btn-build:hover { background: var(--accent-hover); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(234, 179, 8, 0.3); }
  .btn-build:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; background: var(--border); color: var(--text-muted); }

  .btn-vary {
    width: 100%; padding: 10px; margin-top: 12px; background: transparent; color: var(--text-sec);
    font-size: 0.85rem; font-weight: 500; border: 1px solid var(--border); border-radius: var(--radius); cursor: pointer;
    transition: all 0.2s;
  }
  .btn-vary:hover { color: var(--text-pri); border-color: var(--border-hover); background: var(--bg-surface-hover); }

  details summary { list-style: none; user-select: none; }
  details summary::-webkit-details-marker { display: none; }

  /* Result Pane */
  .result-pane {
    position: sticky; top: 24px; display: flex; flex-direction: column; gap: 16px;
  }
  
  /* Checkerboard backdrop for transparency */
  .preview-wrapper {
    background-color: #1a1a1a;
    background-image: 
      linear-gradient(45deg, #222 25%, transparent 25%, transparent 75%, #222 75%, #222),
      linear-gradient(45deg, #222 25%, transparent 25%, transparent 75%, #222 75%, #222);
    background-size: 20px 20px;
    background-position: 0 0, 10px 10px;
    border-radius: calc(var(--radius) * 1.5);
    border: 1px solid var(--border);
    overflow: hidden;
    position: relative;
    box-shadow: 0 20px 40px -10px rgba(0,0,0,0.8), inset 0 2px 20px rgba(0,0,0,0.5);
  }
  
  .result-card { border-radius: calc(var(--radius) * 1.5); overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border); }
  .result-card img { width: 100%; display: block; filter: drop-shadow(0 20px 30px rgba(0,0,0,0.5)); }
  
  .result-footer { 
    background: var(--bg-surface); padding: 16px;
    display: flex; justify-content: space-between; align-items: center; 
    border-top: 1px solid var(--border);
  }
  .result-label { font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; color: var(--text-sec); }
  
  .btn-dl {
    background: #10b981; color: #022c22; border: none; padding: 8px 16px;
    border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; text-decoration: none;
    transition: all 0.2s;
  }
  .btn-dl:hover { background: #34d399; }
  .btn-export {
    background: var(--bg-surface-hover); color: var(--text-pri); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 16px; font-weight: 500; cursor: pointer; font-size: 0.85rem; text-decoration: none;
    transition: all 0.2s;
  }
  .btn-export:hover { border-color: var(--border-hover); background: #27272a; }

  #params-angle, #params-split, #params-feather, #params-chevron, #params-offset { display: none; margin-top: 12px; }
  #params-stripe-dir { display: none; margin-top: 12px; }

  .spinner {
    display: inline-block; width: 16px; height: 16px; border: 2px solid var(--border);
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin 0.6s linear infinite; vertical-align: text-bottom; margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  #status { margin-top: 16px; font-size: 0.85rem; font-weight: 500; color: var(--text-sec); min-height: 20px; text-align: center;}
  #status.error { color: #ef4444; }

  .row { display: flex; gap: 16px; }
  .row > * { flex: 1; min-width: 0; }
</style>
</head>
<body>
<div class="header">
  <h1>iRacing Livery Generator</h1>
  <p class="subtitle">Programmatic livery builder — no GPU required. Upload your car template, pick colors, download.</p>
</div>

<div class="layout">

<!-- ── LEFT PANEL ── -->
<div class="panel">

  <div class="section-title">Car &amp; Template</div>

  <div id="drop-zone">
    <input type="file" id="template-file" accept=".png,.psd,.tga,.zip">
    <div id="drop-label">Drop or click to upload full template<br><span>Supports PNG, PSD, and TGA</span></div>
  </div>
  <div id="template-status"></div>

  <div class="row" style="margin-top: 16px;">
    <div>
      <label style="margin-top:0;">Car Number <span class="val" style="font-size:0.7rem; color:var(--text-muted);">(Export)</span></label>
      <input type="text" id="car-number" value="42" maxlength="4">
    </div>
  </div>

  <details style="margin-top:16px;">
    <summary style="font-size:0.8rem; font-weight: 500; color:var(--accent); cursor:pointer;">Select Known Car (Optional iRacing Export) ▸</summary>
    <select id="car-select" style="margin-top:8px;">
      <option value="custom">— none / auto-detect —</option>
      {% for series, cars in groups.items() %}
      <optgroup label="{{ series }}">
        {% for car in cars %}
        <option value="{{ car.id }}" data-ready="{{ car.template_ready | lower }}">
          {{ car.name }}{% if car.template_ready %} ✓{% endif %}
        </option>
        {% endfor %}
      </optgroup>
      {% endfor %}
    </select>
  </details>

  <!-- COLORS -->
  <div class="section-title">Colors</div>
  <div class="preset-bar">
    <span style="font-size:0.7rem; font-weight: 600; color:var(--text-muted); display:flex; align-items:center; margin-right: 4px;">PRESETS</span>
    <button class="preset-btn" data-p="#0a0a0a" data-s="#c8102e" data-a="#ffffff">GT Red</button>
    <button class="preset-btn" data-p="#ffffff" data-s="#003087" data-a="#c8102e">Gulf</button>
    <button class="preset-btn" data-p="#003087" data-s="#ffd700" data-a="#ffffff">Rothmans</button>
    <button class="preset-btn" data-p="#1b1b1b" data-s="#ffd700" data-a="#888888">Carbon Gold</button>
    <button class="preset-btn" data-p="#006341" data-s="#ffffff" data-a="#ffd700">British Green</button>
    <button class="preset-btn" data-p="#e8e8e8" data-s="#cc0000" data-a="#111111">Martini</button>
    <button class="preset-btn" data-p="#2d2d2d" data-s="#ff6b00" data-a="#ffffff">Stealth</button>
  </div>
  
  <div class="color-grid">
    <div class="color-card">
      <label>PRIMARY</label>
      <div class="color-picker-wrap">
        <input type="color" id="col-primary" value="#1a1a2e">
      </div>
      <input type="text" class="color-hex" id="hex-primary" value="#1a1a2e" maxlength="7">
    </div>
    <div class="color-card">
      <label>SECONDARY</label>
      <div class="color-picker-wrap">
        <input type="color" id="col-secondary" value="#e63946">
      </div>
      <input type="text" class="color-hex" id="hex-secondary" value="#e63946" maxlength="7">
    </div>
    <div class="color-card">
      <label>ACCENT</label>
      <div class="color-picker-wrap">
        <input type="color" id="col-accent" value="#ffd700">
      </div>
      <input type="text" class="color-hex" id="hex-accent" value="#ffd700" maxlength="7">
    </div>
  </div>
  
  <div class="btn-row">
    <button class="btn-sm gold" onclick="suggestHarmony()">Auto-Harmony</button>
    <button class="btn-sm" onclick="saveConfig()">Save Palette</button>
    <label class="btn-sm" style="display:flex;align-items:center;justify-content:center;margin:0;cursor:pointer;">Load Config<input type="file" id="config-file" accept=".json" style="display:none" onchange="loadConfig(this)"></label>
    <button class="btn-sm" onclick="shareConfig()">Copy Link</button>
  </div>

  <!-- DESIGN PATTERN -->
  <div class="section-title">Design Layer</div>
  <div class="design-grid">
    <div class="design-btn active" data-design="solid">
      <svg><rect width="24" height="24" fill="currentColor"/></svg> Solid
    </div>
    <div class="design-btn" data-design="racing_stripes">
      <svg><rect width="24" height="24" fill="currentColor" fill-opacity="0.2"/><path d="M8 0h3v24H8zM13 0h3v24h-3z"/></svg> Stripes
    </div>
    <div class="design-btn" data-design="diagonal_stripes">
      <svg><rect width="24" height="24" fill="currentColor" fill-opacity="0.2"/><path d="M0 16L16 0h8L0 24z"/></svg> Diagonal
    </div>
    <div class="design-btn" data-design="gradient">
      <svg><defs><linearGradient id="g1"><stop offset="0%" stop-color="currentColor"/><stop offset="100%" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><rect width="24" height="24" fill="url(#g1)"/></svg> Gradient
    </div>
    <div class="design-btn" data-design="sweep">
      <svg><path d="M0 16l12-8h12v6l-12 10H0z"/></svg> GT Sweep
    </div>
    <div class="design-btn" data-design="split">
      <svg><rect y="6" width="24" height="12"/></svg> Split
    </div>
    <div class="design-btn" data-design="chevron">
      <svg><path d="M0 0l12 12L0 24h6l12-12L6 0z"/></svg> Chevron
    </div>
    <div class="design-btn" data-design="two_tone">
      <svg><path d="M0 24L24 0v24z"/></svg> Two-Tone
    </div>
    <div class="design-btn" data-design="gradient_chevron">
      <svg><path d="M0 0l10 10v4L0 24z" fill-opacity="0.5"/><path d="M0 4l6 8-6 8z"/></svg> Grad Chev
    </div>
    <div class="design-btn" data-design="radial_gradient">
      <svg><circle cx="12" cy="12" r="10" fill="currentColor" fill-opacity="0.5"/></svg> Radial
    </div>
    <div class="design-btn" data-design="harlequin">
      <svg><path d="M12 0l6 6-6 6-6-6z M12 12l6 6-6 6-6-6z M0 6l6 6-6 6-6-6z M24 6l-6 6-6-6 6-6z"/></svg> Harlequin
    </div>
    <div class="design-btn" data-design="pinstripe">
      <svg><path d="M0 20L20 0h2L0 22zM0 10L10 0h2L0 12z" /></svg> Pinstripe
    </div>
    <div class="design-btn" data-design="number_panel">
      <svg><rect width="24" height="24" fill="currentColor" fill-opacity="0.2"/><rect x="6" y="8" width="12" height="8" rx="1"/></svg> Num Panel
    </div>
  </div>

  <div id="params-angle">
    <label>Angle <span class="val" id="angle-val">45°</span></label>
    <div class="slider-row">
      <input type="range" id="angle" min="10" max="80" value="45" oninput="document.getElementById('angle-val').textContent=this.value+'°'; scheduleLive()">
    </div>
    <label>Stripe Width <span class="val" id="sw-val">160</span></label>
    <div class="slider-row">
      <input type="range" id="stripe-width" min="40" max="400" value="160" oninput="document.getElementById('sw-val').textContent=this.value; scheduleLive()">
    </div>
  </div>

  <div id="params-stripe-dir">
    <label>Direction</label>
    <select id="stripe-dir" onchange="scheduleLive()">
      <option value="vertical">Vertical</option>
      <option value="horizontal">Horizontal</option>
    </select>
  </div>

  <div id="params-split">
    <label>Split Position <span class="val" id="sp-val">50%</span></label>
    <div class="slider-row">
      <input type="range" id="split-pos" min="20" max="80" value="50" oninput="document.getElementById('sp-val').textContent=this.value+'%'; scheduleLive()">
    </div>
    <label>Direction</label>
    <select id="split-dir" onchange="scheduleLive()">
      <option value="horizontal">Horizontal</option>
      <option value="vertical">Vertical</option>
    </select>
  </div>

  <div id="params-feather">
    <label>Edge Fade <span class="val" id="feather-val">60px</span></label>
    <div class="slider-row">
      <input type="range" id="feather" min="0" max="200" value="60" oninput="document.getElementById('feather-val').textContent=this.value+'px'; scheduleLive()">
    </div>
  </div>

  <div id="params-chevron">
    <label>Chevron Angle <span class="val" id="depth-val">35%</span></label>
    <div class="slider-row">
      <input type="range" id="chevron-depth" min="5" max="70" value="35" oninput="document.getElementById('depth-val').textContent=this.value+'%'; scheduleLive()">
    </div>
  </div>

  <div id="params-offset">
    <label>Horizontal Offset <span class="val" id="offset-x-val">50%</span></label>
    <div class="slider-row">
      <input type="range" id="h-offset" min="10" max="90" value="50" oninput="document.getElementById('offset-x-val').textContent=this.value+'%'; scheduleLive()">
    </div>
    <label>Vertical Offset <span class="val" id="offset-y-val">50%</span></label>
    <div class="slider-row">
      <input type="range" id="v-offset" min="10" max="90" value="50" oninput="document.getElementById('offset-y-val').textContent=this.value+'%'; scheduleLive()">
    </div>
  </div>

  <!-- OVERLAY PATTERN -->
  <div class="section-title">Overlay Mix</div>
  <div class="row">
    <div>
      <label style="margin-top:0;">Secondary Pattern</label>
      <select id="overlay-design" onchange="scheduleLive()">
        <option value="none">None</option>
        <option value="solid">Solid</option>
        <option value="racing_stripes">Racing Stripes</option>
        <option value="diagonal_stripes">Diagonal</option>
        <option value="gradient">Gradient</option>
        <option value="sweep">GT Sweep</option>
        <option value="split">Split</option>
        <option value="chevron">Chevron</option>
        <option value="two_tone">Two-Tone</option>
        <option value="gradient_chevron">Grad. Chevron</option>
        <option value="radial_gradient">Radial</option>
        <option value="harlequin">Harlequin</option>
        <option value="pinstripe">Pinstripe</option>
        <option value="number_panel">Num Panel</option>
      </select>
    </div>
    <div>
      <label style="margin-top:0;">Mix Opacity <span class="val" id="ov-val">40%</span></label>
      <input type="range" id="overlay-opacity" min="0" max="90" value="40" style="margin-top:14px;" oninput="document.getElementById('ov-val').textContent=this.value+'%'; scheduleLive()">
    </div>
  </div>

  <!-- LOGO / SPONSOR -->
  <div class="section-title">Logo & Decals</div>
  <div class="logo-zone" id="logo-zone">
    <input type="file" id="logo-file" accept=".png,.jpg,.jpeg,.webp" onchange="uploadLogo(this)">
    <div id="logo-label">Drop or click to upload main sponsor logo<br><span>(Requires transparent PNG to blend cleanly)</span></div>
  </div>
  <div id="logo-controls" style="display:none; background: var(--bg-surface-hover); padding: 16px; border-radius: var(--radius); margin-top: 12px; border: 1px solid var(--border);">
    <label style="margin-top:0;">Scale <span class="val" id="logo-scale-val">20%</span></label>
    <div class="slider-row">
      <input type="range" id="logo-scale" min="5" max="60" value="20" oninput="document.getElementById('logo-scale-val').textContent=this.value+'%'; scheduleLive()">
    </div>
    <label>Align X <span class="val" id="logo-x-val">50%</span></label>
    <div class="slider-row">
      <input type="range" id="logo-x" min="5" max="95" value="50" oninput="document.getElementById('logo-x-val').textContent=this.value+'%'; scheduleLive()">
    </div>
    <label>Align Y <span class="val" id="logo-y-val">50%</span></label>
    <div class="slider-row">
      <input type="range" id="logo-y" min="5" max="95" value="50" oninput="document.getElementById('logo-y-val').textContent=this.value+'%'; scheduleLive()">
    </div>
    <button class="btn-sm" style="margin-top:12px; width:100%; border-color:#ef4444; color:#ef4444;" onclick="removeLogo()">Remove Logo</button>
  </div>

  <!-- FINISH -->
  <div class="section-title">Material Finish</div>
  <div class="row">
    <div>
      <label style="margin-top:0;">Surface</label>
      <select id="texture" onchange="scheduleLive()">
        <option value="none">Clearcoat (Gloss)</option>
        <option value="matte">Matte</option>
        <option value="carbon_fiber">Carbon Fiber</option>
        <option value="brushed_metal">Brushed Metal</option>
      </select>
    </div>
    <div>
      <label style="margin-top:0;">Texture Mix <span class="val" id="to-val">25%</span></label>
      <input type="range" id="texture-opacity" min="0" max="70" value="25" style="margin-top:14px;" oninput="document.getElementById('to-val').textContent=this.value+'%'; scheduleLive()">
    </div>
  </div>
  <label>Seam Line Visibility <span class="val" id="tpl-val">35%</span></label>
  <input type="range" id="template-opacity" min="0" max="80" value="35" style="margin-top:4px;" oninput="document.getElementById('tpl-val').textContent=this.value+'%'; scheduleLive()">

  <button class="btn-build" id="btn-build">Generate High-Res Livery</button>
  <button class="btn-vary" id="btn-vary">✨ Generate 4 AI Variations</button>
  <div id="status"></div>

</div>

<!-- ── RIGHT PANEL ── -->
<div class="result-pane">
  <div id="results">
     <div style="padding: 48px; text-align: center; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-surface);">
       <svg style="width:48px;height:48px;fill:var(--text-muted);margin-bottom:16px;" viewBox="0 0 24 24"><path d="M21 3H3C2 3 1 4 1 5v14c0 1.1.9 2 2 2h18c1 0 2-.9 2-2V5c0-1.1-1-2-2-2zM5 17l3.5-4.5 2.5 3.01L14.5 11l4.5 6H5z"/></svg>
       <p style="color:var(--text-sec);font-size:0.95rem;font-weight:500;">Upload an iRacing template and click Generate.</p>
       <p style="color:var(--text-muted);font-size:0.8rem;margin-top:8px;">Your high-res preview will appear here.</p>
     </div>
  </div>
</div>

</div><!-- end layout -->
{JS_CONTENT}
</body>
</html>
"""

# The JS in the current file updates a card rendering. I need to make sure the class names match.
# The card uses: 
# <div class="result-card" data-filename="...">
#    <div class="preview-wrapper"><img src="..."></div>
#    <div class="result-footer">... <a class="btn-dl"> </div>
# Look at original `renderResult` block, it injects `<img src...>` then `<div class="result-footer">...`.
# I will modify the function renderResult via python replace to add the "preview-wrapper" around img.

new_script = script_content.replace(
    '''<img src="/preview/${filename}?t=${Date.now()}" alt="Livery">''',
    '''<div class="preview-wrapper"><img src="/preview/${filename}?t=${Date.now()}" alt="Livery"></div>'''
)

final_html = new_html.replace("{JS_CONTENT}", new_script)

with open("flask_templates/index.html", "w", encoding="utf-8") as f:
    f.write(final_html)

print("Rewrite complete")
