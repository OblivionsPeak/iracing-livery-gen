"""
Automated template downloader.

Sources (tried in order):
  1. Trading Paints public template library
  2. Manual URL fallback (cars.json)

Templates are saved to car_templates/<car_id>/template.png
and edge maps auto-generated at car_templates/<car_id>/controlnet_map.png
"""

import json
import re
import zipfile
import io
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image

from pipeline.template_processor import build_controlnet_map

TEMPLATES_DIR = Path("car_templates")
CARS_JSON = Path("cars.json")
TP_TEMPLATES_URL = "https://www.tradingpaints.com/page/templates"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; livery-gen/1.0)"
}


def load_cars() -> dict:
    with open(CARS_JSON) as f:
        return json.load(f)


def save_cars(cars: dict):
    with open(CARS_JSON, "w") as f:
        json.dump(cars, f, indent=2)


# ---------------------------------------------------------------------------
# Trading Paints scraper
# ---------------------------------------------------------------------------

def scrape_trading_paints() -> dict[str, str]:
    """
    Scrape the Trading Paints template page and return a dict of
    {car_name_slug: download_url} for all listed templates.
    """
    print("Fetching Trading Paints template list...")
    resp = requests.get(TP_TEMPLATES_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    templates = {}

    # TP lists templates as links containing "template" in the href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "template" in href.lower() and (href.endswith(".zip") or href.endswith(".png") or href.endswith(".psd")):
            name = a.get_text(strip=True) or Path(href).stem
            slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            if slug:
                templates[slug] = href if href.startswith("http") else f"https://www.tradingpaints.com{href}"

    print(f"  Found {len(templates)} templates on Trading Paints.")
    return templates


def find_best_match(car_id: str, tp_templates: dict[str, str]) -> str | None:
    """
    Fuzzy-match a cars.json car_id against Trading Paints template slugs.
    e.g. 'porsche_911_gt3r' should match 'porsche_911_gt3_r_2023'
    """
    car_words = set(car_id.lower().replace("-", "_").split("_"))
    best_slug, best_score = None, 0

    for slug in tp_templates:
        slug_words = set(slug.split("_"))
        score = len(car_words & slug_words)
        if score > best_score:
            best_slug, best_score = slug, score

    return best_slug if best_score >= 2 else None


# ---------------------------------------------------------------------------
# Download + process
# ---------------------------------------------------------------------------

def download_template(car_id: str, url: str) -> Path | None:
    """Download template PNG/ZIP and extract to car_templates/<car_id>/"""
    dest_dir = TEMPLATES_DIR / car_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    template_path = dest_dir / "template.png"

    if template_path.exists():
        print(f"  [{car_id}] Template already exists, skipping download.")
        return template_path

    print(f"  [{car_id}] Downloading from {url} ...")
    resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")

    if "zip" in content_type or url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            # Find the first PNG or PSD in the zip
            for name in zf.namelist():
                if name.lower().endswith((".png", ".psd")):
                    with zf.open(name) as f:
                        img = Image.open(f).convert("RGBA")
                        img.save(template_path)
                    print(f"    Extracted {name} → template.png")
                    break
            else:
                print(f"    WARNING: No PNG/PSD found in zip for {car_id}")
                return None
    elif "png" in content_type or url.endswith(".png"):
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img.save(template_path)
    elif url.endswith(".psd"):
        # Save raw PSD then flatten with psd-tools
        psd_path = dest_dir / "template.psd"
        psd_path.write_bytes(resp.content)
        _flatten_psd(psd_path, template_path)
    else:
        print(f"    WARNING: Unrecognised content type '{content_type}' for {car_id}")
        return None

    return template_path


def _flatten_psd(psd_path: Path, out_path: Path):
    """Flatten a PSD file to PNG using psd-tools."""
    from psd_tools import PSDImage
    psd = PSDImage.open(psd_path)
    img = psd.composite()
    img.save(out_path)
    print(f"    Flattened PSD → template.png")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fetch_all_templates(force: bool = False):
    """
    For every car in cars.json, download its template and generate
    the ControlNet edge map if not already present.
    """
    cars = load_cars()
    tp_templates = scrape_trading_paints()

    for car_id, car_info in cars.items():
        template_path = TEMPLATES_DIR / car_id / "template.png"
        map_path = TEMPLATES_DIR / car_id / "controlnet_map.png"

        if map_path.exists() and not force:
            print(f"[{car_id}] Already processed, skipping.")
            continue

        # Try explicit URL from cars.json first
        url = car_info.get("template_url")

        if not url:
            match = find_best_match(car_id, tp_templates)
            if match:
                url = tp_templates[match]
                print(f"[{car_id}] Matched TP template: {match}")
            else:
                print(f"[{car_id}] WARNING: No template URL found — add manually to cars.json")
                continue

        result = download_template(car_id, url)
        if result:
            build_controlnet_map(result, map_path)
            print(f"[{car_id}] Done.")


def fetch_single(car_id: str, force: bool = False, manual_url: str | None = None):
    """Fetch and process template for one car."""
    cars = load_cars()
    if car_id not in cars:
        raise ValueError(f"Car '{car_id}' not found in cars.json")

    map_path = TEMPLATES_DIR / car_id / "controlnet_map.png"
    if map_path.exists() and not force:
        print(f"[{car_id}] Already processed.")
        return

    # Priority: manual URL passed in > cars.json url > Trading Paints scrape
    url = manual_url or cars[car_id].get("template_url")

    if not url:
        print(f"[{car_id}] No manual URL — trying Trading Paints scraper...")
        try:
            tp_templates = scrape_trading_paints()
            match = find_best_match(car_id, tp_templates)
            if match:
                url = tp_templates[match]
                print(f"[{car_id}] Matched: {match} → {url}")
        except Exception as e:
            print(f"[{car_id}] Scraper failed: {e}")

    if not url:
        raise RuntimeError(
            f"Could not find a template for '{car_id}'. "
            f"Go to tradingpaints.com/page/templates, find the {cars[car_id]['display_name']}, "
            f"right-click the download button, copy the link, and paste it into the URL field."
        )

    # Save URL back to cars.json for next time
    if manual_url and not cars[car_id].get("template_url"):
        cars[car_id]["template_url"] = manual_url
        save_cars(cars)

    result = download_template(car_id, url)
    if result:
        build_controlnet_map(result, map_path)
        print(f"[{car_id}] Done.")


if __name__ == "__main__":
    fetch_all_templates()
