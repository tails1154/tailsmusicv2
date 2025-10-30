# TailsMusicv2
better than v1, that's for sure!
mp3 player but uses bluetooth and headphone buttons to control

ai "enhanced" instructions below


## TODO

- ~~make it so you can interrupt the tts in some places~~

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
*(Note: If you arn't going to contibute, then you probably want to add --depth 1 to the end to not download the entire commit history)*

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

| Button                | Action                                                                                           |
|-----------------------|--------------------------------------------------------------------------------------------------|
| **OK / OK2**          | Play/Pause toggle                                                                                |
| **Skip**              | Next track                                                                                       |
| **Back**              | Previous track                                                                                   |
| **Skip (when paused)**| Open shutdown menu                                                                               |
| **Back (when paused)**| Speak current date and time                                                                      |

- **Button names** (“okbutton”, “okbutton2”, “skipbutton”, “backbutton”) are mapped in your `config.json` and may correspond to your headphone/media controls.

## Shutdown Menu  
*Navigating: Use Back/Skip to move, OK/OK2 to select.*

| Option                 | Functionality                                                                                    |
|------------------------|-------------------------------------------------------------------------------------------------|
| Playlists              | Enter playlist management                                                                       |
| Random Song            | Play a random track                                                                             |
| Update TailsMusic      | Pull latest code updates and reload the app                                                     |
| Manual Text to Speech  | Compose a custom TTS message using the buttons                                                  |
| Rescan Songs           | Reload the music library                                                                        |
| Connect to WiFi        | Configure WiFi connection (choose network, enter password with button navigation)               |
| Get local IP           | Announce current local IP address                                                               |
| Open App               | List and launch `.py` apps from the `apps/` directory                                           |
| Shut Down              | Power off the system                                                                            |
| Back                   | Return to playback                                                                              |

## Playlist Management

### Main Playlist Menu
- **Create**: Make a new playlist
- **[Playlist Name]**: Manage an existing playlist
- **Back**: Return to shutdown menu

### Playlist Actions

| Option  | Functionality                                                                                       |
|---------|----------------------------------------------------------------------------------------------------|
| Play    | Play all songs in playlist. Use Skip/Back to go to next/previous song in playlist.                 |
| Delete  | Remove playlist (requires confirmation via Skip/Back)                                              |
| Back    | Return to playlist list                                                                            |

#### While Playing a Playlist
- **Skip**: Next song in playlist
- **Back**: Previous song in playlist

### Creating Playlists
1. Select **Add song**
2. Browse songs with **Back/OK/OK2** (OK/OK2 moves up, Back moves down)
3. Press **Skip** to add song to playlist
4. Choose **Finish** (via Skip) to save playlist

## WiFi Setup
1. Select network with **Back/OK/OK2** buttons
2. Press **Skip** to choose
3. Enter password using character selector:
    - Navigate characters with **Back/OK/OK2**
    - Select character with **Skip**
    - **space**: Add space
    - **Done**: Confirm and connect

---

**Notes:**
- Button assignments can be customized in `config.json`.
- Long presses are not used; actions change depending on whether playback is paused or active.
- All menus, playlists, and WiFi setup are accessible/controllable via the defined buttons; no keyboard or mouse is required.

