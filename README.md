# TailsMusic v2

A headless MP3 player for Raspberry Pi with Bluetooth headphone controls, WiFi setup, and a captive portal for song uploads.

## Quick Start

```bash
# On a fresh Raspberry Pi OS lite:
sudo apt install -y git
git clone https://github.com/tails1154/tailsmusicv2 /home/pi/mp3player
cd /home/pi/mp3player
sudo bash setup.sh
```

The setup script will guide you through:
- Installing all dependencies
- Pairing Bluetooth headphones
- Auto-start on boot (systemd service)
- Creating a default `config.json`



## Long Start



## Requirements

### Hardware
- Raspberry Pi (any model with WiFi)
- Bluetooth headphones with media buttons (tested with SIMOLIO)
- MicroSD card (8GB+)
- Power supply

### System Dependencies (installed by setup.sh)
```bash
sudo apt install -y \
  pulseaudio pulseaudio-module-bluetooth \
  espeak-ng evtest python3-evdev \
  network-manager \
  hostapd dnsmasq \
  python3-pip python3-pygame
```

### Python Packages (installed by setup.sh)
```bash
pip3 install --break-system-packages pygame evdev pulsectl bleak
```

## Manual Setup

### 1. Install the Project
```bash
cd /home/pi
git clone https://github.com/tails1154/tailsmusicv2 mp3player
cd mp3player
```

### 2. Pair Bluetooth Headphones
```bash
sudo bluetoothctl scan on          # Find your headphones MAC
sudo bluetoothctl pair AA:BB:CC:DD:EE:FF
sudo bluetoothctl trust AA:BB:CC:DD:EE:FF
sudo bluetoothctl connect AA:BB:CC:DD:EE:FF
```

### 3. Configure Button Controls
```bash
sudo evtest                        # Find your device and note button codes
```
Edit `config.json` to match your headphone's button codes and device name (e.g., `"evtestname": "SIMOLIO"` matches `SIMOLIO (AVRCP)`).

### 4. Add Music
Place `.mp3` files in `/home/pi/mp3player/songs/`.

### 5. Run
```bash
cd /home/pi/mp3player && python3 player.py
```

## Controls

| Button (when playing)      | Action         |
|----------------------------|----------------|
| **OK / OK2**               | Play/Pause     |
| **Skip**                   | Next track     |
| **Back**                   | Previous track |

| Button (when paused)       | Action                   |
|----------------------------|--------------------------|
| **Skip**                   | Open shutdown menu       |
| **Back**                   | Song menu (add to playlist) |

From the **shutdown menu** you can:
- Manage playlists
- Play random songs / shuffle
- Connect to WiFi
- **Start setup hotspot** (creates `TailsMusic-Setup` WiFi for uploading songs via web browser)
- Manage Bluetooth audio sinks
- Open apps from the `apps/` directory
- Update TailsMusic via git pull
- Shut down the Pi

## Captive Portal (Hotspot)

Select **Setup Hotspot** from the menu to create a WiFi network:

- **SSID:** `TailsMusic-Setup`
- **Password:** `tailsmusic`

Connect from any device — a captive portal opens automatically with:
- Upload MP3 files or ZIP folders
- Scan and connect to WiFi networks
- View system status

## Project Structure

| Path | Purpose |
|------|---------|
| `player.py` | Main music player (entrypoint) |
| `hotspot.py` | WiFi hotspot + captive portal control |
| `portal/` | Web server, HTML templates, CSS, JS |
| `wifi.py` | WiFi scanning/connection via nmcli |
| `tools.py` | API helper for app development |
| `apps/` | Plugin-based app system |
| `setup.sh` | One-shot Raspberry Pi setup script |
| `bashrc` | Bluetooth auto-connect template |
| `config.json` | Button code mappings (not committed) |
| `TailsFile` | Entrypoint marker (`./player.py`) |

## Troubleshooting

- **Bluetooth not connecting?** Run `bluetoothctl` and check the device is paired/trusted.
- **No sound?** Check PulseAudio sinks: `pactl list short sinks`
- **Buttons not working?** Re-run `sudo evtest` to confirm button codes and update `config.json`.
- **ALSA underrun errors?** The player sets a 2048-sample audio buffer. If you still see underruns, edit `player.py` and increase `buffer=4096` in the `pygame.mixer.pre_init()` call.
