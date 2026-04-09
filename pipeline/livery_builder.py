"""
Programmatic livery builder.

Flow:
  1. Draw a design layer (solid, stripes, gradient, sweep, etc.)
  2. Optionally blend a procedural texture (carbon, metal, matte)
  3. Composite the UV template on top at low opacity so panel seams show through
  4. Return a 2048x2048 RGB image ready for Trading Paints

No AI involved — fast, deterministic, reliable.
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 2048


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build(
    template_path: Path,
    primary: tuple,        # (R, G, B)
    secondary: tuple,
    accent: tuple,
    design: str = "solid",
    design_params: dict | None = None,
    texture: str = "none",
    texture_opacity: float = 0.25,
    template_opacity: float = 0.35,
) -> Image.Image:
    """
    Build a livery image.

    Args:
        template_path:    Path to template.png
        primary:          Main body color (R,G,B)
        secondary:        Stripe/secondary panel color
        accent:           Trim / outline color
        design:           One of: solid, racing_stripes, diagonal_stripes,
                          gradient, sweep, split, chevron
        design_params:    Dict of parameters for the chosen design
        texture:          none | carbon_fiber | brushed_metal | matte
        texture_opacity:  0–1, how strongly texture blends over color
        template_opacity: 0–1, how visible the UV template lines are on top

    Returns:
        PIL Image (RGB, 2048x2048)
    """
    dp = design_params or {}

    # 1. Design layer
    canvas = _make_design(primary, secondary, accent, design, dp)

    # 2. Texture overlay
    if texture != "none":
        from pipeline.textures import generate_texture
        tex = generate_texture(texture, SIZE)
        canvas = _blend_texture(canvas, tex, texture_opacity)

    # 3. Template overlay (shows panel seam lines)
    template = Image.open(template_path).convert("RGBA").resize((SIZE, SIZE))
    canvas = _overlay_template(canvas, template, template_opacity)

    return canvas


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# Design patterns
# ---------------------------------------------------------------------------

def _make_design(primary, secondary, accent, design, params) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), primary)
    draw = ImageDraw.Draw(img)

    if design == "solid":
        pass

    elif design == "racing_stripes":
        # Classic Le Mans style — one wide centre stripe + two thin accents
        # Angle tilts the stripes; direction controls vertical vs horizontal orientation
        w = params.get("stripe_width", 160)
        gap = params.get("gap", 25)
        angle = params.get("angle", 45)
        direction = params.get("direction", "vertical")
        shift = int(SIZE * math.tan(math.radians(angle % 180)))
        hs = shift // 2  # half-shift keeps the stripe visually centred

        if direction == "horizontal":
            # Stripes run left-to-right across the canvas
            cy = SIZE // 2
            draw.polygon([
                (0, cy - w // 2 - hs), (SIZE, cy - w // 2 + hs),
                (SIZE, cy + w // 2 + hs), (0, cy + w // 2 - hs),
            ], fill=secondary)
            ay = cy - w // 2 - gap - 40
            draw.polygon([
                (0, ay - hs), (SIZE, ay + hs),
                (SIZE, ay + 40 + hs), (0, ay + 40 - hs),
            ], fill=accent)
            by_ = cy + w // 2 + gap
            draw.polygon([
                (0, by_ - hs), (SIZE, by_ + hs),
                (SIZE, by_ + 40 + hs), (0, by_ + 40 - hs),
            ], fill=accent)
        else:
            # Stripes run top-to-bottom (vertical, default)
            cx = SIZE // 2
            draw.polygon([
                (cx - w // 2 - hs, 0), (cx + w // 2 - hs, 0),
                (cx + w // 2 + hs, SIZE), (cx - w // 2 + hs, SIZE),
            ], fill=secondary)
            lx = cx - w // 2 - gap - 40
            draw.polygon([
                (lx - hs, 0), (lx + 40 - hs, 0),
                (lx + 40 + hs, SIZE), (lx + hs, SIZE),
            ], fill=accent)
            rx = cx + w // 2 + gap
            draw.polygon([
                (rx - hs, 0), (rx + 40 - hs, 0),
                (rx + 40 + hs, SIZE), (rx + hs, SIZE),
            ], fill=accent)

    elif design == "diagonal_stripes":
        angle = params.get("angle", 45)
        w = params.get("stripe_width", 140)
        _draw_diagonal_stripes(draw, secondary, angle, w)
        # Thin accent between stripes
        _draw_diagonal_stripes(draw, accent, angle, 20,
                                offset_fraction=0.5 * w / SIZE)

    elif design == "gradient":
        direction = params.get("direction", "horizontal")
        _draw_gradient(img, primary, secondary, direction)

    elif design == "split":
        pos = params.get("split", 0.5)
        direction = params.get("direction", "horizontal")
        sp = int(SIZE * pos)
        if direction == "horizontal":
            draw.rectangle([0, sp, SIZE, SIZE], fill=secondary)
            draw.rectangle([0, sp - 6, SIZE, sp + 6], fill=accent)
        else:
            draw.rectangle([sp, 0, SIZE, SIZE], fill=secondary)
            draw.rectangle([sp - 6, 0, sp + 6, SIZE], fill=accent)

    elif design == "chevron":
        depth = params.get("depth", 0.35)
        _draw_chevron(draw, secondary, accent, depth)

    elif design == "sweep":
        _draw_sweep(draw, img, secondary, accent, params)

    elif design == "two_tone":
        # Diagonal two-tone split (common GT livery style)
        angle = params.get("angle", 30)
        _draw_diagonal_split(draw, secondary, accent, angle)

    return img


def _draw_diagonal_stripes(draw, color, angle_deg, stripe_width, offset_fraction=0.0):
    angle_rad = math.radians(angle_deg % 180)
    if abs(math.sin(angle_rad)) < 0.01:
        period = stripe_width * 2
        start = int(offset_fraction * period)
        for x in range(start - SIZE, SIZE * 2, period):
            draw.rectangle([x, 0, x + stripe_width, SIZE], fill=color)
        return

    tan_a = math.tan(angle_rad)
    period = stripe_width * 2
    offset_px = int(offset_fraction * period)
    for i in range(offset_px - SIZE * 2, SIZE * 2, period):
        pts = [
            (i, 0),
            (i + stripe_width, 0),
            (i + stripe_width + int(SIZE * tan_a), SIZE),
            (i + int(SIZE * tan_a), SIZE),
        ]
        draw.polygon(pts, fill=color)


def _draw_gradient(img, color1, color2, direction):
    arr = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    c1 = np.array(color1, dtype=float)
    c2 = np.array(color2, dtype=float)
    t = np.linspace(0, 1, SIZE)
    band = (c1[None, :] * (1 - t[:, None]) + c2[None, :] * t[:, None]).astype(np.uint8)
    if direction == "horizontal":
        arr[:] = band
    else:
        arr[:] = band[:, None, :]
        arr = arr.transpose(1, 0, 2)
    img.paste(Image.fromarray(arr), (0, 0))


def _draw_chevron(draw, secondary, accent, depth):
    px = int(SIZE * 0.55)
    half = SIZE // 2
    dy = int(SIZE * depth)
    # Secondary region (left/front of chevron)
    pts = [
        (0, 0),
        (px - dy, 0),
        (px, half),
        (px - dy, SIZE),
        (0, SIZE),
    ]
    draw.polygon(pts, fill=secondary)
    # Accent outline
    draw.line([(px - dy, 0), (px, half), (px - dy, SIZE)], fill=accent, width=18)


def _draw_sweep(draw, img, secondary, accent, params):
    """Dynamic angular band sweeping front-low to rear-high — common GT style."""
    pts_main = [
        (0, int(SIZE * 0.55)),
        (int(SIZE * 0.50), 0),
        (SIZE, 0),
        (SIZE, int(SIZE * 0.35)),
        (int(SIZE * 0.55), SIZE),
        (0, SIZE),
    ]
    draw.polygon(pts_main, fill=secondary)
    # Accent stripe at the leading edge of the sweep
    pts_accent = [
        (0, int(SIZE * 0.52)),
        (int(SIZE * 0.47), 0),
        (int(SIZE * 0.50), 0),
        (0, int(SIZE * 0.55)),
    ]
    draw.polygon(pts_accent, fill=accent)


def _draw_diagonal_split(draw, secondary, accent, angle_deg):
    """Clean diagonal two-tone split."""
    angle_rad = math.radians(angle_deg)
    tan_a = math.tan(angle_rad)
    mid = SIZE // 2
    offset = int(mid * tan_a)
    pts = [
        (0, 0),
        (SIZE, 0),
        (SIZE, mid - offset),
        (0, mid + offset),
    ]
    draw.polygon(pts, fill=secondary)
    # Accent divider line
    draw.line([(0, mid + offset), (SIZE, mid - offset)], fill=accent, width=14)


# ---------------------------------------------------------------------------
# Texture blending
# ---------------------------------------------------------------------------

def _blend_texture(canvas: Image.Image, texture: Image.Image, opacity: float) -> Image.Image:
    """Multiply-blend texture over canvas to add surface finish."""
    tex = texture.resize((SIZE, SIZE)).convert("RGB")
    c = np.array(canvas, dtype=float)
    t = np.array(tex, dtype=float) / 255.0
    # Multiply: darkens where texture is dark, neutral where texture is mid-grey (0.7+)
    blended = c * (t * opacity + (1.0 - opacity))
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------------------
# Template overlay
# ---------------------------------------------------------------------------

def _overlay_template(canvas: Image.Image, template: Image.Image, opacity: float) -> Image.Image:
    """
    Overlay ONLY the panel seam lines from the template, not the background color.

    Uses Canny edge detection to extract structural lines, then composites
    them as semi-transparent black lines over the design. The template's own
    background color is discarded so it never bleeds into the livery.
    """
    if opacity <= 0:
        return canvas

    import cv2

    # Convert template to greyscale for edge detection
    grey = np.array(template.convert("L"))

    # Canny edge detection — finds panel seam lines
    edges = cv2.Canny(grey, 25, 90)

    # Dilate slightly so thin lines are visible at 2048px
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    # Build transparent overlay: black lines where edges are, clear elsewhere
    overlay = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    line_alpha = int(np.clip(opacity * 320, 0, 220))  # scale opacity to line alpha
    overlay[edges > 0] = [10, 10, 10, line_alpha]

    canvas_rgba = canvas.convert("RGBA")
    line_layer = Image.fromarray(overlay, "RGBA")
    result = Image.alpha_composite(canvas_rgba, line_layer)
    return result.convert("RGB")
