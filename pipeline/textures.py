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
    """2x2 woven carbon fiber pattern tiled across the canvas."""
    tile = 12  # pixel size of one weave cell
    arr = np.zeros((size, size), dtype=np.uint8)

    for y in range(size):
        for x in range(size):
            cx, cy = x // tile, y // tile
            tx, ty = x % tile, y % tile
            # Alternate horizontal / vertical highlight
            if (cx + cy) % 2 == 0:
                brightness = int(30 + 40 * (ty / tile))
            else:
                brightness = int(30 + 40 * (tx / tile))
            arr[y, x] = brightness

    img = Image.fromarray(arr, mode="L").convert("RGB")
    # Slight blur to soften pixel edges
    return img.filter(ImageFilter.GaussianBlur(radius=0.4))


def _brushed_metal(size: int) -> Image.Image:
    """Horizontal brushed-metal streaks."""
    rng = np.random.default_rng(42)
    # Base: medium grey
    arr = np.full((size, size), 160, dtype=np.float32)
    # Add horizontal noise streaks
    for y in range(size):
        streak = rng.normal(0, 18)
        arr[y, :] += streak
    # Fine horizontal grain
    grain = rng.normal(0, 6, (size, size))
    arr += grain
    arr = np.clip(arr, 60, 220).astype(np.uint8)
    return Image.fromarray(arr, mode="L").convert("RGB")


def _matte_noise(size: int) -> Image.Image:
    """Subtle uniform noise for a matte/flat finish."""
    rng = np.random.default_rng(7)
    arr = np.full((size, size), 180, dtype=np.float32)
    arr += rng.normal(0, 8, (size, size))
    arr = np.clip(arr, 140, 220).astype(np.uint8)
    return Image.fromarray(arr, mode="L").convert("RGB")
