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
    overlay_design: str = "none",
    overlay_opacity: float = 0.4,
    logo_params: "list | None" = None,
) -> Image.Image:
    """
    Build a livery image.
    """
    dp = design_params or {}

    # 1. Design layer
    canvas = _make_design(primary, secondary, accent, design, dp)

    # 2. Optional pattern overlay — blend a second fully-rendered design over the base
    if overlay_design and overlay_design != "none":
        ov_rgb   = _make_design(primary, secondary, accent, overlay_design, dp)
        base_arr = np.array(canvas, dtype=float)
        ov_arr   = np.array(ov_rgb, dtype=float)
        blended  = base_arr * (1.0 - overlay_opacity) + ov_arr * overlay_opacity
        canvas   = Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))

    # 3. Texture overlay
    if texture != "none":
        from pipeline.textures import generate_texture
        tex = generate_texture(texture, SIZE)
        canvas = _blend_texture(canvas, tex, texture_opacity)

    canvas_clean = canvas.copy()

    # 4. Template overlay (shows panel seam lines)
    if template_opacity > 0:
        edge_mask_path = template_path.parent / "edge_mask.png"
        if edge_mask_path.exists():
            canvas = _overlay_edge_mask(canvas, edge_mask_path, template_opacity)

    # 5. Optional logo/sponsor overlay array
    if logo_params and len(logo_params) > 0:
        for logo_obj in logo_params:
            lp = logo_obj.get("path")
            if lp and Path(lp).exists():
                canvas = _overlay_logo(canvas, lp, logo_obj)

    return canvas_clean, canvas


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

    elif design == "radial_gradient":
        cx = params.get("cx_frac", 0.5)
        cy = params.get("cy_frac", 0.5)
        _draw_radial_gradient(img, primary, secondary, cx, cy)

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
        depth    = params.get("depth", 0.35)
        h_offset = params.get("h_offset", 0.0)
        v_offset = params.get("v_offset", 0.0)
        _draw_chevron(draw, secondary, accent, depth, h_offset, v_offset)

    elif design == "sweep":
        _draw_sweep(draw, img, secondary, accent, params)

    elif design == "two_tone":
        # Diagonal two-tone split (common GT livery style)
        angle = params.get("angle", 30)
        _draw_diagonal_split(draw, secondary, accent, angle)

    elif design == "gradient_chevron":
        # Gradient fills the chevron shape; solid primary outside
        depth    = params.get("depth", 0.35)
        feather  = int(params.get("feather", 60))   # 0 = hard edge, 60+ = soft fade
        h_offset = params.get("h_offset", 0.0)
        v_offset = params.get("v_offset", 0.0)
        px_   = int(SIZE * (0.55 + h_offset))
        half  = int(SIZE * (0.5 + v_offset))
        dy    = int(SIZE * depth)
        # Build a gradient layer
        grad = Image.new("RGB", (SIZE, SIZE), primary)
        _draw_gradient(grad, primary, secondary, "horizontal")
        # Chevron mask — blur it to feather the edge into the primary color
        mask = Image.new("L", (SIZE, SIZE), 0)
        ImageDraw.Draw(mask).polygon(
            [(0, 0), (px_ - dy, 0), (px_, half), (px_ - dy, SIZE), (0, SIZE)],
            fill=255,
        )
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
        img.paste(grad, mask=mask)
        # Only draw hard accent line when edge is crisp (feather=0)
        if feather == 0:
            draw.line([(px_ - dy, 0), (px_, half), (px_ - dy, SIZE)], fill=accent, width=18)

    elif design == "harlequin":
        # Classic McLaren-style diamond grid — alternating primary/secondary diamonds
        tile_size = params.get("tile_size", 180)
        half_tile = tile_size // 2
        # Compute diamond centres covering the full canvas (with one extra ring for edges)
        cols = math.ceil(SIZE / tile_size) + 2
        rows = math.ceil(SIZE / tile_size) + 2
        cx_coords = np.arange(-1, cols) * tile_size + half_tile
        cy_coords = np.arange(-1, rows) * tile_size + half_tile
        cx_grid, cy_grid = np.meshgrid(cx_coords, cy_coords)
        cx_flat = cx_grid.flatten().astype(int)
        cy_flat = cy_grid.flatten().astype(int)
        # Column/row parity determines color (checkerboard)
        col_idx = np.arange(-1, cols)
        row_idx = np.arange(-1, rows)
        col_grid, row_grid = np.meshgrid(col_idx, row_idx)
        parity = (col_grid + row_grid).flatten() % 2
        for i in range(len(cx_flat)):
            cx_d, cy_d = cx_flat[i], cy_flat[i]
            color = secondary if parity[i] == 0 else primary
            pts = [
                (cx_d,             cy_d - half_tile),  # top
                (cx_d + half_tile, cy_d),               # right
                (cx_d,             cy_d + half_tile),   # bottom
                (cx_d - half_tile, cy_d),               # left
            ]
            draw.polygon(pts, fill=color)

    elif design == "pinstripe":
        # Very thin repeated diagonal lines over the primary color
        stripe_width = params.get("stripe_width", 8)
        angle = params.get("angle", 45)
        _draw_diagonal_stripes(draw, secondary, angle, stripe_width)

    elif design == "number_panel":
        # High-contrast rectangle zone for the race number (GT endurance style)
        cx = params.get("cx_frac", 0.5)
        cy = params.get("cy_frac", 0.5)
        x0 = int(SIZE * (cx - 0.15))
        y0 = int(SIZE * (cy - 0.20))
        x1 = int(SIZE * (cx + 0.15))
        y1 = int(SIZE * (cy + 0.20))
        border_w = 12
        trim_h = 8
        trim_gap = 20
        # Solid secondary fill
        draw.rectangle([x0, y0, x1, y1], fill=secondary)
        # Thick accent border
        draw.rectangle([x0, y0, x1, y1], outline=accent, width=border_w)
        # Thin accent trim lines above and below
        draw.rectangle(
            [x0, y0 - trim_gap - trim_h, x1, y0 - trim_gap],
            fill=accent,
        )
        draw.rectangle(
            [x0, y1 + trim_gap, x1, y1 + trim_gap + trim_h],
            fill=accent,
        )

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


