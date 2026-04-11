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
from PIL import Image, ImageDraw, ImageFilter, ImageChops

# Vector support
DEFAULT_SIZE = 2048

def _get_noise(size, scale=100.0):
    """Simple procedural noise using numpy for grunge effects."""
    from numpy.random import default_rng
    rng = default_rng()
    return rng.standard_normal((size, size))


def hex_to_rgb(hex_str: str) -> tuple:
    """Utility to convert #RRGGBB to (R, G, B) tuple."""
    if not hex_str: return (0, 0, 0)
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


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
    base_metallic: float = 0.0,
    base_roughness: float = 0.1,
    size: int = DEFAULT_SIZE
) -> tuple:
    """
    Build a livery image and its corresponding spec map at the requested 'size'.
    Returns (clean_livery, baked_livery, spec_map)
    """
    S = size
    # 1. Initialize main (RGBA) and spec (PBR) canvases
    # Spec Map Channel Map: Red=Metallic, Green=Roughness, Blue=Clearcoat
    main_canvas = Image.new("RGBA", (S, S), primary + (255,))
    
    # Base spec: metallic and roughness from payload
    bm = int(base_metallic * 255)
    br = int(base_roughness * 255)
    spec_canvas = Image.new("RGB", (S, S), (bm, br, 0))
    
    layer_list = layers or []
    
    # Process layers in sequence (bottom to top)
    for layer in layer_list:
        l_type = layer.get("type", "design")
        l_id   = layer.get("id", "solid")
        l_params = layer.get("params", {})
        l_metallic = int(layer.get("metallic", 0) * 255)
        l_roughness = int(layer.get("roughness", 0.1) * 255)
        l_opacity = float(layer.get("opacity", 1.0))

        # Per-layer color overrides — fall back to global palette if not set or toggled off
        use_custom = bool(layer.get("use_custom_colors"))
        def _ov(key, fallback):
            v = layer.get(key, "")
            return hex_to_rgb(v) if (use_custom and v and len(v) == 7) else fallback
        l_primary   = _ov("override_primary",   primary)
        l_secondary = _ov("override_secondary", secondary)
        l_accent    = _ov("override_accent",    accent)

        layer_img = None
        pbr_mask = None

        # A. Render the visual contribution
        if l_type == "design":
            layer_img = _make_design(l_primary, l_secondary, l_accent, l_id, l_params, size=S)

        elif l_type == "logo":
            lp = l_params.get("path")
            if lp and Path(lp).exists():
                layer_img = _make_logo_img(lp, l_params, size=S)

        # Composite and extract PBR
        if layer_img:
            # Apply flat opacity
            if l_opacity < 1.0:
                layer_img.putalpha(layer_img.split()[3].point(lambda i: int(i * l_opacity)))

            # Apply fade-direction gradient over alpha
            fade = l_params.get("fade_direction", "none")
            if fade != "none":
                layer_img = _apply_fade(layer_img, fade, S)

            main_canvas = Image.alpha_composite(main_canvas, layer_img)
            pbr_mask = layer_img.split()[3]

            # B. Write PBR metallic/roughness to spec map using the layer's opacity mask
            pbr_fill = Image.new("RGB", (S, S), (l_metallic, l_roughness, 0))
            spec_canvas.paste(pbr_fill, (0, 0), mask=pbr_mask)

    # Convert main back to RGB for finishing
    main_canvas = main_canvas.convert("RGB")

    # 2. Texture overlay (surface patterns)
    if texture != "none":
        from pipeline.textures import generate_texture
        tex = generate_texture(texture, S)
        main_canvas = _blend_texture(main_canvas, tex, texture_opacity, size=S)

    # 3. Grunge overlay (weathering)
    if grunge_amount > 0:
        main_canvas = _apply_grunge(main_canvas, grunge_amount, size=S)

    # 4. UV Template (Panel Seams)
    canvas_clean = main_canvas.copy()
    if template_opacity > 0 and template_path.exists():
        edge_mask_path = template_path.parent / "edge_mask.png"
        
        if edge_mask_path.exists():
            # If we have a crisp wireframe mask, use only that to avoid the template's background color (e.g. blue)
            main_canvas, _ = _overlay_edge_mask(main_canvas, edge_mask_path, template_opacity, size=S)
        else:
            # Fallback to direct hard-light overlay if edge mask generation failed
            main_canvas = _overlay_template_direct(main_canvas, template_path, template_opacity, size=S)

    # Return clean/baked visual and the one spec map
    return canvas_clean, main_canvas, spec_canvas


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# Design patterns
# ---------------------------------------------------------------------------

