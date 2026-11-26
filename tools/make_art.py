"""Generate all of the game's art into assets/, plus sdl3-demo/art_gen.h.

    tools/.venv/Scripts/python tools/make_art.py      (Windows)
    tools/.venv/bin/python tools/make_art.py          (Linux/macOS)

Everything is drawn in code (art_chars.py, art_world.py), so it can be
tweaked and regenerated at any time. Memory photos (memory1.jpg ... memory6.jpg)
are read from art-src/photos/ (kept out of git) and pixelated into
assets/memories/; any missing ones get a drawn placeholder.

Hand-edited sprites: a PNG in art-src/sprites/ named after a sprite (e.g.
pet_sit.png) is used instead of the drawn one, so regenerating never
overwrites it. It's at art resolution (half the game size: one pixel per
art pixel) and gets scaled up 2x. To start one from the current art:

    tools/.venv/Scripts/python tools/make_art.py --export pet_sit hero_walk_down
"""
import glob
import os
import sys
from PIL import Image, ImageEnhance

import art_chars as ch
import art_world as w
from art_lib import Canvas, strip, from_ascii, SCALE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
HEADER = os.path.join(ROOT, 'sdl3-demo', 'art_gen.h')
PHOTOS = os.path.join(ROOT, 'art-src', 'photos')
HAND_SPRITES = os.path.join(ROOT, 'art-src', 'sprites')

ATLAS_COLS = 16

# Optional crop per photo (left, top, right, bottom as fractions) to zoom in
# on the people when they're small in the frame, e.g.
#     'memory1': (0.18, 0.30, 0.86, 0.86),
CROPS = {}

# Memory cards the story expects (assets/memories/<name>.png). Any without a
# photo in art-src/photos/ get a drawn placeholder.
MEMORY_NAMES = [f'memory{i}' for i in range(1, 7)]


