"""Build the game's maps into assets/maps/*.txt.

    tools/.venv/Scripts/python tools/make_maps.py

Each map file has a ground layer and an objects layer of the same size.
The legend is in sdl3-demo/world.h. The interiors are drawn by hand below;
the village is laid out with a few helpers so the route, its grassy margins
(Hero can wander a little) and the forest boundary stay consistent.
"""
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'maps')

# ---------------------------------------------------------------------------
# Interiors (ground, objects)
# ---------------------------------------------------------------------------
BEDROOM = ([
    "#W###W####",
    "........v.",
    "..rrrr....",
    "..rrrr....",
    "..rrrr....",
    "..........",
    "..........",
], [
    "..........",
    "B...K.....",
    ".@&.......",
    "..........",
    "..........",
    "..........",
    "p........p",
])
# B bed, K bookshelf, p plant, & Pet. Hero starts asleep in the bed and
# gets up at the cell to its right.

LIVING = ([
    "##W####W##",
    "........^.",
    "..rrrr....",
    "..rrrr....",
    "..rrrr....",
    "..........",
    "....ee....",
], [
    "..........",
    "pSS....@.p",
    "..........",
    "..AA......",
    "..........",
    ".....&....",
    "..........",
])

# ---------------------------------------------------------------------------
# Village
# ---------------------------------------------------------------------------
W, H = 62, 44


