"""Ground tiles, props and landmarks.

Ground tiles are 16x16 art px. "Autotile" kinds (path, water, rug, fence,
hedge) come in 16 variants, one per combination of which neighbours (N, E,
S, W) are the same kind, so edges join up on their own.
"""
import math
import random
from art_lib import Canvas, hexc, mix, darker, lighter, noise_tile, OUTLINE, CLEAR, light_level, pick, ramp

T = 16
N_, E_, S_, W_ = 1, 2, 4, 8

# palette -------------------------------------------------------------------
GRASS = hexc('8fd35a'); GRASS_D = hexc('76bc4c'); GRASS_L = hexc('b4e672'); GRASS_DD = hexc('4f9c4a'); GRASS_SH = hexc('5f9f5e')
PATH = hexc('f4d48c'); PATH_D = hexc('e0b46e'); PATH_L = hexc('fdeab6'); PATH_EDGE = hexc('bc8452'); PATH_SH = hexc('d49e66')
WATER = hexc('58b8ee'); WATER_D = hexc('3f98de'); WATER_L = hexc('c4f0fc'); WATER_EDGE = hexc('2a5a8e'); WATER_DEEP = hexc('3479c6')
WOOD = hexc('d0925a'); WOOD_D = hexc('a8683c'); WOOD_L = hexc('eab67a'); WOOD_DD = hexc('6a4030')
WALLPAPER = hexc('fbecca'); WALLPAPER_D = hexc('ecd5a4'); TRIM = hexc('7a4e34')
STONE = hexc('c2beba'); STONE_D = hexc('9a96a4'); STONE_L = hexc('e6e2d4'); STONE_DD = hexc('6e6a80')
LEAF = hexc('5fb04a'); LEAF_D = hexc('3d8c48'); LEAF_L = hexc('8fd052'); LEAF_DD = hexc('24603f')
TRUNK = hexc('94603c'); TRUNK_D = hexc('6e4430')
FLOWER_COLS = [hexc('ffffff'), hexc('ffe066'), hexc('ff9ab0'), hexc('c79bff'), hexc('ff7a6b')]


LEAVES = [hexc('24603f'), hexc('3d8c48'), hexc('5fb04a'), hexc('8fd052'), hexc('c6e66c')]
BARK = [hexc('4a2c2a'), hexc('6e4430'), hexc('94603c'), hexc('b78350')]
STONES = [hexc('6e6a80'), hexc('9a96a4'), hexc('c2beba'), hexc('e6e2d4')]


AUTUMN = [hexc('6e2a22'), hexc('b84a2a'), hexc('e87a2e'), hexc('ffad3c'), hexc('ffe07a')]
WHEAT = [hexc('8a5a26'), hexc('b87e32'), hexc('dca444'), hexc('f2c95e'), hexc('fde89a')]
def grass(seed):
    rnd = random.Random(seed)
    c = noise_tile(T, T, GRASS, [GRASS_D, GRASS_L], seed, 0.06)
    for _ in range(3):  # little "v" tufts, lit on top
        x, y = rnd.randrange(0, T - 3), rnd.randrange(2, T - 1)
        c.put(x, y - 1, GRASS_DD); c.put(x + 1, y, GRASS_DD); c.put(x + 2, y - 1, GRASS_DD)
        c.put(x + 1, y - 1, GRASS_L)
    return c


def flowers(seed):
    rnd = random.Random(seed + 100)
    c = grass(seed)
    for _ in range(3):
        x, y = rnd.randrange(1, T - 2), rnd.randrange(1, T - 2)
        col = rnd.choice(FLOWER_COLS)
        c.put(x, y, col); c.put(x + 1, y, col); c.put(x, y + 1, col); c.put(x + 1, y + 1, darker(col, 0.2))
        c.put(x + 1, y - 1 if y > 0 else y, GRASS_DD)
    return c


def long_grass(seed, with_flowers=False):
    """Golden meadow grass (a nod to Moonlighter): a calm gold base with
    scattered tufts, each lit on top and casting a little shadow below."""
    rnd = random.Random(seed + 200)
    c = noise_tile(T, T, WHEAT[2], [WHEAT[1], WHEAT[3]], seed, 0.05)
    spots = []
    for _ in range(5):
        for _try in range(20):
            x, y = rnd.randrange(2, T - 3), rnd.randrange(2, T - 3)
            if all(abs(x - a) + abs(y - b) > 5 for a, b in spots):
                spots.append((x, y))
                break
    for x, y in spots:
        # shadow first, down-right of the tuft
        c.hline(x - 1, x + 2, y + 2, WHEAT[1]); c.hline(x, x + 2, y + 3, WHEAT[1])
        # the tuft: three stalks fanning out, bright tips
        c.put(x - 1, y, WHEAT[3]); c.put(x - 1, y + 1, WHEAT[2])
        c.put(x, y - 1, WHEAT[4]); c.put(x, y, WHEAT[3]); c.put(x, y + 1, WHEAT[2])
        c.put(x + 1, y - 2, WHEAT[4]); c.put(x + 1, y - 1, WHEAT[3]); c.put(x + 1, y, WHEAT[3]); c.put(x + 1, y + 1, WHEAT[1])
        c.put(x + 2, y, WHEAT[2]); c.put(x + 2, y + 1, WHEAT[0])
    if with_flowers:
        for _ in range(3):
            x, y = rnd.randrange(1, T - 1), rnd.randrange(1, T - 1)
            col = rnd.choice([hexc('ffffff'), hexc('ff6a6a'), hexc('c79bff'), hexc('6fb0ff')])
            c.put(x, y, col); c.put(x - 1, y, lighter(col, 0.3)); c.put(x, y + 1, darker(col, 0.35))
    return c


def edge_wobble(rnd):
    return [rnd.choice([0, 0, 1, 1, 2]) for _ in range(T)]


