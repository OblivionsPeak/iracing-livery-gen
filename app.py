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

PREVIEW_CACHE = collections.OrderedDict()
MAX_CACHE_SIZE = 20

# Create runtime dirs
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)


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
            edges_np = _cv2.Canny(grey_np, 50, 150)
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

    try:
        from pipeline.livery_builder import build, hex_to_rgb
        img_clean, img_baked, spec_map = build(
            template_path    = tmpl,
            primary          = hex_to_rgb(data.get("primary",   "#1a1a2e")),
            secondary        = hex_to_rgb(data.get("secondary", "#e63946")),
            accent           = hex_to_rgb(data.get("accent",    "#ffd700")),
            layers           = processed_layers,
            texture          = str(data.get("texture", "none")).lower().strip(),
            texture_opacity  = texture_opacity,
            template_opacity = template_opacity,
            grunge_amount    = _clamp(data.get("grunge_amount", 0.0), 0.0, 1.0, 0.0)
        )
    except Exception as e:
        import traceback
        print(f"BUILD ERROR: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

    base_name = f"{car_id}_{int(time.time() * 1000)}"
    file_clean = f"{base_name}_clean.png"
    file_baked = f"{base_name}_baked.png"
    file_spec  = f"{base_name}_spec.png"

    # Serialize images to RAM cache (evict oldest if full)
    entries = [(file_clean, img_clean), (file_baked, img_baked), (file_spec, spec_map)]
    for fname, pil_img in entries:
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        PREVIEW_CACHE[fname] = buf.getvalue()
        if len(PREVIEW_CACHE) > MAX_CACHE_SIZE:
            PREVIEW_CACHE.popitem(last=False)

    return jsonify({
        "status":      "ok",
        "image_baked": file_baked,
        "image_clean": file_clean,
        "image_spec":  file_spec,
    })


# ---------------------------------------------------------------------------

@app.route("/preview/<filename>")
def preview(filename):
    if filename not in PREVIEW_CACHE:
        return "Not found in RAM cache", 404
    return send_file(io.BytesIO(PREVIEW_CACHE[filename]), mimetype="image/png")


@app.route("/download/<filename>")
def download(filename):
    if filename not in PREVIEW_CACHE:
        return "Not found in RAM cache", 404
    return send_file(
        io.BytesIO(PREVIEW_CACHE[filename]),
        mimetype="image/png",
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# iRacing export
# ---------------------------------------------------------------------------

@app.route("/export-to-iracing", methods=["POST"])
def export_to_iracing():
    data = request.json
    filename   = data.get("filename", "")
    car_id     = data.get("car_id", "")
    car_number = str(data.get("car_number", "0")).strip().lstrip("0") or "0"

    if filename not in PREVIEW_CACHE:
        return jsonify({"error": "Preview RAM stream not found"}), 404

    paint_dir = Path.home() / "Documents" / "iRacing" / "paint" / car_id
    if not paint_dir.exists():
        return jsonify({
            "error": "iRacing paint folder not found",
            "expected_path": str(paint_dir)
        }), 404

    dest = paint_dir / f"car_{car_number}.png"
    dest.write_bytes(PREVIEW_CACHE[filename])
    return jsonify({"status": "ok", "exported_to": str(dest)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