def sprites():
    """name -> (canvas, frame count)."""
    out = {}
    for name, c in ch.all_sprites().items():
        out[name] = (c, c.w // 16)

    head = from_ascii(ch.close_eyes(ch.K_DOWN)[:14], ch.HERO)
    one = lambda c: (c, 1)
    two = lambda f: (strip([f(0), f(1)]), 2)
    out.update({
        'tree0': one(w.tree(0)), 'tree1': one(w.tree(1)), 'tree2': one(w.tree(2)),
        'bigtree': one(w.big_tree()),
        'cottage_red': one(w.cottage(w.hexc('d65f4f'), w.hexc('b44a3e'))),
        'cottage_blue': one(w.cottage(w.hexc('5a86c8'), w.hexc('4670ae'))),
        'cottage_green': one(w.cottage(w.hexc('5fa86a'), w.hexc('4a8c56'), w.hexc('fff1d6'))),
        'fountain': two(w.fountain),
        'dragon': two(w.dragon),
        'stall': one(w.stall()),
        'picnic_mat': one(w.picnic_mat()),
        'basket': one(w.basket()),
        'signpost': one(w.signpost()),
        'lamppost': one(w.lamppost()),
        'duck': two(w.duck),
        'possum': two(w.possum),
        'bird': two(w.bird),
        'bed': one(w.bed()),
        'bed_sleeping': one(w.bed(True, head)),
        'bookshelf': one(w.bookshelf()),
        'plant': one(w.plant()),
        'sofa': one(w.sofa()),
        'table': one(w.table()),
        'bubble': one(w.bubble_exclaim()),
        'zzz': two(w.zzz),
        'heart': one(w.heart()),
    })
    # round off the smaller props: lit top-left edges, shaded bottom-right ones
    for name in ('dragon', 'fountain', 'stall', 'basket', 'signpost', 'lamppost', 'duck', 'possum',
                 'bed', 'bed_sleeping', 'bookshelf', 'plant', 'sofa', 'table'):
        out[name][0].auto_shade(light=0.14, dark=0.22)
    for name in ('cottage_red', 'cottage_blue', 'cottage_green', 'bigtree', 'tree0', 'tree1', 'tree2'):
        out[name][0].auto_shade(light=0.1, dark=0.12)  # just a soft rim
    return out


def preview_sprites():
    s = {k: v[0] for k, v in sprites().items()}
    groups = w.tile_groups()
    for name, tiles in groups:
        s['tiles_' + name] = strip(tiles)
    return s


def build_atlas(assets):
    groups = w.tile_groups()
    entries, total = [], 0
    for name, tiles in groups:
        entries.append((name, total, len(tiles)))
        total += len(tiles)
    rows = (total + ATLAS_COLS - 1) // ATLAS_COLS
    atlas = Canvas(ATLAS_COLS * w.T, rows * w.T)
    i = 0
    for name, tiles in groups:
        for t in tiles:
            atlas.blit(t, (i % ATLAS_COLS) * w.T, (i // ATLAS_COLS) * w.T)
            i += 1
    atlas.save(os.path.join(assets, 'tiles.png'))
    return entries


def placeholder_card(index):
    """A simple drawn landscape (sky, sun, hills, heart) for a memory with no photo."""
    from PIL import ImageDraw
    skies = ['9fd3f0', 'f6c38b', 'c9b6ec', 'a8e0c8', 'f3a9b5', 'b5cdf2']
    hills = ['6fbf73', '8fae5a', '5aa58a', '79b86a', '6a9f5c', '5f9fae']
    img = Image.new('RGB', (116, 92), '#' + skies[index % len(skies)])
    d = ImageDraw.Draw(img)
    d.ellipse((80, 10, 100, 30), fill='#fff1b8')
    d.ellipse((-30, 52, 70, 130), fill='#' + hills[index % len(hills)])
    d.ellipse((40, 58, 150, 140), fill='#' + hills[(index + 2) % len(hills)])
    # a small heart in the middle
    d.ellipse((50, 34, 58, 42), fill='#e0546a')
    d.ellipse((57, 34, 65, 42), fill='#e0546a')
    d.polygon([(50, 39), (65, 39), (57.5, 48)], fill='#e0546a')
    return img


def pixelate_photos(assets, photos_dir, crops):
    """Turn each <photos_dir>/memoryN.* into a chunky pixel-art memory card,
    and draw a placeholder for any memory that has no photo."""
    out_dir = os.path.join(assets, 'memories')
    os.makedirs(out_dir, exist_ok=True)
    made = []
    photos = sorted(glob.glob(os.path.join(photos_dir, 'memory*.*'))) if os.path.isdir(photos_dir) else []
    have = {os.path.splitext(os.path.basename(p))[0] for p in photos}
    for i, name in enumerate(MEMORY_NAMES):
        if name not in have:
            img = placeholder_card(i).resize((116 * SCALE, 92 * SCALE), Image.NEAREST)
            img.save(os.path.join(out_dir, name + '.png'))
            made.append(name + ' (placeholder)')
    for path in photos:
        name = os.path.splitext(os.path.basename(path))[0]
        img = Image.open(path).convert('RGB')
        crop = crops.get(name)
        if crop:
            W, H = img.size
            img = img.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))
        # fit inside 116x92 art pixels (shown at 2x: 232x184 game pixels)
        img.thumbnail((116, 92), Image.LANCZOS)
        img = ImageEnhance.Color(img).enhance(1.2)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = img.quantize(colors=40, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGBA')
        img = img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)
        img.save(os.path.join(out_dir, name + '.png'))
        made.append(name)
    return made


def write_header(entries, sprite_frames):
    lines = [
        '// Generated by tools/make_art.py -- do not edit by hand.',
        '#pragma once',
        '',
        'namespace art {',
        '',
        f'constexpr int ATLAS_COLS = {ATLAS_COLS};',
        '',
        '// Tile indices into assets/tiles.png. Groups with 16 entries are',
        '// autotiles: add a mask of same-kind neighbours (N=1, E=2, S=4, W=8).',
    ]
    for name, start, count in entries:
        lines.append(f'constexpr int TILE_{name} = {start}, TILE_{name}_COUNT = {count};')
    lines += ['', 'struct SpriteDef { const char* name; int frames; };', '',
              '// assets/sprites/<name>.png: horizontal strips of equal-width frames.',
              'inline constexpr SpriteDef SPRITES[] = {']
    for name, frames in sprite_frames:
        lines.append(f'\t{{ "{name}", {frames} }},')
    lines += ['};', '', '} // namespace art', '']
    with open(HEADER, 'w', newline='\n') as f:
        f.write('\n'.join(lines))


def export(names):
    """Write the drawn sprites to art-src/sprites/ for hand-editing."""
    drawn = sprites()
    os.makedirs(HAND_SPRITES, exist_ok=True)
    for name in names:
        if name not in drawn:
            sys.exit(f'no sprite called {name!r}; see the list in sdl3-demo/art_gen.h')
        path = os.path.join(HAND_SPRITES, name + '.png')
        if os.path.exists(path):
            print(f'{path} already exists, left as it is')
            continue
        drawn[name][0].img.save(path)
        print(f'wrote {path} ({drawn[name][1]} frames)')


def hand_sprite(name, frames):
    """The hand-edited version of a sprite at game size, or None."""
    path = os.path.join(HAND_SPRITES, name + '.png')
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert('RGBA')
    if img.width % frames:
        sys.exit(f'{path} is {img.width} px wide, which does not split into {frames} equal frames')
    return img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)


def generate(assets=ASSETS, photos_dir=PHOTOS, crops=None, header=True):
    """Draw everything into `assets`. tools/gift.py calls this for each gift,
    with the gift's folders and its looks already applied (art_chars.apply_looks)."""
    os.makedirs(os.path.join(assets, 'sprites'), exist_ok=True)
    entries = build_atlas(assets)
    frames, by_hand = [], []
    for name, (c, n) in sprites().items():
        out = os.path.join(assets, 'sprites', name + '.png')
        img = hand_sprite(name, n)
        if img:
            img.save(out)
            by_hand.append(name)
        else:
            c.save(out)
        frames.append((name, n))
    if header:
        write_header(entries, frames)
    memories = pixelate_photos(assets, photos_dir, CROPS if crops is None else crops)
    print(f'atlas: {sum(e[2] for e in entries)} tiles, sprites: {len(frames)}, memories: {memories}')
    if by_hand:
        print(f'hand-edited sprites from art-src/sprites: {by_hand}')



def main():
    if sys.argv[1:2] == ['--export']:
        export(sys.argv[2:])
        return
    generate()


if __name__ == '__main__':
    main()
