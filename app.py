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

import cv2
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
        
        # PRE-COMPUTE EDGE MASK FOR RENDERING Loop
        grey = np.array(pil_img.convert("L"))
        # High thresholds ensure we only catch the sharpest seam lines, not logos
        edges = cv2.Canny(grey, 100, 200)
        
        mask = np.zeros((grey.shape[0], grey.shape[1], 4), dtype=np.uint8)
        mask[edges > 0] = [255, 255, 255, 255]
        from PIL import Image
        Image.fromarray(mask, "RGBA").save(destdir / "edge_mask.png")

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
    from pipeline.livery_builder import build, hex_to_rgb

    data    = request.json
    car_id  = data.get("car_id")
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
    overlay_opacity  = _clamp(data.get("overlay_opacity", 0.4), 0.0, 1.0, 0.4)
    h_offset         = _clamp(data.get("h_offset", 0.0), -0.4, 0.4, 0.0)
    v_offset         = _clamp(data.get("v_offset", 0.0), -0.4, 0.4, 0.0)
    cx_frac          = _clamp(data.get("cx_frac",  0.5),  0.1, 0.9, 0.5)
    cy_frac          = _clamp(data.get("cy_frac",  0.5),  0.1, 0.9, 0.5)

    # Process Multi-Logos Array
    logos_data = data.get("logos", [])
    logo_params = []
    for l in logos_data:
        lp = LOGOS_DIR / car_id / l.get("filename", "")
        if lp.exists() and l.get("filename"):
            logo_params.append({
                "path": str(lp),
                "scale": _clamp(l.get("scale", 20), 5, 100, 20) / 100,
                "x_frac": _clamp(l.get("x", 50), 0, 100, 50) / 100,
                "y_frac": _clamp(l.get("y", 50), 0, 100, 50) / 100,
            })

    try:
        img_clean, img_baked = build(
            template_path    = tmpl,
            primary          = hex_to_rgb(data.get("primary",   "#1a1a2e")),
            secondary        = hex_to_rgb(data.get("secondary", "#e63946")),
            accent           = hex_to_rgb(data.get("accent",    "#ffd700")),
            design           = data.get("design", "solid"),
            design_params    = {
                "angle":        angle,
                "stripe_width": stripe_width,
                "gap":          gap,
                "split":        split,
                "direction":    data.get("direction", "horizontal"),
                "depth":        depth,
                "feather":      feather,
                "h_offset":     h_offset,
                "v_offset":     v_offset,
                "cx_frac":      cx_frac,
                "cy_frac":      cy_frac,
            },
            texture          = data.get("texture", "none"),
            texture_opacity  = texture_opacity,
            template_opacity = template_opacity,
            overlay_design   = data.get("overlay_design", "none"),
            overlay_opacity  = overlay_opacity,
            logo_params      = logo_params,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    base_name = f"{car_id}_{int(time.time() * 1000)}"
    file_clean = f"{base_name}_clean.png"
    file_baked = f"{base_name}_baked.png"
    
    io_clean, io_baked = io.BytesIO(), io.BytesIO()
    img_clean.save(io_clean, 'PNG')
    img_baked.save(io_baked, 'PNG')
    
    PREVIEW_CACHE[file_clean] = io_clean.getvalue()
    PREVIEW_CACHE[file_baked] = io_baked.getvalue()
    
    if len(PREVIEW_CACHE) > MAX_CACHE_SIZE:
        PREVIEW_CACHE.popitem(last=False)
        PREVIEW_CACHE.popitem(last=False)
        
    return jsonify({"status": "ok", "image_clean": file_clean, "image_baked": file_baked})


# ---------------------------------------------------------------------------
# Preview + download from RAM
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
