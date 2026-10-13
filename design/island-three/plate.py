"""Compose the finished plate: picture above, formula sheet below."""
from PIL import Image

art = Image.open("art.png").convert("RGB")
sheet = Image.open("sheet.png").convert("RGB")
assert art.width == sheet.width
plate = Image.new("RGB", (art.width, art.height + sheet.height), "white")
plate.paste(art, (0, 0))
plate.paste(sheet, (0, art.height))
plate.save("island-three.png")
print("wrote island-three.png", plate.size)
