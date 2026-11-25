"""Tiny pixel-art drawing helpers used by make_art.py.

Everything is drawn at "art resolution" (16 px per map tile) and saved at 2x,
so one art pixel is 2x2 game pixels: chunky, classic-RPG pixel art on the
game's 32 px tiles.
"""
from PIL import Image
import math
import random

SCALE = 2  # art pixels -> game pixels


def hexc(s, a=255):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + (255,)


# Light comes from the top-left. Shadows lean cool (towards blue-purple) and
# highlights lean warm (towards yellow), as in GBA-era Zelda and Pokemon.
SHADE_TO = (38, 30, 72, 255)
LIGHT_TO = (255, 246, 196, 255)
LIGHT_DIR = (-0.55, -0.70, 0.45)


def darker(c, t=0.25):
    return mix(c, SHADE_TO, t)


def lighter(c, t=0.25):
    return mix(c, LIGHT_TO, t)


def ramp(base, steps=(-0.5, -0.25, 0, 0.22, 0.42)):
    """Colours from dark to light around `base`, hue-shifted."""
    return [darker(base, -t) if t < 0 else lighter(base, t) if t > 0 else base for t in steps]


def light_level(nx, ny, nz):
    lx, ly, lz = LIGHT_DIR
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    return (nx * lx + ny * ly + nz * lz) / n


def pick(colours, level, lo=-0.35, hi=0.95):
    """Choose from a dark-to-light ramp by light level."""
    t = (level - lo) / (hi - lo)
    i = int(t * len(colours))
    return colours[max(0, min(len(colours) - 1, i))]


CLEAR = (0, 0, 0, 0)
OUTLINE = hexc('2b1d2a')


