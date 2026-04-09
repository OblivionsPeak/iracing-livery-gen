"""
iRacing Livery Generator — Lite
No GPU or AI required. Runs anywhere Python runs.

Local:   python app.py  → http://localhost:5002
Railway: auto-detected via Procfile
"""

import json
import os
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from pipeline.template_fetcher import fetch_single

app = Flask(__name__, template_folder="flask_templates")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB upload limit

CARS_JSON     = Path("cars.json")
TEMPLATES_DIR = Path("car_templates")
PREVIEWS_DIR  = Path("static/previews")

# Create runtime dirs (Railway has ephemeral fs — dirs must be created at startup)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def load_cars() -> dict:
    """Return flat {car_id: info} dict, ignoring group keys and _comment."""
    with open(CARS_JSON) as f:
        raw = json.load(f)
    flat = {}
    for key, val in raw.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict) and "display_name" not in val:
            # It's a group (GT3, GT4, etc.) — flatten its children
            for cid, info in val.items():
                flat[cid] = info
        else:
            flat[key] = val
    return flat


@app.route("/")
def index():
    cars = load_cars()
    # Group cars by series for the dropdown
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
    # If no car selected from dropdown, derive an id from the uploaded filename
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
            PSDImage.open(raw).composite().save(template_path)
        else:
            from PIL import Image
            Image.open(raw).convert("RGBA").save(template_path)
    except Exception as e:
        return jsonify({"error": f"Could not read file: {e}"}), 500

    from pipeline.template_processor import build_controlnet_map
    build_controlnet_map(template_path, destdir / "controlnet_map.png")
    return jsonify({"status": "ok", "car_id": car_id})


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

    try:
        img = build(
            template_path    = tmpl,
            primary          = hex_to_rgb(data.get("primary",   "#1a1a2e")),
            secondary        = hex_to_rgb(data.get("secondary", "#e63946")),
            accent           = hex_to_rgb(data.get("accent",    "#ffd700")),
            design           = data.get("design", "solid"),
            design_params    = {
                "angle":        float(data.get("angle", 45)),
                "stripe_width": int(data.get("stripe_width", 160)),
                "gap":          int(data.get("gap", 25)),
                "split":        float(data.get("split", 0.5)),
                "direction":    data.get("direction", "horizontal"),
                "depth":        float(data.get("depth", 0.35)),
                "feather":      int(data.get("feather", 60)),
            },
            texture          = data.get("texture", "none"),
            texture_opacity  = float(data.get("texture_opacity", 0.25)),
            template_opacity = float(data.get("template_opacity", 0.35)),
            overlay_design   = data.get("overlay_design", "none"),
            overlay_opacity  = float(data.get("overlay_opacity", 0.4)),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    filename = f"{car_id}_{int(time.time() * 1000)}.png"
    img.save(PREVIEWS_DIR / filename)
    return jsonify({"status": "ok", "image": filename})


# ---------------------------------------------------------------------------
# Preview + download
# ---------------------------------------------------------------------------

@app.route("/preview/<filename>")
def preview(filename):
    path = PREVIEWS_DIR / filename
    if not path.exists():
        return "Not found", 404
    return send_file(path, mimetype="image/png")


@app.route("/download/<filename>")
def download(filename):
    path = PREVIEWS_DIR / filename
    if not path.exists():
        return "Not found", 404
    return send_file(
        path,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
