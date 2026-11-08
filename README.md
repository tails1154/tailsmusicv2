# TailsMusic v2

> A tactile, headless music player for Raspberry Pi.

TailsMusic turns a Raspberry Pi into a dedicated Bluetooth MP3 player. It is designed for people who want physical controls, no screen, and a simple way to manage music from a phone or laptop.

![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-C51F2A?logo=raspberrypi)
![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)

## What it does

- Plays local MP3 files continuously through Bluetooth headphones or speakers.
- Supports media-button navigation for play/pause, next, previous, menus, and shutdown.
- Uses PulseAudio for Bluetooth playback with an ALSA fallback and a generous audio buffer.
- Provides playlists, shuffle, random playback, song management, and text-to-speech feedback.
- Includes a captive setup hotspot for uploading music and configuring Wi-Fi.
- Supports optional apps through a small plugin API.
- Includes Bluetooth device discovery, pairing, sink routing, and local-IP helpers.

## Install on Raspberry Pi OS / Debian

The installer supports Raspberry Pi OS and Debian-based Linux, with an optional
Kivy touchscreen frontend. Run from an existing checkout:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/tails1154/tailsmusicv2.git
cd tailsmusicv2
sudo bash setup.sh --with-kivy
```

Add `--service` to enable the **headless** player as a systemd **user service** (required to share the user's Bluetooth audio server). Add
`--start-service` to also start it immediately; use neither when you intend
to run only the touchscreen frontend. To preview commands without changing
anything, run `sudo bash setup.sh --dry-run --with-kivy`.

The new installer checks for errors instead of silently ignoring failures. It
uses a local `.venv/` with access to distro-installed Python packages and does
**not** use `--break-system-packages`, rewrite `.bashrc`, delete music, or
overwrite an existing `config.json`. Optional hotspot dependencies are
installed only with `--with-hotspot`. Set `--user USERNAME` if your regular
login username cannot be inferred from sudo.

### Start the Kivy touchscreen interface (Raspberry Pi OS Lite)

On a **local Raspberry Pi text console** (not an SSH session), the Kivy
frontend now selects SDL2's `kmsdrm` video backend by default. This draws
directly to the KMS/DRM display device and **does not require X11, Wayland,
a desktop, or `startx`**. SDL2 does not support the old SDL 1.2 `fbcon`
backend. The Pi must have an active DRM/KMS display, SDL2 compiled with
`kmsdrm`, and suitable `video`/`render` permissions. Log out and
back in after the installer adds those groups. <https://kivy.org/doc/stable/installation/installation-rpi.html>

Install once:

```bash
sudo bash setup.sh --with-kivy
```

Then log in on the Pi's local TTY and launch:

```bash
cd ~/tailsmusicv2
.venv/bin/python kivy_player.py
```

The app enters fullscreen automatically in direct-console mode. In an
existing desktop session it uses the available graphical backend instead.
You can override the default explicitly using `SDL_VIDEODRIVER`.
If SDL says `kmsdrm not available`, verify the installed SDL2 build,
active DRM nodes under `/dev/dri`, and that another display server is
not using the display; forcing the legacy `fbcon` driver will not fix it.

#### Desktop mode

```bash
cd tailsmusicv2
.venv/bin/python kivy_player.py
```

This standalone frontend offers a touch-friendly song list, play/pause,
previous/next, shuffle, refresh, and volume control. It reads `songs/` inside
the checkout. It supports local MP3, OGG, WAV and FLAC where the mixer codecs
are available. Bluetooth pairing and headset-button menus still belong to the
original headless `player.py`, not the touchscreen frontend.

**Do not run the touchscreen frontend and the headless player at the same time.**
If you enabled the service, first run `sudo systemctl stop tailsmusic`.
Audio requires a working user audio session; the installer enables systemd lingering for the selected user. Start PulseAudio or PipeWire-Pulse under that user and connect the Bluetooth headset. Re-log-in after setup so `input` and `audio` group membership takes effect. If Bluetooth playback is silent,
check `pactl list short sinks` under the same user that runs the player.

### Headless setup

```bash
sudo bash setup.sh --service
# Log in as the selected regular user (not root) before running:
systemctl --user start tailsmusic
journalctl --user -u tailsmusic -f
```

Edit `config.json` to match the Bluetooth input device (especially
`evtestname`), pair headphones with `bluetoothctl`, and place MP3s in
`songs/`. If you run without systemd: `.venv/bin/python player.py`.

Existing installations can re-run setup without clearing stored music and
playlists. The player and portal now resolve their runtime directories relative to the checkout, not `/home/pi/mp3player`, and saved playlists use portable filenames. The installer does not automatically migrate old shell-login startup
edits: remove any previous TailsMusic loop from `~/.bashrc` to avoid duplicate
players.

## Controls

Button names are configured in `config.json`; the default navigation convention is:

| Button | While playing | While paused |
| --- | --- | --- |
| OK / OK2 | Play or pause | Play or pause |
| Skip | Next song | Open the main menu |
| Back | Previous song | Open the song menu |

In menus, Back moves left, Skip moves right, and OK selects.

The main menu includes playlists, random playback, shuffle, Wi-Fi setup, the upload hotspot, Bluetooth controls, local IP, apps, AI mode, update, and shutdown.

## Upload music without SSH

1. Pause playback and open the main menu.
2. Select **Setup Hotspot**.
3. Connect to `TailsMusic-Setup` with your configured password (`tailsmusic` if unchanged; change it before sharing the hotspot).
4. Open the hotspot IP shown in logs, port `8080`, and upload MP3 files or ZIP archives. Automatic captive-portal redirection is not provided.

The hotspot is optional and uses NetworkManager's built-in shared Wi-Fi hotspot instead of killing hostapd/dnsmasq or changing global firewall chains. It requires Wi-Fi AP support and NetworkManager authorization for the player user. The setup portal runs on port 8080 on the hotspot IP (shown in the player logs), not port 80. Set `TAILSMUSIC_HOTSPOT_PASSWORD` to a private password before starting the player.

## Audio reliability

TailsMusic prefers PulseAudio because it handles Bluetooth sinks more reliably than direct ALSA output. ALSA remains available as a fallback, with a 4096-sample buffer for underrun resistance. TailsMusic does not change the Bluetooth sink volume; set that level using your headphones or PulseAudio controls.

If there is no sound, check the live sink and stream:

```bash
pactl list short sinks
pactl list short sink-inputs
pactl get-default-sink
```

If the Bluetooth sink is muted or too loud, set it explicitly:

```bash
pactl get-sink-volume @DEFAULT_SINK@
```

## Development

The project intentionally has no test framework yet. Before opening a pull request, run:

```bash
uvx ruff check --output-format=github
python3 -m compileall -q player.py tools.py wifi.py hotspot.py portal apps
```

The GitHub Actions workflow runs the same checks on every push and pull request.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and plugin contract. See [SECURITY.md](SECURITY.md) for responsible vulnerability reporting.

## Project layout

| Path | Role |
| --- | --- |
| `player.py` | Main event loop, playback, menus, Bluetooth, TTS, and apps |
| `tools.py` | App-development API for buttons and speech |
| `wifi.py` | NetworkManager Wi-Fi helpers |
| `hotspot.py` | Captive hotspot lifecycle |
| `portal/` | Upload/configuration web portal |
| `apps/` | Optional app plugins |
| `setup.sh`, `installer.py` | Reliable Debian/Raspberry Pi OS installer and service setup |\n| `kivy_player.py` | Optional touchscreen player |
| `bashrc` | Bluetooth auto-connect startup template |

## Roadmap

- Add a small automated test suite around playlists, navigation, and configuration.
- Replace the shell-login startup loop with a supervised user service.
- Add playback metadata and album-art support to the portal.
- Make audio volume and Bluetooth identity fully configurable instead of template constants.

## License

TailsMusic is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
