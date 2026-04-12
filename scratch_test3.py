from PIL import Image, ImageFilter
import numpy as np

def _forged_carbon(size=512):
    rng = np.random.default_rng(99)
    res = np.full((size, size), 40, dtype=np.float32)
    # create several layers of stretched noise at different angles to make flakes
    for angle in [0, 45, 90, 135]:
        n = rng.uniform(-40, 60, (size//12, size//3)).astype(np.float32)
        layer = Image.fromarray(n).resize((size, size), Image.NEAREST).rotate(angle, Image.NEAREST, fillcolor=0)
        res += np.array(layer)
    arr = np.clip(res, 10, 80).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")

def _metallic_flake(size=512):
    rng = np.random.default_rng(77)
    # Base paint color will tint it later, texture is just grayscale
    # High frequency bright spots
    arr = np.full((size, size), 128, dtype=np.float32)
    flakes = rng.uniform(0, 1, (size, size))
    # only 2% of pixels are flakes
    arr[flakes > 0.95] = 255
    arr[flakes > 0.98] = 200
    arr = np.clip(arr, 90, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")
    
im = _metallic_flake(512)
print("Metallic flake min/max:", np.min(im), np.max(im))
im2 = _forged_carbon(512)
print("Forged min/max:", np.min(im2), np.max(im2))
