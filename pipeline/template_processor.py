"""
Converts a raw UV template PNG into a ControlNet-compatible edge map.

The edge map is what guides SD to respect panel lines and car geometry.
Process:
  1. Flatten alpha (white background)
  2. Convert to greyscale
  3. Canny edge detection
  4. Dilate edges slightly (improves ControlNet guidance strength)
  5. Save as 2048x2048 PNG
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image

TARGET_SIZE = 2048


def build_controlnet_map(
    template_path: Path,
    output_path: Path,
    canny_low: int = 50,
    canny_high: int = 150,
    dilate_px: int = 1,
) -> Path:
    """
    Process a UV template into a ControlNet Canny edge map.

    Args:
        template_path: Path to template.png (RGBA or RGB)
        output_path:   Where to save controlnet_map.png
        canny_low:     Lower threshold for Canny edge detection
        canny_high:    Upper threshold for Canny edge detection
        dilate_px:     Dilation kernel size (makes edges slightly thicker)

    Returns:
        Path to the saved edge map
    """
    print(f"  Processing edge map: {template_path.name} → {output_path.name}")

    img = Image.open(template_path).convert("RGBA")

    # Flatten alpha channel onto white background
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    background.paste(img, mask=img.split()[3])
    img_rgb = background.convert("RGB")

    # Resize to target
    img_rgb = img_rgb.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)

    # Convert to numpy for OpenCV
    arr = np.array(img_rgb)
    grey = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Canny edge detection
    edges = cv2.Canny(grey, canny_low, canny_high)

    # Dilate to thicken lines slightly
    if dilate_px > 0:
        kernel = np.ones((dilate_px + 1, dilate_px + 1), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    edge_img = Image.fromarray(edges)
    edge_img.save(output_path)

    print(f"    Saved: {output_path}")
    return output_path


def get_template_preview(car_id: str, templates_dir: Path = Path("car_templates")) -> Path | None:
    """Return path to the controlnet_map if it exists."""
    p = templates_dir / car_id / "controlnet_map.png"
    return p if p.exists() else None
