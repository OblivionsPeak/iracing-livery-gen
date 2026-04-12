import numpy as np
import math
from PIL import Image

def draw_speed_tear_v2(size=512, angle_deg=45):
    S = size
    angle_rad = math.radians(angle_deg)
    y_g, x_g = np.mgrid[0:S, 0:S]
    
    # Transform to directional axes (u is direction of tear)
    u = (x_g - S/2) * math.cos(angle_rad) + (y_g - S/2) * math.sin(angle_rad)
    v = -(x_g - S/2) * math.sin(angle_rad) + (y_g - S/2) * math.cos(angle_rad)
    
    u_norm = -u / (S / 2.0) # from ~1 to ~-1
    grad = u_norm.astype(np.float32)
    
    rng = np.random.default_rng(42)

    # Anisotropic stretch (X = length of streaks, Y = width of streaks)
    base_noise = rng.uniform(-1, 1, (S//2, S//32)).astype(np.float32)
    S_large = int(S * 1.5) # Overdraw so rotation doesn't have blank corners
    base_img = Image.fromarray(((base_noise+1)/2*255).astype(np.uint8)).resize((S_large, S_large), Image.BICUBIC)
    
    # Rotate
    rot_img = base_img.rotate(-angle_deg, resample=Image.BICUBIC) # PIL rotation is ccw
    # center crop
    left = (S_large - S) // 2
    rot_cropped = rot_img.crop((left, left, left+S, left+S))
    streaks_arr = (np.array(rot_cropped, dtype=np.float32) / 255.0 - 0.5) * 2.0
    
    # Medium Noise for jitter
    med_noise = rng.uniform(-1, 1, (S//4, S//8)).astype(np.float32)
    med_img = Image.fromarray(((med_noise+1)/2*255).astype(np.uint8)).resize((S_large, S_large), Image.BILINEAR)
    rot_med = med_img.rotate(-angle_deg, resample=Image.BILINEAR).crop((left, left, left+S, left+S))
    med_arr = (np.array(rot_med, dtype=np.float32) / 255.0 - 0.5) * 0.8
    
    mask_val = grad + streaks_arr * 0.8 + med_arr * 0.4
    
    flecks = rng.uniform(0, 1, (S, S))
    is_fleck = (flecks > 0.98) & (np.abs(mask_val) < 0.4)
    
    is_sec = (mask_val > 0) | is_fleck
    
    res = np.zeros((S, S, 3), dtype=np.uint8)
    res[is_sec] = [200, 200, 200]
    
    return Image.fromarray(res)

img = draw_speed_tear_v2(512, 10)
img.save("test_tear2.png")
