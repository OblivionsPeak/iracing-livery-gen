from PIL import Image
import numpy as np

res = np.zeros((10, 10, 4), dtype=np.uint8)
# primary (transparent)
res[:] = (0, 0, 0, 0)
# secondary (opaque)
res[5:10, 5:10] = (255, 0, 0, 255)

img = Image.fromarray(res, "RGBA")
print(img.getpixel((0,0)))
print(img.getpixel((5,5)))
