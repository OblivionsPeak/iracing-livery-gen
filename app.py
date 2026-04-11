"""
iRacing Livery Generator — Lite
No GPU or AI required. Runs anywhere Python runs.

Local:   python app.py  → http://localhost:5002
Railway: auto-detected via Procfile
"""

import json
import os
import time
import io
import json
import zipfile
import collections
from pathlib import Path

import numpy as np

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from pipeline.template_fetcher import fetch_single

app = Flask(__name__, template_folder="flask_templates")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB upload limit

CARS_JSON     = Path("cars.json")
TEMPLATES_DIR = Path("car_templates")
LOGOS_DIR     = Path("static/logos")
PREVIEWS_DIR  = Path("static/previews")

# Create runtime dirs
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

def _cleanup_previews():
    """Purge preview files older than 2 hours to save disk space."""
    now = time.time()
    for f in PREVIEWS_DIR.glob("*.png"):
        if now - f.stat().st_mtime > 7200:
            try: f.unlink()
            except: pass


def _clamp(val, lo, hi, default):
    try:
        v = float(val)
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return default


def load_cars() -> dict:
    with open(CARS_JSON) as f:
        raw = json.load(f)
    flat = {}
    for key, val in raw.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict) and "display_name" not in val:
            for cid, info in val.items():
                flat[cid] = info
        else:
            flat[key] = val
    return flat


@app.route("/")
def index():
    cars = load_cars()
    groups: dict[str, list] = {}
    for cid, info in cars.items():
        series = info.get("series", "Other")
        groups.setdefault(series, []).append({
            "id":             cid,
            "name":           info["display_name"],
            "template_ready": (TEMPLATES_DIR / cid / "template.png").exists(),
        })
    return render_template("index.html", groups=groups)


# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------

@app.route("/fetch-template", methods=["POST"])
def fetch_template():
    car_id     = request.json.get("car_id")
    manual_url = request.json.get("url")
    if not car_id:
        return jsonify({"error": "car_id required"}), 400
    try:
        fetch_single(car_id, manual_url=manual_url)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-template", methods=["POST"])
def upload_template():
    car_id = request.form.get("car_id", "").strip()
    if not car_id or car_id == "custom":
        raw_name = request.files.get("file", None)
        fname = secure_filename(raw_name.filename) if raw_name else "custom"
        car_id = Path(fname).stem.lower().replace(" ", "_").replace("-", "_") or "custom"

    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No file provided"}), 400

    f       = request.files["file"]
    ext     = Path(secure_filename(f.filename)).suffix.lower()
    destdir = TEMPLATES_DIR / car_id
    destdir.mkdir(parents=True, exist_ok=True)
    raw     = destdir / f"template{ext}"
    f.save(raw)

    template_path = destdir / "template.png"
    try:
        if ext == ".psd":
            from psd_tools import PSDImage
            pil_img = PSDImage.open(raw).composite()
        else:
            from PIL import Image
            pil_img = Image.open(raw).convert("RGBA")
        
        pil_img.save(template_path)

        # Build edge mask: Canny on a white-background flatten of the template.
        # Saved as plain greyscale (255=edge, 0=background).
        from PIL import Image as _PILEdge, ImageFilter as _IF
        bg = _PILEdge.new("RGBA", pil_img.size, (255, 255, 255, 255))
        bg.alpha_composite(pil_img.convert("RGBA"))
        flat_grey = bg.convert("L")

        try:
            import cv2 as _cv2
            grey_np = np.array(flat_grey)
            # Low thresholds (15/60) to catch subtle UV panel boundaries
            edges_np = _cv2.Canny(grey_np, 15, 60)
            kernel = np.ones((2, 2), np.uint8)
            edges_np = _cv2.dilate(edges_np, kernel, iterations=1)
            _PILEdge.fromarray(edges_np).save(destdir / "edge_mask.png")
        except Exception:
            # cv2 unavailable — Pillow FIND_EDGES fallback
            flat_grey.filter(_IF.FIND_EDGES).save(destdir / "edge_mask.png")

    except Exception as e:
        return jsonify({"error": f"Could not process template: {e}"}), 500

    return jsonify({"status": "ok", "car_id": car_id})


# ---------------------------------------------------------------------------
# Logo upload
# ---------------------------------------------------------------------------

