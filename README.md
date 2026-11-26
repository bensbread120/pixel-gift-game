# pixel-gift-game

A personalised gift you can play: a small top-down adventure that works like a playable card. The hero is woken by their pet, follows it (very unreliably) through a village past six memories, and finds their partner waiting with a picnic and a message. Each gift swaps in its own names, words, colours and photos.

The code in this repo carries a **placeholder story** (Alex, Sam and Biscuit the dog) and drawn placeholder memory cards. Real orders never get committed here.

It's written in C++20 with [SDL3](https://libsdl.org), [SDL3_image](https://github.com/libsdl-org/SDL_image) and [glm](https://github.com/g-truc/glm). It runs as a desktop app and in the browser (phone or laptop) through [Emscripten](https://emscripten.org), and deploys to Cloudflare Pages: one encrypted page per gift, behind a password.

## Controls

| | Keyboard | Touch (phones/tablets) |
|---|---|---|
| Start / next line of text | any key / Space, Enter, Z | tap anywhere |
| Move | arrow keys or WASD | d-pad, bottom left |
| Look at things | Space / Enter / Z / E | **A** button, bottom right |
| Back a page in the final message | Left / Backspace | tap the left side of the screen, or d-pad left |

The touch buttons appear after the first touch and hide again when a key is pressed. Phones play best in landscape.

