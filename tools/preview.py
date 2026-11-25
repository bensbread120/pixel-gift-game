"""Contact sheet of generated sprites, for checking art quickly.

usage: python preview.py <module.function> <out.png> [scale]
e.g.   python preview.py art_chars.all_sprites ../build/chars.png 6
"""
import importlib
import sys
from PIL import Image, ImageDraw

target, out_path = sys.argv[1], sys.argv[2]
scale = int(sys.argv[3]) if len(sys.argv) > 3 else 4
mod_name, fn_name = target.rsplit('.', 1)
sprites = getattr(importlib.import_module(mod_name), fn_name)()

pad, label_h = 6, 12
rows, x, y, row_h, max_w = [], pad, pad, 0, 1400
placements = []
for name, c in sprites.items():
    w, h = c.w * scale, c.h * scale
    if x + w > max_w and x > pad:
        x, y = pad, y + row_h + label_h + pad
        row_h = 0
    placements.append((name, c, x, y))
    x += max(w, len(name) * 6) + pad
    row_h = max(row_h, h)
sheet = Image.new('RGBA', (max_w, y + row_h + label_h + pad * 2), (120, 170, 110, 255))
draw = ImageDraw.Draw(sheet)
for name, c, x, y in placements:
    img = c.img.resize((c.w * scale, c.h * scale), Image.NEAREST)
    sheet.alpha_composite(img, (x, y + label_h))
    draw.text((x, y), name, fill=(0, 0, 0, 255))
sheet.save(out_path)
print(out_path, sheet.size)
