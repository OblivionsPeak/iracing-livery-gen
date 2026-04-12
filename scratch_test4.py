from PIL import Image, ImageChops

img = Image.new("RGBA", (100, 100), (0,0,0,0))
# draw something in middle
img.paste((255,0,0,255), (40, 40, 60, 60))

off_img = ImageChops.offset(img, 30, 30)

print(img.getpixel((50,50)))
print(off_img.getpixel((80,80)))
print(off_img.getpixel((50,50)))