def _make_design(primary, secondary, accent, design, params, size=DEFAULT_SIZE) -> Image.Image:
    S = size
    # CRITICAL: Now using RGBA canvas to support proper layer compositing instead of destructive RGB pastes.
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if design == "solid":
        pass

    elif design == "racing_stripes":
        w         = params.get("stripe_width", 160)
        gap       = params.get("gap", 25)
        angle     = params.get("angle", 45)
        count     = max(1, int(params.get("count", 3)))
        direction = params.get("direction", "vertical")
        shift     = int(S * math.tan(math.radians(angle % 180)))
        hs        = shift // 2

        # Total block of stripes centred on the canvas
        total = count * w + (count - 1) * gap
        start = S // 2 - total // 2

        for i in range(count):
            color = secondary if i % 2 == 0 else accent
            p0 = start + i * (w + gap)
            p1 = p0 + w

            if direction == "horizontal":
                draw.polygon([
                    (0, p0 - hs), (S, p0 + hs),
                    (S, p1 + hs), (0, p1 - hs),
                ], fill=color)
            else:
                draw.polygon([
                    (p0 - hs, 0), (p1 - hs, 0),
                    (p1 + hs, S), (p0 + hs, S),
                ], fill=color)

    elif design == "diagonal_stripes":
        angle = params.get("angle", 45)
        w = params.get("stripe_width", 140)
        _draw_diagonal_stripes(draw, secondary, angle, w, size=S)
        # Thin accent between stripes
        _draw_diagonal_stripes(draw, accent, angle, 20,
                                offset_fraction=0.5 * w / S, size=S)

    elif design == "gradient":
        direction = params.get("direction", "horizontal")
        angle_deg = float(params.get("angle", 45))
        _draw_gradient(img, primary, secondary, direction, angle_deg, size=S)

    elif design == "radial_gradient":
        cx = params.get("cx_frac", 0.5)
        cy = params.get("cy_frac", 0.5)
        _draw_radial_gradient(img, primary, secondary, cx, cy, size=S)

    elif design == "split":
        pos = params.get("split", 0.5)
        direction = params.get("direction", "horizontal")
        sp = int(S * pos)
        if direction == "horizontal":
            draw.rectangle([0, sp, S, S], fill=secondary)
            # Thin hint of accent
            draw.rectangle([0, sp - 2, S, sp + 2], fill=accent)
        else:
            draw.rectangle([sp, 0, S, S], fill=secondary)
            # Thin hint of accent
            draw.rectangle([sp - 2, 0, sp + 2, S], fill=accent)

    elif design == "chevron":
        depth    = params.get("depth", 0.35)
        h_offset = params.get("h_offset", 0.0)
        v_offset = params.get("v_offset", 0.0)
        _draw_chevron(draw, secondary, accent, depth, h_offset, v_offset, size=S)

    elif design == "sweep":
        _draw_sweep(draw, img, secondary, accent, params, size=S)

    elif design == "two_tone":
        # Diagonal two-tone split (common GT livery style)
        angle = params.get("angle", 30)
        _draw_diagonal_split(draw, secondary, accent, angle, size=S)

    elif design == "gradient_chevron":
        depth    = params.get("depth", 0.35)
        feather  = int(params.get("feather", 60))
        h_offset = params.get("h_offset", 0.0)
        v_offset = params.get("v_offset", 0.0)
        px_   = int(S * (0.55 + h_offset))
        half  = int(S * (0.5 + v_offset))
        dy    = int(S * depth)
        
        grad = Image.new("RGBA", (S, S), (0,0,0,0))
        _draw_gradient(grad, primary, secondary, "horizontal", size=S)
        
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).polygon(
            [(0, 0), (px_ - dy, 0), (px_, half), (px_ - dy, S), (0, S)],
            fill=255,
        )
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
            
        grad.putalpha(mask)
        img.paste(grad, (0,0), mask=grad)
        # Only draw hard accent line when edge is crisp (feather=0)
        if feather == 0:
            draw.line([(px_ - dy, 0), (px_, half), (px_ - dy, S)], fill=accent, width=max(4, int(18 * S / DEFAULT_SIZE)))

    elif design == "harlequin":
        # Classic McLaren-style diamond grid — alternating primary/secondary diamonds
        tile_size = params.get("tile_size", 180)
        half_tile = tile_size // 2
        # Compute diamond centres covering the full canvas (with one extra ring for edges)
        cols = math.ceil(S / tile_size) + 2
        rows = math.ceil(S / tile_size) + 2
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
        _draw_diagonal_stripes(draw, secondary, angle, stripe_width, size=S)

    elif design == "checkered":
        _draw_checkered(img, primary, secondary, accent, params, size=S)

    elif design == "hexagon":
        _draw_hexagon_grid(img, primary, secondary, accent, params, size=S)

    elif design == "shard":
        _draw_shards(img, primary, secondary, accent, params, size=S)

    elif design == "tearing":
        _draw_tearing(img, primary, secondary, accent, params, size=S)

    elif design == "digital_camo":
        _draw_digital_camo(img, primary, secondary, accent, params, size=S)

    elif design == "speed_blur":
        _draw_speed_blur(img, primary, secondary, accent, params, size=S)

    elif design == "topographic":
        _draw_topographic(img, primary, secondary, accent, params, size=S)

    elif design == "circuit":
        _draw_circuit(img, primary, secondary, accent, params, size=S)

    elif design == "splatter":
        _draw_splatter(img, primary, secondary, accent, params, size=S)

    elif design == "sunburst":
        _draw_sunburst(img, primary, secondary, accent, params, size=S)

    # Universal Scaling and Positioning
    scale_frac = float(params.get("scale", 1.0))
    # Clamp scale to prevent memory exhaustion (max 8x)
    scale_frac = max(0.01, min(scale_frac, 8.0))
    pos_x = float(params.get("pos_x", 0.0))
    pos_y = float(params.get("pos_y", 0.0))
    
    if scale_frac != 1.0 or pos_x != 0.0 or pos_y != 0.0:
        if scale_frac == 1.0:
            # Full screen pattern: wrap it seamlessly
            img = ImageChops.offset(img, int(pos_x * S), int(pos_y * S))
        else:
            # Scaled pattern: treat like a localized decal on transparent background
            target_size = int(S * scale_frac)
            scaled = img.resize((target_size, target_size), Image.LANCZOS)
            
            # Place it according to pos_x, pos_y. 
            # 0,0 is center. -1 is left/top, 1 is right/bottom.
            center_x = int(S/2 + pos_x * (S/2))
            center_y = int(S/2 + pos_y * (S/2))
            
            paste_x = center_x - target_size // 2
            paste_y = center_y - target_size // 2
            
            out = Image.new("RGBA", (S, S), (0,0,0,0))
            out.paste(scaled, (paste_x, paste_y))
            img = out

    return img


