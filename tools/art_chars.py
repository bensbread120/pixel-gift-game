"""Character sprites: the hero, the partner and the pet.

Drawn as ASCII pixel grids (one character = one art pixel) so they're easy
to tweak by hand. Humans are 16x24 art px, Pet is 16x16. Walk cycles are
4 frames: stand, step, stand, step-other-foot.
"""
from art_lib import hexc, from_ascii, strip, Canvas, OUTLINE

SKIN = {'s': hexc('fcd6bc'), 'S': hexc('e8a088'), 'b': hexc('f69494'),
        'e': hexc('3a2238'), 'm': hexc('d0605e'), 'o': OUTLINE}

HERO = dict(SKIN, **{
    # hair
    'h': hexc('e29a56'), 'H': hexc('b8653a'), 'i': hexc('ffd08a'),
    # dress
    'c': hexc('f09aa8'), 'C': hexc('c86a80'), 'x': hexc('ffcfd4'),
    'k': hexc('8a5040'),
})

PARTNER = dict(SKIN, **{
    # hair
    'h': hexc('c49a58'), 'H': hexc('8a6438'), 'i': hexc('ecc884'),
    # jumper
    'c': hexc('3f86de'), 'C': hexc('2a5aa8'), 'x': hexc('78b0f0'),
    'p': hexc('4c5274'), 'P': hexc('343858'),   # trousers
    'k': hexc('6b4a3a'),
})

PET = {
    'o': OUTLINE,
    'w': hexc('fffaf0'), 'W': hexc('d8cadc'),   # white coat (cool in shadow)
    'r': hexc('e47e36'), 'R': hexc('b0542a'),   # orange ears and patches
    'n': hexc('5a3326'), 'e': hexc('2b1d2a'),
    't': hexc('f08c96'), 'f': hexc('c98a6a'),   # tongue, freckles
}

# --------------------------------------------------------------------------
# Hero: upper body (rows 0-20); legs are added per frame below
# --------------------------------------------------------------------------
K_DOWN = [
    "................",
    ".....oooooo.....",
    "...ooiihhhhoo...",
    "..oiihhiihhhho..",
    ".oiihhiihhhHhho.",
    ".ohhhiihhhhHhho.",
    ".ohhHhhhhhHhhHo.",
    ".ohhHhhssssshHo.",
    ".ohHsssssssshHo.",
    ".ohHsesssssehHo.",
    ".ohhsbssssbshHo.",
    ".oHhsssmmsssHho.",
    ".ohHhossssohHho.",
    ".oHhhHossohHhHo.",
    ".ohHhxccccchHho.",
    ".oHhHccccccHhHo.",
    "..oHsccccccsHo..",
    "...oscccccCso...",
    "...occcccccCo...",
    "..occcccccccCo..",
    "..oooooooooooo..",
]

K_UP = [
    "................",
    ".....oooooo.....",
    "...ooiihhhhoo...",
    "..oiihhhhhhhho..",
    ".oiihhiihhhhhho.",
    ".ohhiihhhhiihho.",
    ".ohhhhHhhiihhHo.",
    ".ohHhhHhhhhhhHo.",
    ".ohHhhhhHhhHhHo.",
    ".ohhHhhhHhhHhHo.",
    ".oHhHhhhhHhhHHo.",
    ".oHhhHhhhHhhhHo.",
    ".oHhhHhhhhHhHHo.",
    ".oHHhhHhhhHhHHo.",
    ".oxHhhHhhHhhHco.",
    ".osHhhhHhHhhHso.",
    "..oscHhHhhHCso..",
    "...occHHHHCCo...",
    "...occcccccCo...",
    "..occcccccccCo..",
    "..oooooooooooo..",
]

K_RIGHT = [
    "................",
    "....oooooo......",
    "...ohhhhiioo....",
    "..ohhhhhhiiho...",
    ".ohhhhhhhhhhho..",
    ".ohhhhhhhhhhhho.",
    ".ohhhhhhhhhhhho.",
    ".oHhhhhhhhsssso.",
    ".oHhhhhhhssssso.",
    ".oHhhhhhhsssseo.",
    ".oHhhhhhhsbssso.",
    ".oHhhhhhhssssmo.",
    ".oHhhhhhhossso..",
    ".oHhhhhhhhoso...",
    ".oHhhhhhhcccco..",
    "..oHhhhhcccCo...",
    "..oHhhhcsccCo...",
    "...oHHccsccCo...",
    "...occcccccCo...",
    "..occcccccccCo..",
    "..oooooooooooo..",
]

# Legs (rows 21-23) for the 4 walk frames
LEGS_FRONT = [
    [".....os..so.....", ".....ok..ko.....", ".....oo..oo....."],
    [".....os..so.....", ".....ok..oo.....", ".....oo........."],
    [".....os..so.....", ".....ok..ko.....", ".....oo..oo....."],
    [".....os..so.....", ".....oo..ko.....", ".........oo....."],
]
LEGS_SIDE = [
    ["......os.so.....", "......ok.ko.....", "......oo.oo....."],
    [".....os...so....", "....okk...kko...", "....ooo...ooo..."],
    ["......os.so.....", "......ok.ko.....", "......oo.oo....."],
    [".....os...so....", "....okk...kko...", "....ooo...ooo..."],
]


