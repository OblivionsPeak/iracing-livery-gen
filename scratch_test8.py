from PIL import Image, ImageChops

def apply_transform(img, scale_frac, pos_x, pos_y):
    S = img.width
    
    if scale_frac == 1.0:
        # Full screen pattern: wrap it
        if pos_x != 0.0 or pos_y != 0.0:
            dx = int(pos_x * S)
            dy = int(pos_y * S)
            return ImageChops.offset(img, dx, dy)
        return img
    else:
        # Scaled pattern: don't wrap, place it like a decal
        target_size = int(S * scale_frac)
        scaled = img.resize((target_size, target_size), Image.LANCZOS)
        
        out = Image.new("RGBA", (S, S), (0,0,0,0))
        
        # In the UI, pos_x and pos_y are currently from -1 to 1.
        # Let's say 0,0 is center? No, let's remap pos_x into the canvas coordinates.
        # But wait, my previous sliders went from -1 to 1.
        # If pos_x is -1 to 1:
        # dx = pos_x * S
        # This meant 0 was no shift. So center is 0. 
        # If scale is used, center is placed at (S/2 + dx, S/2 + dy).
        
        center_x = int(S/2 + pos_x * S)
        center_y = int(S/2 + pos_y * S)
        
        paste_x = center_x - target_size // 2
        paste_y = center_y - target_size // 2
        
        out.paste(scaled, (paste_x, paste_y))
        return out

