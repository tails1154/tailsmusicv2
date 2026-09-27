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

## Quick start

On a fresh Raspberry Pi OS installation:

```bash
sudo apt update
sudo apt install -y git
sudo git clone https://github.com/tails1154/tailsmusicv2 /home/pi/mp3player
cd /home/pi/mp3player
sudo bash setup.sh
```

The setup wizard installs system dependencies, installs Python packages, pairs a Bluetooth device, maps its buttons, creates the music directories, and optionally configures automatic startup.

Add music here:

```text
/home/pi/mp3player/songs/*.mp3
```

Then start the player manually when needed:

```bash
cd /home/pi/mp3player
python3 player.py
```

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
3. Connect to `TailsMusic-Setup` with password `tailsmusic`.
4. Open the captive portal and upload MP3 files or ZIP archives.

The hotspot is optional and only requires `hostapd` and `dnsmasq` when enabled.

## Audio reliability

TailsMusic prefers PulseAudio because it handles Bluetooth sinks more reliably than direct ALSA output. ALSA remains available as a fallback, with a 4096-sample buffer for underrun resistance. The startup template also applies a conservative 15% Bluetooth sink volume to prevent reconnects from restoring an unexpectedly loud level.

If there is no sound, check the live sink and stream:

```bash
pactl list short sinks
pactl list short sink-inputs
pactl get-default-sink
```

If the Bluetooth sink is muted or too loud, set it explicitly:

```bash
pactl set-sink-volume @DEFAULT_SINK@ 15%
pactl set-sink-mute @DEFAULT_SINK@ 0
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
| `setup.sh` | Interactive Raspberry Pi installer |
| `bashrc` | Bluetooth auto-connect startup template |

## Roadmap

- Add a small automated test suite around playlists, navigation, and configuration.
- Replace the shell-login startup loop with a supervised user service.
- Add playback metadata and album-art support to the portal.
- Make audio volume and Bluetooth identity fully configurable instead of template constants.

## License

TailsMusic is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
