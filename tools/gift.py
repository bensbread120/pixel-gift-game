"""One gift order, from the buyer's form to the delivered game.

    tools/.venv/Scripts/python tools/gift.py import <pasted.txt>   form text -> orders/<id>/order.json
    tools/.venv/Scripts/python tools/gift.py build <id>            art, pages, card, delivery message
    tools/.venv/Scripts/python tools/gift.py play <id> [--online]  play it in the browser (autopilot with --auto)
    tools/.venv/Scripts/python tools/gift.py deploy                publish every live gift to Cloudflare Pages

The buyer fills in the order form (web/order/index.html, hosted at /order/)
and pastes the text it makes into an Etsy message. Save that text to a file,
then `import` it. Photos for the "with photos" package go in
orders/<id>/photos/ as memory1.jpg ... memory6.jpg.

orders/ and site/ hold buyers' names, words and photos, so neither is
committed. Each order gets:

    orders/<id>/order.json      the order; edit and rebuild to fix anything
    orders/<id>/photos/         buyer photos (delete after delivery)
    orders/<id>/assets/         the game's assets for this gift (generated)
    orders/<id>/delivery/       what the buyer gets:
        <Title>.html            offline copy to keep: one file, opens from disk
        online.html             the same game, encrypted with the gift's password
        card.png                printable card with a QR code
        message.txt             the Etsy message to send with the files

One build of the game (build-web/sdl3-demo/index.html, from web/shell.html)
serves every gift; this script injects a gift's assets into a copy of it.
"""
import argparse
import base64
import datetime as dt
import functools
import http.server
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import unicodedata
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
ORDERS = os.path.join(ROOT, 'orders')
SITE = os.path.join(ROOT, 'site')
TEMPLATE_ASSETS = os.path.join(ROOT, 'assets')
GAME_PAGE = os.path.join(ROOT, 'build-web', 'sdl3-demo', 'index.html')
ORDER_FORM = os.path.join(ROOT, 'web', 'order', 'index.html')
LANDING = os.path.join(ROOT, 'web', 'site-index.html')
DEPLOY_CONFIG = os.path.join(TOOLS, 'deploy.json')
DESKTOP_EXE = os.path.join(ROOT, 'build', 'sdl3-demo', 'Debug', 'sdl3-demo.exe')

ONLINE_YEARS = 2
PBKDF2_ITERATIONS = 300_000

# What fits on screen (the font is 8 px, the screen 48 characters wide).
# web/order/index.html uses the same limits.
LIMITS = {
    'name': 12, 'title': 24, 'dedication': 60, 'final_line': 20,
    'memory_title': 20, 'memory_caption': 100, 'message': 2500,
}

# Friendly words for passwords: easy to read off a card and type on a phone.
WORDS = """apple acorn badger bagel beach berry biscuit blossom bramble breeze
bubble button cactus candle canoe cherry cloud clover cocoa comet cookie coral
cosy crumble daisy dolphin dragon dumpling ember falcon fern fiddle firefly
flannel fox frost garden ginger glow honey island jelly kettle kite koala lantern
lemon lily maple marble meadow mitten moon moss muffin nectar nutmeg oak ocean
otter owl panda pancake parsnip peach pebble penguin pepper pickle pine pixel
plum pocket pond poppy puffin pumpkin quill rabbit radish raven ribbon river
robin rocket rose saffron sailor sparrow sprout star sunny swan teapot thistle
tiger toast toffee tulip velvet violet waffle walnut willow winter wren yarrow
""".split()


# ---------------------------------------------------------------------------
# Text: the game's font is plain ASCII
# ---------------------------------------------------------------------------
REPLACE = {
    '‘': "'", '’': "'", '‚': "'", '′': "'",
    '“': '"', '”': '"', '„': '"', '″': '"',
    '–': '-', '—': '-', '−': '-', '…': '...',
    ' ': ' ', ' ': ' ', ' ': ' ', '×': 'x',
    'ß': 'ss', 'æ': 'ae', 'Æ': 'AE', 'œ': 'oe', 'ø': 'o', 'Ø': 'O',
    '♥': '<3', '❤': '<3', '️': '',
}