class Grid:
    def __init__(self):
        self.g = [['T'] * W for _ in range(H)]   # forest everywhere to start
        self.o = [['.'] * W for _ in range(H)]

    def ground(self, x, y, ch):
        if 0 <= x < W and 0 <= y < H:
            self.g[y][x] = ch

    def obj(self, x, y, ch):
        self.o[y][x] = ch

    def rect(self, x0, y0, x1, y1, ch=',', only=None):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if only is None or self.g[y][x] in only:
                    self.ground(x, y, ch)

    def ellipse(self, cx, cy, rx, ry, ch=',', only=None):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    if 0 <= x < W and 0 <= y < H and (only is None or self.g[y][x] in only):
                        self.ground(x, y, ch)

    def route(self, pts, margin=2):
        """A 2-wide path along axis-aligned segments, with grass either side."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            lx, hx = min(x0, x1), max(x0, x1)
            ly, hy = min(y0, y1), max(y0, y1)
            self.rect(lx - margin, ly - margin, hx + 1 + margin, hy + 1 + margin, ',', only='T')
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            lx, hx = min(x0, x1), max(x0, x1)
            ly, hy = min(y0, y1), max(y0, y1)
            for y in range(ly, hy + 2):
                for x in range(lx, hx + 2):
                    if self.g[y][x] == '~':
                        self.ground(x, y, 'H' if y0 == y1 else 'I')  # bridge
                    elif self.g[y][x] not in 'HI':
                        self.ground(x, y, '=')

    def text(self, layer):
        return [''.join(r) for r in layer]


def village():
    g = Grid()
    rnd = random.Random(7)

    # --- clearings -----------------------------------------------------------
    g.rect(2, 2, 21, 15)                    # home + village square
    g.ellipse(31, 8, 8, 6.5)                # big tree glade
    g.ellipse(38, 21, 8, 5)                 # dragon's hollow
    g.rect(3, 26, 15, 37)                   # market corner
    g.rect(26, 29, 37, 39)                  # flower garden
    g.ellipse(50, 33, 10, 8)                # the field (kept apart from the
    g.rect(44, 27, 57, 39, only='T')        # hollow so there's no shortcut)

    # --- the stream and the duck pond ----------------------------------------
    for y in range(16, H - 2):
        g.ground(23, y, '~'); g.ground(24, y, '~')
    g.ellipse(20, 29, 4.5, 3, '~')

    # --- the route Pet takes ------------------------------------------------
    g.route([(7, 6), (7, 11), (16, 11), (16, 10), (29, 10), (33, 10), (33, 23), (21, 23), (9, 23), (9, 33),
             (21, 33), (31, 33), (45, 33), (45, 30)])

    # --- long grass and wildflowers in the field -------------------------------
    for y in range(H):
        for x in range(40, W):
            if g.g[y][x] == ',' and y >= 27:
                g.ground(x, y, 'w' if rnd.random() < 0.18 else 'l')

    # --- decoration: flowers in the grass, a few rocks and lone trees ---------
    for y in range(H):
        for x in range(W):
            if g.g[y][x] == ',' and rnd.random() < 0.08:
                g.ground(x, y, ';')

    # --- buildings and landmarks (objects anchor at their footprint's top-left)
    g.obj(6, 4, 'C')     # Hero's cottage (door at 7,5)
    g.obj(14, 3, 'D')
    g.obj(17, 6, 'G')
    g.obj(3, 9, 'G')
    g.obj(12, 7, 'F')    # stop 1: the fountain (footprint 12..14, 7..8)
    g.obj(30, 6, 'Y')    # stop 2: the big tree (trunk 30..31, 6)
    g.obj(37, 19, 'R')   # stop 3: the dragon (37..40, 19..20)
    g.obj(17, 29, 'd'); g.obj(20, 28, 'd'); g.obj(19, 31, 'd')  # stop 4: ducks
    g.obj(5, 29, 'M')    # stop 5: the bakery stall (5..7, 29..30)
    g.obj(31, 31, 'q')   # stop 6: the possum, peeking from a hedge
    g.obj(47, 31, 'm')   # stop 7: the picnic mat (47..48, 31..32)
    g.obj(48, 31, 'b')   # Partner, sitting on the mat
    g.obj(49, 31, 'k')   # picnic basket

    # hedges around the possum, flowerbeds in the garden
    for x in range(28, 36):
        if x != 31:
            g.ground(x, 31, 'h')
    for (x0, y0) in ((27, 36), (31, 36), (35, 36)):
        g.rect(x0, y0, x0 + 1, y0 + 1, '*')
    for (x0, y0) in ((27, 29), (34, 29)):
        g.rect(x0, y0, x0 + 1, y0, '*')
    # rocks round the dragon's hollow
    for (x, y) in ((32, 18), (43, 18), (44, 22), (31, 25), (42, 25)):
        g.ground(x, y, 'o')
    # lamp posts and a signpost in the village
    g.obj(5, 12, 'L'); g.obj(18, 12, 'L'); g.obj(11, 6, 'n')
    # fences along the market corner
    for x in range(3, 8):
        g.ground(x, 26, 'f')
    for y in range(26, 29):
        g.ground(3, y, 'f')

    # --- markers -----------------------------------------------------------------
    g.obj(7, 6, '@')     # Hero steps out of the front door
    g.obj(8, 7, '&')     # Pet waits for her
    g.obj(14, 10, '1')   # Pet's spot at each stop
    g.obj(31, 8, '2')
    g.obj(35, 21, '3')
    g.obj(20, 25, '4')
    g.obj(7, 31, '5')
    g.obj(31, 32, '6')
    g.obj(46, 32, '7')
    return g.text(g.g), g.text(g.o)


def write(name, layers):
    ground, objects = layers
    assert len(ground) == len(objects), name
    for a, b in zip(ground, objects):
        assert len(a) == len(b) == len(ground[0]), (name, a, b)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + '.txt'), 'w', newline='\n') as f:
        f.write(f'# {name} map -- generated by tools/make_maps.py, legend in sdl3-demo/world.h\n')
        f.write('ground\n')
        f.write('\n'.join(ground) + '\n')
        f.write('objects\n')
        f.write('\n'.join(objects) + '\n')


if __name__ == '__main__':
    write('bedroom', BEDROOM)
    write('living', LIVING)
    write('village', village())
    print('maps written to', OUT)
