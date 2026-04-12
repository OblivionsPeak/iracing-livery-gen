import numpy as np
import math
from PIL import Image

def _draw_digital_camo(img, primary, secondary, accent, params, size=512):
    S = size
    grid_size = int(params.get("tile_size", 64) * S / 2048)
    roughness = params.get("roughness", 0.4)
    cols, rows = S // grid_size + 1, S // grid_size + 1
    rng = np.random.default_rng(13)
    choices = rng.choice([0, 1, 2], size=(rows, cols), p=[1.0-roughness, roughness*0.7, roughness*0.3])
    full_mask = choices.repeat(grid_size, axis=0).repeat(grid_size, axis=1)[:S, :S]
    res = np.zeros((S, S, 4), dtype=np.uint8)
    res[full_mask == 1] = list(secondary) + [255]
    res[full_mask == 2] = list(accent) + [255]
    img.paste(Image.fromarray(res), (0,0))

def test_mask(size=512):
    S = size
    params = {"tile_size": 128, "roughness": 0.6}
    
    camo_img = Image.new("RGBA", (S, S), (0,0,0,0))
    _draw_digital_camo(camo_img, (0,0,0), (200,0,0), (0,200,0), params, size=S)
    
    c2 = np.array(camo_img)
    c1 = np.zeros((S, S, 4), dtype=np.uint8)
    
    # Tear mask logic
    y, x = np.mgrid[0:S, 0:S]
    is_sec = x > S//2 # half screen tear
    
    res = np.where(is_sec[..., None], c2, c1).astype(np.uint8)
    
    final_img = Image.fromarray(res)
    final_img.save("test_mask.png")

test_mask()
