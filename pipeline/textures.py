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
