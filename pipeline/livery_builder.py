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
import io

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Vector support
SIZE = 2048

def _get_noise(size, scale=100.0):
    """Simple procedural noise using numpy for grunge effects."""
    from numpy.random import default_rng
    rng = default_rng()
    return rng.standard_normal((size, size))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build(
    template_path: Path,
    primary: tuple,        # (R, G, B)
    secondary: tuple,
    accent: tuple,
    layers: "list | None" = None,
    texture: str = "none",
    texture_opacity: float = 0.25,
    template_opacity: float = 0.35,
    grunge_amount: float = 0.0,
) -> tuple:
    """
    Build a livery image and its corresponding spec map.
    Returns (clean_livery, baked_livery, spec_map)
    """
    # 1. Initialize main (RGB) and spec (PBR) canvases
    # Spec Map Channel Map: Red=Metallic, Green=Roughness, Blue=Clearcoat
    main_canvas = Image.new("RGB", (SIZE, SIZE), primary)
    # Default spec: metallic=20 (base car paint), roughness=20 (gloss)
    spec_canvas = Image.new("RGB", (SIZE, SIZE), (20, 20, 0))
    
    layer_list = layers or []
    
    # Process layers in sequence (bottom to top)
    for layer in layer_list:
        l_type = layer.get("type", "design")
        l_id   = layer.get("id", "solid")
        l_params = layer.get("params", {})
        l_metallic = int(layer.get("metallic", 0) * 255)
        l_roughness = int(layer.get("roughness", 0.1) * 255)

        # A. Render the visual contribution; capture it so we can reuse it as the PBR mask
        pbr_mask = None
        if l_type == "design":
            layer_img = _make_design(primary, secondary, accent, l_id, l_params)
            main_canvas.paste(layer_img, (0, 0))
            pbr_mask = layer_img.convert("L")   # reuse render — no double work
        elif l_type == "logo":
            lp = l_params.get("path")
            if lp and Path(lp).exists():
                main_canvas = _overlay_logo(main_canvas, lp, l_params)
                pbr_mask = _make_logo_mask(lp, l_params)

        # B. Write PBR metallic/roughness to spec map using the same mask
        if pbr_mask is not None:
            pbr_fill = Image.new("RGB", (SIZE, SIZE), (l_metallic, l_roughness, 0))
            spec_canvas.paste(pbr_fill, (0, 0), mask=pbr_mask)

    # 2. Texture overlay (surface patterns)
    if texture != "none":
        from pipeline.textures import generate_texture
        tex = generate_texture(texture, SIZE)
        main_canvas = _blend_texture(main_canvas, tex, texture_opacity)

    # 3. Grunge overlay (weathering)
    if grunge_amount > 0:
        main_canvas = _apply_grunge(main_canvas, grunge_amount)

    # 4. UV Template (Panel Seams)
    canvas_clean = main_canvas.copy()
    if template_opacity > 0:
        edge_mask_path = template_path.parent / "edge_mask.png"
        applied = False
        if edge_mask_path.exists():
            main_canvas, applied = _overlay_edge_mask(main_canvas, edge_mask_path, template_opacity)
        if not applied and template_path.exists():
            # Edge mask missing or blank — composite the raw template directly
            main_canvas = _overlay_template_direct(main_canvas, template_path, template_opacity)

    # Return clean/baked visual and the one spec map
    return canvas_clean, main_canvas, spec_canvas


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
            # Thin hint of accent
            draw.rectangle([0, sp - 2, SIZE, sp + 2], fill=accent)
        else:
            draw.rectangle([sp, 0, SIZE, SIZE], fill=secondary)
            # Thin hint of accent
            draw.rectangle([sp - 2, 0, sp + 2, SIZE], fill=accent)

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

    elif design == "shard":
        _draw_shards(img, primary, secondary, accent, params)

    return img


def _draw_shards(img, primary, secondary, accent, params):
    """Tearing/fragmentation effect — aggressive car wrap style radiating from focal point."""
    cx_frac   = params.get("cx_frac", 0.35)
    cy_frac   = params.get("cy_frac", 0.55)
    count     = int(params.get("shard_count", 12))
    roughness = params.get("shard_roughness", params.get("roughness", 0.6))
    fade_r    = params.get("fade_radius", 0.3)

    cx = cx_frac * SIZE
    cy = cy_frac * SIZE

    y_grid, x_grid = np.mgrid[0:SIZE, 0:SIZE]
    dx = x_grid - cx
    dy = y_grid - cy
    dist = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)

    rng = np.random.default_rng(42)
    noise_map = rng.standard_normal((SIZE, SIZE)).astype(np.float32)
    noise_img = Image.fromarray(((noise_map + 3) / 6 * 255).clip(0, 255).astype(np.uint8), mode='L')
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(radius=40))
    noise_smooth = (np.array(noise_img, dtype=np.float32) / 255.0 - 0.5) * 2.0

    dist_norm = (dist / (SIZE * 0.7)).clip(0, 1)
    perturbation = noise_smooth * roughness * dist_norm * math.pi / count
    perturbed_angle = angle + perturbation

    shard_wave = np.sin(perturbed_angle * count)
    is_secondary = shard_wave > 0
    fade_mask = dist < (fade_r * SIZE)
    is_secondary[fade_mask] = False

    c1 = np.array(primary,   dtype=np.float32)
    c2 = np.array(secondary, dtype=np.float32)
    result = np.where(is_secondary[..., None], c2, c1).astype(np.uint8)
    img.paste(Image.fromarray(result), (0, 0))

    # Accent crack lines along shard boundaries
    edge_h = np.diff(is_secondary.astype(np.int8), axis=1)
    edge_v = np.diff(is_secondary.astype(np.int8), axis=0)
    crack = np.zeros((SIZE, SIZE), dtype=bool)
    crack[:, :-1] |= edge_h != 0
    crack[:-1, :] |= edge_v != 0
    crack[fade_mask] = False
    result_arr = np.array(img)
    result_arr[crack] = np.array(accent, dtype=np.uint8)
    img.paste(Image.fromarray(result_arr), (0, 0))


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
    # Accent outline (removed thick line for cleaner look)
    # draw.line([(px - dy, 0), (px, half), (px - dy, SIZE)], fill=accent, width=4)


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
    # Optional: Accent divider line (removed for cleaner two_tone)
    # draw.line([(0, mid + offset), (SIZE, mid - offset)], fill=accent, width=14)


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