def _draw_diagonal_stripes(draw, color, angle, width, offset_fraction=0.0, size=DEFAULT_SIZE):
    """Utility to draw repeated diagonal lines across the whole canvas."""
    S = size
    angle_rad = math.radians(angle)
    # Distance between stripe centers
    stride = width * 2
    
    # Range that covers the whole viewport after rotation
    diag = int(S * 1.5)
    for i in range(-diag, diag, stride):
        d = i + offset_fraction * stride
        # Line: x*cos + y*sin = d
        # Find intersections with image boundaries
        if math.sin(angle_rad) == 0: # vertical
            draw.line([(d, 0), (d, S)], fill=color, width=width)
        elif math.cos(angle_rad) == 0: # horizontal
            draw.line([(0, d), (S, d)], fill=color, width=width)
        else:
            # General case: draw a long enough line
            p1 = (d * math.cos(angle_rad) - 2*S * math.sin(angle_rad), d * math.sin(angle_rad) + 2*S * math.cos(angle_rad))
            p2 = (d * math.cos(angle_rad) + 2*S * math.sin(angle_rad), d * math.sin(angle_rad) - 2*S * math.cos(angle_rad))
            draw.line([p1, p2], fill=color, width=width)

def _draw_gradient(img, c1, c2, direction="horizontal", angle_deg=45, size=DEFAULT_SIZE):
    """Linear color transition. direction='angle' uses angle_deg for free rotation."""
    S = size
    if direction == "angle":
        y_g, x_g = np.mgrid[0:S, 0:S]
        rad = math.radians(angle_deg)
        # Project each pixel onto the gradient axis; normalise to [0,1]
        proj = (x_g - S / 2) * math.cos(rad) + (y_g - S / 2) * math.sin(rad)
        t = (proj / (S * 0.707) * 0.5 + 0.5).clip(0, 1).astype(np.float32)
        c1a = np.array(list(c1) + [255], dtype=np.float32)
        c2a = np.array(list(c2) + [255], dtype=np.float32)
        blended = (c1a * (1 - t[:, :, None]) + c2a * t[:, :, None]).astype(np.uint8)
        img.paste(Image.fromarray(blended, "RGBA"), (0, 0))
    else:
        grad = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(grad)
        for i in range(S):
            d.line([(0, i), (S, i)] if direction == "vertical" else [(i, 0), (i, S)],
                   fill=int(255 * i / S))
        layer_c2 = Image.new("RGBA", (S, S), tuple(list(c2) + [255]))
        img.paste(layer_c2, (0, 0), mask=grad)

def _draw_radial_gradient(img, c1, c2, cx_f=0.5, cy_f=0.5, size=DEFAULT_SIZE):
    """Circular color transition from focal point."""
    S = size
    y, x = np.mgrid[0:S, 0:S]
    dist = np.sqrt((x - cx_f*S)**2 + (y - cy_f*S)**2)
    mask_arr = (dist / (S * 0.7) * 255).clip(0, 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr)
    
    layer_c2 = Image.new("RGBA", (S, S), tuple(list(c2) + [255]))
    img.paste(layer_c2, (0, 0), mask=mask)