def path(mask, seed=7):
    """Sandy path set a little below the grass: the grass edge casts a shadow
    onto it along the top and left, and catches the light along the bottom."""
    rnd = random.Random(seed)
    c = noise_tile(T, T, PATH, [PATH_D, PATH_L], seed + mask, 0.08)
    for _ in range(2):  # pebbles, lit from the top-left
        x, y = rnd.randrange(3, T - 4), rnd.randrange(3, T - 4)
        c.put(x, y, PATH_L); c.put(x + 1, y, PATH_D); c.put(x + 1, y + 1, PATH_EDGE)
    g = grass(seed + 50 + mask)
    w = edge_wobble(rnd)
    for i in range(T):
        d = 2 + w[i]
        for k in range(d):
            if not mask & N_: c.put(i, k, g.get(i, k))
            if not mask & S_: c.put(i, T - 1 - k, g.get(i, T - 1 - k))
            if not mask & W_: c.put(k, i, g.get(k, i))
            if not mask & E_: c.put(T - 1 - k, i, g.get(T - 1 - k, i))
    for i in range(T):
        d = 2 + w[i]
        if not mask & N_:
            c.put(i, d, PATH_EDGE); c.put(i, d + 1, PATH_SH)
            c.put(i, d - 1, GRASS_DD)
        if not mask & W_:
            c.put(d, i, PATH_EDGE); c.put(d + 1, i, PATH_SH)
            c.put(d - 1, i, GRASS_DD)
        if not mask & S_:
            c.put(i, T - 1 - d, PATH_L); c.put(i, T - d, GRASS_L)
        if not mask & E_:
            c.put(T - 1 - d, i, PATH_L); c.put(T - d, i, GRASS_L)
    return c


def water(mask, frame):
    """Water sits below its banks: a deep shadow under the top and left
    banks, a bright line where it laps the bottom and right ones."""
    rnd = random.Random(31 + mask)
    c = Canvas(T, T, WATER)
    for y in range(T):  # a gentle texture, deeper towards the top
        for x in range(T):
            if (x * 7 + y * 3) % 11 == 0 and y < 9:
                c.put(x, y, WATER_D)
    for k in range(4):  # drifting glints; frame 1 shifts them sideways
        x = (rnd.randrange(0, T) + frame * 3) % T
        y = rnd.randrange(2, T - 2)
        c.put(x, y, WATER_L); c.put((x + 1) % T, y, WATER_L); c.put((x + 2) % T, y, lighter(WATER, 0.3))
        c.put((x + 1) % T, y + 1, WATER_D)
    g = grass(77 + mask)
    w = edge_wobble(rnd)
    for i in range(T):
        d = 2 + (w[i] > 1)
        for k in range(d):
            if not mask & N_: c.put(i, k, g.get(i, k))
            if not mask & S_: c.put(i, T - 1 - k, g.get(i, T - 1 - k))
            if not mask & W_: c.put(k, i, g.get(k, i))
            if not mask & E_: c.put(T - 1 - k, i, g.get(T - 1 - k, i))
    for i in range(T):
        d = 2 + (w[i] > 1)
        if not mask & N_:
            c.put(i, d, WATER_EDGE); c.put(i, d + 1, WATER_DEEP); c.put(i, d + 2, WATER_DEEP)
            c.put(i, d + 3, WATER_D)
        if not mask & W_:
            c.put(d, i, WATER_EDGE); c.put(d + 1, i, WATER_DEEP); c.put(d + 2, i, WATER_D)
        if not mask & S_:
            c.put(i, T - 1 - d, WATER_EDGE); c.put(i, T - 2 - d, WATER_L)
        if not mask & E_:
            c.put(T - 1 - d, i, WATER_EDGE); c.put(T - 2 - d, i, WATER_L)
    return c


def bridge(horizontal):
    c = water(N_ | E_ | S_ | W_, 0)
    for y in range(T):
        for x in range(T):
            along = x if horizontal else y
            across = y if horizontal else x
            if 2 <= across <= T - 3:
                k = along % 4
                col = WOOD_L if k == 0 else WOOD if k in (1, 2) else WOOD_D
                if across in (2, T - 3):
                    col = WOOD_DD
                elif across == 3:
                    col = lighter(col, 0.2)
                c.put(x, y, col)
            elif across == T - 2:
                c.put(x, y, WATER_EDGE)   # the bridge's shadow on the water
            elif across == T - 1:
                c.put(x, y, WATER_DEEP)
            elif across == 1:
                c.put(x, y, WATER_D)
    return c


def floor(seed):
    """Floorboards: each board lit along its top edge, a dark seam beneath,
    and a slightly different tone per board."""
    rnd = random.Random(seed)
    c = Canvas(T, T, WOOD)
    tones = [WOOD, mix(WOOD, WOOD_L, 0.25), mix(WOOD, WOOD_D, 0.2), WOOD]
    seam = mix(WOOD_D, WOOD_DD, 0.45)
    for row in range(4):
        y0 = row * 4
        jx = (row * 7 + seed * 5) % T
        for x in range(T):
            board = 0 if x < jx else 1
            col = tones[(row * 2 + board + seed) % len(tones)]
            c.put(x, y0, lighter(col, 0.07))
            c.put(x, y0 + 1, col); c.put(x, y0 + 2, col)
            c.put(x, y0 + 3, seam)
            if rnd.random() < 0.05:
                c.put(x, y0 + 1 + rnd.randrange(2), darker(col, 0.12))  # grain
        for y in range(y0, y0 + 3):
            c.put(jx, y, seam)
    return c


