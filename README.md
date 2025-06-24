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
sudo apt install -y pulseaudio pulseaudio-module-bluetooth espeak evtest python3-evdev
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
   source ~/.bashrc
   ```

---

## **5. Configure Button Controls**  
1. Identify your headphone buttons:  
   ```bash
   sudo evtest
   ```
   - Select your headphones from the list.  
   - Press buttons (Play/Pause, Next, etc.) and note the `(KEY_XXX)` codes (e.g., `KEY_PLAYCD`, `KEY_NEXTSONG`).  

2. Update `player.py`:  
   - Replace all `KEY_CDPLAY`/`KEY_CDPAUSE` with your noted codes.  

---

## **6. Add Music and Playlists**  
```bash
mkdir -p /home/pi/mp3player/songs
mkdir -p /home/pi/mp3player/playlists
```
- Place MP3 files in `songs/`.  
- Playlists are auto-generated or manually created via the script.  

---

## **7. Run TailsMusic**  
```bash
python3 /home/pi/mp3player/player.py
```

*(Optional: Auto-start on boot with `systemd`)*  
```bash
sudo cp /home/pi/mp3player/tailsmusic.service /etc/systemd/system/
sudo systemctl enable tailsmusic.service
sudo systemctl start tailsmusic.service
```

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
  Double-check `evtest` codes and update `player.py`.  

---

### **Done!**  
Your **TailsMusic** should now:  
✅ Auto-connect to Bluetooth headphones.  
✅ Respond to media buttons.  
✅ Announce actions via eSpeak.  
