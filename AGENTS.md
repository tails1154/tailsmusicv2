# TailsMusic v2 — Agent Guide

## Entrypoint & runtime
- `player.py` runs as `#!/bin/python3` on Raspberry Pi OS. Must run from `/home/pi/mp3player/`.
- Hardcoded paths in code: `MUSIC_DIR = /home/pi/mp3player/songs`, `PLAYLIST_DIR = /home/pi/mp3player/playlists`, `sfx/`, `apps/` all under repo root.

## Config
- `config.json` maps button key codes (`okbutton`, `okbutton2`, `backbutton`, `skipbutton`) and `evtestname` (substring-matched against input device name).
- `.gitignore` lists `config.json` — it is intentionally **not** committed. Do not add it to a commit.

## Button navigation convention (all menus)
- `backbutton` → cycle BACK (left), `skipbutton` → cycle FORWARD (right), `okbutton`/`okbutton2` → select/confirm.
- Always implement menus via the `menu_nav()` helper in `player.py` for consistency.

## Lint & CI (no tests)
- **Ruff**: `uvx ruff check --output-format=github` (CI via `astral-sh/setup-uv@v7`).
- Rules in `pyproject.toml`: E, F, YTT, T10, ISC, G, PIE, RSE, PLC, PLE, RUF.
- Ignored: E501 (line-length), E402 (import-not-at-top), E701 (multi-stmt-colon), PLC0415 (import-outside-top-level).
- **No test framework**, no typechecker, no pre-commit hooks.

## App plugin system
- `apps/*.py` files must export a class `APP` with `__init__(self, dev, queue)`, `checkDaemon(self) -> bool`, and `start(self)`.
- The app `.py` is copied to `app.py`, then `import app as appModule` / `appModule.APP(dev, cmdq).start()`.
- If `checkDaemon()` returns `True`, the app runs in a `multiprocessing.Process` (background) and sets `daemonRunning = True` (affects whether `cmdq.process_Command()` is called in the main loop).
- `exampleApp.py` is the canonical template. `tools.py` provides `API(device)` for button polling and TTS.

## System dependencies (Raspberry Pi OS)
- `pulseaudio`, `pulseaudio-module-bluetooth`, `espeak-ng`, `evtest`, `python3-evdev`, `nmcli` (NetworkManager for WiFi).
- Captive portal hotspot: `hostapd`, `dnsmasq` (optional — only needed for the "Setup Hotspot" feature).
- Python: `pygame`, `evdev`, `pulsectl` (optional), `bleak` (optional), `vosk`/`sounddevice`/`numpy` (optional).
- The code uses `pip install --break-system-packages` for auto-install — do not replicate this pattern in new code.

## Code quirks & gotchas
- Many `try/except Exception` swallowing errors silently. Avoid this in new code.
- `os.system()` used for pip auto-install + restart. Prefer `subprocess.run()`.
- `shutil.rmtree("__pycache__")` on startup — stale cache is expected.
- `global daemonRunning` flag controls `cmdq.process_Command()` polling in the main event loop.
- `app.py` is deleted at startup (`os.remove("app.py")`) and after non-daemon apps finish. It is in `.gitignore`.
- `player.py` auto-advances to next song when `pygame.mixer.music.get_busy()` is false.
- `sys.exit()` is intentionally replaced with `os.system("killall -9 python3")` — this is a hard-kill pattern for the single-process embedded environment.

## Docs
- Doxygen: `./docs.sh` regenerates HTML docs (runs `doxygen`, copies `docs/html/*` to `docs/`, removes source).
- `push.sh` runs `docs.sh` before committing. The workflow is: `./docs.sh && git add . && git commit`.

## Architecture
- `player.py` — main event loop, Bluetooth input via `evdev`, playback via `pygame.mixer`, TTS via `espeak-ng`.
- `tools.py` — `API` helper class for app development (button polling wrappers).
- `wifi.py` — `scan_wifi()` / `connect_wifi()` using `nmcli`, `get_ip()` via `ip route`.
- `apps/pager.py`, `apps/pager_message.py` — optional pager system with external Node.js server + SQLite offline cache.