def rug(mask):
    """A thick rug: a lit border along the top-left, a shaded one along the
    bottom-right, and a warm diamond pattern."""
    base, inner, gold, gold_d = hexc('c85068'), hexc('a83c58'), hexc('f6cf7e'), hexc('c89a4e')
    c = Canvas(T, T, base)
    for y in range(T):
        for x in range(T):
            d = abs((x % 8) - 4) + abs((y % 8) - 4)
            if d == 3:
                c.put(x, y, inner)
            elif d == 0:
                c.put(x, y, gold)
            elif d == 1 and (x + y) % 2 == 0:
                c.put(x, y, lighter(base, 0.15))
    for i in range(T):
        if not mask & N_: c.put(i, 0, OUTLINE); c.put(i, 1, lighter(base, 0.25)); c.put(i, 2, gold)
        if not mask & W_: c.put(0, i, OUTLINE); c.put(1, i, lighter(base, 0.25)); c.put(2, i, gold)
        if not mask & S_: c.put(i, T - 1, OUTLINE); c.put(i, T - 2, darker(base, 0.3)); c.put(i, T - 3, gold_d)
        if not mask & E_: c.put(T - 1, i, OUTLINE); c.put(T - 2, i, darker(base, 0.3)); c.put(T - 3, i, gold_d)
    f = floor(1)
    if not mask & N_ and not mask & W_: c.put(0, 0, f.get(0, 0))
    if not mask & N_ and not mask & E_: c.put(T - 1, 0, f.get(T - 1, 0))
    if not mask & S_ and not mask & W_: c.put(0, T - 1, f.get(0, T - 1))
    if not mask & S_ and not mask & E_: c.put(T - 1, T - 1, f.get(T - 1, T - 1))
    return c


def wall(window=False):
    """The back wall, seen face on: a dark cornice on top, striped wallpaper
    that darkens towards the floor, and a lit wooden wainscot."""
    c = Canvas(T, T, WALLPAPER)
    for y in range(T):
        for x in range(T):
            col = WALLPAPER_D if x % 4 == 1 else WALLPAPER
            if y >= 8:
                col = darker(col, 0.04 + (y - 8) * 0.012)
            c.put(x, y, col)
    c.rect(0, 0, T, 2, darker(TRIM, 0.2)); c.hline(0, T - 1, 2, TRIM); c.hline(0, T - 1, 3, darker(WALLPAPER, 0.18))
    c.rect(0, T - 5, T, 5, WOOD_D)
    c.hline(0, T - 1, T - 5, WOOD_L); c.hline(0, T - 1, T - 4, WOOD)
    for x in range(0, T, 8):
        c.vline(x + 3, T - 3, T - 2, WOOD_DD)
    c.hline(0, T - 1, T - 1, WOOD_DD)
    if window:
        frame, frame_d = hexc('fbfbf6'), hexc('cfcad8')
        c.rect(3, 3, 10, 9, frame)
        c.rect(4, 4, 8, 7, hexc('8fd0f2'))
        c.hline(4, 11, 4, hexc('5aa0d0')); c.vline(4, 4, 10, hexc('5aa0d0'))   # recess shadow
        c.put(6, 6, hexc('ffffff')); c.put(7, 5, hexc('e6f7ff')); c.put(9, 8, hexc('d8f2ff'))  # sky glint
        c.vline(8, 4, 10, frame); c.hline(4, 11, 7, frame)
        c.vline(12, 3, 11, frame_d); c.hline(3, 12, 11, frame_d)
        c.rect(2, 11, 12, 2, WOOD_L); c.hline(2, 13, 12, WOOD_D)
        # curtains: lit on the left, folds
        for x0 in (2, 12):
            c.rect(x0, 3, 2, 8, hexc('ee8ea0')); c.vline(x0 + 1, 3, 10, hexc('c86478'))
            c.put(x0, 3, hexc('ffb8c4'))
    return c


def stairs(down):
    c = Canvas(T, T, WOOD_DD if down else WOOD)
    for step in range(4):
        y = step * 4
        if down:
            col = mix(hexc('3a2a22'), WOOD, step / 4)
        else:
            col = mix(WOOD_L, WOOD_D, step / 4)
        c.hline(1, T - 2, y, lighter(col, 0.2))
        c.rect(1, y + 1, T - 2, 2, col)
        c.hline(1, T - 2, y + 3, darker(col, 0.35))
    c.vline(0, 0, T - 1, WOOD_DD); c.vline(T - 1, 0, T - 1, WOOD_DD)
    c.vline(1, 0, T - 1, darker(WOOD, 0.3))
    return c


def doormat():
    c = floor(2)
    c.rect(2, 4, 12, 9, hexc('8f5e3c'))
    c.rect(3, 5, 10, 7, hexc('b98552'))
    for x in range(4, 12, 2):
        c.vline(x, 6, 10, hexc('a2703f'))
    return c