def _overlay_edge_mask(canvas: Image.Image, edge_mask_path: Path, opacity: float):
    """
    Overlay the pre-computed edge mask. Returns (result_image, had_edges).
    had_edges=False means the mask was blank so the caller should use a fallback.
    """
    if opacity <= 0:
        return canvas, False

    em = Image.open(edge_mask_path).convert("RGBA").resize((SIZE, SIZE))
    em_arr = np.array(em)
    edges = em_arr[:, :, 3]  # alpha channel: 255 = edge, 0 = background

    edge_count = int((edges > 128).sum())
    if edge_count < 100:          # fewer than 100 edge pixels → treat as blank
        return canvas, False

    overlay = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    line_alpha = int(np.clip(opacity * 400, 0, 240))
    overlay[edges > 128] = [0, 0, 0, line_alpha]

    canvas_rgba = canvas.convert("RGBA")
    line_layer = Image.fromarray(overlay, "RGBA")
    result = Image.alpha_composite(canvas_rgba, line_layer)
    return result.convert("RGB"), True


def _overlay_logo(canvas: Image.Image, logo_path, params: dict) -> Image.Image:
    """Composite a logo (PNG/JPG/SVG) onto the canvas."""
    p = Path(logo_path)
    logo = None
    
    scale = params.get("scale", 0.20)
    target_w = int(SIZE * scale)
    
    if p.suffix.lower() == ".svg":
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            drawing = svg2rlg(str(p))
            s_factor = target_w / drawing.width
            drawing.width *= s_factor
            drawing.height *= s_factor
            drawing.scale(s_factor, s_factor)
            buf = io.BytesIO()
            renderPM.drawToFile(drawing, buf, fmt="PNG")
            buf.seek(0)
            logo = Image.open(buf).convert("RGBA")
        except ImportError:
            return canvas  # SVG support not available; skip logo silently
    else:
        # Standard raster logo
        logo = Image.open(logo_path).convert("RGBA")
        aspect = logo.height / logo.width
        target_h = int(target_w * aspect)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)

    # x_frac, y_frac are the CENTER of the logo on the canvas
    x_frac = params.get("x_frac", 0.5)
    y_frac = params.get("y_frac", 0.5)
    x = int(SIZE * x_frac) - logo.width // 2
    y = int(SIZE * y_frac) - logo.height // 2
    
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(logo, (x, y), mask=logo)
    return canvas_rgba.convert("RGB")


# ---------------------------------------------------------------------------
# PBR & Masking Helpers
# ---------------------------------------------------------------------------

def _make_logo_mask(logo_path, params: dict) -> "Image.Image | None":
    """Greyscale mask for a logo layer (just its alpha footprint)."""
    try:
        logo = Image.open(logo_path).convert("RGBA")
        scale = params.get("scale", 0.20)
        target_w = int(SIZE * scale)
        aspect = logo.height / logo.width
        target_h = int(target_w * aspect)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        mask = Image.new("L", (SIZE, SIZE), 0)
        x_frac = params.get("x_frac", params.get("x", 50) / 100)
        y_frac = params.get("y_frac", params.get("y", 50) / 100)
        x = int(SIZE * x_frac) - target_w // 2
        y = int(SIZE * y_frac) - target_h // 2
        mask.paste(logo.split()[-1], (x, y))
        return mask
    except Exception:
        return None


def _overlay_template_direct(canvas: Image.Image, template_path: Path, opacity: float) -> Image.Image:
    """Fallback: composite the raw UV template at low opacity to show panel seams."""
    tmpl = Image.open(template_path).convert("RGBA").resize((SIZE, SIZE))
    # Darken the template and reduce its opacity so it shows as subtle seam lines
    r, g, b, a = tmpl.split()
    # Dim the alpha by opacity so it's a subtle overlay
    a = a.point(lambda p: int(p * opacity * 0.6))
    tmpl = Image.merge("RGBA", (r, g, b, a))
    result = Image.alpha_composite(canvas.convert("RGBA"), tmpl)
    return result.convert("RGB")

def _apply_grunge(canvas: Image.Image, amount: float) -> Image.Image:
    """Adds procedural dirt and rubber marks."""
    if amount <= 0: return canvas
    noise = _get_noise(SIZE)
    # Normalize noise to 0-255
    noise = ((noise - noise.min()) / (noise.max() - noise.min()) * 255).astype(np.uint8)
    noise_img = Image.fromarray(noise).convert("L")
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Dirt color (dark brown/grey)
    dirt = Image.new("RGB", (SIZE, SIZE), (25, 20, 15))
    mask = noise_img.point(lambda p: p if p > 200 else 0) # Only high noise areas
    # Scale mask by user amount (0.0 to 1.0)
    mask = mask.point(lambda p: int(p * amount))
    
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(dirt, (0,0), mask=mask)
    return canvas_rgba.convert("RGB")
