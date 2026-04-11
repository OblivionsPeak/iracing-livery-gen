"""
Procedural texture generators — no AI required.
Returns PIL Images that can be blended over color layers.
"""

from PIL import Image, ImageFilter
import numpy as np

SIZE = 2048


def generate_texture(name: str, size: int = SIZE) -> Image.Image:
    generators = {
        "carbon_fiber": _carbon_fiber,
        "brushed_metal": _brushed_metal,
        "matte":         _matte_noise,
        "forged_carbon": _forged_carbon,
        "metallic_flake": _metallic_flake,
    }
    fn = generators.get(name)
    if fn is None:
        raise ValueError(f"Unknown texture '{name}'")
    return fn(size)


def _carbon_fiber(size: int) -> Image.Image:
    """2x2 woven carbon fiber pattern tiled across the canvas (NumPy vectorised)."""
    tile = 12  # pixel size of one weave cell

    # Build full coordinate grids in one shot
    y_idx, x_idx = np.mgrid[0:size, 0:size]

    cx = x_idx // tile   # cell column index
    cy = y_idx // tile   # cell row index
    tx = x_idx % tile    # x position within cell
    ty = y_idx % tile    # y position within cell

    # Even cells: brightness varies with ty (horizontal highlight)
    even_bright = (30 + 40 * (ty / tile)).astype(np.float32)
    # Odd cells: brightness varies with tx (vertical highlight)
    odd_bright  = (30 + 40 * (tx / tile)).astype(np.float32)

    arr = np.where((cx + cy) % 2 == 0, even_bright, odd_bright).astype(np.uint8)

    img = Image.fromarray(arr, mode="L").convert("RGB")
    # Slight blur to soften pixel edges
    return img.filter(ImageFilter.GaussianBlur(radius=0.4))


def _brushed_metal(size: int) -> Image.Image:
    """Horizontal brushed-metal streaks."""
    rng = np.random.default_rng(42)
    arr = np.full((size, size), 160, dtype=np.float32)
    # Vectorised: generate all per-row streaks at once and broadcast across columns
    streaks = rng.normal(0, 18, (size, 1))
    arr += streaks
    arr += rng.normal(0, 6, (size, size))
    arr = np.clip(arr, 60, 220).astype(np.uint8)
    return Image.fromarray(arr, mode="L").convert("RGB")


def _matte_noise(size: int) -> Image.Image:
    """Subtle uniform noise for a matte/flat finish."""
    rng = np.random.default_rng(7)
    arr = np.full((size, size), 180, dtype=np.float32)
    arr += rng.normal(0, 8, (size, size))
    arr = np.clip(arr, 140, 220).astype(np.uint8)
    return Image.fromarray(arr, mode="L").convert("RGB")

def _forged_carbon(size: int) -> Image.Image:
    """Angular, overlapping shards of carbon fiber composites."""
    rng = np.random.default_rng(99)
    res = np.full((size, size), 40, dtype=np.float32)
    for angle in [0, 45, 90, 135]:
        n = rng.uniform(-40, 60, (size//12, size//3)).astype(np.float32)
        layer = Image.fromarray(n).resize((size, size), Image.NEAREST).rotate(angle, Image.NEAREST, fillcolor=0)
        res += np.array(layer)
    arr = np.clip(res, 10, 80).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")

def _metallic_flake(size: int) -> Image.Image:
    """High frequency bright specks mimicking metallic car paint."""
    rng = np.random.default_rng(77)
    arr = np.full((size, size), 128, dtype=np.float32)
    flakes = rng.uniform(0, 1, (size, size))
    arr[flakes > 0.95] = 255
    arr[flakes > 0.98] = 200
    arr = np.clip(arr, 90, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")