def flowerbed(seed):
    """A raised planter: flowers on top, a wooden front face below, so it
    reads as a box standing on the grass."""
    rnd = random.Random(seed)
    soil, soil_d = hexc('8a5b3b'), hexc('6a3f2c')
    c = Canvas(T, T, soil)
    for y in range(T):
        for x in range(T):
            if rnd.random() < 0.15:
                c.put(x, y, soil_d)
    c.rect(0, 1, T, 2, soil_d)  # shadow of the back edge
    col = FLOWER_COLS[seed % len(FLOWER_COLS)]
    col2 = FLOWER_COLS[(seed + 2) % len(FLOWER_COLS)]
    for row, y in enumerate((4, 9)):
        for x in range(1 + (row % 2) * 2, T - 1, 4):
            c.put(x, y, LEAF_D); c.put(x + 1, y, LEAF_DD); c.put(x - 1, y, LEAF)
            cc = col if (x // 4 + row) % 2 == 0 else col2
            c.put(x, y - 2, lighter(cc, 0.35)); c.put(x + 1, y - 2, cc)
            c.put(x, y - 1, cc); c.put(x + 1, y - 1, darker(cc, 0.3))
    c.hline(0, T - 1, 0, WOOD_L)
    # front face of the planter
    c.hline(0, T - 1, 11, WOOD_L)
    c.rect(0, 12, T, 3, WOOD_D)
    for x in range(0, T, 5):
        c.vline(x + 2, 12, 14, WOOD_DD)
    c.hline(0, T - 1, T - 1, darker(WOOD_DD, 0.2))
    return c


def fence(mask):
    c = grass(400 + mask)
    rail, rail_l, dark = hexc('d9b07a'), hexc('f2d39e'), hexc('7a5232')
    if mask & (E_ | W_) or not mask & (N_ | S_):
        x0 = 0 if mask & W_ else 6
        x1 = T - 1 if mask & E_ else 9
        for y in (5, 9):
            for x in range(x0, x1 + 1):  # the rail's shadow on the grass
                on_grass(c, x, y + 3)
            c.hline(x0, x1, y, rail_l); c.hline(x0, x1, y + 1, rail); c.hline(x0, x1, y + 2, dark)
    if mask & (N_ | S_):
        y0 = 0 if mask & N_ else 4
        y1 = T - 1 if mask & S_ else 12
        for y in range(y0, y1 + 1):
            on_grass(c, 10, y); on_grass(c, 11, y)
        c.vline(7, y0, y1, rail_l); c.vline(8, y0, y1, rail); c.vline(9, y0, y1, dark)
    for y in range(5, 15):  # the post's shadow, falling down-right
        on_grass(c, 10, y); on_grass(c, 11, y + 1)
    post = Canvas(T, T)
    post.cylinder_x(6, 3, 4, 11, [dark, hexc('a87444'), hexc('c49460'), rail_l])
    post.hline(6, 9, 2, rail_l); post.put(9, 2, rail)
    c.blit(post, 0, 0)
    c.hline(6, 9, 14, GRASS_DD)
    return c


def hedge(mask):
    """A raised hedge: a lumpy, lit top, a darker front face where it ends,
    and a shadow on the grass beneath."""
    c = grass(500 + mask)
    x0 = 0 if mask & W_ else 1
    x1 = T if mask & E_ else T - 1
    y0 = 0 if mask & N_ else 1
    front = not mask & S_
    y1 = T if not front else T - 3         # bottom of the hedge
    top_end = y1 if not front else y1 - 4  # where the top gives way to the front face
    shape = Canvas(T, T)
    for y in range(y0, y1):
        for x in range(x0, x1):
            # leafy clumps on an 8px lattice (two offset grids), so tiles join seamlessly
            best = None
            for gx0, gy0 in ((0, 0), (4, 4)):
                cx = round((x - gx0) / 8) * 8 + gx0
                cy = round((y - gy0) / 8) * 8 + gy0
                dx, dy = (x + 0.5 - cx) / 5.0, (y + 0.5 - cy) / 5.0
                d = dx * dx + dy * dy
                if best is None or d < best[0]:
                    best = (d, dx, dy)
            d, dx, dy = best
            d = min(d, 0.99)
            lvl = light_level(dx, dy, math.sqrt(1 - d)) * 0.7 + 0.15
            if y >= top_end:
                # front face: in shade, with hanging leaf texture
                k = y - top_end
                lvl = -0.1 - k * 0.08 + (0.15 if (x * 3 + y) % 5 == 0 else 0)
            shape.put(x, y, pick(LEAVES, lvl))
    # round the free corners
    for (cx, cy, need) in ((x0, y0, (N_, W_)), (x1 - 1, y0, (N_, E_)), (x0, y1 - 1, (S_, W_)), (x1 - 1, y1 - 1, (S_, E_))):
        if not mask & need[0] and not mask & need[1]:
            shape.put(cx, cy, CLEAR)
    shape.outline(LEAF_DD)
    if front:
        for x in range(T):
            for y in range(T - 3, T):
                on_grass(c, x, y)
    if not mask & E_:
        for y in range(y0 + 2, T):
            on_grass(c, T - 1, y)
    c.blit(shape, 0, 0)
    return c


def rock():
    c = grass(700)
    for y in range(9, 16):
        for x in range(4, 16):
            dx, dy = (x + 0.5 - 10) / 6, (y + 0.5 - 12.5) / 3
            if dx * dx + dy * dy <= 1:
                on_grass(c, x, y)
    r = Canvas(T, T)
    r.dome(8, 9, 6, 5, STONES)
    r.put(6, 7, lighter(STONE_L, 0.3)); r.put(5, 8, STONE_L)
    r.line(9, 7, 11, 10, STONE_D)  # a crack
    r.outline(STONE_DD)
    c.blit(r, 0, 0)
    return c


def on_grass(c, x, y):
    """Darken the grass under something: a cast shadow."""
    p = c.get(x, y)
    if p[3]:
        c.put(x, y, mix(p, (40, 60, 90, 255), 0.32))


def tile_groups():
    """(name, [canvases]) in atlas order. Autotile groups have 16 entries."""
    return [
        ('GRASS', [grass(s) for s in range(4)]),
        ('FLOWERS', [flowers(s) for s in range(3)]),
        ('LONG_GRASS', [long_grass(s) for s in range(3)]),
        ('WILDFLOWERS', [long_grass(s + 10, True) for s in range(3)]),
        ('PATH', [path(m) for m in range(16)]),
        ('WATER', [water(m, 0) for m in range(16)]),
        ('WATER2', [water(m, 1) for m in range(16)]),
        ('BRIDGE_H', [bridge(True)]),
        ('BRIDGE_V', [bridge(False)]),
        ('FENCE', [fence(m) for m in range(16)]),
        ('HEDGE', [hedge(m) for m in range(16)]),
        ('ROCK', [rock()]),
        ('FLOWERBED', [flowerbed(s) for s in range(3)]),
        ('FLOOR', [floor(s) for s in range(2)]),
        ('RUG', [rug(m) for m in range(16)]),
        ('WALL', [wall()]),
        ('WALL_WINDOW', [wall(True)]),
        ('STAIRS_DOWN', [stairs(True)]),
        ('STAIRS_UP', [stairs(False)]),
        ('DOORMAT', [doormat()]),
    ]


# ---------------------------------------------------------------------------
# Props (drawn standing on the ground, bottom-aligned to their footprint)
# ---------------------------------------------------------------------------
def tree(kind=0):
    """0: round leafy tree, 1: pine, 2: round tree in autumn colours."""
    c = Canvas(16, 24)
    c.cylinder_x(6, 15, 4, 8, BARK)
    c.hline(6, 9, 15, BARK[0]); c.hline(6, 9, 16, BARK[1])  # canopy shadow on the trunk
    if kind in (0, 2):
        cols = LEAVES if kind == 0 else AUTUMN
        c.blobs([(8, 9, 7.5, 7.5), (4.5, 10, 3.8, 4), (11.5, 10, 3.8, 4), (8, 5, 5, 4), (6, 7, 3.5, 3), (10, 12.5, 4, 3)], cols)
        c.outline_lit(LEAF_DD if kind == 0 else hexc('4a1e1c'))
    else:  # pine: three tiers, lit on the left, each shading the one below
        for (y, w) in ((3, 3), (7, 5), (11, 7)):
            for yy in range(y - 2, y + 4):
                half = (yy - (y - 2)) * w / 6 + 1
                for x in range(int(8 - half), int(8 + half)):
                    nx = (x + 0.5 - 8) / half
                    lvl = light_level(nx, -0.3, 0.8) - (0.35 if yy >= y + 2 else 0)
                    c.put(x, yy, pick(LEAVES[:4], lvl))
        c.put(8, 0, LEAVES[3])
        c.outline_lit(LEAF_DD)
    c.hline(5, 10, 23, OUTLINE)
    return c


def big_tree():
    c = Canvas(64, 80)
    rnd = random.Random(5)
    # trunk and roots
    c.cylinder_x(24, 44, 16, 32, BARK)
    for x0, dx in ((22, -6), (40, 6), (28, -3), (36, 4)):
        c.line(x0, 70, x0 + dx, 78, BARK[2]); c.line(x0 + 1, 70, x0 + dx + 1, 78, BARK[0])
    c.rect(29, 56, 5, 7, BARK[0]); c.hline(29, 33, 56, OUTLINE)  # a knot hole
    for y in range(44, 52):  # the canopy's shadow on the trunk
        c.hline(24, 39, y, BARK[0] if y < 48 else BARK[1])
    for y in range(52, 76, 5):  # bark texture
        c.put(27 + (y % 3), y, BARK[1]); c.put(36 - (y % 2), y + 2, BARK[0])
    blobs = [(32, 26, 30, 22), (14, 30, 13, 12), (50, 30, 13, 12), (32, 12, 18, 11), (20, 40, 12, 8), (44, 40, 12, 8)]
    for _ in range(26):
        x, y = rnd.randrange(8, 56), rnd.randrange(6, 42)
        dx, dy = (x - 32) / 30, (y - 26) / 22
        if dx * dx + dy * dy < 0.8:
            blobs.append((x, y, rnd.uniform(4, 7), rnd.uniform(3.5, 5.5)))
    c.blobs(blobs, LEAVES, mix_global=0.55)
    c.outline_lit(LEAF_DD)
    return c


def cottage(roof, roof_d, wall_col=hexc('fbf3e1')):
    c = Canvas(48, 48)
    wall_sh = mix(wall_col, (70, 60, 110, 255), 0.28)
    # walls, with the shadow of the eaves along the top and a little
    # ambient shade towards the ground
    c.rect(4, 22, 40, 24, wall_col)
    for y in range(28, 31):
        c.hline(4, 43, y, wall_sh)
    for y in range(40, 44):
        for x in range(4, 44):
            if (x + y) % 2 == 0 or y >= 42:
                c.put(x, y, mix(wall_col, (70, 60, 110, 255), 0.12))
    for x in (4, 43):
        c.rect(x, 22, 1, 24, TRIM)
    c.rect(4, 44, 40, 2, STONES[1]); c.hline(4, 43, 44, STONES[2])
    for x in range(6, 44, 5):
        c.put(x, 45, STONES[0])
    # door, set into the wall
    c.rect(19, 31, 10, 15, darker(WOOD_D, 0.3))
    c.rect(20, 32, 8, 14, WOOD); c.rect(20, 32, 8, 2, WOOD_D); c.vline(20, 32, 45, WOOD_D)
    c.vline(24, 34, 45, WOOD_D); c.vline(21, 34, 45, WOOD_L)
    c.put(26, 39, hexc('ffd76a')); c.put(26, 40, hexc('c08a2a'))
    # windows with flower boxes: recessed glass with a glint
    for x in (7, 33):
        c.rect(x, 31, 8, 7, hexc('fbfbf6'))
        c.rect(x + 1, 32, 6, 5, hexc('7fbfe6')); c.hline(x + 1, x + 6, 32, hexc('4f8ab8')); c.vline(x + 1, 32, 36, hexc('4f8ab8'))
        c.put(x + 3, 34, hexc('e3f6ff')); c.put(x + 4, 33, hexc('e3f6ff')); c.put(x + 5, 35, hexc('bfe6fa'))
        c.vline(x + 4, 32, 36, hexc('fbfbf6'))
        c.rect(x - 1, 38, 10, 2, WOOD); c.hline(x - 1, x + 8, 39, WOOD_DD)
        for k in range(4):
            col = FLOWER_COLS[(k + x) % 5]
            c.put(x + k * 2, 37, col); c.put(x + k * 2 + 1, 37, darker(col, 0.25))
    # roof: rows of shingles, each lit along its top and shadowed by the row
    # above; the whole roof is lighter on the left than the right
    for y in range(0, 26):
        inset = max(0, 10 - y) if y < 10 else 0
        x0, x1 = 1 + inset, 46 - inset
        row = y % 4
        for x in range(x0, x1 + 1):
            side = (x - 24) / 24.0
            base = roof if row in (1, 2) else roof_d
            if row == 0:
                base = lighter(roof, 0.25)
            if row == 3:
                base = darker(roof_d, 0.15)
            if (x + (y // 4) * 3) % 6 == 0 and row != 0:
                base = darker(roof_d, 0.3)  # gaps between shingles
            col = lighter(base, 0.12) if side < -0.55 else darker(base, 0.18) if side > 0.6 else base
            c.put(x, y + 2, col)
    c.hline(1, 46, 27, darker(roof_d, 0.45)); c.hline(1, 46, 26, darker(roof_d, 0.2))
    c.hline(12, 35, 2, lighter(roof, 0.45))  # sun on the ridge
    # chimney: lit on the left
    c.cylinder_x(33, 0, 7, 9, [hexc('7a3328'), hexc('a24a38'), hexc('c4604a'), hexc('dc8068')])
    c.rect(32, 0, 9, 2, hexc('6a2c24')); c.hline(33, 39, 0, hexc('8a3d2e'))
    c.outline()
    return c


def fountain(frame):
    c = Canvas(48, 48)
    c.ellipse(24, 34, 23, 13, STONE_D)
    c.ellipse(24, 32, 23, 12, STONE, shade=(STONE_L, STONE_D))
    c.ellipse(24, 32, 18, 8, WATER_D)
    c.ellipse(24, 31, 17, 7, WATER)
    rnd = random.Random(frame)
    for _ in range(8):
        x, y = rnd.randrange(10, 38), rnd.randrange(26, 37)
        if c.get(x, y)[:3] == WATER[:3]:
            c.put(x, y, WATER_L); c.put(x + 1, y, WATER_L)
    # pillar and top bowl
    c.rect(21, 14, 6, 18, STONE); c.rect(25, 14, 2, 18, STONE_D)
    c.ellipse(24, 14, 9, 4, STONE, shade=(STONE_L, STONE_D))
    c.ellipse(24, 13, 7, 2.5, WATER)
    # spray
    for i in range(6):
        t = i / 5
        dx = 4 + t * 8
        y = 10 - math.sin(t * math.pi) * 8 + 2
        off = (frame * 2) % 3
        c.put(24 - dx, y + off * 0.3, WATER_L); c.put(24 + dx, y + off * 0.3, WATER_L)
    c.vline(24, 2 + frame, 12, WATER_L); c.put(23, 3 + frame, WATER_L); c.put(25, 3 + frame, WATER_L)
    c.outline()
    return c


def dragon(frame):
    body, body_d, belly = hexc('5fb09a'), hexc('3f8a78'), hexc('e9e0a8')
    c = Canvas(64, 48)
    b = frame  # breathing: the body swells a pixel
    # tail curling round the front
    for i in range(18):
        t = i / 17
        x = 8 + t * 34
        y = 40 + math.sin(t * math.pi) * 4
        c.ellipse(x, y, 4 - t * 2, 3.5 - t * 1.5, body_d)
    c.put(43, 40, hexc('e27a4a')); c.put(44, 39, hexc('e27a4a')); c.put(44, 41, hexc('e27a4a'))
    # body
    c.ellipse(28, 28 - b * 0.5, 22, 13 + b * 0.5, body, shade=(lighter(body, 0.2), body_d))
    c.ellipse(30, 33, 14, 6, belly)
    for x in range(18, 44, 4):
        c.put(x, 33, darker(belly, 0.15))
    # spikes along the back
    for i, x in enumerate(range(10, 46, 6)):
        y = 17 - math.sin((x - 10) / 36 * math.pi) * 3 - b * 0.5
        c.put(x, y - 2, hexc('f09a5a')); c.hline(x - 1, x + 1, y - 1, hexc('f09a5a')); c.hline(x - 2, x + 2, y, hexc('d07a3a'))
    # folded wing
    for y in range(0, 12):
        c.hline(16 + y // 2, 34 - y // 3, 14 + y - b, hexc('4a9a86') if y % 3 else hexc('357a68'))
    # head resting on its front paws
    c.ellipse(50, 33, 10, 8, body, shade=(lighter(body, 0.2), body_d))
    c.ellipse(57, 36, 5, 4, lighter(body, 0.1))
    c.put(60, 35, hexc('2b1d2a'))  # nostril
    c.hline(47, 51, 31, hexc('2b1d2a')); c.put(46, 30, hexc('2b1d2a')); c.put(52, 30, hexc('2b1d2a'))  # closed eye
    c.put(49, 34, hexc('f2a0a0')); c.put(50, 34, hexc('f2a0a0'))  # rosy cheek
    for hx in (45, 50):  # little horns sweeping back
        c.put(hx, 26, belly); c.put(hx - 1, 25, belly); c.put(hx - 2, 24, belly); c.put(hx - 1, 26, belly)
    # paws
    c.ellipse(44, 42, 4, 2.5, body_d); c.ellipse(54, 42, 4, 2.5, body_d)
    c.outline()
    return c


def stall():
    c = Canvas(48, 48)
    # counter: a lit top, a front face in shade, planks
    c.rect(2, 26, 44, 20, WOOD_D)
    c.rect(2, 26, 44, 4, WOOD_L); c.hline(2, 45, 29, WOOD)
    for x in range(6, 44, 8):
        c.vline(x, 31, 45, WOOD_DD); c.vline(x + 1, 31, 45, WOOD)
    c.hline(2, 45, 30, WOOD_DD)
    for y in range(41, 46):
        c.hline(2, 45, y, darker(WOOD_D, 0.12 + (y - 41) * 0.04))
    # goods: bread and sausages
    for x in (6, 14):
        c.ellipse(x + 3, 24, 4, 2.5, hexc('d9a05a'), shade=(hexc('f6cc88'), hexc('b07a3a')))
        c.hline(x + 1, x + 4, 23, hexc('fde2ac'))
    c.ellipse(28, 25, 6, 2, hexc('f4f4f0'), shade=(hexc('ffffff'), hexc('c8c4d0')))
    for i in range(4):
        c.hline(24 + i * 2, 25 + i * 2, 24, hexc('b04a3a')); c.put(26 + i * 2, 23, hexc('e8745a'))
    c.ellipse(40, 24, 4, 2.5, hexc('e38c8c'), shade=(hexc('fbc4c4'), hexc('b86060')))  # a cake
    c.put(40, 21, hexc('ff4a4a')); c.put(39, 21, hexc('ff9a9a'))
    # posts
    c.cylinder_x(3, 8, 2, 18, [WOOD_DD, WOOD]); c.cylinder_x(43, 8, 2, 18, [WOOD_DD, WOOD])
    # the awning's shadow on the counter and goods
    for y in range(15, 22):
        for x in range(2, 46):
            p = c.get(x, y)
            if p[3] and y < 19:
                c.put(x, y, darker(p, 0.3))
    # striped awning, curving: lit along the top, darker to the scalloped edge
    red, white = hexc('ec5a5a'), hexc('fff6ee')
    for y in range(2, 14):
        t = (y - 2) / 11
        for x in range(1, 47):
            base = red if (x // 4) % 2 == 0 else white
            col = lighter(base, 0.25) if t < 0.2 else base if t < 0.65 else darker(base, 0.18)
            if x > 40:
                col = darker(col, 0.1)
            c.put(x, y, col)
    for x in range(1, 47):
        if x % 4 in (1, 2):
            c.put(x, 14, darker(red if (x // 4) % 2 == 0 else white, 0.3))
    c.hline(1, 46, 2, hexc('b83a3a'))
    c.outline()
    return c


def picnic_mat():
    c = Canvas(32, 32)
    for y in range(1, 31):
        for x in range(1, 31):
            a, b = (x // 4) % 2, (y // 4) % 2
            c.put(x, y, hexc('e05a5a') if a and b else hexc('fbf0e6') if not a and not b else hexc('f09a96'))
    for x in range(1, 31, 2):
        c.put(x, 0, hexc('fbf0e6')); c.put(x, 31, hexc('fbf0e6'))
    return c


def basket():
    c = Canvas(16, 16)
    c.rect(2, 8, 12, 7, hexc('c48a4a'))
    for y in range(8, 15):
        for x in range(2, 14):
            if (x + y) % 3 == 0:
                c.put(x, y, hexc('9e6a34'))
    c.rect(3, 6, 10, 2, hexc('e05a5a')); c.put(5, 6, hexc('fbf0e6')); c.put(9, 6, hexc('fbf0e6'))
    for i in range(9):
        t = i / 8
        c.put(3 + t * 10, 6 - math.sin(t * math.pi) * 5, hexc('9e6a34'))
    c.outline()
    return c


def signpost():
    c = Canvas(16, 24)
    c.rect(7, 12, 2, 12, WOOD_D)
    c.rect(1, 6, 14, 7, WOOD); c.rect(1, 6, 14, 1, WOOD_L)
    c.hline(3, 12, 8, WOOD_DD); c.hline(3, 10, 10, WOOD_DD)
    c.outline()
    return c


def lamppost():
    c = Canvas(16, 32)
    c.rect(7, 8, 2, 23, hexc('3c3c4a')); c.rect(5, 29, 6, 2, hexc('3c3c4a'))
    c.rect(4, 2, 8, 7, hexc('3c3c4a')); c.rect(5, 3, 6, 5, hexc('ffe9a0')); c.rect(6, 4, 2, 2, hexc('fffbe0'))
    c.hline(3, 12, 1, hexc('3c3c4a'))
    c.outline()
    return c


def duck(frame):
    c = Canvas(16, 16)
    y = 7 + frame
    c.ellipse(7, y + 3, 5, 3, hexc('fff8e8'), shade=(hexc('ffffff'), hexc('d8cfc0')))
    c.ellipse(11, y - 1, 2.5, 2.5, hexc('3f9a5a'))
    c.put(14, y - 1, hexc('f5a63a')); c.put(13, y, hexc('f5a63a'))
    c.put(11, y - 2, hexc('1f1f1f'))
    c.hline(4, 6, y + 1, hexc('d8cfc0'))
    c.outline()
    # ripple under the duck
    c.hline(2, 12, y + 7, hexc('a8e0f6'))
    return c


def possum(frame):
    """A possum peeking out of a bush: frame 0 just ears, frame 1 the face."""
    c = Canvas(16, 16)
    grey, grey_d, pink = hexc('a8a4a8'), hexc('7a767c'), hexc('f2a6b6')
    y = 6 if frame else 9
    c.ellipse(8, y + 3, 4.5, 4, grey, shade=(hexc('c8c4c8'), grey_d))
    c.ellipse(4.5, y, 2, 2, grey_d); c.put(4, y, pink)
    c.ellipse(11.5, y, 2, 2, grey_d); c.put(12, y, pink)
    if frame:
        c.ellipse(8, y + 5, 2.5, 1.5, hexc('f4f0f0'))
        c.put(6, y + 3, hexc('1f1f1f')); c.put(10, y + 3, hexc('1f1f1f'))
        c.put(8, y + 6, pink)
    c.outline()
    # bush in front
    bush = Canvas(16, 16)
    bush.ellipse(8, 13, 8, 4, LEAF, shade=(LEAF_L, LEAF_D))
    bush.outline(LEAF_DD)
    c.blit(bush, 0, 0)
    return c


def bird(frame):
    c = Canvas(8, 8)
    col = hexc('4a4e5c')
    if frame == 0:
        c.line(0, 2, 3, 4, col); c.line(4, 4, 7, 2, col)
    else:
        c.line(0, 5, 3, 4, col); c.line(4, 4, 7, 5, col)
    c.put(3, 4, col); c.put(4, 4, col); c.put(3, 5, col); c.put(4, 5, col)
    return c


def bed(sleeping=False, head=None):
    c = Canvas(16, 32)
    c.rect(0, 0, 16, 6, WOOD_D); c.rect(1, 1, 14, 4, WOOD); c.hline(1, 14, 1, WOOD_L)   # headboard
    c.rect(1, 5, 14, 25, hexc('fbf6ee'))                                                 # sheet
    c.rect(2, 6, 12, 6, hexc('ffffff')); c.hline(2, 13, 11, hexc('ddd6e2')); c.vline(13, 6, 11, hexc('e6e0ea'))  # pillow
    blanket, blanket_l, blanket_d = hexc('78b4ea'), hexc('a8d4f6'), hexc('5a90cc')

    def draw_blanket():
        c.rect(1, 13, 14, 16, blanket); c.hline(1, 14, 13, blanket_l); c.hline(1, 14, 14, lighter(blanket, 0.1))
        for y in range(17, 28, 4):  # soft folds: lit ridge, shaded hollow
            c.hline(2, 13, y, blanket_d); c.hline(2, 13, y - 1, lighter(blanket, 0.12))
        c.vline(14, 13, 28, blanket_d)
    draw_blanket()
    c.rect(0, 29, 16, 3, WOOD_D); c.hline(0, 15, 29, WOOD)
    if sleeping and head is not None:
        c.blit(head, 0, 1)
        draw_blanket()
        c.ellipse(8, 19, 5, 3, lighter(blanket, 0.08), shade=(blanket_l, blanket_d))  # her shape under the blanket
    c.outline()
    return c


def bookshelf():
    c = Canvas(16, 32)
    c.rect(0, 0, 16, 31, WOOD_D); c.rect(1, 1, 14, 29, hexc('4a2c22'))
    c.hline(0, 15, 0, WOOD_L); c.vline(0, 0, 30, WOOD)
    rnd = random.Random(3)
    book_cols = [hexc('d0584a'), hexc('4f7fc0'), hexc('e9b44c'), hexc('7ab86a'), hexc('c879c0'), hexc('f2a6b6'), hexc('6a5acd')]
    for shelf_y in (2, 10, 18):
        x = 1
        while x < 15:
            w = rnd.choice([1, 2, 2])
            h = rnd.randrange(5, 8)
            col = rnd.choice(book_cols)
            ww = min(w, 15 - x)
            c.rect(x, shelf_y + 7 - h, ww, h, col)
            c.put(x, shelf_y + 7 - h, lighter(col, 0.3))             # lit top of the spine
            if ww == 2:
                c.vline(x + 1, shelf_y + 8 - h, shelf_y + 6, darker(col, 0.25))
            x += w
        c.hline(1, 14, shelf_y, hexc('2e1c18'))  # shadow under the shelf above
        c.rect(1, shelf_y + 7, 14, 1, WOOD_L)
    c.rect(1, 26, 14, 4, WOOD); c.hline(1, 14, 26, WOOD_L)
    c.outline()
    return c


def plant():
    c = Canvas(16, 24)
    c.rect(4, 15, 8, 7, hexc('c8704a')); c.rect(3, 14, 10, 2, hexc('e08a5a')); c.vline(11, 15, 21, hexc('a85a3a'))
    for (x, y, rx, ry) in ((8, 8, 4, 6), (4, 10, 3, 4), (12, 10, 3, 4), (8, 4, 2, 3)):
        c.ellipse(x, y, rx, ry, LEAF, shade=(LEAF_L, LEAF_D))
    c.outline()
    return c


def sofa():
    c = Canvas(32, 20)
    col, dark, light = hexc('6f9ee6'), hexc('4e78c0'), hexc('a4c8f6')
    c.rect(1, 2, 30, 9, col); c.rect(1, 2, 30, 2, light); c.hline(1, 30, 10, dark)   # back
    c.rect(0, 9, 32, 9, dark)
    for x0 in (3, 17):  # seat cushions: rounded, lit top-left
        c.rect(x0, 10, 12, 6, col); c.hline(x0, x0 + 11, 10, light); c.vline(x0, 10, 15, lighter(col, 0.1))
        c.hline(x0, x0 + 11, 15, dark); c.vline(x0 + 11, 10, 15, dark)
    c.rect(0, 5, 3, 13, dark); c.rect(29, 5, 3, 13, darker(dark, 0.15))      # arms
    c.vline(0, 5, 17, col); c.hline(0, 2, 5, light); c.hline(29, 31, 5, col)
    c.rect(4, 4, 6, 5, hexc('f6c45a')); c.hline(4, 9, 4, hexc('ffe08a')); c.hline(4, 9, 8, hexc('c8902e'))  # a cushion
    c.rect(1, 18, 30, 1, darker(dark, 0.3))
    c.outline()
    return c


def table():
    c = Canvas(32, 24)
    c.rect(1, 4, 30, 10, WOOD); c.rect(1, 4, 30, 2, WOOD_L); c.rect(1, 13, 30, 2, WOOD_D)
    for x in range(4, 30, 7):
        c.hline(x, x + 3, 9, lighter(WOOD, 0.1))   # a sheen on the varnish
    c.rect(1, 15, 30, 1, WOOD_DD)
    c.cylinder_x(3, 15, 3, 8, [WOOD_DD, WOOD_D, WOOD]); c.cylinder_x(26, 15, 3, 8, [WOOD_DD, WOOD_D, WOOD])
    c.ellipse(10, 7, 3, 1.5, hexc('8a6040'))                        # the mug's shadow
    c.rect(9, 3, 3, 4, hexc('f6f0e6')); c.vline(11, 3, 6, hexc('cfc8d8')); c.put(12, 4, hexc('f6f0e6'))  # a mug
    c.ellipse(23, 8, 4, 2, hexc('8a6040'))
    c.ellipse(22, 7, 4, 2, hexc('e9b44c'), shade=(hexc('ffd880'), hexc('b8822a')))   # fruit bowl
    c.put(21, 6, hexc('e0584a')); c.put(23, 6, hexc('7ac86a')); c.put(22, 5, hexc('ff8a7a'))
    c.outline()
    return c


def bubble_exclaim():
    c = Canvas(10, 12)
    c.rect(1, 0, 8, 9, hexc('ffffff')); c.put(4, 9, hexc('ffffff')); c.put(4, 10, hexc('ffffff')); c.put(5, 9, hexc('ffffff'))
    c.vline(4, 2, 5, hexc('e04848')); c.vline(5, 2, 5, hexc('e04848')); c.put(4, 7, hexc('e04848')); c.put(5, 7, hexc('e04848'))
    c.outline()
    return c


def zzz(frame):
    c = Canvas(12, 12)
    col = hexc('ffffff')
    def z(x, y, s):
        c.hline(x, x + s, y, col); c.line(x + s, y, x, y + s, col); c.hline(x, x + s, y + s, col)
    z(1, 7 - frame, 3)
    z(6, 2 - frame + 1, 2)
    c.outline()
    return c


def heart():
    c = Canvas(9, 8)
    rows = [".rr...rr.", "rrrr.rrrr", "rwrrrrrrr", "rrrrrrrrr", ".rrrrrrr.", "..rrrrr..", "...rrr...", "....r...."]
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch == 'r': c.put(x, y, hexc('e8485a'))
            if ch == 'w': c.put(x, y, hexc('ffb0b8'))
    c.outline()
    return c
