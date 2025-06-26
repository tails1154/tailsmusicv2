# TailsMusicv2
better than v1, that's for sure!

ai "enhanced" instructions below




# **TailsMusic v2 Setup Guide**  
*A headless MP3 player for Raspberry Pi with Bluetooth headphone control*  

### **Prerequisites**  
- Raspberry Pi OS (Debian-based)  
- Bluetooth headphones (tested with SIMOLIO)  
- Basic terminal knowledge  

---

## **1. Install the Project**  
```bash
cd /home/pi
git clone https://github.com/tails1154/tailsmusicv2 mp3player
cd mp3player
```

*(Optional: Symlink instead of renaming)*  
```bash
ln -s /home/pi/tailsmusicv2 /home/pi/mp3player
```

---

## **2. Pair Bluetooth Headphones**  
1. Find your headphones’ MAC address:  
   ```bash
   sudo bluetoothctl scan le
   ```
   - Note the MAC address (e.g., `AA:BB:CC:DD:EE:FF`).  

2. Pair and trust the device:  
   ```bash
   sudo bluetoothctl pair AA:BB:CC:DD:EE:FF
   sudo bluetoothctl trust AA:BB:CC:DD:EE:FF
   ```

---

## **3. Install Dependencies**  
```bash
sudo apt update
sudo apt install -y pulseaudio pulseaudio-module-bluetooth espeak-ng evtest python3-evdev
```

---

## **4. Configure PulseAudio**  
1. Restart PulseAudio:  
   ```bash
   pulseaudio --kill && pulseaudio --start
   ```

2. Find your Bluetooth sink:  
   ```bash
   pactl list short sinks
   ```
   - Note the `bluez_sink.XX_XX_XX_XX_XX_XX` address.  

3. Update `bashrc` in the repo:  
   - Replace all `bluez_sink.XX_XX_XX_XX_XX_XX` references with your sink.  
   - Update the `bluetoothctl connect` command with your headphones’ MAC.  

4. Apply the new `bashrc`:  
   ```bash
   cp ~/.bashrc ~/.bashrc.bak  # Backup
   cp bashrc ~/.bashrc          # Overwrite
   ```

---

## **5. Configure Button Controls**  
1. Identify your headphone buttons:  
   ```bash
   sudo evtest
   ```
   - Select your headphones from the list.  
   - Press buttons (Play/Pause, Next, etc.) and note the `(KEY_XXX)` codes (e.g., `KEY_PLAYCD`, `KEY_NEXTSONG`).  

2. Update `config.json`:  
   - Replace the codes with the ones you noted down.
   - Replace the "evtestname" field with the name of the device you selected in evtest. (example name below)

Example name:
```
$ evtest
No device specified, trying to scan all of /dev/input/event*
Available devices:
/dev/input/event0:	Dell KB216 Wired Keyboard
/dev/input/event1:	etc
/dev/input/event2:	vc4-hdmi
/dev/input/event5:	SIMOLIO (AVRCP)
                         ^
			 |  This is our bluetooth headphones. Yours will be different.
```

The config file checks if that json text is INCLUDED in the device name, so instead of putting `SIMOLIO (AVRCP)`, I put just `SIMOLIO`


---

## **6. Add Music and Playlists**  
```bash
mkdir -p /home/pi/mp3player/songs
mkdir -p /home/pi/mp3player/playlists
```
- Place MP3 files in `songs/`.  
- Playlists are auto-generated or manually created via the script.  

---

## **7. Reboot**  


Your system should auto start tailsmusic when you log in (after a short delay)

---

## **Troubleshooting**  
- **Bluetooth not connecting?**  
  Run `bluetoothctl` and ensure the device is paired/trusted:  
  ```bash
  connect AA:BB:CC:DD:EE:FF
  ```

- **No sound?**  
  Check PulseAudio sinks:  
  ```bash
  pacmd list-sinks | grep -e 'name:' -e 'index'
  ```

- **Buttons not working?**  
  Double-check `evtest` codes and update `config.json`.  

---

### **Done!**  
Your **TailsMusic** should now:  
✅ Auto-connect to Bluetooth headphones.  
✅ Respond to media buttons.  
✅ Announce actions via eSpeak.  



# TailsMusic Control Guide

## Main Controls
| Button          | Action                          |
|-----------------|---------------------------------|
| **Play/Pause**  | Toggle playback pause           |
| **Next Track**  | Skip to next song               |
| **Previous**    | Go to previous song             |
| **Next (Hold)** | Open shutdown menu when paused  |
| **Previous**    | Tell you the date/time when paused |

## Shutdown Menu
*Navigate with Previous/Play, select with Next button*

| Option           | Functionality                              |
|------------------|-------------------------------------------|
| Playlists        | Enter playlist management                 |
| Random Song      | Play a random track                       |
| Manual Text to speech       | Type custom text-to-speech message        |
| Rescan Songs     | Reload music library                      |
| Connect to WiFi  | Configure WiFi connection                 |
| Get IP           | Announce current IP address               |
| Open App         | Display a list of apps in apps/ and lets you select one to run |
| Shut Down        | Power off the system                      |
| Back             | Return to playback                        |

## Playlist Management
### Main Playlist Menu
- **Create**: Make a new playlist
- **[Playlist Name]**: Manage existing playlist
- **Back**: Return to shutdown menu

### Playlist Actions
| Option | Functionality                              |
|--------|-------------------------------------------|
| Play   | Play all songs in playlist                |
| Delete | Remove playlist (requires confirmation)   |
| Back   | Return to playlist list                   |

### Creating Playlists
1. Select **Add song**
2. Browse songs with **Previous/Next**
3. Press **Next** to add song
4. Choose **Finish** to save playlist

## WiFi Setup
1. Select network with **Previous/Next**
2. Enter password using character selector:
   - Navigate characters with **Previous/Next**
   - Select with **Next**
   - **space**: Add space
   - **Done**: Confirm password

## Manual TTS
1. Select letters with **Previous/Next**
2. Press **Next** to add character
3. Choose **Done** to speak message