def human_walk(upper, legs, pal):
    frames = []
    for i in range(4):
        rows = upper + legs[i]
        f = from_ascii(rows, pal)
        if i in (1, 3):
            # bob: the upper body rises a pixel mid-stride
            body = from_ascii(upper + ["." * 16] * 3, pal).shifted(0, -1)
            legs_only = from_ascii(["." * 16] * 21 + legs[i], pal)
            f = Canvas(16, 24)
            f.blit(legs_only, 0, 0)
            f.blit(body, 0, 0)
        frames.append(f)
    return frames


def close_eyes(rows, eye_row=9):
    """Happy closed eyes: replace the eye pixels with a little curve."""
    r = list(rows)
    line = r[eye_row].replace('e', 's')
    r[eye_row] = line
    above = list(r[eye_row - 1])
    for x, ch in enumerate(rows[eye_row]):
        if ch == 'e':
            above[x] = 'e'
            # widen the curve by one pixel towards the centre
            nx = x + 1 if x < 8 else x - 1
            if above[nx] == 's':
                above[nx] = 'e'
    r[eye_row - 1] = ''.join(above)
    return r


def hero_sprites():
    out = {
        'hero_walk_down': strip(human_walk(K_DOWN, LEGS_FRONT, HERO)),
        'hero_walk_up': strip(human_walk(K_UP, LEGS_FRONT, HERO)),
        'hero_walk_right': strip(human_walk(K_RIGHT, LEGS_SIDE, HERO)),
    }
    out['hero_walk_left'] = flip_strip(out['hero_walk_right'], 16)
    # lying on her back on the picnic mat, eyes closed and smiling
    lying = close_eyes(K_DOWN)
    out['hero_lying'] = from_ascii(lying + LEGS_FRONT[0], HERO)
    return out


def flip_strip(s, fw):
    n = s.w // fw
    out = Canvas(s.w, s.h)
    for i in range(n):
        f = Canvas(fw, s.h)
        for y in range(s.h):
            for x in range(fw):
                f.px[x, y] = s.px[i * fw + x, y]
        out.blit(f.flipped(), i * fw, 0)
    return out


# --------------------------------------------------------------------------
# Partner: sitting cross-legged on the picnic mat, and lying down
# --------------------------------------------------------------------------
B_HEAD = [
    "................",
    "................",
    ".....oooooo.....",
    "...oohhhhhhoo...",
    "..ohhiihhhhhho..",
    ".ohhiihhHhhhiho.",
    ".ohhhhhHHhhhhho.",
    ".ohhhssssssshHo.",
    ".ohheesssseehHo.",
    ".ohhsesssssehHo.",
    ".oHhsssssssshHo.",
    ".oHhsssmmssshHo.",
    ".oHHhossssohHHo.",
    "..oHHoossooHHo..",
]
B_SIT = B_HEAD + [
    "..oxcccccccccCo.",
    ".oxcccccccccccCo",
    ".ocscccccccccsCo",
    ".oCsccccccccCsCo",
    "..ooppppppppPo..",
    ".oppppPPpppppPo.",
    "oPpkkppppppkkpPo",
    ".oookkoooookkoo.",
    "..oooo....oooo..",
    "................",
]
B_LIE = B_HEAD + [
    "..oxccccccccCo..",
    "..oscccccccCso..",
    "..oscccccccCso..",
    "...occcccccCo...",
    "...opppppppPo...",
    "...oppppPpppo...",
    "...opppoppppo...",
    "...oppo.oppPo...",
    "...okko.okko....",
    "....oo...oo.....",
]


def partner_sprites():
    sit = from_ascii(fix_width(B_SIT), PARTNER)
    blink_rows = list(fix_width(B_SIT))
    blink_rows[9] = blink_rows[9].replace('e', 'S')
    blink = from_ascii(blink_rows, PARTNER)
    lie = from_ascii(fix_width(close_eyes(B_LIE)), PARTNER)
    return {
        # idle loop: mostly eyes open, a quick blink
        'partner_sit': strip([sit, sit, sit, blink]),
        'partner_lying': lie,
    }


def fix_width(rows, w=16):
    return [r[:w].ljust(w, '.') for r in rows]