def _draw_chevron(draw, secondary, accent, depth, h_off, v_off, size=DEFAULT_SIZE):
    """Modern V-shaped design."""
    S = size
    px = int(S * (0.5 + h_off))
    py = int(S * (0.5 + v_off))
    dy = int(S * depth)
    pts = [(0, py - dy), (px, py), (0, py + dy), (0, S), (S, S), (S, 0), (0, 0)]
    draw.polygon(pts, fill=secondary)
    draw.line([(0, py - dy), (px, py), (0, py + dy)], fill=accent, width=max(2, int(12 * S / DEFAULT_SIZE)))

def _draw_diagonal_split(draw, color2, accent, angle, size=DEFAULT_SIZE):
    """Two-tone diagonal cut."""
    S = size
    rad = math.radians(angle)
    # Simplified: draw a giant polygon covering half the screen
    dist = S * 1.5
    p1 = (int(S/2 - dist*math.cos(rad+math.pi/2)), int(S/2 - dist*math.sin(rad+math.pi/2)))
    p2 = (int(S/2 + dist*math.cos(rad+math.pi/2)), int(S/2 + dist*math.sin(rad+math.pi/2)))
    # Polygon that covers everything "below" the line
    pts = [p1, p2, (S*2, S*2), (-S, S*2)]
    draw.polygon(pts, fill=color2)
    draw.line([p1, p2], fill=accent, width=max(2, int(8 * S / DEFAULT_SIZE)))


def _draw_sweep(draw, img, secondary, accent, params, size=DEFAULT_SIZE):
    """Dynamic angular band sweeping front-low to rear-high — common GT style."""
    S = size
    h_offset = params.get("h_offset", 0.0)
    pts_main = [
        (0, int(S * 0.55)),
        (int(S * (0.50 + h_offset)), 0),
        (S, 0),
        (S, int(S * 0.35)),
        (int(S * (0.55 + h_offset)), S),
        (0, S),
    ]
    draw.polygon(pts_main, fill=secondary)
    # Accent stripe at the leading edge of the sweep
    pts_accent = [
        (0, int(S * 0.52)),
        (int(S * (0.47 + h_offset)), 0),
        (int(S * (0.50 + h_offset)), 0),
        (0, int(S * 0.55)),
    ]
    draw.polygon(pts_accent, fill=accent)


