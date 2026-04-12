from PIL import Image, ImageDraw
primary = (26, 26, 46) # dark blue
S = 512
img = Image.new("RGB", (S, S), primary)
draw = ImageDraw.Draw(img)
w = 40
draw.polygon([(0, 0), (w, 0), (w, S), (0, S)], fill=(230, 57, 70))
mask = img.convert("L")
print(img.getpixel((0,0)))
print(mask.getpixel((0,0))) 
print(img.getpixel((w+10,0)))
print(mask.getpixel((w+10,0)))