# --------------------------------------------------------------------------
# Pet: white and orange cocker spaniel, 16x16
# --------------------------------------------------------------------------
S_RIGHT = [
    "................",
    "................",
    "........oooo....",
    ".......owwwwo...",
    "......orwwwwwo..",
    ".o....orrwwewwoo",
    "owo..orrrwwwwwno",
    "owwo.orrRrwwwffo",
    ".owwoorrRRowwwo.",
    "..owwwwrRRowoo..",
    "..owrrwwwRowo...",
    "..oWrrwwwwwwo...",
    "..oWWwwwwwwWo...",
]
S_LEGS_SIDE = [
    ["...owo..owo.....", "...owo..owo.....", "...oo...oo......"],
    ["..owo....owo....", "..owo....owo....", "..oo.....oo....."],
    ["...owo..owo.....", "...owo..owo.....", "...oo...oo......"],
    ["....owoowo......", "....owoowo......", "....oo.oo......."],
]

S_DOWN = [
    "................",
    "....oo....oo....",
    "...orRooooRro...",
    "..orRwwwwwwRro..",
    "..orrweffewrro..",
    "..orrwwnnwwrro..",
    "..orrwwwwwwrro..",
    "...orrwttwrro...",
    "....owwwwwwo....",
    "...owwwwwwwwo...",
    "...owwrrwwwwo...",
    "...oWwrrwwwWo...",
    "...oWWwwwwWWo...",
]
S_UP = [
    "................",
    "....oo....oo....",
    "...orRooooRro...",
    "..orRrwwwwrRro..",
    "..orrwwwwwwrro..",
    "..orrwwwwwwrro..",
    "..orrwwwwwwrro..",
    "...orrwwwwrro...",
    "....owwwwwwo....",
    "...owwrrrwwwo...",
    "...owrrRrrwwo...",
    "...oWwrrrwwWo...",
    "...oWWwwwwWWo...",
]
S_LEGS_FRONT = [
    ["....owo..owo....", "....owo..owo....", "....oo....oo...."],
    ["....owo..owo....", "....owo..oo.....", "....oo.........."],
    ["....owo..owo....", "....owo..owo....", "....oo....oo...."],
    ["....owo..owo....", "....oo...owo....", "..........oo...."],
]

S_SIT = [
    "................",
    "....oo....oo....",
    "...orRooooRro...",
    "..orRwwwwwwRro..",
    "..orrweffewrro..",
    "..orrwwnnwwrro..",
    "..orrwwwwwwrro..",
    "...orrwttwrro...",
    "....owwwwwwo....",
    "...owwwwwwwwo...",
    "...owwwwwwwwo...",
    "..owwrrwwwwwwo..",
    "..owrrRwwwwwwo..",
    "..oWwrwwwwwwWo..",
    "..oowwoooowwoo..",
    "...oooo..oooo...",
]

S_LIE = [
    "................",
    "................",
    "................",
    "....oo....oo....",
    "...orRooooRro...",
    "..orRwwwwwwRro..",
    "..orrwwwwwwrro..",
    "..orreewweerro..",
    "..orrwwnnwwrro..",
    "..orrwwwwwwrro..",
    "..oorwwwwwwroo..",
    ".owwwoowwoowwwo.",
    ".owwwwwwwwwwwwo.",
    ".oWwwrrwwwwwwWo.",
    ".oWWwrrwwwwwWWo.",
    "..oooooooooooo..",
]


def pet_sprites():
    def walk(upper, legs):
        frames = []
        for i in range(4):
            f = from_ascii(upper + legs[i], PET)
            frames.append(f)
        return frames

    right = strip(walk(S_RIGHT, S_LEGS_SIDE))
    sit = from_ascii(S_SIT, PET)
    # tail-wag / tongue frame for sitting excitedly
    sit2_rows = list(S_SIT)
    sit2_rows[7] = "...orrwwwwrro..."
    sit2 = from_ascii(sit2_rows, PET)
    return {
        'pet_walk_right': right,
        'pet_walk_left': flip_strip(right, 16),
        'pet_walk_down': strip(walk(S_DOWN, S_LEGS_FRONT)),
        'pet_walk_up': strip(walk(S_UP, S_LEGS_FRONT)),
        'pet_sit': strip([sit, sit2]),
        'pet_lying': from_ascii(S_LIE, PET),
    }


# little details that shouldn't be shaded: eyes, mouths, cheeks, tongue, nose
DETAILS = [SKIN['e'], SKIN['m'], SKIN['b'], PET['n'], PET['e'], PET['t'], PET['f']]


def all_sprites():
    out = {}
    out.update(hero_sprites())
    out.update(partner_sprites())
    out.update(pet_sprites())
    for c in out.values():
        c.auto_shade(skip=DETAILS, round_fw=16)
    return out


def apply_looks(hero=None, partner=None, pet=None):
    """Recolour the characters for a gift (palette entries from looks.py).
    Call before drawing; the palettes above are changed in place."""
    global DETAILS
    for pal, new in ((HERO, hero), (PARTNER, partner), (PET, pet)):
        if new:
            pal.update(new)
    # the blush follows each skin tone; keep every one out of the shading
    DETAILS = [SKIN['e'], SKIN['m'], HERO['b'], PARTNER['b'], PET['n'], PET['e'], PET['t'], PET['f']]