def _draw_shards(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Tearing/fragmentation effect — aggressive car wrap style radiating from focal point."""
    S = size
    cx_frac   = params.get("cx_frac", 0.35)
    cy_frac   = params.get("cy_frac", 0.55)
    count     = int(params.get("shard_count", 12))
    roughness = params.get("shard_roughness", params.get("roughness", 0.6))
    fade_r    = params.get("fade_radius", 0.3)

    cx = cx_frac * S
    cy = cy_frac * S

    y_grid, x_grid = np.mgrid[0:S, 0:S]
    dx = x_grid - cx
    dy = y_grid - cy
    dist = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)

    rng = np.random.default_rng(24)
    noise_map = rng.standard_normal((S//2, S//2)).astype(np.float32)
    noise_img = Image.fromarray(((noise_map + 3) / 6 * 255).clip(0, 255).astype(np.uint8), mode='L')
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(radius=max(1, int(40 * S / DEFAULT_SIZE))))
    noise_smooth = (np.array(noise_img, dtype=np.float32) / 255.0 - 0.5) * 2.0

    dist_norm = (dist / (S * 0.7)).clip(0, 1)
    perturbation = noise_smooth * roughness * dist_norm * math.pi / count
    perturbed_angle = angle + perturbation

    shard_wave = np.sin(perturbed_angle * count)
    is_secondary = shard_wave > 0
    fade_mask = dist < (fade_r * S)
    is_secondary[fade_mask] = False

    c1 = np.array([0, 0, 0, 0], dtype=np.uint8)
    c2 = np.array(list(secondary) + [255], dtype=np.uint8)
    result = np.where(is_secondary[..., None], c2, c1).astype(np.uint8)
    img.paste(Image.fromarray(result), (0, 0))

    # Accent crack lines along shard boundaries
    edge_h = np.diff(is_secondary.astype(np.int8), axis=1, append=0)
    edge_v = np.diff(is_secondary.astype(np.int8), axis=0, append=0)
    crack = np.zeros((S, S), dtype=bool)
    crack |= edge_h != 0
    crack |= edge_v != 0
    crack[fade_mask] = False
    
    arr = np.array(img)
    arr[crack] = np.array(list(accent) + [255], dtype=np.uint8)
    img.paste(Image.fromarray(arr), (0, 0))

    img.paste(Image.fromarray(arr), (0, 0))


def _draw_tearing(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """
    High-Speed Tearing effect — Highly anisotropic streaks disintegrating across a boundary.
    Matches modern GT3 'shredded camo' style graphics.
    """
    S = size
    angle_deg = params.get("angle", 0)
    density   = params.get("shred_density", 0.4)
    roughness = params.get("roughness", 0.7)

    angle_rad = math.radians(angle_deg)
    y_g, x_g = np.mgrid[0:S, 0:S]
    
    # Transform to directional axes (u is direction of tear)
    u = (x_g - S/2) * math.cos(angle_rad) + (y_g - S/2) * math.sin(angle_rad)
    
    # 1. Base gradient along U direction (tear direction fading out)
    u_norm = -u / (S / 2.0)
    grad = u_norm.astype(np.float32)
    
    rng = np.random.default_rng(24)

    # 2. Hard, long anisotropic streaks (v-axis is the detail layer)
    # Using 128 here instead of 32 for thicker, more intentional 'torn' bands
    # Stretching the noise on the U axis (S//2) vs high-contrast on V axis (S//128)
    base_noise = rng.uniform(-1, 1, (S//2, S//128)).astype(np.float32)
    S_large = int(S * 1.5) # Overdraw so rotation doesn't have blank corners
    base_img = Image.fromarray(((base_noise+1)/2*255).astype(np.uint8)).resize((S_large, S_large), Image.BICUBIC)
    
    # Rotate (PIL rotates counter-clockwise by default, we apply -angle to match Cartesian)
    rot_img = base_img.rotate(-angle_deg, resample=Image.BICUBIC)
    left = (S_large - S) // 2
    rot_cropped = rot_img.crop((left, left, left+S, left+S))
    streaks_arr = (np.array(rot_cropped, dtype=np.float32) / 255.0 - 0.5) * 2.0
    
    # 3. Medium Noise for boundary jitter
    med_noise = rng.uniform(-1, 1, (S//4, S//8)).astype(np.float32)
    med_img = Image.fromarray(((med_noise+1)/2*255).astype(np.uint8)).resize((S_large, S_large), Image.BILINEAR)
    rot_med = med_img.rotate(-angle_deg, resample=Image.BILINEAR).crop((left, left, left+S, left+S))
    med_arr = (np.array(rot_med, dtype=np.float32) / 255.0 - 0.5) * 0.8
    
    # 4. Composite height map
    mask_val = grad + streaks_arr * roughness + med_arr * (roughness * 0.5)
    
    # 5. Flying flecks (splatter) randomly appearing in the transition zone
    flecks = rng.uniform(0, 1, (S, S))
    is_fleck = (flecks > (1.0 - density * 0.05)) & (np.abs(mask_val) < 0.4)
    
    # Threshold at 0
    is_sec = (mask_val > 0) | is_fleck
    
    # Draw to RGBA layer
    c1 = np.array([0, 0, 0, 0], dtype=np.uint8)
    
    fill_pat = params.get("fill_pattern", "solid")
    
    # Parse color overrides if present
    f_pri_str = params.get("fill_primary", "")
    f_sec_str = params.get("fill_secondary", "")
    f_acc_str = params.get("fill_accent", "")
    
    # Note: hex_to_rgb is globally available in livery_builder
    f_pri = hex_to_rgb(f_pri_str) if f_pri_str else primary
    f_sec = hex_to_rgb(f_sec_str) if f_sec_str else secondary
    f_acc = hex_to_rgb(f_acc_str) if f_acc_str else accent

    if fill_pat == "digital_camo":
        fill_img = Image.new("RGBA", (S, S), (0,0,0,0))
        _draw_digital_camo(fill_img, f_pri, f_sec, f_acc, params, size=S)
        c2 = np.array(fill_img)
    elif fill_pat == "topographic":
        fill_img = Image.new("RGBA", (S, S), (0,0,0,0))
        _draw_topographic(fill_img, f_pri, f_sec, f_acc, params, size=S)
        c2 = np.array(fill_img)
    elif fill_pat == "circuit":
        fill_img = Image.new("RGBA", (S, S), (0,0,0,0))
        _draw_circuit(fill_img, f_pri, f_sec, f_acc, params, size=S)
        c2 = np.array(fill_img)
    else:
        # Default solid color
        c2 = np.array(list(f_sec) + [255], dtype=np.uint8)
        
    res = np.where(is_sec[..., None], c2, c1).astype(np.uint8)
    img.paste(Image.fromarray(res), (0, 0))
    
    # Accent Highlights on Tear Edges
    edge_h = np.diff(is_sec.astype(np.int8), axis=1, append=0)
    edge_v = np.diff(is_sec.astype(np.int8), axis=0, append=0)
    crack = np.zeros((S, S), dtype=bool)
    crack |= edge_h != 0
    crack |= edge_v != 0
    
    arr = np.array(img)
    arr[crack] = np.array(list(accent) + [255], dtype=np.uint8)
    img.paste(Image.fromarray(arr), (0, 0))

def _draw_digital_camo(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Military/Drift style block camo."""
    S = size
    grid_size = int(params.get("tile_size", 64) * S / DEFAULT_SIZE)
    roughness = params.get("roughness", 0.4)
    
    cols, rows = S // grid_size + 1, S // grid_size + 1
    rng = np.random.default_rng(13)
    # 0=primary, 1=secondary, 2=accent
    choices = rng.choice([0, 1, 2], size=(rows, cols), p=[1.0-roughness, roughness*0.7, roughness*0.3])
    
    # Upscale to full canvas
    full_mask = choices.repeat(grid_size, axis=0).repeat(grid_size, axis=1)[:S, :S]
    
    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[full_mask == 0] = list(primary) + [255]
    res[full_mask == 1] = list(secondary) + [255]
    res[full_mask == 2] = list(accent) + [255]
    img.paste(Image.fromarray(res), (0,0))

def _draw_speed_blur(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Anisotropic noise stretching for a high-speed motion effect."""
    S = size
    angle = math.radians(params.get("angle", 0))
    roughness = params.get("roughness", 0.5)
    
    y, x = np.mgrid[0:S, 0:S]
    u = (x - S/2) * math.cos(angle) + (y - S/2) * math.sin(angle)
    # We only care about the axis perpendicular to flight for the noise seed
    v = -(x - S/2) * math.sin(angle) + (y - S/2) * math.cos(angle)
    
    rng = np.random.default_rng(99)
    # Generate 1D noise for the cross-section
    seed = rng.standard_normal(S // 4).astype(np.float32)
    noise_1d = Image.fromarray(((seed + 3)/6 * 255).astype(np.uint8), "L").resize((1, S), Image.BICUBIC)
    noise_arr = np.array(noise_1d).astype(np.float32) / 255.0
    
    # Broadcast across the U axis
    mask = np.tile(noise_arr, (1, S))
    # Distortion
    res_mask = mask > (1.0 - roughness)
    
    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[res_mask] = list(secondary) + [255]
    
    # Thin accent highlight lines
    edges = np.diff(res_mask.astype(np.int8), axis=0, append=0) != 0
    res[edges] = list(accent) + [255]
    img.paste(Image.fromarray(res), (0,0))

def _draw_topographic(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Contour lines based on thresholded multi-octave noise."""
    S = size
    freq = params.get("frequency", 4.0)
    roughness = params.get("roughness", 0.3)
    
    rng = np.random.default_rng(55)
    # Octave 1: Large features
    n1 = rng.standard_normal((S//16, S//16)).astype(np.float32)
    n1_img = Image.fromarray(((n1 + 3)/6 * 255).astype(np.uint8), "L").resize((S, S), Image.BICUBIC)
    # Octave 2: Small features
    n2 = rng.standard_normal((S//4, S//4)).astype(np.float32)
    n2_img = Image.fromarray(((n2 + 3)/6 * 255).astype(np.uint8), "L").resize((S, S), Image.BILINEAR)
    
    noise = (np.array(n1_img).astype(np.float32)/255.0 * 0.7 + np.array(n2_img).astype(np.float32)/255.0 * 0.3)
    
    # Contours: where noise % interval is small
    interval = 1.0 / max(1, freq)
    is_line = (noise % interval) < (0.02 * roughness)
    is_sec  = (noise % (interval * 4)) < (interval * 2) # Large bands
    
    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[:] = list(primary) + [255]
    res[is_sec] = list(secondary) + [255]
    res[is_line] = list(accent) + [255]
    img.paste(Image.fromarray(res), (0,0))

def _draw_circuit(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Futuristic tech vibes with Manhattan paths and nodes."""
    S = size
    grid = int(params.get("tile_size", 128) * S / DEFAULT_SIZE)
    roughness = params.get("roughness", 0.5)
    
    draw = ImageDraw.Draw(img)
    rng = np.random.default_rng(77)
    
    for x in range(0, S, grid):
        for y in range(0, S, grid):
            if rng.random() > roughness: continue
            # Draw a path
            path_type = rng.choice(["L", "T", "45"])
            if path_type == "L":
                draw.line([(x, y), (x+grid, y), (x+grid, y+grid)], fill=secondary, width=4)
            elif path_type == "T":
                draw.line([(x, y+grid//2), (x+grid, y+grid//2)], fill=secondary, width=4)
                draw.line([(x+grid//2, y), (x+grid//2, y+grid)], fill=secondary, width=4)
            else:
                draw.line([(x, y), (x+grid, y+grid)], fill=secondary, width=4)
            
            # Draw nodes (dots) at corners
            if rng.random() > 0.5:
                rad = 6
                draw.ellipse([x-rad, y-rad, x+rad, y+rad], fill=accent)

def _draw_splatter(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Messy, organic ink splashes."""
    S = size
    roughness = params.get("roughness", 0.5)
    
    rng = np.random.default_rng(88)
    noise = rng.standard_normal((S//2, S//2)).astype(np.float32)
    noise_img = Image.fromarray(((noise + 3)/6 * 255).astype(np.uint8), "L").resize((S, S), Image.BICUBIC)
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(radius=max(1, int(15 * S / DEFAULT_SIZE))))
    
    arr = np.array(noise_img).astype(np.float32) / 255.0
    # Create distinct blobs via high-contrast thresholding
    is_sec = arr > (1.1 - roughness)
    is_acc = (arr > (1.08 - roughness)) & (~is_sec)
    
    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[is_sec] = list(secondary) + [255]
    res[is_acc] = list(accent) + [255]
    img.paste(Image.fromarray(res), (0,0))


def _draw_sunburst(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Radial rays originating from a focal point."""
    S = size
    cx = int(params.get("cx_frac", 0.5) * S)
    cy = int(params.get("cy_frac", 0.5) * S)
    count = int(params.get("count", 12))
    
    y, x = np.mgrid[0:S, 0:S]
    angle = np.arctan2(y - cy, x - cx)
    
    # Use Sine to create rays
    wave = np.sin(angle * count)
    is_sec = wave > 0
    
    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[is_sec] = list(secondary) + [255]
    
    # Accent lines on ray edges
    edges = np.diff(is_sec.astype(np.int8), axis=1, append=0) != 0
    res[edges] = list(accent) + [255]
    img.paste(Image.fromarray(res), (0,0))


def _draw_checkered(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Classic chequered flag grid. Even cells = secondary, odd = transparent (shows base)."""
    S = size
    tile = max(4, int(params.get("tile_size", 64) * S / DEFAULT_SIZE))
    border = max(0, int(params.get("border", 0) * S / DEFAULT_SIZE))

    y_g, x_g = np.mgrid[0:S, 0:S]
    col = x_g // tile
    row = y_g // tile
    is_sec = (col + row) % 2 == 0

    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[is_sec]  = list(secondary) + [255]
    # Thin accent border around each cell if requested
    if border > 0:
        edge_h = (x_g % tile) < border
        edge_v = (y_g % tile) < border
        res[edge_h | edge_v] = list(accent) + [255]
    img.paste(Image.fromarray(res, "RGBA"), (0, 0))


def _draw_hexagon_grid(img, primary, secondary, accent, params, size=DEFAULT_SIZE):
    """Honeycomb hexagon grid. Pointy-top orientation."""
    S = size
    r = max(4, int(params.get("tile_size", 40) * S / DEFAULT_SIZE))
    style = params.get("style", "filled")  # "filled" or "outline"

    draw = ImageDraw.Draw(img)
    col_w = int(math.sqrt(3) * r)
    row_h = int(1.5 * r)

    rows = S // row_h + 3
    cols = S // col_w + 3

    for row in range(-1, rows):
        for col in range(-1, cols):
            offset = col_w // 2 if row % 2 else 0
            cx = col * col_w + offset
            cy = row * row_h
            inner_r = r - 2  # 2px gap between cells
            pts = [
                (int(cx + inner_r * math.cos(math.radians(60 * i - 30))),
                 int(cy + inner_r * math.sin(math.radians(60 * i - 30))))
                for i in range(6)
            ]
            if style == "outline":
                draw.polygon(pts, outline=secondary)
            else:
                color = secondary if (col + row) % 2 == 0 else accent
                draw.polygon(pts, fill=color)


# ---------------------------------------------------------------------------
# Fade direction mask
# ---------------------------------------------------------------------------

def _apply_fade(layer_img: Image.Image, direction: str, size: int) -> Image.Image:
    """
    Multiply the layer's alpha channel by a linear gradient so the pattern
    fades out in the given direction.
    Supported directions: left, right, top, bottom, center-out, edges-in
    """
    S = size
    y_g, x_g = np.mgrid[0:S, 0:S]

    if direction == "right":
        ramp = x_g / (S - 1)
    elif direction == "left":
        ramp = 1.0 - x_g / (S - 1)
    elif direction == "bottom":
        ramp = y_g / (S - 1)
    elif direction == "top":
        ramp = 1.0 - y_g / (S - 1)
    elif direction == "center-out":
        dx = (x_g / (S - 1) - 0.5) * 2
        dy = (y_g / (S - 1) - 0.5) * 2
        ramp = np.sqrt(dx**2 + dy**2).clip(0, 1)
    elif direction == "edges-in":
        dx = (x_g / (S - 1) - 0.5) * 2
        dy = (y_g / (S - 1) - 0.5) * 2
        ramp = 1.0 - np.sqrt(dx**2 + dy**2).clip(0, 1)
    else:
        return layer_img

    fade_mask = (ramp * 255).clip(0, 255).astype(np.uint8)
    orig_alpha = np.array(layer_img.split()[3], dtype=np.uint16)
    new_alpha = ((orig_alpha * fade_mask) // 255).clip(0, 255).astype(np.uint8)
    layer_img.putalpha(Image.fromarray(new_alpha))
    return layer_img


# ---------------------------------------------------------------------------
# Texture blending
# ---------------------------------------------------------------------------

def _blend_texture(canvas: Image.Image, texture: Image.Image, opacity: float, size=DEFAULT_SIZE) -> Image.Image:
    """Multiply-blend texture over canvas to add surface finish."""
    S = size
    tex = texture.resize((S, S)).convert("RGB")
    c = np.array(canvas, dtype=float)
    t = np.array(tex, dtype=float) / 255.0
    # Multiply: darkens where texture is dark, neutral where texture is mid-grey (0.7+)
    blended = c * (t * opacity + (1.0 - opacity))
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------------------
# Edge Mask Overlay
# ---------------------------------------------------------------------------

def _overlay_edge_mask(canvas: Image.Image, edge_mask_path: Path, opacity: float, size=DEFAULT_SIZE):
    """
    Overlay the pre-computed Canny edge mask (greyscale PNG, 255=edge).
    Returns (result_image, had_edges).
    """
    S = size
    if opacity <= 0:
        return canvas, False

    # Edge mask is greyscale: bright pixels are panel seam lines
    em = Image.open(edge_mask_path).convert("L").resize((S, S))
    edges = np.array(em)

    # Amplify faint edges
    edges = np.clip(edges.astype(np.int32) * 2, 0, 255).astype(np.uint8)

    edge_count = int((edges > 20).sum())
    if edge_count < 100:
        return canvas, False

    # Adaptive edge color: light lines on dark canvas, dark lines on light canvas
    canvas_arr = np.array(canvas.convert("RGB"), dtype=np.float32)
    avg_brightness = canvas_arr.mean() / 255.0
    edge_rgb = [220, 220, 220] if avg_brightness < 0.5 else [20, 20, 20]

    line_alpha = int(np.clip(opacity * 600, 80, 255))
    overlay = np.zeros((S, S, 4), dtype=np.uint8)
    overlay[edges > 20] = [*edge_rgb, line_alpha]

    canvas_rgba = canvas.convert("RGBA")
    line_layer = Image.fromarray(overlay, "RGBA")
    result = Image.alpha_composite(canvas_rgba, line_layer)
    return result.convert("RGB"), True


def _overlay_logo(canvas: Image.Image, logo_path, params: dict, size=DEFAULT_SIZE) -> Image.Image:
    """Composite a logo (PNG/JPG/SVG) onto the canvas."""
    S = size
    p = Path(logo_path)
    logo = None
    
    scale = params.get("scale", 0.20)
    target_w = int(S * scale)
    
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

def _make_logo_img(logo_path, params: dict, size=DEFAULT_SIZE) -> "Image.Image | None":
    """Return RGBA canvas containing the placed logo."""
    S = size
    try:
        logo = Image.open(logo_path).convert("RGBA")
        scale = params.get("scale", 0.20)
        target_w = int(S * scale)
        aspect = logo.height / logo.width
        target_h = int(target_w * aspect)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        
        mirror = params.get("mirror", "none")
        if mirror == "horizontal":
            logo = logo.transpose(Image.FLIP_LEFT_RIGHT)
            
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        x_frac = params.get("x_frac", params.get("x", 50) / 100)
        y_frac = params.get("y_frac", params.get("y", 50) / 100)
        x = int(S * x_frac) - target_w // 2
        y = int(S * y_frac) - target_h // 2
        img.paste(logo, (x, y))
        return img
    except Exception:
        return None


def _overlay_template_direct(canvas: Image.Image, template_path: Path, opacity: float, size=DEFAULT_SIZE) -> Image.Image:
    """
    Blend the UV template onto the canvas using a mode that works on any
    background brightness:
      - Where template is DARK  → canvas is darkened (seam lines visible on light bg)
      - Where template is LIGHT → canvas is lightened (seam lines visible on dark bg)
    This is achieved via Pillow's built-in "hard light" composite, which applies
    multiply for dark template pixels and screen for bright template pixels.
    """
    S = size
    tmpl = Image.open(template_path).convert("RGB").resize((S, S))
    c = np.array(canvas.convert("RGB"), dtype=np.float32) / 255.0
    t = np.array(tmpl, dtype=np.float32) / 255.0

    # Hard-light: if template < 0.5 use multiply, else use screen
    dark  = 2.0 * c * t                          # multiply for seam lines
    light = 1.0 - 2.0 * (1.0 - c) * (1.0 - t)  # screen for bright regions
    hard  = np.where(t < 0.5, dark, light)

    # Blend between original and hard-light result by opacity
    result = c + opacity * (hard - c)
    return Image.fromarray((result.clip(0, 1) * 255).astype(np.uint8), "RGB")

def _apply_grunge(canvas: Image.Image, amount: float, size=DEFAULT_SIZE) -> Image.Image:
    """Adds procedural dirt and rubber marks."""
    S = size
    if amount <= 0: return canvas
    noise = _get_noise(S)
    # Normalize noise to 0-255
    noise = ((noise - noise.min()) / (noise.max() - noise.min()) * 255).astype(np.uint8)
    noise_img = Image.fromarray(noise).convert("L")
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Dirt color (dark brown/grey)
    dirt = Image.new("RGB", (S, S), (25, 20, 15))
    mask_arr = np.array(noise_img)
    mask_arr = np.where(mask_arr > 200, (mask_arr * amount).clip(0, 255), 0).astype(np.uint8)
    mask = Image.fromarray(mask_arr)
    
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(dirt, (0,0), mask=mask)
    return canvas_rgba.convert("RGB")