**Testing shortcuts:** `1` toggles debug view (solid cells, the hero's collider, beat number). In debug view, `N` skips to the next part of the story and `F` turns on the autopilot (the hero follows the pet and taps through the text). The desktop build also takes `--start <label>` (`bedroom`, `living`, `village`, `stop1` … `stop6`, `field`, `ending`) and `--auto` on the command line, `--assets <dir>` to play a gift's assets (such as `orders/<id>/assets`) instead of the template's, and `--shot <file.png> [seconds]` saves a screenshot of the scene without the UI (after 1.5 s by default) and quits, which is handy for checking art changes. In the browser, `?start=<label>` and `?auto` do the same.

## Making a gift (an order, start to finish)

One build of the game serves every gift. A gift is a folder of assets: the template's art recoloured, its memory cards, and `gift.txt` with its names and words. `tools/gift.py` makes that folder from an order and injects it into a copy of the web build.

1. **The buyer fills in the order form** at `/order/` on the site (`web/order/index.html`). It sends nothing: it makes a block of text that they paste into an Etsy message. Photos (for the *With photos* package) come attached to the same message.
2. **Import it.** Save the message text to a file, then:
   ```bash
   tools/.venv/Scripts/python tools/gift.py import message.txt
   ```
   This writes `orders/<date>-<name>/order.json`, with the gift's link and password, and warns about anything the game can't draw (emoji, accents) or that's too long. For photos, save them as `orders/<id>/photos/memory1.jpg` … `memory6.jpg`. A crop per photo (`"crops": {"memory1": [0.1, 0.2, 0.9, 0.9]}`) zooms in on the people.
3. **Build it**, and again after any fix to `order.json`:
   ```bash
   tools/.venv/Scripts/python tools/gift.py build <id>
   ```
   Output in `orders/<id>/delivery/`: `<Title>.html` (the offline copy: one file that opens from disk, no password), `online.html` (the same, encrypted), `card.png` (a printable A6 card with a QR code that opens the game already unlocked) and `message.txt` (the Etsy delivery message).
4. **Play it through** before delivering: `gift.py play <id> --auto` (autopilot), `--online` for the password page, `--desktop` for the native build.
5. **Deploy**: `gift.py deploy` publishes every gift that's still within its two years, plus the order form, to Cloudflare Pages (see *Deploying*).
6. **Deliver** on Etsy: send `message.txt` with the offline copy and the card attached. Then delete the buyer's photos (`orders/<id>/photos/`).

`orders/` and `site/` hold buyers' names, words and photos, so they're never committed. Back them up somewhere private: the password and link of every live gift are in `orders/<id>/order.json`.

**What a buyer can choose** is in `tools/looks.py` (skin, hair, outfit and trousers for the two people, a coat for the dog), mirrored in the order form. Each choice is a palette swap of the drawn characters, so a new option is one line in each. The player always has long hair and a dress, the partner short hair and trousers, and the pet is a dog: other bodies need new sprites in `tools/art_chars.py`. Text limits (what fits on screen) are `LIMITS` in `tools/gift.py`, also mirrored in the form.

## Project layout

- **`sdl3-demo/`** holds the game source. The name is historical, from the demo the game grew out of.
  - `story.h`: **the story template**: every line of dialogue, the things you can inspect, and the order it all happens in. `{hero}`, `{partner}` and `{pet}` are filled in at startup from `assets/gift.txt`, which also holds the title, dedication, memory captions, long message and final line.
  - `sdl3-demo.cpp`: the game. It covers characters, the pet's guiding, the story director, drawing and input, and uses SDL's callback entry points so the same code runs natively and in the browser.
  - `world.h`: map loading, tile choice, collision and the pet's route-finding. The map legend is at the top.
  - `ui.h`: the dialogue box, memory cards, the paged message, and the title card.
  - `input.h`: keyboard/touch input and the on-screen touch controls.
  - `art_gen.h`: tile indices and sprite list, **generated** by `tools/make_art.py`.
- **`assets/`** holds the game's files, all generated: `tiles.png`, `sprites/`, `memories/`, `maps/`. The desktop build copies them next to the exe. The web build carries none: `tools/gift.py` injects a gift's own copy.
- **`tools/`** has Python scripts that draw all the art and build the maps (see below).
- **`art-src/photos/`** holds memory photos (`memory1.jpg` … `memory6.jpg`) for a gift. It **isn't committed**; missing photos get a drawn placeholder card.

- **`art-src/sprites/`** holds hand-edited sprites that replace the drawn ones (see below).
- **`assets/gift.txt`**: the placeholder gift's names and words. Each order gets its own, written by `tools/gift.py`.
- **`web/shell.html`** is the page wrapped around the web build. It also holds the password gate and writes a gift's assets into the game's filesystem.
- **`web/order/index.html`** is the buyer's order form; **`web/site-index.html`** the site's front page.
- **`tools/gift.py`** turns an order into a delivered gift (see *Making a gift*). `tools/looks.py` has the colour choices.

## Changing the story, art and maps

**Words:** a gift's words are in its `gift.txt` (for an order, edit `order.json` and rebuild it). The dialogue everyone shares is in `sdl3-demo/story.h`. The built-in font is plain ASCII, so use straight quotes (`'`, `"`) and no emoji; `gift.py` cleans buyers' text.

**Art and maps** are drawn by code, so they can be tweaked and regenerated at any time. The scripts need Python 3 and Pillow, installed into a local virtual environment once:

```bash
python -m venv tools/.venv
tools/.venv/Scripts/python -m pip install -r tools/requirements.txt     # Windows
# tools/.venv/bin/python -m pip install -r tools/requirements.txt       # Linux/macOS
```

Then regenerate and rebuild:

```bash
tools/.venv/Scripts/python tools/make_art.py    # assets/tiles.png, sprites/, memories/ + sdl3-demo/art_gen.h
tools/.venv/Scripts/python tools/make_maps.py   # assets/maps/*.txt
```

- `tools/art_chars.py`: the hero, partner and pet, as text pixel grids where one character is one pixel. Change colours in the palettes at the top.
- `tools/art_world.py`: ground tiles, props and landmarks.
- `tools/make_art.py`: also turns `art-src/photos/memoryN.*` into the pixel-art memory cards, and draws a placeholder card for any memory without a photo. `CROPS` zooms in on a photo.
- `tools/make_maps.py`: the bedroom and living room are drawn by hand as text grids. The village is laid out with helpers: clearings, the route with its grassy margins (how far the hero can stray), the stream, landmarks, and markers for the pet's stops.
- **Hand-edited sprites** go in `art-src/sprites/`. A PNG there named after a sprite (for example `pet_sit.png`) is used in place of the drawn one, so re-running `make_art.py` never overwrites it. These files are at art resolution, half the in-game size, so one pixel is one art pixel; `make_art.py` scales them up 2x. To get a starting copy of the current art, run `tools/.venv/Scripts/python tools/make_art.py --export pet_sit hero_walk_down`. A strip's width must divide evenly into its frame count (listed in `sdl3-demo/art_gen.h`). Otherwise any size works: characters are drawn bottom-centred on their tile, so a taller or wider sprite just sticks out further. Keep `.aseprite` source files next to the PNGs if you like, since only the `.png` is read.
- `tools/preview.py`: draws a contact sheet of the sprites for checking, e.g. `tools/.venv/Scripts/python tools/preview.py make_art.preview_sprites sheet.png 4`, run from `tools/`.

## Native (desktop) build

You need a C++20 compiler and **CMake 3.24+**.

- **Windows:** Visual Studio 2022 or newer with the *Desktop development with C++* workload.
- **Linux:** GCC 13+ or Clang 17+, plus SDL's build dependencies (see below).

The first configure downloads SDL3 3.4.14, SDL3_image 3.4.4 and glm 1.0.3 and builds them, which takes a few minutes. If CMake can find installed copies of these libraries it uses them instead, which is much faster.

### Windows

```powershell
# Fast: use prebuilt SDL dev packages (SDL3-devel-3.4.14-VC.zip and
# SDL3_image-devel-3.4.4-VC.zip from the SDL release pages, extracted to C:\dev)
cmake -S . -B build -D CMAKE_PREFIX_PATH="C:/dev/SDL3-3.4.14;C:/dev/SDL3_image-3.4.4;C:/dev/glm-1.0.3-VC"
# ...or drop the -D to download and build them instead
cmake --build build
.\build\sdl3-demo\Debug\sdl3-demo.exe
```

Add `--config Release` to the build command for an optimised build in `build\sdl3-demo\Release\`.

In Visual Studio, use **File → Open → Folder…** on the repo root, pick the **x64 Debug** preset, choose **sdl3-demo.exe** as the startup item and press F5. To use the prebuilt libraries there, add `CMAKE_PREFIX_PATH` to a preset in a `CMakeUserPresets.json` (not committed).

### Linux

```bash
sudo apt install build-essential cmake ninja-build pkg-config \
  libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxfixes-dev libxi-dev \
  libxss-dev libxtst-dev libxkbcommon-dev libwayland-dev libdecor-0-dev \
  libegl1-mesa-dev libgl1-mesa-dev libgles2-mesa-dev libdrm-dev libgbm-dev \
  libasound2-dev libpulse-dev libpipewire-0.3-dev libdbus-1-dev libudev-dev

cmake -S . -B build -G Ninja -D CMAKE_BUILD_TYPE=Debug
cmake --build build
./build/sdl3-demo/sdl3-demo
```

## Web build (Emscripten)

### 1. Install emsdk (once)

Use the same version as CI (6.0.13):

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install 6.0.13      # emsdk.bat on Windows
./emsdk activate 6.0.13
```

### 2. Build

Load the Emscripten environment in each new terminal, then configure with `emcmake`:

```bash
# Linux/macOS/Git Bash
source /path/to/emsdk/emsdk_env.sh
# Windows PowerShell:  C:\path\to\emsdk\emsdk_env.ps1   (cmd: emsdk_env.bat)

emcmake cmake -S . -B build-web -G Ninja     # Ninja or Makefiles; not a Visual Studio generator
cmake --build build-web
```

On Windows, Ninja comes with Visual Studio. If `ninja` isn't on your PATH, add `C:\Program Files\Microsoft Visual Studio\<version>\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja`, or use a *Developer PowerShell for VS*.

The web build always downloads and statically links its libraries, so it never picks up system packages. It defaults to Release. The output is one file, `build-web/sdl3-demo/index.html` (about 1.3 MB), with the wasm embedded (`-sSINGLE_FILE`) and **no assets**: it's the same for every gift, and on its own it only says it has no gift in it. Changing the code or the shell triggers a relink on the next build.

### 3. Test locally

Build a gift into it first. `tools/sample-order.txt` is a made-up order (with an emoji and curly quotes, to test the clean-up): `gift.py import tools/sample-order.txt --id sample`, then `gift.py build sample`. Then open the offline copy straight from disk, or play it with `tools/gift.py play <id>`, which serves it on localhost. `?auto` plays it through by itself.

To try it on your phone, make sure the phone is on the same Wi-Fi and serve the delivery folder with `python -m http.server 8000 --bind 0.0.0.0`. Then open `http://<your-PC's-LAN-IP>:8000/<file>.html`. Windows may ask to let Python through the firewall. The password page needs https (or localhost) to unlock, so test it on the phone after deploying. If you want to test touch on desktop, Chrome DevTools' device toolbar (Ctrl+Shift+M) emulates it.

## Deploying

The site is static, on **Cloudflare Pages** (free plan), project and address in `tools/deploy.json`. `tools/gift.py deploy` builds `site/` and uploads it with `wrangler pages deploy`:

| Path | What |
|---|---|
| `/` | a short front page (`web/site-index.html`) |
| `/order/` | the order form |
| `/g/<slug>/` | one gift, encrypted, for each order still within its two years |

**How the password works:** there's no server code. Each gift's page holds its assets encrypted with AES-GCM, with a key made from the password (PBKDF2-SHA256, 300,000 rounds). The page asks for the password and decrypts in the browser, so Cloudflare only ever stores ciphertext, and the same file works on any static host. The slug is random (10 characters), so a gift can't be found without its link, and `robots.txt` and `X-Robots-Tag` keep gifts out of search engines. The QR code on the card carries the password after `#`, which browsers never send to the server, so scanning opens the game straight away. A correct password is remembered on that device.

The passwords are two words and a number, chosen to be easy to type on a phone. That's enough on top of a secret link for a gift, but not for anything sensitive.

**Every deploy is the whole site:** Pages replaces the previous deploy, so `deploy` always rebuilds `site/` from every order in `orders/`. Keep `orders/` (it's not in git). Gifts past their `online_until` date are left out at the next deploy.

**First time:** `npx wrangler login`, then `npx wrangler pages project create <name> --production-branch main`, and put the name and its `https://<name>.pages.dev` address in `tools/deploy.json` before building any orders (the address goes into each card's QR code).

## Notes for adding content

- **Images:** SDL_image is built with PNG support only, to keep the web build small. Everything in `assets/` is PNG or text.
- **Audio:** browsers keep audio muted until the page has had a tap, click or key press. The title screen provides that gesture, and SDL resumes its audio automatically after it. Adding sound needs `SDL_INIT_AUDIO` (plus SDL_mixer or `SDL_LoadWAV`). The game has no audio yet.
- **New source files:** add headers and `.cpp` files to `add_executable` in `sdl3-demo/CMakeLists.txt`.
- **Frame rate:** game logic uses delta time (capped at 50 ms per frame), so it runs the same at 60 Hz, 120 Hz, or after the tab has been hidden.