class Canvas:
    def __init__(self, w, h, fill=CLEAR):
        self.w, self.h = w, h
        self.img = Image.new('RGBA', (w, h), fill)
        self.px = self.img.load()

    # --- basic plotting ---------------------------------------------------
    def put(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h and c is not None:
            if len(c) == 4 and c[3] < 255 and c[3] > 0:
                # simple alpha blend over what's there
                old = self.px[x, y]
                a = c[3] / 255
                self.px[x, y] = tuple(int(old[i] * (1 - a) + c[i] * a) for i in range(3)) + (max(old[3], c[3]),)
            else:
                self.px[x, y] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[x, y]
        return CLEAR

    def opaque(self, x, y):
        return self.get(x, y)[3] > 0

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.put(xx, yy, c)

    def hline(self, x0, x1, y, c):
        for x in range(int(x0), int(x1) + 1):
            self.put(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(int(y0), int(y1) + 1):
            self.put(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c, shade=None):
        """Filled ellipse. `shade` = (light, dark) for top-left lit shading."""
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                dx = (x + 0.5 - cx) / rx
                dy = (y + 0.5 - cy) / ry
                d = dx * dx + dy * dy
                if d <= 1.0:
                    col = c
                    if shade:
                        # a rounded lump lit from the top-left
                        light, dark = shade
                        col = pick([darker(dark, 0.25), dark, c, light], light_level(dx, dy, math.sqrt(1 - d)))
                    self.put(x, y, col)

    def blobs(self, blobs, colours, mix_global=0.45, bounds=None):
        """Leafy clumps: each blob (cx, cy, rx, ry) is a shaded dome; later
        blobs sit on top of earlier ones. Shading mixes the clump's own
        light with the light on the whole shape, so it reads as one rounded
        mass made of rounded clumps."""
        if bounds is None:
            x0 = min(b[0] - b[2] for b in blobs); x1 = max(b[0] + b[2] for b in blobs)
            y0 = min(b[1] - b[3] for b in blobs); y1 = max(b[1] + b[3] for b in blobs)
            bounds = ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2)
        gcx, gcy, grx, gry = bounds
        owner = {}
        for i, (cx, cy, rx, ry) in enumerate(blobs):
            for y in range(int(cy - ry - 1), int(cy + ry + 2)):
                for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                    dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                    if dx * dx + dy * dy <= 1.0:
                        owner[(x, y)] = i
        for (x, y), i in owner.items():
            cx, cy, rx, ry = blobs[i]
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            local = light_level(dx, dy, math.sqrt(max(0.0, 1 - dx * dx - dy * dy)))
            gx, gy = (x + 0.5 - gcx) / grx, (y + 0.5 - gcy) / gry
            g2 = min(1.0, gx * gx + gy * gy)
            glob = light_level(gx, gy, math.sqrt(1 - g2))
            self.put(x, y, pick(colours, local * (1 - mix_global) + glob * mix_global))

    def dome(self, cx, cy, rx, ry, colours, lo=-0.35, hi=0.95):
        """A shaded ellipse lit from the top-left (a rounded 3D lump)."""
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                d = dx * dx + dy * dy
                if d <= 1.0:
                    self.put(x, y, pick(colours, light_level(dx, dy, math.sqrt(1 - d)), lo, hi))

    def cylinder_x(self, x, y, w, h, colours):
        """A vertical cylinder (trunk, post): lit on the left, dark on the right."""
        for xx in range(int(w)):
            nx = (xx + 0.5) / w * 2 - 1
            c = pick(colours, light_level(nx, 0, math.sqrt(max(0, 1 - nx * nx))))
            self.vline(x + xx, y, y + h - 1, c)

    def auto_shade(self, outline=None, light=0.18, dark=0.26, skip=(), round_fw=None):
        """Give flat-filled pixel art some volume: fill pixels along an edge
        facing the top-left catch the light, those along the bottom-right edge
        fall into shadow (two pixels deep, fading). Edges are transparency or
        the outer outline; inner lines (a chin, a sleeve) don't count, so
        faces don't get pillow-shaded. Colours in `skip` (eyes...) are left alone."""
        outline = outline or OUTLINE
        W, H = self.w, self.h
        src = [[self.px[x, y] for x in range(W)] for y in range(H)]

        def clear(x, y):
            return not (0 <= x < W and 0 <= y < H) or src[y][x][3] == 0

        outer = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                if src[y][x][:3] == outline[:3] and any(clear(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    outer[y][x] = True

        def edge(x, y):
            return clear(x, y) or outer[y][x]

        skip = {c[:3] for c in skip}
        if round_fw:
            # round the whole figure: across each row of each frame, the left
            # side is lit and the right side turns away into shadow
            for f0 in range(0, W, round_fw):
                for y in range(H):
                    xs = [x for x in range(f0, f0 + round_fw) if not clear(x, y)]
                    if len(xs) < 4:
                        continue
                    mid, half = (xs[0] + xs[-1]) / 2, (xs[-1] - xs[0]) / 2
                    for x in xs:
                        c = src[y][x]
                        if c[:3] == outline[:3] or c[:3] in skip:
                            continue
                        nx = (x - mid) / half
                        if nx > 0.3:
                            src[y][x] = darker(c, 0.16 if nx < 0.7 else 0.24)
                        elif nx < -0.45:
                            src[y][x] = lighter(c, 0.1)
                        self.px[x, y] = src[y][x]
        for y in range(H):
            for x in range(W):
                c = src[y][x]
                if c[3] == 0 or c[:3] == outline[:3] or c[:3] in skip:
                    continue
                if edge(x + 1, y) or edge(x, y + 1):
                    self.px[x, y] = darker(c, dark)
                elif edge(x - 1, y) or edge(x, y - 1):
                    self.px[x, y] = lighter(c, light)
                elif edge(x + 2, y) or edge(x, y + 2):
                    self.px[x, y] = darker(c, dark * 0.45)
        # selective outline: soften the outer outline on the lit (top-left) side
        for y in range(H):
            for x in range(W):
                if not outer[y][x]:
                    continue
                if clear(x - 1, y) or clear(x, y - 1):
                    for dx, dy in ((1, 0), (0, 1)):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < W and 0 <= yy < H and src[yy][xx][3] and src[yy][xx][:3] != outline[:3]:
                            if not (clear(x + 1, y) or clear(x, y + 1)):
                                self.px[x, y] = mix(outline, darker(src[yy][xx], 0.35), 0.55)
                            break

    def outline_lit(self, dark, light=None):
        """1px outline; with `light`, the top-left edges use the lighter colour
        (selective outlining, which keeps lit edges soft)."""
        src = [[self.opaque(x, y) for x in range(self.w)] for y in range(self.h)]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x]:
                    continue
                hit = []
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < self.w and 0 <= yy < self.h and src[yy][xx]:
                        hit.append((dx, dy))
                if hit:
                    # the object is to the right/below this pixel -> it's a top-left edge
                    top_left = all(d in ((1, 0), (0, 1)) for d in hit)
                    self.px[x, y] = light if (light and top_left) else dark

    def line(self, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n):
            t = i / max(n - 1, 1)
            self.put(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)

    def outline(self, c=OUTLINE, diagonal=False):
        """Add a 1px outline around every opaque pixel."""
        src = [[self.opaque(x, y) for x in range(self.w)] for y in range(self.h)]
        n = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diagonal:
            n += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x]:
                    continue
                for dx, dy in n:
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < self.w and 0 <= yy < self.h and src[yy][xx]:
                        self.px[x, y] = c
                        break

    def blit(self, other, x, y, flip=False):
        for yy in range(other.h):
            for xx in range(other.w):
                c = other.px[other.w - 1 - xx if flip else xx, yy]
                if c[3] > 0:
                    self.put(x + xx, y + yy, c)

    def flipped(self):
        c = Canvas(self.w, self.h)
        c.blit(self, 0, 0, flip=True)
        return c

    def copy(self):
        c = Canvas(self.w, self.h)
        c.blit(self, 0, 0)
        return c

    def shifted(self, dx, dy):
        c = Canvas(self.w, self.h)
        c.blit(self, dx, dy)
        return c

    # --- output -------------------------------------------------------------
    def scaled(self, s=SCALE):
        return self.img.resize((self.w * s, self.h * s), Image.NEAREST)

    def save(self, path):
        self.scaled().save(path)


def from_ascii(rows, palette):
    """Build a canvas from rows of characters; '.' and ' ' are transparent."""
    w = max(len(r) for r in rows)
    for i, r in enumerate(rows):
        assert len(r) == w, f"row {i} is {len(r)} wide, expected {w}: {r!r}"
    c = Canvas(w, len(rows))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in '. ':
                continue
            c.put(x, y, palette[ch])
    return c


def strip(frames):
    """Lay frames out horizontally into one canvas (a sprite strip)."""
    w, h = frames[0].w, frames[0].h
    out = Canvas(w * len(frames), h)
    for i, f in enumerate(frames):
        out.blit(f, i * w, 0)
    return out


def noise_tile(w, h, base, specks, seed, density=0.12):
    """Base colour with random specks: grass, floors, etc."""
    rnd = random.Random(seed)
    c = Canvas(w, h, base)
    for y in range(h):
        for x in range(w):
            if rnd.random() < density:
                c.put(x, y, rnd.choice(specks))
    return c
