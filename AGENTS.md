# TailsMusic v2 — Agent Guide

## Entrypoint

`player.py` is the sole entrypoint. Run with `python3 player.py`.

## Project structure

| Path | Purpose |
|---|---|
| `player.py` | Main loop: pygame audio, evdev button handler, all menus |
| `tools.py` | `tools.API` helper class for app developers |
| `wifi.py` | WiFi scan/connect via `nmcli` |
| `config.json` | Button keycode mappings + `evtestname` device name prefix |
| `apps/*.py` | Pluggable apps with class `APP(dev, queue)` + `checkDaemon() -> bool` + `start()` |
| `songs/` | MP3 files (gitignored) |
| `playlists/` | JSON playlist files (gitignored) |
| `sfx/` | 5 WAV/MP3 sound effects (pause, click, panel, dialup, bonk) |
| `bashrc` | Auto-start script for Raspberry Pi — also shows PulseAudio/Bluetooth pairing flow |

## Config (`config.json`)

- `evtestname` is matched as substring (not exact). Example: `"SIMOLIO"` matches `"SIMOLIO (AVRCP)"`.
- Button keys: `okbutton`, `okbutton2`, `skipbutton`, `backbutton` — values are evdev `KEY_*` codes.

## Navigation convention (menus)

- **Back button** = cycle left/back through options
- **Skip button** = cycle right/forward
- **OK/OK2** = select current option
- All menus use `menu_nav()` in `player.py`.

## App system

- Apps live in `apps/*.py`. Copied to `app.py`, then `import app as appModule` at runtime.
- Each app must define class `APP` with:
  - `__init__(self, dev, queue)` — `dev` is evdev `InputDevice`, `queue` is `CommandQueue`
  - `checkDaemon(self) -> bool` — `True` = run in background process, `False` = run interactively
  - `start(self)` — app logic
- Daemon apps get a `multiprocessing.Process`; interactive apps block the main thread.
- `tools.API(dev)` provides helpers: `speak()`, `checkLeft/Right/PlayPause()`, `getEvent()`.

## Button layout in main loop

| Button | When playing | When paused |
|---|---|---|
| OK/OK2 | Play/pause toggle | Play/pause toggle |
| Skip | Next track | Open shutdown menu |
| Back | Previous track | Open song menu |

## Linting & CI

- Only CI check: `uvx ruff check --output-format=github`
- Lint config in `pyproject.toml` with Ruff (selects E, F, YTT, T10, ISC, G, PIE, RSE, PLC, PLE, RUF; ignores E501, E402, E701, PLC0415).
- **No tests exist** — no test framework, no test directory.

## System dependencies

`apt: pulseaudio pulseaudio-module-bluetooth espeak-ng evtest python3-evdev`

Python deps in `requirements.txt`: `pygame evdev pulsectl bleak vosk sounddevice numpy`

On missing `pulsectl`/`bleak`, `player.py` auto-installs with `--break-system-packages` then exits.

## Hardcoded paths

- Music: `/home/pi/mp3player/songs/`
- Playlists: `/home/pi/mp3player/playlists/`
- SFX: `/home/pi/mp3player/sfx/`
- `config.json` read from current working directory

## Docs generation

`./docs.sh` runs Doxygen then flattens `docs/html/` into `docs/`.

## `config.json` is gitignored

The repo's `config.json` is in `.gitignore`. A default is present in the working tree but won't be committed.