def clean(text, what, warnings):
    """Plain ASCII the game can draw, warning about anything changed or dropped."""
    original = text = str(text).replace('\r\n', '\n').replace('\r', '\n')
    for a, b in REPLACE.items():
        text = text.replace(a, b)
    # accents: e-acute becomes e
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    dropped = sorted({c for c in text if ord(c) > 126 or (ord(c) < 32 and c != '\n')})
    if dropped:
        text = ''.join(c for c in text if c not in dropped)
    text = '\n'.join(re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    if dropped:
        warnings.append(f'{what}: removed characters the game can\'t draw: {" ".join(dropped)}')
    elif text != original.strip() and any(ord(c) > 126 for c in original):
        warnings.append(f'{what}: changed to plain letters: {text[:60]!r}')
    return text


def check_length(text, limit, what, errors):
    if not text:
        errors.append(f'{what} is empty')
    elif len(text) > limit:
        errors.append(f'{what} is {len(text)} characters; the most that fits is {limit}: {text[:40]!r}...')


# ---------------------------------------------------------------------------
# import: the order form's text -> order.json
# ---------------------------------------------------------------------------
SECTIONS = {'player': 'hero', 'you': 'partner', 'dog': 'pet'}


def parse_form(text):
    """Read the block the order form makes (see web/order/index.html)."""
    text = text.replace('\r\n', '\n')
    start = text.find('=== Pixel gift order')
    end = text.find('=== End of order ===')
    if start < 0 or end < 0:
        sys.exit('No order found: the text needs the "=== Pixel gift order" and "=== End of order ===" lines.')
    lines = text[start:end].split('\n')[1:]
    order = {'hero': {}, 'partner': {}, 'pet': {}, 'memories': [{} for _ in range(6)]}
    section = None
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\[(\w+)\]', line)
        if m:
            section = SECTIONS.get(m.group(1).lower(), m.group(1).lower())
            continue
        if line.lower().startswith('message:'):
            first = line.split(':', 1)[1].strip()
            order['message'] = '\n'.join(([first] if first else []) + [l.rstrip() for l in lines[i + 1:]]).strip()
            break
        if ':' not in line:
            continue
        key, value = (s.strip() for s in line.split(':', 1))
        key = key.lower()
        m = re.match(r'memory (\d) (title|caption)', key)
        if m and 1 <= int(m.group(1)) <= 6:
            order['memories'][int(m.group(1)) - 1][m.group(2)] = value
        elif section in ('hero', 'partner', 'pet'):
            order[section][key] = value
        else:
            order[key.replace(' ', '_')] = value
    order['package'] = 'photos' if 'photo' in order.get('package', '').lower() else 'basic'
    return order


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'gift'


def cmd_import(args):
    with open(args.file, encoding='utf-8') as f:
        order = parse_form(f.read())
    today = dt.date.today()
    oid = args.id or f'{today:%Y%m%d}-{slugify(order["hero"].get("name", ""))}'
    folder = os.path.join(ORDERS, oid)
    path = os.path.join(folder, 'order.json')
    if os.path.exists(path) and not args.force:
        sys.exit(f'{path} already exists (use --force to replace it)')
    order = {
        'id': oid,
        'created': today.isoformat(),
        **order,
        # the gift's address and password: never change these after delivery
        'slug': ''.join(secrets.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(10)),
        'password': f'{secrets.choice(WORDS)}-{secrets.choice(WORDS)}-{secrets.randbelow(90) + 10}',
        'online_until': today.replace(year=today.year + ONLINE_YEARS).isoformat(),
    }
    os.makedirs(os.path.join(folder, 'photos'), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(order, f, indent=2, ensure_ascii=False)
    print(f'wrote {os.path.relpath(path, ROOT)}')
    if order['package'] == 'photos':
        print(f'photos package: save the buyer\'s photos as {os.path.relpath(folder, ROOT)}/photos/memory1.jpg ... memory6.jpg')
    _, warnings, errors = validate(order)
    report(warnings, errors)
    print(f'next: check the order, then  tools/.venv/Scripts/python tools/gift.py build {oid}')


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def load_order(oid):
    path = os.path.join(ORDERS, oid, 'order.json')
    if not os.path.exists(path):
        sys.exit(f'no order {oid!r}: expected {path}')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def validate(order):
    """The gift's text, cleaned, plus warnings and errors for the order."""
    warnings, errors = [], []
    t = {}
    for role, label in (('hero', 'player'), ('partner', 'you'), ('pet', 'dog')):
        name = clean(order.get(role, {}).get('name', ''), f'{label} name', warnings)
        check_length(name, LIMITS['name'], f'{label} name', errors)
        t[role] = name
    for key in ('title', 'dedication', 'final_line'):
        t[key] = clean(order.get(key, ''), key, warnings)
        check_length(t[key], LIMITS[key], key, errors)
    for i, m in enumerate(order.get('memories', [])[:6]):
        for part in ('title', 'caption'):
            v = clean(m.get(part, ''), f'memory {i + 1} {part}', warnings)
            check_length(v, LIMITS['memory_' + part], f'memory {i + 1} {part}', errors)
            t[f'memory{i + 1}_{part}'] = v
    if len(order.get('memories', [])) < 6:
        errors.append('the order needs six memories')
    t['message'] = clean(order.get('message', ''), 'message', warnings)
    check_length(t['message'], LIMITS['message'], 'message', errors)
    if len({t['hero'].lower(), t['partner'].lower(), t['pet'].lower()}) < 3:
        warnings.append('two characters share a name, which reads oddly in the dialogue')

    # looks: make sure every choice is a known colour
    sys.path.insert(0, TOOLS)
    import looks
    try:
        looks.person(order.get('hero', {}), 'player')
        looks.person({**order.get('partner', {}), 'trousers': order.get('partner', {}).get('trousers', 'navy')}, 'you')
        looks.dog(order.get('pet', {}))
    except ValueError as e:
        errors.append(str(e))
    return t, warnings, errors


def report(warnings, errors):
    for w in warnings:
        print(f'  warning: {w}')
    for e in errors:
        print(f'  ERROR: {e}')


def escape(value):
    return value.replace('\\', '\\\\').replace('\n', '\\n')


def write_gift_txt(text, path):
    keys = ['hero', 'partner', 'pet', 'title', 'dedication', 'final_line']
    keys += [f'memory{i}_{p}' for i in range(1, 7) for p in ('title', 'caption')]
    keys.append('message')
    lines = ['# Written by tools/gift.py from order.json: edit that and rebuild instead.']
    lines += [f'{k}: {escape(text[k])}' for k in keys]
    with open(path, 'w', encoding='ascii', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def make_assets(order, text, folder):
    """The template's assets, recoloured for this gift, with its memory cards and words."""
    sys.path.insert(0, TOOLS)
    import art_chars
    import looks
    import make_art
    assets = os.path.join(folder, 'assets')
    if os.path.isdir(assets):
        shutil.rmtree(assets)
    shutil.copytree(TEMPLATE_ASSETS, assets, ignore=shutil.ignore_patterns('*.aseprite', 'memories'))
    partner = dict(order['partner'])
    partner.setdefault('trousers', 'navy')
    art_chars.apply_looks(looks.person(order['hero'], 'player'), looks.person(partner, 'you'), looks.dog(order['pet']))
    photos = os.path.join(folder, 'photos')
    make_art.generate(assets=assets, photos_dir=photos, crops=order.get('crops', {}), header=False)
    write_gift_txt(text, os.path.join(assets, 'gift.txt'))
    have = [f for f in os.listdir(photos) if f.startswith('memory')] if os.path.isdir(photos) else []
    return assets, have


def collect(assets):
    files = {}
    for dirpath, _, names in os.walk(assets):
        for n in names:
            full = os.path.join(dirpath, n)
            rel = os.path.relpath(full, assets).replace(os.sep, '/')
            with open(full, 'rb') as f:
                files[rel] = base64.b64encode(f.read()).decode('ascii')
    return files


def encrypt(payload, password):
    """AES-256-GCM with a PBKDF2-SHA256 key, as web/shell.html's decrypt() expects."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import hashlib
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac('sha256', password.strip().lower().encode(), salt, PBKDF2_ITERATIONS, 32)
    data = AESGCM(key).encrypt(iv, payload, None)
    b64 = lambda b: base64.b64encode(b).decode('ascii')
    return {'salt': b64(salt), 'iv': b64(iv), 'iter': PBKDF2_ITERATIONS, 'data': b64(data)}


def game_page(title, gift):
    if not os.path.exists(GAME_PAGE):
        sys.exit(f'{GAME_PAGE} is missing: build the web version first (see README, "Web build").')
    with open(GAME_PAGE, encoding='utf-8') as f:
        page = f.read()
    # the shell's <script id="gift-data"> holds this token (Emscripten
    # minifies the tag itself, so match the token alone)
    if page.count('__GIFT_DATA__') != 1:
        sys.exit(f'{GAME_PAGE} has no gift slot: rebuild it from the current web/shell.html')
    html_title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    data = json.dumps(gift, separators=(',', ':')).replace('</', '<\\/')
    return page.replace('__GIFT_DATA__', data).replace('__GIFT_TITLE__', html_title)


def site_config():
    if not os.path.exists(DEPLOY_CONFIG):
        sys.exit(f'{DEPLOY_CONFIG} is missing; create it with {{"project": "...", "url": "https://....pages.dev"}}')
    with open(DEPLOY_CONFIG, encoding='utf-8') as f:
        return json.load(f)


def gift_url(order):
    return f'{site_config()["url"].rstrip("/")}/g/{order["slug"]}/'


def make_card(order, text, assets, path):
    """A printable A6 card (300 dpi): the three characters, a QR code that opens
    the game already unlocked, and the address and password to type by hand."""
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1240, 1748
    paper, ink, accent = (255, 248, 236), (43, 29, 42), (232, 106, 142)
    card = Image.new('RGB', (W, H), paper)
    d = ImageDraw.Draw(card)
    d.rectangle((30, 30, W - 31, H - 31), outline=accent, width=8)
    font = lambda size: ImageFont.load_default(size=size)

    def centred(y, s, size, fill=ink):
        f = font(size)
        while d.textlength(s, font=f) > W - 160 and size > 20:
            size -= 4
            f = font(size)
        d.text(((W - d.textlength(s, font=f)) / 2, y), s, font=f, fill=fill)

    centred(110, text['title'], 84, accent)
    centred(220, f'A little game for {text["hero"]}', 46)

    # the characters, first frame of each sprite, scaled up crisply
    def frame(name, frames):
        img = Image.open(os.path.join(assets, 'sprites', name + '.png')).convert('RGBA')
        fw = img.width // frames
        img = img.crop((0, 0, fw, img.height))
        return img.resize((img.width * 6, img.height * 6), Image.NEAREST)
    people = [frame('hero_walk_down', 4), frame('pet_sit', 2), frame('partner_sit', 4)]
    gap = 40
    total = sum(p.width for p in people) + gap * 2
    x, base = (W - total) // 2, 640
    for p in people:
        card.paste(p, (x, base - p.height), p)
        x += p.width + gap

    url = gift_url(order)
    qr = qrcode.QRCode(border=2, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(f'{url}#p={order["password"]}')
    qr.make(fit=True)
    q = qr.make_image(fill_color=ink, back_color=paper).get_image().convert('RGB')
    q = q.resize((560, 560), Image.NEAREST)
    card.paste(q, ((W - 560) // 2, 720))
    centred(1300, 'Scan to play', 52, accent)
    centred(1390, url.replace('https://', ''), 34)
    centred(1450, f'Password: {order["password"]}', 40)
    centred(1580, f'With love from {text["partner"]}', 40)
    card.save(path, dpi=(300, 300))


def delivery_message(order, text, keepsake):
    until = dt.date.fromisoformat(order['online_until'])
    photos = '\nI delete your photos once you\'re happy with the gift.' if order['package'] == 'photos' else ''
    return f"""Hi! {text['hero']}'s game is ready. I hope they love it.

PLAY ONLINE
{gift_url(order)}
Password: {order['password']}
It works on phones (turn them sideways), tablets and laptops, and stays online until {until:%d %B %Y}.

ATTACHED
- {keepsake}: a copy to keep forever. Open it in any web browser, no internet or password needed.
- card.png: a printable card. Its QR code opens the game straight away, no typing needed.

HOW TO PLAY
Arrow keys or WASD to walk, Space to read on and look at things. On a phone, use the on-screen pad and the A button.
It takes about ten minutes to play through.

If anything looks wrong (a typo, a colour), reply here and I'll fix it.{photos}
"""


def cmd_build(args):
    order = load_order(args.id)
    folder = os.path.join(ORDERS, args.id)
    text, warnings, errors = validate(order)
    report(warnings, errors)
    if errors:
        sys.exit('fix order.json and build again')
    assets, photos = make_assets(order, text, folder)
    if order['package'] == 'photos' and len(photos) < 6:
        print(f'  warning: photos package, but only {len(photos)} photos in {folder}/photos; the rest get drawn cards')

    out = os.path.join(folder, 'delivery')
    os.makedirs(out, exist_ok=True)
    files = collect(assets)
    keepsake = re.sub(r'[^A-Za-z0-9]+', '-', text['title'].replace("'", '')).strip('-') + '.html'
    for old in os.listdir(out):
        if old.endswith('.html'):
            os.remove(os.path.join(out, old))
    with open(os.path.join(out, keepsake), 'w', encoding='utf-8') as f:
        f.write(game_page(text['title'], {'files': files}))
    payload = json.dumps({'files': files}, separators=(',', ':')).encode()
    with open(os.path.join(out, 'online.html'), 'w', encoding='utf-8') as f:
        f.write(game_page(text['title'], {'enc': encrypt(payload, order['password'])}))
    make_card(order, text, assets, os.path.join(out, 'card.png'))
    with open(os.path.join(out, 'message.txt'), 'w', encoding='utf-8') as f:
        f.write(delivery_message(order, text, keepsake))
    size = os.path.getsize(os.path.join(out, keepsake)) / 1e6
    print(f'built {os.path.relpath(out, ROOT)}: {keepsake} ({size:.1f} MB), online.html, card.png, message.txt')
    print(f'next: play it through:  tools/.venv/Scripts/python tools/gift.py play {args.id} --auto')


# ---------------------------------------------------------------------------
# play: serve the delivery folder and open it
# ---------------------------------------------------------------------------
def cmd_play(args):
    order = load_order(args.id)
    if args.desktop:
        if not os.path.exists(DESKTOP_EXE):
            sys.exit(f'{DESKTOP_EXE} is missing: build the desktop version first')
        cmd = [DESKTOP_EXE, '--assets', os.path.join(ORDERS, args.id, 'assets')] + (['--auto'] if args.auto else [])
        sys.exit(subprocess.call(cmd))
    out = os.path.join(ORDERS, args.id, 'delivery')
    page = 'online.html' if args.online else next(f for f in os.listdir(out) if f.endswith('.html') and f != 'online.html')
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=out)
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    url = f'http://127.0.0.1:{server.server_port}/{page}' + ('?auto' if args.auto else '')
    print(f'playing {url}' + (f'  (password: {order["password"]})' if args.online else ''))
    print('Ctrl+C to stop')
    threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# deploy: every live gift, the order form and a landing page -> Cloudflare Pages
# ---------------------------------------------------------------------------
def cmd_deploy(args):
    config = site_config()
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    shutil.copy(LANDING, os.path.join(SITE, 'index.html'))
    os.makedirs(os.path.join(SITE, 'order'))
    shutil.copy(ORDER_FORM, os.path.join(SITE, 'order', 'index.html'))
    with open(os.path.join(SITE, 'robots.txt'), 'w') as f:
        f.write('User-agent: *\nDisallow: /g/\n')
    with open(os.path.join(SITE, '_headers'), 'w') as f:
        f.write('/g/*\n  X-Robots-Tag: noindex\n  Referrer-Policy: no-referrer\n  Cache-Control: no-cache\n')

    today, live, expired = dt.date.today(), [], []
    for oid in sorted(os.listdir(ORDERS)) if os.path.isdir(ORDERS) else []:
        path = os.path.join(ORDERS, oid, 'order.json')
        page = os.path.join(ORDERS, oid, 'delivery', 'online.html')
        if not (os.path.exists(path) and os.path.exists(page)):
            continue
        order = load_order(oid)
        if dt.date.fromisoformat(order['online_until']) < today:
            expired.append(oid)
            continue
        dest = os.path.join(SITE, 'g', order['slug'])
        os.makedirs(dest)
        shutil.copy(page, os.path.join(dest, 'index.html'))
        live.append(oid)
    print(f'site: {len(live)} live gifts {live}' + (f', {len(expired)} expired and left out {expired}' if expired else ''))
    if args.dry_run:
        print(f'dry run: the site is in {SITE}, not deployed')
        return
    wrangler = shutil.which('wrangler') or shutil.which('wrangler.cmd')
    cmd = [wrangler or 'npx', *([] if wrangler else ['wrangler']), 'pages', 'deploy', SITE,
           '--project-name', config['project'], '--branch', 'main', '--commit-dirty=true']
    sys.exit(subprocess.call(cmd))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('import', help="turn the order form's text into orders/<id>/order.json")
    s.add_argument('file')
    s.add_argument('--id', help='order folder name (default: date and player name)')
    s.add_argument('--force', action='store_true', help='replace an existing order.json')
    s = sub.add_parser('build', help='make the delivery files for an order')
    s.add_argument('id')
    s = sub.add_parser('play', help='play a built order in the browser')
    s.add_argument('id')
    s.add_argument('--online', action='store_true', help='the encrypted online copy (asks for the password)')
    s.add_argument('--auto', action='store_true', help='autopilot: plays itself through')
    s.add_argument('--desktop', action='store_true', help='the desktop build instead of the browser')
    s = sub.add_parser('deploy', help='publish all live gifts to Cloudflare Pages')
    s.add_argument('--dry-run', action='store_true', help='build site/ but do not upload it')
    args = p.parse_args()
    {'import': cmd_import, 'build': cmd_build, 'play': cmd_play, 'deploy': cmd_deploy}[args.cmd](args)


if __name__ == '__main__':
    main()