@app.route("/upload-logo", methods=["POST"])
def upload_logo():
    car_id = request.form.get("car_id", "custom").strip() or "custom"
    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    ext = Path(secure_filename(f.filename)).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        return jsonify({"error": "Only PNG/JPG/WEBP logos supported"}), 400
    
    destdir = LOGOS_DIR / car_id
    destdir.mkdir(parents=True, exist_ok=True)
    
    logo_filename = f"logo_{int(time.time() * 1000)}.png"
    logo_path = destdir / f"raw_{logo_filename}{ext}"
    f.save(logo_path)
    
    from PIL import Image as PILImage
    img = PILImage.open(logo_path).convert("RGBA")
    png_path = destdir / logo_filename
    img.save(png_path)
    
    if logo_path != png_path:
        logo_path.unlink(missing_ok=True)
        
    return jsonify({"status": "ok", "logo_id": car_id, "filename": logo_filename})


# ---------------------------------------------------------------------------
# Livery build
# ---------------------------------------------------------------------------

@app.route("/build", methods=["POST"])
def build_livery():
    data    = request.json
    car_id  = data.get("car_id")
    # Comprehensive log of incoming configuration
    print(f"--- BUILD REQUEST @ {time.ctime()} ---")
    print(f"JSON: {json.dumps(data)}")
    print(f"--- END BUILD REQUEST ---")
    
    if not car_id:
        return jsonify({"error": "car_id required"}), 400

    tmpl = TEMPLATES_DIR / car_id / "template.png"
    if not tmpl.exists():
        return jsonify({"error": "Template not uploaded yet."}), 400

    angle            = _clamp(data.get("angle", 45), 5, 85, 45)
    stripe_width     = int(_clamp(data.get("stripe_width", 160), 10, 500, 160))
    gap              = int(_clamp(data.get("gap", 25), 0, 200, 25))
    split            = _clamp(data.get("split", 0.5), 0.1, 0.9, 0.5)
    depth            = _clamp(data.get("depth", 0.35), 0.05, 0.7, 0.35)
    feather          = int(_clamp(data.get("feather", 60), 0, 300, 60))
    texture_opacity  = _clamp(data.get("texture_opacity", 0.25), 0.0, 1.0, 0.25)
    template_opacity = _clamp(data.get("template_opacity", 0.35), 0.0, 1.0, 0.35)
    
    # Process Unified Layers Array
    raw_layers = data.get("layers", [])
    processed_layers = []
    
    for l in raw_layers:
        l_type = l.get("type", "design")
        l_params = l.get("params", {})
        
        if l_type == "logo":
            # Map logo filename to full path for the builder
            fname = l_params.get("filename", "")
            lp = LOGOS_DIR / car_id / fname
            if lp.exists():
                l_params["path"] = str(lp)
        
        processed_layers.append({
            "type": l_type,
            "id": l.get("id"),
            "params": l_params,
            "metallic": l.get("metallic", 0.0),
            "roughness": l.get("roughness", 0.1),
            "opacity": l.get("opacity", 1.0)
        })

    _cleanup_previews()
    try:
        from pipeline.livery_builder import build, hex_to_rgb
        img_clean, img_baked, spec_map = build(
            template_path    = tmpl,
            primary          = hex_to_rgb(data.get("primary",   "#111111")),
            secondary        = hex_to_rgb(data.get("secondary", "#e63946")),
            accent           = hex_to_rgb(data.get("accent",    "#ffd700")),
            layers           = processed_layers,
            texture          = str(data.get("texture", "none")).lower().strip(),
            texture_opacity  = texture_opacity,
            template_opacity = template_opacity,
            grunge_amount    = _clamp(data.get("grunge_amount", 0.0), 0.0, 1.0, 0.0),
            base_metallic    = float(data.get("base_metallic", 0.0)),
            base_roughness   = float(data.get("base_roughness", 0.1)),
            size             = 1024 # PREVIEW SCALE: 4x faster than 2048
        )
    except Exception as e:
        import traceback
        print(f"BUILD ERROR: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

    base_name = f"{car_id}_{int(time.time() * 1000)}"
    file_clean = f"{base_name}_clean.png"
    file_baked = f"{base_name}_baked.png"
    file_spec  = f"{base_name}_spec.png"

    # Save to disk cache for multi-worker support
    img_clean.save(PREVIEWS_DIR / file_clean, compress_level=1)
    img_baked.save(PREVIEWS_DIR / file_baked, compress_level=1)
    spec_map.save(PREVIEWS_DIR / file_spec, compress_level=1)

    return jsonify({
        "status":      "ok",
        "image_baked": file_baked,
        "image_clean": file_clean,
        "image_spec":  file_spec,
    })


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------

@app.route("/template-debug/<car_id>")
def template_debug(car_id):
    """Returns pixel stats for the uploaded template and edge mask. Useful for diagnosing wireframe issues."""
    tmpl = TEMPLATES_DIR / car_id / "template.png"
    edge = TEMPLATES_DIR / car_id / "edge_mask.png"
    info = {"car_id": car_id}

    if not tmpl.exists():
        info["template"] = "NOT FOUND"
    else:
        from PIL import Image as _I
        arr = np.array(_I.open(tmpl).convert("L"))
        info["template"] = {
            "exists": True,
            "size": list(_I.open(tmpl).size),
            "grey_min": int(arr.min()),
            "grey_max": int(arr.max()),
            "grey_mean": round(float(arr.mean()), 1),
            "dark_pixels_pct": round(float((arr < 50).mean() * 100), 2),
        }

    if not edge.exists():
        info["edge_mask"] = "NOT FOUND"
    else:
        from PIL import Image as _I2
        earr = np.array(_I2.open(edge).convert("L"))
        info["edge_mask"] = {
            "exists": True,
            "edge_pixels": int((earr > 30).sum()),
            "max_val": int(earr.max()),
        }

    return jsonify(info)
# ---------------------------------------------------------------------------

@app.route("/preview/<filename>")
def preview(filename):
    path = PREVIEWS_DIR / filename
    if not path.exists():
        return "Not found in cache", 404
    return send_file(path, mimetype="image/png")


@app.route("/download/<filename>")
def download(filename):
    path = PREVIEWS_DIR / filename
    if not path.exists():
        return "Not found in cache", 404
    return send_file(
        path,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# iRacing export
# ---------------------------------------------------------------------------

@app.route("/export-tga", methods=["POST"])
def export_tga():
    """Generates a ZIP with TGA files for manual iRacing deployment."""
    from PIL import Image
    data = request.json
    layers = data.get("layers", [])
    car_id = data.get("car_id", "custom")
    customer_id = str(data.get("customer_id", "42")).strip()
    
    # 1. Re-run build to get clean and spec buffers
    # (In a production app we'd pull from cache, but building is fast)
    from pipeline.livery_builder import build, hex_to_rgb
    tmpl = TEMPLATES_DIR / car_id / "template.png"
    
    img_clean, _, spec_map = build(
        template_path = tmpl,
        primary = hex_to_rgb(data.get("primary", "#1a1a2e")),
        secondary = hex_to_rgb(data.get("secondary", "#e63946")),
        accent = hex_to_rgb(data.get("accent", "#ffd700")),
        layers = layers,
        texture = data.get("texture", "none"),
        texture_opacity = float(data.get("texture_opacity", 0.25)),
        template_opacity = 0, # FORCE NO WIREFRAMES FOR TGA
        grunge_amount = float(data.get("grunge_amount", 0.0)),
        base_metallic = float(data.get("base_metallic", 0.0)),
        base_roughness = float(data.get("base_roughness", 0.1)),
        size = 2048 # MASTER EXPORT RESOLUTION
    )

    # 2. Package into ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        # iRacing expects .tga files. PIL handles this.
        # Main Livery
        main_tga = io.BytesIO()
        img_clean.save(main_tga, format="TGA")
        zf.writestr(f"car_{customer_id}.tga", main_tga.getvalue())
        
        # Spec Map
        spec_tga = io.BytesIO()
        spec_map.save(spec_tga, format="TGA")
        zf.writestr(f"car_spec_{customer_id}.tga", spec_tga.getvalue())

    zip_buf.seek(0)
    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"iracing_liveries_{customer_id}.zip"
    )


@app.route("/export-to-iracing", methods=["POST"])
def export_to_iracing():
    data = request.json
    filename   = data.get("filename", "") # This should ideally be the _clean version
    car_id     = data.get("car_id", "")
    car_number = str(data.get("car_number", "0")).strip().lstrip("0") or "0"

    # FORCE USE CLEAN BUFFER IF POSSIBLE
    clean_filename = filename.replace("_baked.png", "_clean.png")
    target_file = clean_filename if (PREVIEWS_DIR / clean_filename).exists() else filename
    target_path = PREVIEWS_DIR / target_file

    if not target_path.exists():
        return jsonify({"error": "Preview disk stream not found"}), 404

    paint_dir = Path.home() / "Documents" / "iRacing" / "paint" / car_id
    if not paint_dir.exists():
        # Fallback to current dir if iRacing path is missing (for local dev testing)
        paint_dir = Path("exports") / car_id
        paint_dir.mkdir(parents=True, exist_ok=True)

    dest = paint_dir / f"car_{car_number}.tga" # Save as TGA for iRacing
    
    # Convert PNG from disk to TGA using PIL
    from PIL import Image
    img = Image.open(target_path)
    img.save(dest, format="TGA")
    
    return jsonify({"status": "ok", "exported_to": str(dest)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