def _draw_radial_gradient(img, color1, color2, cx_frac=0.5, cy_frac=0.5):
    """Circular gradient: color1 at (cx_frac, cy_frac), color2 at radius=1."""
    c1 = np.array(color1, dtype=float)
    c2 = np.array(color2, dtype=float)
    cx = SIZE * cx_frac
    cy = SIZE * cy_frac
    half = SIZE / 2.0          # normalisation radius stays fixed so scale is consistent
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    dist = np.sqrt(((x - cx) / half) ** 2 + ((y - cy) / half) ** 2)
    t = np.clip(dist, 0, 1)[..., None]
    arr = (c1 * (1 - t) + c2 * t).astype(np.uint8)
    img.paste(Image.fromarray(arr), (0, 0))


def _draw_chevron(draw, secondary, accent, depth, h_offset=0.0, v_offset=0.0):
    px = int(SIZE * (0.55 + h_offset))
    half = int(SIZE * (0.5 + v_offset))
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
    h_offset = params.get("h_offset", 0.0)
    pts_main = [
        (0, int(SIZE * 0.55)),
        (int(SIZE * (0.50 + h_offset)), 0),
        (SIZE, 0),
        (SIZE, int(SIZE * 0.35)),
        (int(SIZE * (0.55 + h_offset)), SIZE),
        (0, SIZE),
    ]
    draw.polygon(pts_main, fill=secondary)
    # Accent stripe at the leading edge of the sweep
    pts_accent = [
        (0, int(SIZE * 0.52)),
        (int(SIZE * (0.47 + h_offset)), 0),
        (int(SIZE * (0.50 + h_offset)), 0),
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
# Edge Mask Overlay
# ---------------------------------------------------------------------------

def _overlay_edge_mask(canvas: Image.Image, edge_mask_path: Path, opacity: float) -> Image.Image:
    """
    Overlays the pre-computed edge mask generated by Canny.
    """
    if opacity <= 0:
        return canvas

    em = Image.open(edge_mask_path).convert("RGBA").resize((SIZE, SIZE))
    em_arr = np.array(em)
    
    # edge_mask generated during upload uses White [255,255,255,255] for edges.
    edges = em_arr[:, :, 3]  # Use alpha channel if pure transparent png
    
    overlay = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    line_alpha = int(np.clip(opacity * 320, 0, 220))
    # Make the white edges appear as translucent black lines over the design
    overlay[edges > 128] = [10, 10, 10, line_alpha]

    canvas_rgba = canvas.convert("RGBA")
    line_layer = Image.fromarray(overlay, "RGBA")
    result = Image.alpha_composite(canvas_rgba, line_layer)
    return result.convert("RGB")


# ---------------------------------------------------------------------------
# Logo / sponsor overlay
# ---------------------------------------------------------------------------

def _overlay_logo(canvas: Image.Image, logo_path, params: dict) -> Image.Image:
    """Composite a logo PNG (with alpha) onto the canvas at a given position/scale."""
    logo = Image.open(logo_path).convert("RGBA")
    scale = params.get("scale", 0.20)       # fraction of canvas width
    target_w = int(SIZE * scale)
    aspect = logo.height / logo.width
    target_h = int(target_w * aspect)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)
    # x_frac, y_frac are the CENTER of the logo on the canvas
    x_frac = params.get("x_frac", 0.5)
    y_frac = params.get("y_frac", 0.5)
    x = int(SIZE * x_frac) - target_w // 2
    y = int(SIZE * y_frac) - target_h // 2
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(logo, (x, y), mask=logo)
    return canvas_rgba.convert("RGB")
