# pixel-gift-game

A personalised gift you can play: a small top-down adventure that works like a playable card. The hero is woken by their pet, follows it (very unreliably) through a village past six memories, and finds their partner waiting with a picnic and a message. Each gift swaps in its own names, words, colours and photos.

The code in this repo carries a **placeholder story** (Alex, Sam and Biscuit the dog) and drawn placeholder memory cards. Real orders never get committed here.

It's written in C++20 with [SDL3](https://libsdl.org), [SDL3_image](https://github.com/libsdl-org/SDL_image) and [glm](https://github.com/g-truc/glm). It runs as a desktop app and in the browser (phone or laptop) through [Emscripten](https://emscripten.org), and will deploy to Cloudflare behind a password page (not set up yet).

## Controls

| | Keyboard | Touch (phones/tablets) |
|---|---|---|
| Start / next line of text | any key / Space, Enter, Z | tap anywhere |
| Move | arrow keys or WASD | d-pad, bottom left |
| Look at things | Space / Enter / Z / E | **A** button, bottom right |
| Back a page in the final message | Left / Backspace | tap the left side of the screen, or d-pad left |

The touch buttons appear after the first touch and hide again when a key is pressed. Phones play best in landscape.

**Testing shortcuts:** `1` toggles debug view (solid cells, the hero's collider, beat number). In debug view, `N` skips to the next part of the story and `F` turns on the autopilot (the hero follows the pet and taps through the text). The desktop build also takes `--start <label>` (`bedroom`, `living`, `village`, `stop1` … `stop6`, `field`, `ending`) and `--auto` on the command line, and `--shot <file.png> [seconds]` saves a screenshot of the scene without the UI (after 1.5 s by default) and quits, which is handy for checking art changes.

## Project layout

- **`sdl3-demo/`** holds the game source. The name is historical, from the demo the game grew out of.
  - `story.h`: **the story**. It has every line of dialogue, the memory captions, the things you can inspect, the final message, and the order it all happens in. Edit the words here.
  - `sdl3-demo.cpp`: the game. It covers characters, the pet's guiding, the story director, drawing and input, and uses SDL's callback entry points so the same code runs natively and in the browser.
  - `world.h`: map loading, tile choice, collision and the pet's route-finding. The map legend is at the top.
  - `ui.h`: the dialogue box, memory cards, the paged message, and the title card.
  - `input.h`: keyboard/touch input and the on-screen touch controls.
  - `art_gen.h`: tile indices and sprite list, **generated** by `tools/make_art.py`.
- **`assets/`** holds the game's files, all generated: `tiles.png`, `sprites/`, `memories/`, `maps/`. The desktop build copies them next to the exe, and the web build packs them into `index.data`.
- **`tools/`** has Python scripts that draw all the art and build the maps (see below).
- **`art-src/photos/`** holds memory photos (`memory1.jpg` … `memory6.jpg`) for a gift. It **isn't committed**; missing photos get a drawn placeholder card.
- **`art-src/sprites/`** holds hand-edited sprites that replace the drawn ones (see below).
- **`web/shell.html`** is the page wrapped around the web build.

## Changing the story, art and maps

**Words:** edit `sdl3-demo/story.h` and rebuild. The built-in font is plain ASCII, so use straight quotes (`'`, `"`) and no emoji.

**Art and maps** are drawn by code, so they can be tweaked and regenerated at any time. The scripts need Python 3 and Pillow, installed into a local virtual environment once:

```bash
python -m venv tools/.venv
tools/.venv/Scripts/python -m pip install pillow     # Windows
# tools/.venv/bin/python -m pip install pillow       # Linux/macOS
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

The web build always downloads and statically links its libraries, so it never picks up system packages. It defaults to Release. Output in `build-web/sdl3-demo/`:

| File | What |
|---|---|
| `index.html` | the page (from `web/shell.html`) |
| `index.js` | Emscripten loader/runtime |
| `index.wasm` | the compiled game |
| `index.data` | the packed `assets/` folder, mounted at `/assets` |

Changing the code, the shell or any asset triggers a relink on the next build.

### 3. Test locally

Opening `index.html` straight from disk won't work, because browsers refuse to load the `.wasm` and `.data` files from `file://`. Serve the folder instead:

```bash
cd build-web/sdl3-demo
python3 -m http.server 8000      # then open http://localhost:8000
# or:  emrun --no_browser --port 8000 .
```

To try it on your phone, make sure the phone is on the same Wi-Fi and serve with `python3 -m http.server 8000 --bind 0.0.0.0`. Then open `http://<your-PC's-LAN-IP>:8000`. Windows may ask to let Python through the firewall. If you want to test touch on desktop, Chrome DevTools' device toolbar (Ctrl+Shift+M) emulates it.

## Deploying

Not set up yet. The plan is Cloudflare Pages or Workers, with a password page in front of every file (including `index.data`, which holds the memory photos), and one deploy per gift.

## Notes for adding content

- **Images:** SDL_image is built with PNG support only, to keep the web build small. Everything in `assets/` is PNG or text.
- **Audio:** browsers keep audio muted until the page has had a tap, click or key press. The title screen provides that gesture, and SDL resumes its audio automatically after it. Adding sound needs `SDL_INIT_AUDIO` (plus SDL_mixer or `SDL_LoadWAV`). The game has no audio yet.
- **New source files:** add headers and `.cpp` files to `add_executable` in `sdl3-demo/CMakeLists.txt`.
- **Frame rate:** game logic uses delta time (capped at 50 ms per frame), so it runs the same at 60 Hz, 120 Hz, or after the tab has been hidden.
