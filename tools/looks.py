"""The looks a buyer can choose on the order form: skin, hair and outfit for
the two people, and a coat for the dog. Every choice is a palette swap of the
drawn characters in art_chars.py, so new options are one line each here (and
one line in the order form, web/order/index.html).

Each preset is one base colour; the shades are worked out from it, so a
custom hex colour ('#7a4fd0') works anywhere a preset name does.
"""
from art_lib import hexc, darker, lighter, mix

SKIN = {
    'porcelain': 'fcd6bc',
    'light': 'f3c3a0',
    'medium': 'd9a07a',
    'tan': 'bf855e',
    'brown': '96603f',
    'deep': '6b412c',
}

HAIR = {
    'blonde': 'ecc66c',
    'ginger': 'e29a56',
    'light brown': 'c49a58',
    'dark brown': '6e4630',
    'black': '3b2d36',
    'grey': 'b9b5bd',
    'pink': 'f29ac0',
    'blue': '6aa8e8',
}

OUTFIT = {
    'pink': 'f09aa8',
    'red': 'd9534f',
    'orange': 'ee8f45',
    'yellow': 'f2c14e',
    'green': '5fae6a',
    'teal': '3fb8a8',
    'blue': '3f86de',
    'purple': '9a72d0',
    'black': '4a4458',
}

TROUSERS = {
    'navy': '4c5274',
    'denim': '4a6fa5',
    'grey': '7a7a88',
    'brown': '7a5a44',
    'black': '3a3646',
}

# coat, then ears and patches
DOG = {
    'white and orange': ('fffaf0', 'e47e36'),
    'white and brown': ('fffaf0', '7a4a32'),
    'white and black': ('fffaf0', '3d3640'),
    'golden': ('e9b860', 'c98a3a'),
    'cream': ('f6e6c4', 'e0bd88'),
    'chocolate': ('8a5a3e', '5e3a28'),
    'black': ('4a4450', '332e3a'),
    'grey': ('bcbcc8', '8a8a9c'),
}


def colour(table, choice, what):
    """A preset name or '#rrggbb' -> RGBA."""
    key = str(choice).strip().lower()
    if key in table:
        v = table[key]
        return tuple(hexc(c) for c in v) if isinstance(v, tuple) else hexc(v)
    if key.startswith('#') and len(key) == 7:
        return hexc(key)
    raise ValueError(f'{what}: {choice!r} is not one of {", ".join(table)} (or a #rrggbb colour)')


def person(look, who):
    """Palette entries for a person: skin, hair and top (plus trousers)."""
    s = colour(SKIN, look.get('skin', 'porcelain'), f'{who} skin')
    h = colour(HAIR, look.get('hair', 'ginger'), f'{who} hair')
    c = colour(OUTFIT, look.get('outfit', 'pink'), f'{who} outfit')
    pal = {
        's': s, 'S': mix(s, hexc('b85a50'), 0.3), 'b': mix(s, hexc('ee5a6e'), 0.35),
        'h': h, 'H': darker(h, 0.3), 'i': lighter(h, 0.4),
        'c': c, 'C': darker(c, 0.3), 'x': lighter(c, 0.45),
    }
    if 'trousers' in look:
        p = colour(TROUSERS, look['trousers'], f'{who} trousers')
        pal.update({'p': p, 'P': darker(p, 0.3)})
    return pal


def dog(look):
    coat, patch = colour(DOG, look.get('coat', 'white and orange'), 'dog coat')
    return {'w': coat, 'W': mix(darker(coat, 0.18), hexc('c8b8d8'), 0.25),
            'r': patch, 'R': darker(patch, 0.3)}
