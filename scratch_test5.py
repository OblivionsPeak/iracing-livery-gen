import numpy as np
from PIL import Image

def draw_speed_tear(size=512):
    S = size
    # 1. Base gradient (left to right, 1 to 0)
    # Tear happens roughly in the middle half
    x = np.linspace(1.5, -0.5, S) 
    grad = np.tile(x, (S, 1)).astype(np.float32)

    rng = np.random.default_rng(42)

    # 2. Hard, long streaks
    # Generate low X-res, high Y-res noise
    noise_streaks = rng.uniform(-1, 1, (S//2, S//32)).astype(np.float32)
    streaks_img = Image.fromarray(((noise_streaks+1)/2*255).astype(np.uint8)).resize((S, S), Image.BICUBIC)
    streaks_arr = (np.array(streaks_img, dtype=np.float32) / 255.0 - 0.5) * 2.0

    # 3. Medium noise for edge jitter
    noise_med = rng.uniform(-1, 1, (S//4, S//8)).astype(np.float32)
    med_img = Image.fromarray(((noise_med+1)/2*255).astype(np.uint8)).resize((S, S), Image.BILINEAR)
    med_arr = (np.array(med_img, dtype=np.float32) / 255.0 - 0.5) * 0.8

    # Mask thresholding
    mask_val = grad + streaks_arr * 0.6 + med_arr * 0.3
    
    # 4. Tiny flecks (splatter) randomly appearing in the transition zone
    flecks = rng.uniform(0, 1, (S, S))
    is_fleck = (flecks > 0.98) & (np.abs(mask_val) < 0.3)
    
    # Threshold at 0
    is_sec = (mask_val > 0) | is_fleck
    
    res = np.zeros((S, S, 3), dtype=np.uint8)
    res[is_sec] = [200, 200, 200]
    
    return Image.fromarray(res)

img = draw_speed_tear(512)
img.save("test_tear.png")
